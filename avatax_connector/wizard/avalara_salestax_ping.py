from odoo import api, fields, models
from odoo.addons.avatax_connector.models.avalara_api import AvaTaxService


class AvalaraSalestaxPing(models.TransientModel):
    _name = 'avalara.salestax.ping'
    _description = 'Ping Service'

    @api.model
    def default_get(self, fields):
        res = super(AvalaraSalestaxPing, self).default_get(fields)
        self.ping()
        return res

    name = fields.Char('Name')

    @api.model
    def ping(self):
        """ Call the AvaTax's Ping Service to test the connection. """
        context = dict(self._context or {})
        active_id = context.get('active_id')

        if active_id:
            avatax_pool = self.env['avalara.salestax']
            avatax_config = avatax_pool.browse(active_id)
            avapoint = AvaTaxService(avatax_config.account_number, avatax_config.license_key,
                                      avatax_config.service_url, avatax_config.request_timeout, avatax_config.logging)
            taxSvc = avapoint.create_tax_service().taxSvc     # Create 'tax' service for Ping and is_authorized calls
            avapoint.ping()
            result = avapoint.is_authorized()
            avatax_config.write({'date_expiration': result.Expires})
        return True
