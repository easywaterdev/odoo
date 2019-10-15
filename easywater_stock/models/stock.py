# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class PickingType(models.Model):
    _inherit = "stock.picking.type"

    is_auto_packing = fields.Boolean(string="Automated Packaging")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def auto_pack(self):
        print("Inside auto_pack")

    @api.multi
    def action_assign(self):
        res = super(StockPicking, self).action_assign()
        print("WE ARE INSIDE ACTION ASSIGN")
        # If the type is auto_packing and the delivery method is set
        auto_picks = self.filtered(lambda p: p.picking_type_id.is_auto_packing and p.sale_id.carrier_id)
        for pick in auto_picks:
            print("this is a auto designated type")
            print(pick)
            for move in pick.move_ids_without_package:
                # Reverse sorted list of the package types(biggest package qty first)
                pack_list = move.product_id.packaging_type_ids.filtered(
                    lambda l: l.package_carrier_type == pick.carrier_id.delivery_type
                ).sorted(key=lambda r: r.qty, reverse=True)
                if pack_list:
                    print(pack_list.name_get())
                    move.pack_move(move.reserved_availability, pack_list)
        return res


class StockMove(models.Model):
    _inherit = "stock.move"

    # Logic to find the best fit package type, returns index
    @api.multi
    def find_fit_index(self, cur_res_qty, pack_list):
        for i in range(0, len(pack_list)):
            cur_pack_qty = pack_list[i].qty
            try:
                next_pack_qty = pack_list[i+1].qty
            except IndexError:
                next_pack_qty = -1.0
            if cur_pack_qty <= cur_res_qty or cur_res_qty > next_pack_qty:
                return i
        return -1

    # Logic to create packages and auto fill the package details
    @api.multi
    def do_auto_pack(self, pack_list, fit_index, qty_to_pack):
        pack_no_type = self.picking_id.put_in_pack()
        quant_pack = self.env['stock.quant.package']
        cur_package = quant_pack.browse(pack_no_type['context']['default_stock_quant_package_id'])
        if cur_package:
            cur_package.packaging_id = pack_list[fit_index]
            cur_package.shipping_weight = qty_to_pack * self.product_id.weight
        else:
            _logger.error('There was no package for the current stock.move, %s', self._name)

    # Logic to pack the current move, ensure everything is correctly sorted
    @api.multi
    def pack_move(self, cur_res_qty, pack_list):
        self.ensure_one()
        if not cur_res_qty:
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _("There must be a reserved quantity on the picking, %s, to auto package.") % (
                        self._name),
                },
            }
        while cur_res_qty:
            move_line_ids = self.move_line_ids.filtered(lambda o: not o.result_package_id)
            if not move_line_ids:
                return False
            fit_index = self.find_fit_index(cur_res_qty, pack_list)
            # If there is no suitable box
            if fit_index < 0:
                return False
            else:
                qty_to_pack = pack_list[fit_index].qty

                if qty_to_pack < 1:
                    raise UserError(_('Package Types for %s must have max quantity greater than 0 for auto pack.' % pack_list[fit_index].name_get()))
                # ex: cur_res_qty = 3 and qty_to_pack = 3
                if cur_res_qty == qty_to_pack:
                    move_line_ids.qty_done = qty_to_pack
                    self.do_auto_pack(pack_list, fit_index, qty_to_pack)
                    cur_res_qty = 0
                # ex: cur_res_qty = 4 and qty_to_pack = 3
                elif cur_res_qty > qty_to_pack:
                    move_line_ids.qty_done = qty_to_pack
                    self.do_auto_pack(pack_list, fit_index, qty_to_pack)
                    cur_res_qty = cur_res_qty - qty_to_pack
                # ex: cur_res_qty = 2 and qty_to_pack = 3
                else:
                    move_line_ids.qty_done = cur_res_qty
                    self.do_auto_pack(pack_list, fit_index, qty_to_pack)
                    cur_res_qty = 0


class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
