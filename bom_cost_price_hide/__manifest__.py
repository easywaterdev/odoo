# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Bill of Material Cost Price Hide/Show',
    'version': '3.2.4',
    'price': 69.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Manufacturing/Manufacturing',
    'summary':  """This module add feature to hide a bom cost price on bom report.""",
    'support': 'contact@probuse.com',
    'author' : 'Probuse Consulting Service Pvt. Ltd.',
    'website' : 'www.probuse.com',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/bom_cost_price_hide/1029',#'https://youtu.be/JLHFYxfLFAg',
    'images': ['static/description/img1.png'],
    'description': """
    Product cost price hide on BoM Structure & Cost 
This module add feature to hide a cost price on BoM Structure & Cost.
Bill of Material Cost Price Hide/Show
bom cost price hide
bom cost hide
price hide
cost price hide bom

    """,
    'depends': [
        'mrp',
        'product_cost_price_hide',
        'mrp_account',
     ],
    'data': [
        'views/mrp_report_bom_structure.xml',
     ],
    
    'installable': True,
    'application': False,
}
