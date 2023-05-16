# -*- coding: utf-8 -*-
{
    'name': 'EasyWater Commercial Configurator',
    'summary': 'EasyWater Commercial Configurator',
    'description': """
    The purpose of this customization is to override the generated description on sales order lines for configured 
    products (variants). The program will likely need to be an inheritance/override to the Configurator Wizard.
    The program will only proceed if the product selected is in the product category “Commercial Products” or within a 
    Product Category that is a child of Commercial Products at any level.
    """,
    'author': 'OYBI',
    'website': 'https://www.oybi.com',
    "category": 'Inventory',
    'version': '15.0.0.1',
    'license': 'OPL-1',
    'depends': [
        'stock',
        'sale_management',
    ],
    
    'data': [
        'views/product_template_views.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False
}