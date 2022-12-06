from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    carrier_id = fields.Many2one(required=True)

    def action_quotation_send(self):
        if not self.carrier_id:
            raise UserError("You cannot mark quotations as sent until you enter a carrier!")
        else:
            return super(SaleOrder, self).action_quotation_send()

    @api.onchange('team_id')
    def _set_default_carrier(self):
        for record in self:
            if record.team_id:
                if record.team_id.name == 'Commercial Sales':
                    record.carrier_id = record.env['delivery.carrier'].search([('name', '=', 'Custom Freight Quote')]).id