from odoo import fields, models, api


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _redirect_email_to_contact_or_opp(self):
        self.env.cr.commit()
        contacts = self.env['res.partner'].filtered(lambda x: 'easywater' not in x['email'])
        if len(contacts) > 0:
            for contact in contacts:
                self.sudo(user=2).copy({'message_type': 'comment',
                                          'res_id': contact['id']
                                          })

                opp = self.env['crm.lead'].search([('partner_id', '=', contact['id']), ('won_status', '!=', 'won')],
                                             order='create_date desc', limit=1)
                if len(opp) == 1:
                    self.sudo(user=2).copy({
                        'model': 'crm.lead',
                        'message_type': 'comment',
                        'res_id': opp['id']
                    })
