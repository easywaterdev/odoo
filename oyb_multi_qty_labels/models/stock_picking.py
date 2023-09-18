from odoo import models, fields, api

class CustomStockMove(models.Model):
    _inherit = 'stock.move'

    def action_open_label_type(self):
        custom_product_wizard = self.env['product.label.layout']

        for move_line in self.move_line_ids:
            # Create a new instance of the custom wizard
            wizard = custom_product_wizard.create({
                'part_number': move_line.product_id.product_tmpl_id.id,
                'total_product_quantity': move_line.qty_done,
                'label_quantity': 1,
                'product_ids': move_line.product_id.ids,
                'labels': [(0, 0, {'product_qty': move_line.qty_done})]
            })

            # Open the custom wizard
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Print Labels',
                'res_model': 'product.label.layout',
                'view_mode': 'form',
                'target': 'new',
                'res_id': wizard.id,
            }

            return action
