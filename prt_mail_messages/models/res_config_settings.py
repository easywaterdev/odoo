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

from odoo import _, fields, models


###################
# Config Settings #
###################
class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    messages_easy_text_preview = fields.Integer(
        string="Text preview length",
        config_parameter="cetmix.messages_easy_text_preview",
    )
    messages_easy_color_note = fields.Char(
        string="Note Background",
        config_parameter="cetmix.messages_easy_color_note",
        help="Background color for internal notes in HTML format (e.g. #fbd78b)",
    )
    messages_easy_empty_trash = fields.Integer(
        string="Empty trash in (days)",
        config_parameter="cetmix.messages_easy_empty_trash",
        default=0,
    )

    def action_configure_cron(self):
        return {
            "name": _("Edit cron"),
            "views": [(False, "form")],
            "res_model": "ir.cron",
            "res_id":
                self.env
                .ref("prt_mail_messages.ir_cron_ptr_mail_messages_action_unlink").id,
            "type": "ir.actions.act_window",
            "target": "new",
        }
