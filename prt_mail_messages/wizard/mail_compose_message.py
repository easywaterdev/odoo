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

from odoo import _, api, fields, models, tools


########################
# Mail.Compose Message #
########################
class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    wizard_mode = fields.Char(string="Wizard mode")
    forward_ref = fields.Reference(
        string="Attach to record", selection="_referenceable_models_fwd", readonly=False
    )
    signature_location = fields.Selection(
        [("b", "Before quote"), ("a", "Message bottom"), ("n", "No signature")],
        string="Signature Location",
        default="b",
        required=True,
        help="Whether to put signature before or after the quoted text.",
    )

    # -- Send
    def _action_send_mail(self, auto_commit=False):
        return super(
            MailComposer,
            self.with_context(
                signature_location=self.signature_location,
                default_wizard_mode=self.wizard_mode,
            ),
        )._action_send_mail(auto_commit=auto_commit)

    # -- Ref models
    @api.model
    def _referenceable_models_fwd(self):
        return [
            (x.model, x.name)
            for x in self.env["ir.model"]
            .sudo()
            .search([("is_mail_thread", "=", True), ("model", "!=", "mail.thread")])
        ]

    # -- Record ref change
    @api.onchange("forward_ref")
    def ref_change(self):
        self.ensure_one()
        if self.forward_ref:
            self.update(
                {"model": self.forward_ref._name, "res_id": self.forward_ref.id}
            )

    # -- Get record data
    @api.model
    def get_record_data(self, values):
        """
        Copy-pasted mail.compose.message original function so stay
         aware in case it is changed in Odoo core!

        Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values."""
        result = {}
        subj = self._context.get("default_subject", False)
        subject = tools.ustr(subj) if subj else False
        if not subject:
            if values.get("parent_id"):
                parent = self.env["mail.message"].browse(values.get("parent_id"))
                result["record_name"] = (parent.record_name,)
                subject = tools.ustr(parent.subject or parent.record_name or "")
                if not values.get("model"):
                    result["model"] = parent.model
                if not values.get("res_id"):
                    result["res_id"] = parent.res_id
                partner_ids = values.get("partner_ids", list()) + [
                    (4, xid)
                    for xid in parent.partner_ids.filtered(
                        lambda rec: rec.email
                        not in [self.env.user.email, self.env.user.company_id.email]
                    ).ids
                ]
                if (
                    self._context.get("is_private") and parent.author_id
                ):  # check message is private then add author also in partner list.
                    partner_ids += [(4, parent.author_id.id)]
                result["partner_ids"] = partner_ids
            elif values.get("model") and values.get("res_id"):
                doc_name_get = (
                    self.env[values.get("model")]
                    .browse(values.get("res_id"))
                    .name_get()
                )
                result["record_name"] = doc_name_get and doc_name_get[0][1] or ""
                subject = tools.ustr(result["record_name"])

            # Change prefix in case we are forwarding
            re_prefix = (
                _("Fwd:")
                if self._context.get("default_wizard_mode", False) == "forward"
                else _("Re:")
            )

            if subject and not (
                subject.startswith("Re:") or subject.startswith(re_prefix)
            ):
                subject = " ".join((re_prefix, subject))

        result["subject"] = subject

        return result
