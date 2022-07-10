from odoo import fields, models
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        for rec in self:
            rec.avalara_compute_taxes()
        return super(SaleOrder, self).action_quotation_send()

    def print_quotation(self):
        for rec in self:
            rec.avalara_compute_taxes()
        return super(SaleOrder, self).print_quotation()

    def preview_sale_order(self):
        for rec in self:
            rec.avalara_compute_taxes()
        return super(SaleOrder, self).preview_sale_order()
