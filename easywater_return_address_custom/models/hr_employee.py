from odoo import api, models, fields, _


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    use_address_for_returns = fields.Boolean(string="Use for UPS return labels?")
