# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    is_auto_packing = fields.Boolean(string="Automated Packaging")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def auto_pack(self):
        print("Inside auto_pack")


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
