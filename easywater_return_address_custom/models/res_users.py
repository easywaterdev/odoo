from odoo import api, models, fields, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    use_address_for_returns = fields.Boolean(string="Use for UPS return labels?")
