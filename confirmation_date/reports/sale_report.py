# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleReport(models.Model):
    _inherit = "sale.report"

    original_confirmation_date = fields.Date(string="Original Confirmation", copy=False, readonly=True)

    def _select_additional_fields(self, fields):
        fields['original_confirmation_date'] = ", s.original_confirmation_date"
        return super()._select_additional_fields(fields)
