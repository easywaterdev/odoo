# -*- coding: utf-8 -*-

from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.multi
    def get_url_for_record(self, res_id, res_model, user_id):
        self.ensure_one()
        url = user_id.partner_id.sudo().with_context(signup_valid=True)._get_signup_url_for_action(
            view_type="form",
            res_id=res_id,
            model=res_model,
        )[user_id.partner_id.id]
        url = url.replace('res_id', 'id')
        return url
