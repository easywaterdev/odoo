from odoo import fields, models, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    full_search = fields.Char(string='Full Search', store=True, compute="_compute_full_search", search='_search_full_search')

    @api.depends('name', 'partner_id.email', 'partner_id.phone_sanitized')
    def _compute_full_search(self):
        for record in self:

            search = []
            if record.name:
                search.append(f"{record.name}|~|")
            if record.partner_id.name:
                search.append(f"{record.partner_id.name}|~|")
            if record.email_from:
                search.append(f"{record.email_from}|~|")
            if record.phone_sanitized:
                search.append(f"{record.phone_sanitized}")

            record.full_search = "".join(search)

    def _search_full_search(self, operator, value):
        return [('full_search', operator, value)]
