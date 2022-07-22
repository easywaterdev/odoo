###################################################################################
# 
#    Copyright (C) Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

import logging
import threading

from odoo import SUPERUSER_ID, Command, api, models, registry
from odoo.tools.misc import clean_context, split_every

_logger = logging.getLogger(__name__)


##############################
# Mail.Thread
##############################
class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def unlink(self):
        self.env["mail.message"].sudo().with_context(active_test=False).search(
            [("model", "=", self._name), ("res_id", "in", self.ids)]
        )
        return super(MailThread, self).unlink()

    # -- Notify partner
    def _notify_record_by_email(
        self,
        message,
        recipients_data,
        msg_vals=False,
        model_description=False,
        mail_auto_delete=True,
        check_existing=False,
        force_send=True,
        send_after_commit=True,
        **kwargs
    ):

        # Cetmix. Sent from Messages Easy composer?
        if not self._context.get("default_wizard_mode", False) in ["quote", "forward"]:
            return super(MailThread, self)._notify_record_by_email(
                message,
                recipients_data,
                msg_vals,
                model_description,
                mail_auto_delete,
                check_existing,
                force_send,
                send_after_commit,
                **kwargs
            )
        # Cetmix. Get signature location
        signature_location = self._context.get("signature_location", False)
        if signature_location == "a":  # Regular signature location
            return super(MailThread, self)._notify_record_by_email(
                message,
                recipients_data,
                msg_vals,
                model_description,
                mail_auto_delete,
                check_existing,
                force_send,
                send_after_commit,
                **kwargs
            )

        partners_data = [r for r in recipients_data if r["notif"] == "email"]
        if not partners_data:
            return True

        model = msg_vals.get("model") if msg_vals else message.model
        model_name = model_description or (
            self._fallback_lang().env["ir.model"]._get(model).display_name
            if model
            else False
        )  # one query for display name
        recipients_groups_data = self._notify_classify_recipients(
            partners_data, model_name, msg_vals=msg_vals
        )

        if not recipients_groups_data:
            return True
        force_send = self.env.context.get("mail_notify_force_send", force_send)

        template_values = self._notify_prepare_template_context(
            message, msg_vals, model_description=model_description
        )  # 10 queries

        # Cetmix. Replace signature
        if signature_location:  # Remove signature, we don't need it in values
            signature = template_values.pop("signature", False)
        else:
            signature = False

        email_layout_xmlid = (
            msg_vals.get("email_layout_xmlid")
            if msg_vals
            else message.email_layout_xmlid
        )
        template_xmlid = (
            email_layout_xmlid
            if email_layout_xmlid
            else "mail.message_notification_email"
        )
        try:
            base_template = self.env.ref(
                template_xmlid, raise_if_not_found=True
            ).with_context(
                lang=template_values["lang"]  # noqa
            )  # noqa
        except ValueError:
            _logger.warning(
                "QWeb template %s not found when sending notification emails."
                " Sending without layouting." % (template_xmlid)
            )
            base_template = False

        mail_subject = message.subject or (
            message.record_name and "Re: %s" % message.record_name
        )  # in cache, no queries
        # Replace new lines by spaces to conform to email headers requirements
        mail_subject = " ".join((mail_subject or "").splitlines())
        # prepare notification mail values
        base_mail_values = {
            "mail_message_id": message.id,
            "mail_server_id": message.mail_server_id.id,
            "auto_delete": mail_auto_delete,
            # due to ir.rule, user have no right to access parent
            # message if message is not published
            "references": message.parent_id.sudo().message_id
            if message.parent_id
            else False,
            "subject": mail_subject,
        }
        base_mail_values = self._notify_by_email_add_values(base_mail_values)

        SafeMail = (
            self.env["mail.mail"].sudo().with_context(clean_context(self._context))
        )
        SafeNotification = (
            self.env["mail.notification"]
            .sudo()
            .with_context(clean_context(self._context))
        )
        emails = self.env["mail.mail"].sudo()

        notif_create_values = []
        recipients_max = 50
        for recipients_group_data in recipients_groups_data:
            # generate notification email content
            recipients_ids = recipients_group_data.pop("recipients")
            render_values = {**template_values, **recipients_group_data}

            if base_template:
                mail_body = base_template._render(
                    render_values, engine="ir.qweb", minimal_qcontext=True
                )
            else:
                mail_body = message.body

            # Cetmix. Put signature before quote?
            if signature and signature_location == "b":
                quote_index = mail_body.find("<blockquote")
                if quote_index:
                    mail_body = "".join(
                        (mail_body[:quote_index], signature, mail_body[quote_index:])
                    )

            mail_body = self.env["mail.render.mixin"]._replace_local_links(mail_body)

            # create email
            for recipients_ids_chunk in split_every(recipients_max, recipients_ids):
                recipient_values = self._notify_email_recipient_values(
                    recipients_ids_chunk
                )
                email_to = recipient_values["email_to"]
                recipient_ids = recipient_values["recipient_ids"]

                create_values = {
                    "body_html": mail_body,
                    "subject": mail_subject,
                    "recipient_ids": [Command.link(pid) for pid in recipient_ids],
                }
                if email_to:
                    create_values["email_to"] = email_to
                create_values.update(
                    base_mail_values
                )  # mail_message_id, mail_server_id, auto_delete, references, headers
                email = SafeMail.create(create_values)

                if email and recipient_ids:
                    tocreate_recipient_ids = list(recipient_ids)
                    if check_existing:
                        existing_notifications = (
                            self.env["mail.notification"]
                            .sudo()
                            .search(
                                [
                                    ("mail_message_id", "=", message.id),
                                    ("notification_type", "=", "email"),
                                    ("res_partner_id", "in", tocreate_recipient_ids),
                                ]
                            )
                        )
                        if existing_notifications:
                            tocreate_recipient_ids = [
                                rid
                                for rid in recipient_ids
                                if rid
                                not in existing_notifications.mapped(
                                    "res_partner_id.id"
                                )
                            ]
                            existing_notifications.write(
                                {
                                    "notification_status": "ready",
                                    "mail_mail_id": email.id,
                                }
                            )
                    notif_create_values += [
                        {
                            "mail_message_id": message.id,
                            "res_partner_id": recipient_id,
                            "notification_type": "email",
                            "mail_mail_id": email.id,
                            "is_read": True,  # discard Inbox notification
                            "notification_status": "ready",
                        }
                        for recipient_id in tocreate_recipient_ids
                    ]
                emails |= email

        if notif_create_values:
            SafeNotification.create(notif_create_values)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.currentThread(), "testing", False)
        if (
            force_send
            and len(emails) < recipients_max
            and (not self.pool._init or test_mode)
        ):
            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                email_ids = emails.ids
                dbname = self.env.cr.dbname
                _context = self._context

                @self.env.cr.postcommit.add
                def send_notifications():
                    db_registry = registry(dbname)
                    with db_registry.cursor() as cr:
                        env = api.Environment(cr, SUPERUSER_ID, _context)
                        env["mail.mail"].browse(email_ids).send()

            else:
                emails.send()

        return True
