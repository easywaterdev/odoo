# -*- coding: utf-8 -*-
{
    'name': "3CX Integration",

    'summary': """Lets you integrate 3CX with your Contacts,
        Configure using clientPhone and callerName in the URL in your 3CX configuration.
        URL should be https://your_odoo_instance.com/3cx/clientPhone OR https://your_odoo_instance.com/3cx/clientPhone/callerName""",

    'description': """
        Lets you integrate 3CX with your Contacts,
        Configure using clientPhone and callerName in the URL in your 3CX configuration.
        URL should be https://your_odoo_instance.com/3cx/clientPhone OR https://your_odoo_instance.com/3cx/clientPhone/callerName
    """,

    'author': "Nalios",
    'website': "https://nalios.be",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'application': True,
    'version': '16.0.0.1',
    'price': 39.00,
    'currency': 'EUR',
    'license': 'OPL-1',
    'images': ['static/description/main_screenshot.png',],
    'support': 'lop@nalios.be',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/res_partner_views.xml',
    ],
}
