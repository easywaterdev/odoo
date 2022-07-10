# -*- coding: utf-8 -*-
# Copyright 2018-Today datenpol gmbh (<http://www.datenpol.at>)
# License OPL-1 or later (https://www.odoo.com/documentation/user/12.0/legal/licenses/licenses.html#licenses).

# noinspection PyStatementEffect
{
    'name': 'ZPL Printer Pro',
    'summary': 'Print labels on Zebra Printers via FTP using ZPL and Jinja2 Template rendering',
    'description': """Print labels on Zebra Printers via FTP using ZPL and Jinja2 Template rendering.
    Dev:
    Create a button in your model and use print_model or print_values.

    Tools:
    online zpl viewer/designer (use with care, does not generate 100% design solutions, useful as basis):
    http://labelary.com

    zpl documentation:
    http://labelary.com/docs.html

    https://www.zebra.com/content/dam/zebra/manuals/en-us/software/zpl-zbi2-pm-en.pdf

    https://www.zebra.com/content/dam/zebra/manuals/en-us/software/zplii-pm-vol2-en.pdf
    """,
    'version': '12.0.1.1.0',
    'license': 'OPL-1',
    'author': 'datenpol gmbh',
    'support': 'office@datenpol.at',
    'website': 'https://www.datenpol.at',
    'depends': [
        'base'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dp_print_zpl.xml',
    ],
    'images': [
        'static/description/Banner.jpg'
    ],
    'price': 399.00,
    'currency':'EUR',
    'installable': True,
    'auto_install': False,
    'application': True
}
