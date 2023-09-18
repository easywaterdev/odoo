from odoo import models, api
from odoo.exceptions import AccessError


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    #
    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     user = self.env.user
    #     if user.has_group('ew_sales_team_restrictions.group_allow_restriction_in_sales_team_new'):
    #         if 'team_id' not in self.env.context:
    #             args += [('team_id', '=', user.sale_team_id.id)]
    #         return super(SaleOrder, self).search(args, offset=offset, limit=limit, order=order, count=count)
    #
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user = self.env.user
        if not user.has_group('ew_sales_team_restrictions.group_allow_restriction_in_sales_team_new'):
            return super(SaleOrder, self).search(args, offset=offset, limit=limit, order=order, count=count)
        else:
            if 'team_id' not in self.env.context:
                args += [('team_id', '=', user.sale_team_id.id)]
            return super(SaleOrder, self).search(args, offset=offset, limit=limit, order=order, count=count)

