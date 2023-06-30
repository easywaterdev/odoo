# -*- coding: utf-8 -*-
{
    'name': 'EasyWater Return/Refund Sales Report',
    'summary': 'EasyWater Return/Refund Sales Report',
    'description': """
    This a custom Sales Report that will be launched from Sales > Reporting.
    The menu item will be called "Return/Refund Sales Report".
    The menu item will launch a custom wizard that allows the user to select the start date
     and end date. The wizard will have a "Print" button that will execute the report logic.
     The report logic will build a report that uses confirmed sales order lines where the order 
     date is in the date range and credit memo lines where the credit memo date is within the date range.
    """,
    'author': 'OYBI',
    'website': 'https://www.oybi.com',
    "category": 'Sales',
    "type":  'Module',
    'version': '15.0.0.1',
    'license': 'OPL-1',
    'depends': ['base', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'reports/sale_return_refund.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False
}
