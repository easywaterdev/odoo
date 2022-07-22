# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    type = fields.Selection(selection_add=[('install', 'Installation address')])
