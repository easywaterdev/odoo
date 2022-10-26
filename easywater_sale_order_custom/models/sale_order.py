from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        if not self.carrier_id:
            raise UserError("You cannot mark quotations as sent until you enter a carrier!")
        else:
            return super(SaleOrder, self).action_quotation_send()
