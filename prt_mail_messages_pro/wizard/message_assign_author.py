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

from odoo import api, models


#################
# Author assign #
#################
class MessagePartnerAssign(models.TransientModel):
    _inherit = "cx.message.partner.assign.wiz"

    # -- Change Same Email only
    @api.onchange("same_email", "email")
    def is_same(self):
        if self.same_email:
            return {"domain": {"partner_id": [("email", "=", self.email)]}}
        else:
            return {"domain": {"partner_id": []}}

    # -- Assign current message
    def assign_one(self):
        self._cr.execute(
            """
        UPDATE mail_message
        SET author_id=%s
        WHERE id=%s""",
            (
                self.partner_id.id,
                self._context.get("active_id"),
            ),
        )

    # -- Assign all unassigned messages with same email in 'From'
    def assign_all(self):
        self._cr.execute(
            """
        UPDATE mail_message
        SET author_id=%s
        WHERE (email_from LIKE %s OR email_from=%s) AND (author_id IS NULL)""",
            (
                self.partner_id.id,
                "".join(["%<", self.email, ">"]),
                self.email,
            ),
        )
