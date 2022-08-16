from odoo import fields, models, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    full_search = fields.Char(string='Full Search', store=True, compute="_compute_full_search", search='_search_full_search')
    # mobile_sanitized = fields.Char(string='Sanitized Mobile Number', readonly=True, compute='_compute_mobile_sanitized')
    #
    # @api.depends('mobile')
    # def _compute_mobile_sanitized(self):
    #     for record in self:
    #         if record.mobile:
    #             record.mobile_sanitized = str(record.mobile).replace("-", "")

    @api.depends('name', 'partner_id.name', 'email_from', 'phone', 'mobile')
    def _compute_full_search(self):
        for record in self:

            search = []
            if record.name:
                search.append(f"{record.name}")
            if record.partner_id.name:
                search.append(f"|~|{record.partner_id.name}")
            if record.email_from:
                search.append(f"|~|{record.email_from}")
            if record.phone:
                search.append(f"|~|{self.sanitize_number(record.phone)}")
                search.append(f"|~|{record.phone}")
            if record.mobile:
                search.append(f"|~|{self.sanitize_number(record.mobile)}")
                search.append(f"|~|{record.mobile}")

            record.full_search = "".join(search)

    # Sanitized field only stores recent number
    def sanitize_number(self, num):
        remove_whitespace = num.replace(' ', '')
        remove_bracket_left = remove_whitespace.replace('(', '')
        remove_bracket_right = remove_bracket_left.replace(')', '')
        remove_plus = remove_bracket_right.replace('+', '')
        sanitized_number = remove_plus.replace('-', '')
        return sanitized_number

    def _search_full_search(self, operator, value):
        return [('full_search', operator, value)]
