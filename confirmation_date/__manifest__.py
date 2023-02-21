# -*- coding: utf-8 -*-
{
    'name': 'Original Confirmation Date',
    'summary': 'Original Confirmation Date',
    'description': """
        This customization was written by Brian Lefler @ OYBI (https://www.oybi.com) for Easywater. This customization 
        adds an "Original Confirmation Date" to the sale.order model that is set when confirming an order by using the 
        current date unless there is already a date in the field. This field is also copied to the sale.report 
        model for reporting.
    """,
    'version': '16.0.0.1',
    'author': 'OYBI',
    'website': 'https://www.oybi.com',
    'category': 'Sales',
    'depends': ['sale_management'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'demo': [],
    'license': 'OPL-1',
    'assets': {}
}
