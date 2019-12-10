# -*- coding: utf-8 -*-

import logging
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ActivityAlarm(models.Model):
    _name = 'ba_activity_deadline.alarm'
    _description = 'Activity Alarm'

    @api.depends('interval', 'duration')
    def _compute_duration_sec(self):
        for alarm in self:
            if alarm.interval == "minutes":
                alarm.duration_sec = alarm.duration * 60
            elif alarm.interval == "hours":
                alarm.duration_sec = alarm.duration * 60 * 60
            elif alarm.interval == "days":
                alarm.duration_sec = alarm.duration * 60 * 60 * 24
            else:
                alarm.duration_sec = 0

    _interval_selection = {'minutes': 'Minute(s)', 'hours': 'Hour(s)', 'days': 'Day(s)'}
    _types = [('popup', 'Popup'), ('email', 'Email')]

    name = fields.Char('Name', translate=True, required=True)
    type = fields.Selection(_types, 'Type', required=True,
                            default='popup')
    duration = fields.Integer('Remind Before', required=True, default=1)
    interval = fields.Selection(list(_interval_selection.items()), 'Unit', required=True, default='hours')
    duration_sec = fields.Integer('Duration in minutes', compute='_compute_duration_sec', store=True,
                                  help="Duration in minutes")

    @api.onchange('duration', 'interval', 'type')
    def _onchange_duration_interval(self):
        display_interval = self._interval_selection.get(self.interval, '')
        self.name = '{} {} [{}]'.format(str(self.duration), display_interval, self.type)

    @api.model
    def alarm_reminder(self):
        now = fields.Datetime.to_string(fields.Datetime.now())
        last_notif_mail = self.env['ir.config_parameter'].sudo().get_param(
            'ba_activity_deadline.last_alarm',
            default=now
        )

        notif_activities = self.get_next_alarms(last_notif_mail, now)
        if notif_activities:
            for rec in notif_activities:
                if rec['type'] == 'popup':
                    self.send_popup(rec)
                if rec['type'] == 'email':
                    self.send_email(rec)
        self.env['ir.config_parameter'].sudo().set_param('ba_activity_deadline.last_alarm', now)

    def get_next_alarms(self, last_notif_mail, now):
        result = []
        request = """
            SELECT
                rel.mail_activity_id AS activity_id,
                alarm.type AS alarm_type,
                act.user_id AS user_id
            FROM
                mail_activity_ba_activity_deadline_alarm_rel AS rel
            LEFT JOIN 
                ba_activity_deadline_alarm AS alarm 
                ON alarm.id = rel.ba_activity_deadline_alarm_id
            LEFT JOIN 
                mail_activity AS act 
                ON act.id = rel.mail_activity_id
            WHERE 
                act.dd - interval '1 second' * alarm.duration_sec >= '{}' AND act.dd - interval '1 second' * alarm.duration_sec <= '{}'
            GROUP BY 
                rel.mail_activity_id,
                alarm.type,
                act.user_id
        """

        self._cr.execute(request.format(last_notif_mail, now))

        for activity_id, alarm_type, user_id in self._cr.fetchall():
            result.append({'id': activity_id, 'type': alarm_type, 'user_id': user_id})

        return result

    @api.model
    def send_popup(self, rec):
        self.env['bus.bus'].sendone('ba_activity_deadline.alarm', rec)

    @api.model
    def send_email(self, rec):
        activity_id = self.env['mail.activity'].browse(rec.get('id'))
        user_id = self.env['res.users'].browse(rec.get('user_id'))
        record = self.env[activity_id.res_model].browse(activity_id.res_id)

        context = self.env.context.copy()
        context.update({
            'activity': activity_id,
            'record': record,
            'user_id': user_id,
            'rec_name': activity_id.activity_type_id.name,
            'model_name': activity_id.res_model_id.name,
        })
        template = self.with_context(lang=user_id.partner_id.lang).env.ref(
            'ba_activity_deadline.activity_due_date_template'
        )

        subject = template.with_context(context)._render_template(
            template.subject,
            'res.users',
            user_id.id,
        )
        body_html = template.with_context(context)._render_template(
            template.body_html,
            'res.users',
            user_id.id,
        )
        mail_server = self.env['ir.mail_server']
        message = mail_server.build_email(
            email_from=self.sudo().env.user.partner_id.email or '',
            subject=subject,
            body=body_html,
            subtype='html',
            email_to=[user_id.partner_id.email or ''],
        )
        try:
            mail_server.send_email(message)
        except Exception as e:
            _logger.warning("Don't send notification email: {}".format(e))
