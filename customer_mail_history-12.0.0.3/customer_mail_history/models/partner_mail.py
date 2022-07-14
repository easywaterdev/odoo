# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.translate import _
from email.utils import formataddr


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.multi
    def action_view_send_mail(self):
        mail_pool = self.env['mail.message']
        result = []
        for partner in self:
            send_search = mail_pool.search([('email_from', '=', partner.email_formatted)])
            
            if send_search:
                result = self.env['ir.actions.act_window'].for_xml_id('customer_mail_history', 'action_view_mail_message_send')
                result['res_id'] = [x.id for x in send_search] or False
                result['domain'] = [('email_from', '=', partner.email_formatted)]
            else:
                result = self.env['ir.actions.act_window'].for_xml_id('customer_mail_history', 'action_view_mail_message_send')
                result['domain'] = [('email_from', '=', partner.email_formatted)]
            return result
        
        
    @api.multi
    def action_view_recieve_mail(self):
        mail_pool = self.env['mail.message']
        result = []
        for partner in self:
            recv_search = mail_pool.search([('partner_ids', 'in', [partner.id])])
            if recv_search:
                result = self.env['ir.actions.act_window'].for_xml_id('customer_mail_history', 'action_view_mail_message_recieve')
                result['res_id'] = [x.id for x in recv_search] or False
                result['domain'] = [('partner_ids', 'in', [partner.id])]
            else:
                result = self.env['ir.actions.act_window'].for_xml_id('customer_mail_history', 'action_view_mail_message_recieve')
            return result

    @api.multi
    def _get_send_mail_count(self):
        for send in self:
            if send.email:
                partner_email = formataddr((send.name, send.email))
                send_mail_ids = self.env['mail.message'].search([('email_from','=',partner_email)])
                send.send_mail_count = len(send_mail_ids)
            
    @api.multi
    def _get_receive_mail_count(self):
        for receive in self:
            receive_mail_ids = self.env['mail.message'].search([('partner_ids','=',receive.id)])
            receive.receive_mail_count = len(receive_mail_ids)

    receive_mail_count  =  fields.Integer('Received Mail', compute='_get_receive_mail_count')
    send_mail_count  =  fields.Integer('Send Mail', compute='_get_send_mail_count')

class MailMessage(models.Model):
    _inherit='mail.message'

    receive_mail_id  =  fields.Many2one('res.partner', 'Receive Mail')     
                
