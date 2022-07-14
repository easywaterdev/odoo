# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.product"

    packaging_type_ids = fields.One2many('product.packaging', 'product_id', string="Default Packaging Types")
