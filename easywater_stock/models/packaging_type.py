# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PackagingType(models.Model):
    _name = "easywater.packaging.type"
    _description = "Default Packaging Type"

    name = fields.Char(string="Packaging Type", required=True)
    quantity = fields.Integer(string="Quantity")

    weight = fields.Float(string="Weight")
    length = fields.Float(string="Length")
    width = fields.Float(string="Width")
    height = fields.Float(string="Height")

    product_ids = fields.Many2many('product.template', string="Product")
    active = fields.Boolean(string="Active", default="True")

