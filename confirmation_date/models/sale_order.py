# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class SaleOrder(models.Model):
    _inherit = "sale.order"

    original_confirmation_date = fields.Date(string="Original Confirmation", copy=False, tracking=True)
    check_is_admin = fields.Boolean(string="Is User a Manager?", compute="_compute_is_admin")

    def action_confirm(self):
        for record in self:
            if not record.original_confirmation_date:
                record.original_confirmation_date = date.today()
        return super().action_confirm()

    def _compute_is_admin(self):
        for record in self:
            if self.env.user.has_group('sales_team.group_sale_manager'):
                record.check_is_admin = True
            else:
                record.check_is_admin = False

