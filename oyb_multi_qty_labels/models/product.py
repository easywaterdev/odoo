from odoo import fields, models, api, _,http,exceptions
from odoo.exceptions import UserError
from odoo.osv import osv
import math


class CustomProduct(models.Model):
    _inherit = 'product.template'

    def print_label(self):
        product_id = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
        return {
            'name': 'Print Labels',
            'type': 'ir.actions.act_window',
            'res_model': 'product.label.layout',  # Replace with your wizard model name
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_part_number': self.id,
                        'default_product_ids': product_id.ids},
        }



class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'  # Inherited to add one2many for label quantity

    part_number = fields.Many2one('product.template', string='Part Number', required=True,
                                  default=lambda self: self.env.context.get('active_id'))
    total_product_quantity = fields.Integer(string='Total Product Quantity', required=True,default=1)
    label_quantity = fields.Integer(string='Label Quantity', required=True,default=1)
    labels = fields.One2many('custom.product.label.new', 'wizard_id_new', string='Labels')

    @api.depends('print_format')
    def _compute_dimensions(self):
        for wizard in self:
            if 'x' in wizard.print_format and not 'zpl' in wizard.print_format:
                columns, rows = wizard.print_format.split('x')[:2]
                wizard.columns = int(columns)
                wizard.rows = int(rows)
            else:
                wizard.columns, wizard.rows = 1, 1

    @api.onchange('label_quantity')
    def generate_labels(self):
        # Clear existing labels
        self.labels = False

        if self.label_quantity > 0:

            if math.ceil(self.total_product_quantity / self.label_quantity) - math.floor(
                    self.total_product_quantity / self.label_quantity) >= 0.5:
                qty_on_label = math.ceil(self.total_product_quantity / self.label_quantity)

            else:
                qty_on_label = math.floor(self.total_product_quantity / self.label_quantity)

            remainder = self.total_product_quantity - (qty_on_label * (self.label_quantity - 1))

            for i in range(self.label_quantity):
                product_qty = qty_on_label
                if i == self.label_quantity - 1 and remainder > 0:
                    product_qty = remainder
                self.labels += self.labels.new({'product_qty': product_qty})

    def process(self):
        self.ensure_one()
        if self.total_product_quantity != sum(self.labels.mapped('product_qty')):
            raise exceptions.UserError(
                "The Total Product Quantity is different from the sum of Product Quantities in the Labels.")

        xml_id, data = self._prepare_report_data()

        if not xml_id:
            raise exceptions.UserError(_('Unable to find report template for %s format', self.print_format))

        report_action = self.env.ref(xml_id).report_action(None, data=data)
        report_action.update({'close_on_report_download': True})
        return report_action


    def _prepare_report_data(self):
        if self.custom_quantity <= 0:
            raise UserError(_('You need to set a positive quantity.'))
        elif len(self.labels) <= 0:
            raise UserError(_('You need to set a Label Quantity for Labels.'))

        # Get layout grid
        if self.print_format == 'dymo':
            xml_id = 'product.report_product_template_label_dymo'
        elif 'x' in self.print_format and  not 'zpl' in self.print_format:
            xml_id = 'product.report_product_template_label'
        elif 'zpl' in self.print_format:
            xml_id = 'stock.label_product_product'
        else:
            xml_id = ''

        active_model = ''
        if self.product_tmpl_ids:
            products = self.product_tmpl_ids.ids
            active_model = 'product.template'
        elif self.product_ids:
            products = self.product_ids.ids
            active_model = 'product.product'
        else:
            raise UserError(_("No product to print, if the product is archived please unarchive it before printing its label."))

        label_by_product = {}
        for p in products:
            label_by_product[p] = []
            for label in self.labels:
                label_by_product[p].append(label.product_qty)

        # Build data to pass to the report
        data = {
            'active_model': active_model,
            'quantity_by_product': {p: len(self.labels) for p in products},
            'label_by_product': label_by_product,
            'layout_wizard': self.id,
            'price_included': 'xprice' in self.print_format,
        }
        return xml_id, data




class CustomProductLabelNew(models.TransientModel):
    _name = 'custom.product.label.new'

    wizard_id_new = fields.Many2one('product.label.layout', string='Wizard')
    product_qty = fields.Integer(string='Product Quantity')




