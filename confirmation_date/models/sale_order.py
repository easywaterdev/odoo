# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import date


class SaleOrder(models.Model):
    _inherit = "sale.order"

    original_confirmation_date = fields.Date(string="Original Confirmation", copy=False, tracking=True)

    def action_confirm(self):
        for record in self:
            if not record.original_confirmation_date:
                record.original_confirmation_date = date.today()
        return super().action_confirm()
