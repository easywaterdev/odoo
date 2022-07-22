###################################################################################
# 
#    Copyright (C) Cetmix OÜ
#
#   Odoo Proprietary License v1.0
# 
#   This software and associated files (the "Software") may only be used (executed,
#   modified, executed after modifications) if you have purchased a valid license
#   from the authors, typically via Odoo Apps, or if you have received a written
#   agreement from the authors of the Software (see the COPYRIGHT file).
# 
#   You may develop Odoo modules that use the Software as a library (typically
#   by depending on it, importing it and using its resources), but without copying
#   any source code or material from the Software. You may distribute those
#   modules under the license of your choice, provided that this license is
#   compatible with the terms of the Odoo Proprietary License (For example:
#   LGPL, MIT, or proprietary licenses similar to this one).
# 
#   It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#   or modified copies of the Software.
# 
#   The above copyright notice and this permission notice must be included in all
#   copies or substantial portions of the Software.
# 
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#   DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.
#
###################################################################################

import logging
import threading

from odoo import SUPERUSER_ID, api, models, registry
from odoo.tools import formataddr
from odoo.tools.misc import clean_context, split_every

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def append_email_address_in_email(self, list_ids):
        partners = self.env["res.partner"].browse(list_ids)
        email_key = []
        for partner in partners:
            partner_to = formataddr((partner.name or "False", partner.email or "False"))
            email_key.append(partner_to)
        return email_key

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
        to_ids = self._context.get("to_ids", False)
        if not to_ids:
            return super(MailThread, self)._notify_record_by_email(
                message,
                recipients_data,
                msg_vals=msg_vals,
                model_description=model_description,
                mail_auto_delete=mail_auto_delete,
                check_existing=check_existing,
                force_send=force_send,
                send_after_commit=send_after_commit,
                **kwargs
            )
        cc_ids = self._context.get("cc_ids", False)
        bcc_ids = self._context.get("bcc_ids", False)

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
                lang=template_values["lang"]
            )  # 1 query
        except ValueError:
            _logger.warning(
                "QWeb template %s not found when sending notification emails. "
                "Sending without layouting." % (template_xmlid)
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
            # 2 query, check acces + read, may be useless, Falsy, when will it be used?
            "auto_delete": mail_auto_delete,
            # due to ir.rule, user have no right to access
            # parent message if message is not published
            "references": message.parent_id.sudo().message_id
            if message.parent_id
            else False,
            "subject": mail_subject,
        }
        base_mail_values = self._notify_by_email_add_values(base_mail_values)

        # Clean the context to get rid of residual
        # default_* keys that could cause issues during
        # the mail.mail creation.
        # Example: 'default_state' would refer to the
        # default state of a previously created record
        # from another model that in turns triggers an
        # assignation notification that ends up here.
        # This will lead to a traceback when trying
        # to create a mail.mail with this state value that
        # doesn't exist.
        SafeMail = (
            self.env["mail.mail"].sudo().with_context(clean_context(self._context))
        )
        SafeNotification = (
            self.env["mail.notification"]
            .sudo()
            .with_context(clean_context(self._context))
        )
        emails = self.env["mail.mail"].sudo()

        # loop on groups (customer, portal, user,
        # ... + model specific like group_sale_salesman)
        notif_create_values = []
        recipients_max = 50
        for recipients_group_data in recipients_groups_data:
            # generate notification email content
            recipients_ids = recipients_group_data.pop("recipients")
            render_values = {**template_values, **recipients_group_data}
            # {company, is_discussion, lang, message,
            # model_description, record, record_name,
            # signature, subtype, tracking_values, website_url}
            # {actions, button_access, has_button_access, recipients}

            if base_template:
                mail_body = base_template._render(
                    render_values, engine="ir.qweb", minimal_qcontext=True
                )
            else:
                mail_body = message.body
            mail_body = self.env["mail.render.mixin"]._replace_local_links(mail_body)

            # create email
            for recipients_ids_chunk in split_every(recipients_max, recipients_ids):
                recipient_values = self._notify_email_recipient_values(
                    recipients_ids_chunk
                )
                # email_to = recipient_values["email_to"]
                recipient_ids = recipient_values["recipient_ids"]

                create_values = {
                    "body_html": mail_body,
                    "subject": mail_subject,
                    # "recipient_ids": [Command.link(pid) for pid in recipient_ids],
                }
                if to_ids:
                    create_values["email_to"] = ",".join(
                        self.append_email_address_in_email(to_ids)
                    )
                if cc_ids:
                    create_values["email_cc"] = ",".join(
                        self.append_email_address_in_email(cc_ids)
                    )
                if bcc_ids:
                    create_values["email_bcc"] = ",".join(
                        self.append_email_address_in_email(bcc_ids)
                    )
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
