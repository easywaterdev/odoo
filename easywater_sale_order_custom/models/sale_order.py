from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    def _default_carrier_id(self):
        user = self.env['res.users'].search([('id', '=', self._uid)])
        if user.team_id.name == 'Commercial Sales':
            return self.env['delivery.carrier'].search([('name', '=', 'Custom Freight Quote')]).id

    carrier_id = fields.Many2one(default=_default_carrier_id, required=True)

    def action_quotation_send(self):
        if not self.carrier_id:
            raise UserError("You cannot mark quotations as sent until you enter a carrier!")
        else:
            return super(SaleOrder, self).action_quotation_send()
