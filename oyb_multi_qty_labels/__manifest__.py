# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Multi-Quantity Labels',
    'description': 'Multi-Quantity Labels',
    'author': 'OYBI',
    'website': 'https://www.oybi.com',
    'version': '15.0.0.1',
    'license': 'OPL-1',
    'category': 'Product',
    'type': 'module',
    'depends': ['base', 'product', 'stock', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/template.xml',
        'views/custom_wizard.xml',
        'views/product.xml',
        'views/stock_picking.xml',
    ],
}
