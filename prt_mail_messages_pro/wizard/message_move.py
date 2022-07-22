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

from odoo import _, models
from odoo.exceptions import AccessError


#####################
# Mail Move Message #
#####################
class MailMove(models.TransientModel):
    _inherit = "prt.message.move.wiz"

    # -- Move messages
    def message_move(self):
        # -- Can move messages?
        if not self.env.user.has_group("prt_mail_messages.group_move"):
            raise AccessError(_("You cannot move messages!"))

        self.ensure_one()
        if not self.model_to:
            return

        # Check call source.
        # If conversation take all conversation messages.
        # If thread then take active ids
        if self.is_conversation:
            messages = self.env["mail.message"].search(
                [
                    ("model", "=", "cetmix.conversation"),
                    ("res_id", "in", self._context.get("active_ids", False)),
                    ("message_type", "!=", "notification"),
                ]
            )
        else:
            thread_message_id = self._context.get("thread_message_id", False)
            message_ids = (
                self._context.get("active_ids", False)
                if not thread_message_id
                else [thread_message_id]
            )
            if not message_ids or len(message_ids) < 1:
                return
            messages = self.env["mail.message"].browse(message_ids)

        # Move messages
        messages.message_move(
            self.model_to._name,
            self.model_to.id,
            lead_delete=self.is_lead and self.lead_delete,
            opp_delete=self.is_lead and self.opp_delete,
        )
