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

from odoo import fields, models


class MailComposer(models.TransientModel):
    _inherit = "mail.compose.message"

    def _default_wizard_type(self):
        return self.env.user.wizard_type

    wizard_type = fields.Selection(
        [("odoo", "Odoo"), ("email", "E-Mail")],
        string="Composer Mode",
        default=_default_wizard_type,
        required=True,
        help="Odoo: use regular Odoo messaging flow\n"
        "E-Mail: use classic email mode with CC and BCC fields\n"
        "Important: existing followers well be notified"
        " regular way according to settings",
    )
    partner_cc_ids = fields.Many2many(
        string="CC",
        comodel_name="res.partner",
        relation="mail_composer_partner_cc_rel",
        column1="message_id",
        column2="partner_id",
    )
    partner_bcc_ids = fields.Many2many(
        string="BCC",
        comodel_name="res.partner",
        relation="mail_composer_partner_bcc_rel",
        column1="message_id",
        column2="partner_id",
    )

    # -- Send
    def send_mail(self, auto_commit=False):
        if self.wizard_type == "email":
            self = self.with_context(
                to_ids=self.partner_ids.ids,
                cc_ids=self.partner_cc_ids.ids,
                bcc_ids=self.partner_bcc_ids.ids,
            )
        return super(MailComposer, self).send_mail(auto_commit=auto_commit)
