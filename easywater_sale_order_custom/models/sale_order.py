from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        res = super(SaleOrder, self).action_quotation_send()
        for record in self:
            if not record.team_id or not record.team_id.name = "Commercial Sales":
                if not record.carrier_id:
                    raise ValidationError("You cannot mark Quotations as sent until you enter a delivery method!")
        return res

    @api.onchange('team_id')
    def _set_default_carrier(self):
        for record in self:
            if record.team_id:
                if record.team_id.name == 'Commercial Sales':
                    record.carrier_id = record.env['delivery.carrier'].search([('name', '=', 'Custom Freight Quote')]).id
                else:
                    record.carrier_id = ''
            else:
                record.carrier_id = ''

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for record in self:
            if record.state == "sale":
                if record.team_id:
                    if record.team_id.name != 'Commercial Sales':
                        if not record.carrier_id:
                            raise ValidationError("You cannot confirm a Sales Order until you enter a delivery method!")
        return res
