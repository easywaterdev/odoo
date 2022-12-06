from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one(default="_default_carrier_id")

    def action_quotation_send(self):
        if not self.carrier_id:
            raise UserError("You cannot mark quotations as sent until you enter a carrier!")
        else:
            return super(SaleOrder, self).action_quotation_send()

    def _default_carrier_id(self):
        for record in self:
            if record.team_id.name == 'Commercial Sales':
                record.carrier_id = 'Custom Freight Quote'
