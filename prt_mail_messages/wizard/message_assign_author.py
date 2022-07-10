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

from odoo import fields, models


#################
# Author assign #
#################
class MessagePartnerAssign(models.TransientModel):
    _name = "cx.message.partner.assign.wiz"
    _description = "Assign Partner to Messages"

    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    same_email = fields.Boolean(
        string="Match Email",
        default=True,
        help="Show Partners with same email address only",
    )
    partner_id = fields.Many2one(string="Assign To", comodel_name="res.partner")
