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

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def append_email_address_in_email(self, list_ids):
        partners = self.browse(list_ids)
        email_key = []
        for partner in partners:
            partner_to = formataddr((partner.name or "False", partner.email or "False"))
            email_key.append(partner_to)
        return email_key

    # -- Notify partner
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
        """
        If message is sent in "Email" mode send notifications only
        to partners who are not in "To" "CC" and "BCC" fields
        """
        if not rdata:
            return True

        to_ids = self._context.get("to_ids", False)

        if not to_ids:
            return super(Partner, self)._notify(
                message=message,
                rdata=rdata,
                record=record,
                force_send=force_send,
                send_after_commit=send_after_commit,
                model_description=model_description,
                mail_auto_delete=mail_auto_delete,
            )
        cc_ids = self._context.get("cc_ids", False)
        bcc_ids = self._context.get("bcc_ids", False)

        base_template_ctx = self._notify_prepare_template_context(
            message, record, model_description=model_description
        )
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
                "QWeb template %s not found when sending notification emails. "
                "Sending without layouting." % (template_xmlid)
            )
            base_template = False
        base_mail_values = {
            "mail_message_id": message.id,
            "mail_server_id": message.mail_server_id.id,
            "auto_delete": mail_auto_delete,
            "references":
                message.parent_id.sudo().message_id if message.parent_id else False,
        }
        if record:
            base_mail_values.update(
                self.env["mail.thread"]._notify_specific_email_values_on_records(
                    message, records=record
                )
            )

        Mail = self.env["mail.mail"].sudo()

        template_ctx = {**base_template_ctx, "actions": []}
        mail_body = (
            base_template.render(template_ctx, engine="ir.qweb", minimal_qcontext=True)
            if base_template else message.body
        )
        mail_body = self.env["mail.thread"]._replace_local_links(mail_body)
        mail_subject = message.subject or (
            message.record_name and "Re: %s" % message.record_name
        )

        create_values = {
            "body_html": mail_body,
            "subject": mail_subject,
            "email_to": ",".join(self.append_email_address_in_email(to_ids)),
            "email_cc":
                ",".join(self.append_email_address_in_email(cc_ids)) if cc_ids else "",
            "email_bcc":
                ",".join(self.append_email_address_in_email(bcc_ids))
                if bcc_ids else "",
        }
        create_values.update(base_mail_values)
        emails = Mail.create(create_values)

        test_mode = getattr(threading.currentThread(), "testing", False)
        if force_send and (not self.pool._init or test_mode):
            email_ids = emails.ids
            dbname = self.env.cr.dbname
            _context = self._context

            def send_notifications():
                db_registry = registry(dbname)
                with api.Environment.manage(), db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, _context)
                    env["mail.mail"].browse(email_ids).send()

            if not test_mode and send_after_commit:
                self._cr.after("commit", send_notifications)
            else:
                emails.send()
        return True
