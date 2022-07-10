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

from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.tools.misc import split_every

_logger = logging.getLogger(__name__)


################
# Res.Partner #
################
class Partner(models.Model):
    _inherit = "res.partner"

    # -- Notify
    def _notify(
        self,
        message,
        rdata,
        record,
        force_send=False,
        send_after_commit=True,
        model_description=False,
        mail_auto_delete=True,
    ):
        """Method to send email linked to notified messages. The recipients are
        the recordset on which this method is called.

        :param message: mail.message record to notify;
        :param rdata: recipient data (see mail.message _notify);
        :param record: optional record on which the message was posted;
        :param force_send: tells whether to send notification emails within the
          current transaction or to use the email queue;
        :param send_after_commit: if force_send, tells whether to send emails after
          the transaction has been committed using a post-commit hook;
        :param model_description: optional data used in notification process (see
          notification templates);
        :param mail_auto_delete: delete notification emails once sent;
        """
        if not rdata:
            return True

        # Cetmix. Check context.
        if not self._context.get("default_wizard_mode", False) in ["quote", "forward"]:
            return super(Partner, self)._notify(
                message=message,
                rdata=rdata,
                record=record,
                force_send=force_send,
                send_after_commit=send_after_commit,
                model_description=model_description,
                mail_auto_delete=mail_auto_delete,
            )

        # Get signature location
        signature_location = self._context.get("signature_location", False)

        # After quote
        if signature_location == "a":
            return super(Partner, self)._notify(
                message=message,
                rdata=rdata,
                record=record,
                force_send=force_send,
                send_after_commit=send_after_commit,
                model_description=model_description,
                mail_auto_delete=mail_auto_delete,
            )

        base_template_ctx = self._notify_prepare_template_context(
            message, record, model_description=model_description
        )
        # Cetmix. Get signature
        signature = base_template_ctx.pop("signature", False)
        template_xmlid = (
            message.layout if message.layout else "mail.message_notification_email"
        )
        try:
            base_template = self.env.ref(template_xmlid,
                                         raise_if_not_found=True).with_context(
                                             lang=base_template_ctx["lang"]
                                         )  # noqa
        except ValueError:
            _logger.warning(
                "QWeb template %s not found when sending notification emails."
                " Sending without layouting." % (template_xmlid)
            )
            base_template = False

        # prepare notification mail values
        base_mail_values = {
            "mail_message_id": message.id,
            "mail_server_id": message.mail_server_id.id,
            "auto_delete": mail_auto_delete,
            "references": message.parent_id.message_id if message.parent_id else False,
        }
        if record:
            base_mail_values.update(
                self.env["mail.thread"]._notify_specific_email_values_on_records(
                    message, records=record
                )
            )

        # classify recipients: actions / no action
        recipients = self.env["mail.thread"]._notify_classify_recipients_on_records(
            message, rdata, records=record
        )

        Mail = self.env["mail.mail"].sudo()
        emails = self.env["mail.mail"].sudo()
        email_pids = set()
        recipients_nbr, recipients_max = 0, 50  # noqa
        for group_tpl_values in [
            group for group in recipients.values() if group["recipients"]
        ]:
            # generate notification email content
            template_ctx = {**base_template_ctx, **group_tpl_values}
            mail_body = base_template.render(
                template_ctx, engine="ir.qweb", minimal_qcontext=True
            )
            mail_body = self.env["mail.thread"]._replace_local_links(mail_body)
            mail_subject = message.subject or (
                message.record_name and "Re: %s" % message.record_name
            )

            # Cetmix. Put signature before quote
            if signature_location == "b":
                quote_index = mail_body.find("<blockquote")
                if quote_index:
                    mail_body = "{}{}{}".format(
                        mail_body[:quote_index],
                        signature,
                        mail_body[quote_index:],
                    )  # legacy mode

            # send email
            for email_chunk in split_every(50, group_tpl_values["recipients"]):
                recipient_values = self.env["mail.thread"
                                            ]._notify_email_recipients_on_records(
                                                message, email_chunk, records=record
                                            )  # noqa
                create_values = {
                    "body_html": mail_body,
                    "subject": mail_subject,
                }
                create_values.update(base_mail_values)
                create_values.update(recipient_values)
                recipient_ids = [r[1] for r in create_values.get("recipient_ids", [])]
                email = Mail.create(create_values)

                if email and recipient_ids:
                    notifications = (
                        self.env["mail.notification"].sudo().search([
                            ("mail_message_id", "=", email.mail_message_id.id),
                            ("res_partner_id", "in", list(recipient_ids)),
                        ])
                    )
                    notifications.write({
                        "is_email": True,
                        "mail_id": email.id,
                        "is_read": True,  # handle by email discards Inbox notification
                        "email_status": "ready",
                    })

                emails |= email
                email_pids.update(recipient_ids)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.currentThread(), "testing", False)
        if (
            force_send and len(emails) < recipients_max
            and (not self.pool._init or test_mode)
        ):
            email_ids = emails.ids
            dbname = self.env.cr.dbname
            _context = self._context

            def send_notifications():
                db_registry = registry(dbname)
                with api.Environment.manage(), db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, _context)
                    env["mail.mail"].browse(email_ids).send()

            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                self._cr.after("commit", send_notifications)
            else:
                emails.send()

        return True

    messages_from_count = fields.Integer(
        string="Messages From", compute="_compute_from_count"
    )
    messages_to_count = fields.Integer(
        string="Messages To", compute="_compute_to_count"
    )

    # -- Count messages from
    @api.depends("message_ids")
    def _compute_from_count(self):
        for rec in self:
            if rec.id:
                rec.messages_from_count = self.env["mail.message"].search_count([
                    ("author_id", "child_of", rec.id),
                    ("message_type", "!=", "notification"),
                    ("model", "!=", "mail.channel"),
                ])
            else:
                rec.messages_from_count = 0

    # -- Count messages from
    @api.depends("message_ids")
    def _compute_to_count(self):
        for rec in self:
            rec.messages_to_count = self.env["mail.message"].search_count([
                ("partner_ids", "in", [rec.id]),
                ("message_type", "!=", "notification"),
                ("model", "!=", "mail.channel"),
            ])

    # -- Open related
    def partner_messages(self):
        self.ensure_one()

        # Choose what messages to display
        open_mode = self._context.get("open_mode", "from")

        if open_mode == "from":
            domain = [
                ("message_type", "!=", "notification"),
                ("author_id", "child_of", self.id),
                ("model", "!=", "mail.channel"),
            ]
        elif open_mode == "to":
            domain = [
                ("message_type", "!=", "notification"),
                ("partner_ids", "in", [self.id]),
                ("model", "!=", "mail.channel"),
            ]
        else:
            domain = [
                ("message_type", "!=", "notification"),
                ("model", "!=", "mail.channel"),
                "|",
                ("partner_ids", "in", [self.id]),
                ("author_id", "child_of", self.id),
            ]

        # Cache Tree View and Form View ids
        tree_view_id = self.env.ref("prt_mail_messages.prt_mail_message_tree").id
        form_view_id = self.env.ref("prt_mail_messages.prt_mail_message_form").id

        return {
            "name": _("Messages"),
            "views": [[tree_view_id, "tree"], [form_view_id, "form"]],
            "res_model": "mail.message",
            "type": "ir.actions.act_window",
            "context": "{'check_messages_access': True}",
            "target": "current",
            "domain": domain,
        }

    # -- Send email from partner's form view
    def send_email(self):
        self.ensure_one()

        return {
            "name": _("New message"),
            "views": [[False, "form"]],
            "res_model": "mail.compose.message",
            "type": "ir.actions.act_window",
            "target": "new",
            "context": {
                "default_res_id": False,
                "default_parent_id": False,
                "default_model": False,
                "default_partner_ids": [self.id],
                "default_attachment_ids": False,
                "default_is_log": False,
                "default_body": False,
                "default_wizard_mode": "compose",
                "default_no_auto_thread": False,
            },
        }
