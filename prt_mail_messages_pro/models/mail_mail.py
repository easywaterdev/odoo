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

import base64
import logging
import re
import smtplib

import psycopg2

from odoo import _, fields, models, tools
from odoo.tools.safe_eval import safe_eval

from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)


###################################################
# Mail Mail
###################################################
class MailMail(models.AbstractModel):
    _inherit = "mail.mail"

    email_bcc = fields.Char(string="Bcc", help="BCC email addresses")

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        mail_regular = self.env["mail.mail"]
        mail_with_bcc = self.env["mail.mail"]
        for mail in self:
            if mail.email_bcc:
                mail_with_bcc |= mail
            else:
                mail_regular |= mail
        if mail_regular:
            super(MailMail, mail_regular)._send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                smtp_session=smtp_session,
            )
        if not mail_with_bcc:
            return True
        self = mail_with_bcc
        IrMailServer = self.env["ir.mail_server"]
        IrAttachment = self.env["ir.attachment"]
        for mail_id in self.ids:
            success_pids = []
            failure_type = None
            processing_pid = None
            mail = None
            try:
                mail = self.browse(mail_id)
                if mail.state != "outgoing":
                    if mail.state != "exception" and mail.auto_delete:
                        mail.sudo().unlink()
                    continue

                # remove attachments if user send the link with the access_token
                body = mail.body_html or ""
                attachments = mail.attachment_ids
                for link in re.findall(r"/web/(?:content|image)/([0-9]+)", body):
                    attachments = attachments - IrAttachment.browse(int(link))

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [
                    (a["datas_fname"], base64.b64decode(a["datas"]), a["mimetype"])
                    for a in
                    attachments.sudo().read(["datas_fname", "datas", "mimetype"])
                    if a["datas"] is not False
                ]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail._send_prepare_values())
                for partner in mail.recipient_ids:
                    values = mail._send_prepare_values(partner=partner)
                    values["partner_id"] = partner
                    email_list.append(values)

                # headers
                headers = {}
                ICP = self.env["ir.config_parameter"].sudo()
                bounce_alias = ICP.get_param("mail.bounce.alias")
                catchall_domain = ICP.get_param("mail.catchall.domain")
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers["Return-Path"] = "%s+%d-%s-%d@%s" % (
                            bounce_alias,
                            mail.id,
                            mail.model,
                            mail.res_id,
                            catchall_domain,
                        )
                    else:
                        headers["Return-Path"] = "%s+%d@%s" % (
                            bounce_alias,
                            mail.id,
                            catchall_domain,
                        )
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    "state": "exception",
                    "failure_reason":
                        _(
                            "Error without exception. Probably due do "
                            "sending an email without computed recipients."
                        ),
                })
                notifs = self.env["mail.notification"].search([
                    ("is_email", "=", True),
                    ("mail_id", "in", mail.ids),
                    ("email_status", "not in", ("sent", "canceled")),
                ])
                if notifs:
                    notif_msg = _(
                        "Error without exception. Probably due do "
                        "concurrent access update of notification records. "
                        "Please see with an administrator."
                    )
                    notifs.sudo().write({
                        "email_status": "exception",
                        "failure_type": "UNKNOWN",
                        "failure_reason": notif_msg,
                    })

                res = None
                for email in email_list:
                    msg = IrMailServer.build_email(
                        email_from=mail.email_from,
                        email_to=email.get("email_to"),
                        subject=mail.subject,
                        body=email.get("body"),
                        body_alternative=email.get("body_alternative"),
                        email_cc=tools.email_split(mail.email_cc),
                        email_bcc=tools.email_split(mail.email_bcc),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id
                        and ("{}-{}".format(mail.res_id, mail.model)),
                        subtype="html",
                        subtype_alternative="plain",
                        headers=headers,
                    )
                    processing_pid = email.pop("partner_id", None)
                    try:
                        res = IrMailServer.send_email(
                            msg,
                            mail_server_id=mail.mail_server_id.id,
                            smtp_session=smtp_session,
                        )
                        if processing_pid:
                            success_pids.append(processing_pid)
                        processing_pid = None
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            failure_type = "RECIPIENT"
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info(
                                "Ignoring invalid recipients for mail.mail %s: %s",
                                mail.message_id,
                                email.get("email_to"),
                            )
                        else:
                            raise
                if res:  # mail has been sent at least once, no major exception occured
                    mail.write({
                        "state": "sent", "message_id": res, "failure_reason": False
                    })
                    _logger.info(
                        "Mail with ID %r and Message-Id %r successfully sent",
                        mail.id,
                        mail.message_id,
                    )
                    mail._postprocess_sent_message(
                        success_pids=success_pids, failure_type=failure_type
                    )
            except MemoryError:
                # prevent catching transient MemoryErrors,
                # bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    "MemoryError while processing mail with ID %r and Msg-Id %r. "
                    "Consider raising the --limit-memory-hard startup option",
                    mail.id,
                    mail.message_id,
                )
                # mail status will stay on ongoing since transaction will be rollback
                raise
            except (psycopg2.Error, smtplib.SMTPServerDisconnected):
                # If an error with the database or SMTP session occurs,
                # chances are that the cursor
                # or SMTP session are unusable,
                # causing further errors when trying to save the state.
                _logger.exception(
                    "Exception while processing mail with ID %r and Msg-Id %r.",
                    mail.id,
                    mail.message_id,
                )
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception(
                    "failed sending mail (id: %s) due to %s", mail.id, failure_reason
                )
                mail.write({"state": "exception", "failure_reason": failure_reason})
                mail._postprocess_sent_message(
                    success_pids=success_pids,
                    failure_reason=failure_reason,
                    failure_type="UNKNOWN",
                )
                if raise_exception:
                    if isinstance(e, (AssertionError, UnicodeEncodeError)):
                        if isinstance(e, UnicodeEncodeError):
                            value = "Invalid text: %s" % e.object
                        else:
                            # get the args of the original error,
                            # wrap into a value and throw a MailDeliveryException
                            # that is an except_orm, with name and value as arguments
                            value = ". ".join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True
