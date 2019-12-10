# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    dd = fields.Datetime('Due Date', index=True, required=True,
                         default=lambda self: fields.Datetime.now() + relativedelta(hours=24))
    reminder_ids = fields.Many2many('ba_activity_deadline.alarm', 'mail_activity_ba_activity_deadline_alarm_rel',
                                    string="Reminder")
    model_name = fields.Char('Model Name', compute='_get_model_name', store=True)

    @api.onchange('dd')
    def onchange_dd(self):
        self.date_deadline = self.dd.date()

    @api.depends('res_model')
    def _get_model_name(self):
        for act in self:
            model = self.env['ir.model'].sudo().search([('model', '=', act.res_model)], limit=1)
            act.model_name = model.name
