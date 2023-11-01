# -*- coding: utf-8 -*

from odoo.http import request, route, Controller
import re

CLEAN = re.compile('(^\+[\d]{3}|^[\d]{2})')


class Main3CX(Controller):
    @route(['/3cx/<string:clientPhone>', '/3cx/<string:clientPhone>/<string:callerName>'], type='http', auth='public')
    def identify_3cx_partner(self, clientPhone, callerName=False):
        if request.env.user._is_public():
            return request.redirect('/web/login')
        action_id = request.env.ref('base.action_partner_form').id
        if clientPhone:
            clientPhone = clientPhone.replace(' ', '')
            clientPhoneMatch = re.sub(CLEAN, '', clientPhone)
            url = '/web?#view_type=form&id=%s&model=res.partner&action=%s'
            if partners := request.env['res.partner'].search(['|', ('phone_formatted', 'ilike', '%' + clientPhoneMatch), ('mobile_formatted', 'ilike', '%' + clientPhoneMatch)]):
                if partners[0].is_3cx_internal:
                    return request.redirect('/web')
                if len(partners) > 1:
                    server_action = request.env.ref("nalios_3cx_integration.action_3cx_to_partner_list")
                    return request.redirect("/web?#action={}&model=res.partner&view_type=list&res_ids={}".format(server_action.id, ','.join([str(i) for i in partners.ids])))
                url = url % (partners.id, action_id)
                return request.redirect(url)
            vals = {'name': callerName if callerName else 'New', 'phone': clientPhone}
            partner = request.env['res.partner'].create(vals)
            url = url % (partner.id, action_id)
            return request.redirect(url)
        return request.redirect('/web?#view_type=form&model=res.partner&action=%s' % (action_id))
