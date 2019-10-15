# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        print("HELLO I'M HERE")

        # for delivery in self.picking_ids.filtered(lambda p: p.picking_type_id.is_auto_packing):
        #     print(delivery)
        #     # TODO: Might need to move this to super action_assign on a stock.picking
        #     for move in delivery.move_ids_without_package:
        #         # Reverse sorted list of the package types(biggest package qty first)
        #         pack_list = move.product_id.packaging_type_ids.sorted(key=lambda r: r.qty, reverse=True)
        #         if pack_list:
        #             print(pack_list.name_get())
        #             move.pack_move(move.reserved_availability, pack_list)
        #             # move.quantity_done = move.reserved_availability
        return res
