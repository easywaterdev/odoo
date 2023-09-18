# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError


#
class ReportProductTemplateLabel(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        return self._prepare_data(data)

    def _prepare_data(self, data):
        # change product ids by actual product object to get access to fields in xml template
        # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template'].with_context(display_default_code=False)
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product'].with_context(display_default_code=False)
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        total = 0
        quantity_by_product = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))

            label_by_product = data.get('label_by_product')
            quantity_by_product[product].append((product.barcode, q, label_by_product[p]))
            total += q

            # Append the values to quantity_by_product dictionary

        if data.get('custom_barcodes'):
            # we expect custom barcodes format as: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
                total += sum(qty for _, qty in barcodes_qtys)

        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        if not layout_wizard:
            return {}


        return {
            # 'label_qty': {label_line.product_qty for label_line in label},
            'quantity': quantity_by_product,
            'rows': layout_wizard.rows,
            'columns': layout_wizard.columns,
            'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
            'price_included': data.get('price_included'),
            'extra_html': layout_wizard.extra_html,
        }


class ReportProductTemplateLabelDymo(models.AbstractModel):
    _inherit = 'report.product.report_producttemplatelabel_dymo'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        return self._prepare_data(data)

    def _prepare_data(self, data):
        # change product ids by actual product object to get access to fields in xml template
        # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template'].with_context(display_default_code=False)
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product'].with_context(display_default_code=False)
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        total = 0
        quantity_by_product = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))

            label_by_product = data.get('label_by_product')
            quantity_by_product[product].append((product.barcode, q, label_by_product[p]))
            total += q

            # Append the values to quantity_by_product dictionary

        if data.get('custom_barcodes'):
            # we expect custom barcodes format as: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
                total += sum(qty for _, qty in barcodes_qtys)

        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        if not layout_wizard:
            return {}

        return {
            # 'label_qty': {label_line.product_qty for label_line in label},
            'quantity': quantity_by_product,
            'rows': layout_wizard.rows,
            'columns': layout_wizard.columns,
            'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
            'price_included': data.get('price_included'),
            'extra_html': layout_wizard.extra_html,
        }


class ReportProductLabel(models.AbstractModel):
    _inherit = 'report.stock.label_product_product_view'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template']
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product']
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        quantity_by_product = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))
            label_by_product = data.get('label_by_product')
            quantity_by_product[product].append((product.barcode, label_by_product[p]))
        if data.get('custom_barcodes'):
            # we expect custom barcodes to be: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
        data['quantity'] = quantity_by_product
        return data
