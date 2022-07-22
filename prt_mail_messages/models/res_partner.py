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

from odoo import _, api, fields, models


################
# Res.Partner #
################
class Partner(models.Model):
    _inherit = "res.partner"

    messages_from_count = fields.Integer(
        string="Messages From", compute="_compute_messages_from_count"
    )
    messages_to_count = fields.Integer(
        string="Messages To", compute="_compute_messages_to_count"
    )

    # -- Count messages from
    @api.depends("message_ids")
    def _compute_messages_from_count(self):
        for rec in self:
            if rec.id:
                rec.messages_from_count = self.env["mail.message"].search_count(
                    [
                        ("author_id", "child_of", rec.id),
                        ("message_type", "in", ["email", "comment"]),
                        ("model", "!=", "mail.channel"),
                    ]
                )
            else:
                rec.messages_from_count = 0

    # -- Count messages from
    @api.depends("message_ids")
    def _compute_messages_to_count(self):
        for rec in self:
            rec.messages_to_count = self.env["mail.message"].search_count(
                [
                    ("partner_ids", "in", [rec.id]),
                    ("message_type", "in", ["email", "comment"]),
                    ("model", "!=", "mail.channel"),
                ]
            )

    # -- Open related
    def partner_messages(self):
        self.ensure_one()

        # Choose what messages to display
        open_mode = self._context.get("open_mode", "from")

        if open_mode == "from":
            domain = [
                ("message_type", "in", ["email", "comment"]),
                ("author_id", "child_of", self.id),
                ("model", "!=", "mail.channel"),
            ]
        elif open_mode == "to":
            domain = [
                ("message_type", "in", ["email", "comment"]),
                ("partner_ids", "in", [self.id]),
                ("model", "!=", "mail.channel"),
            ]
        else:
            domain = [
                ("message_type", "in", ["email", "comment"]),
                ("model", "!=", "mail.channel"),
                "|",
                ("partner_ids", "in", [self.id]),
                ("author_id", "child_of", self.id),
            ]

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
