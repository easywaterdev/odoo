from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

# this action runs when using "Mark Quoation as Sent"

    def action_quotation_sent(self):
        self.button_update_avatax()
        return super().action_quotation_sent()
