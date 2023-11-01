# -*- coding: utf-8 -*

from odoo import models, fields, api


class Partner(models.Model):
    _inherit = 'res.partner'

    is_3cx_internal = fields.Boolean("Is 3CX Internal")
    mobile_formatted = fields.Char(compute='_compute_mobile_formatted', store=True)
    phone_formatted = fields.Char(compute='_compute_phone_formatted', store=True)

    @api.depends('mobile')
    def _compute_mobile_formatted(self):
        for rec in self:
            if rec.mobile:
                rec.mobile_formatted = ''.join(rec.mobile.split(' '))

    @api.depends('phone')
    def _compute_phone_formatted(self):
        for rec in self:
            if rec.phone:
                rec.phone_formatted = ''.join(rec.phone.split(' '))

    def action_open_3cx_to_partner_list(self):
        if 'params' in self.env.context and 'res_ids' in self.env.context['params']:
            ids = self.env.context['params']['res_ids'].split(',')
            partners = self.env['res.partner'].search([('id', 'in', ids)])
            if len(partners):
                return {
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'name': 'Partners',
                'res_model': 'res.partner',
                'domain': [('id', 'in', partners.ids)],
                'target': 'self'
            }
