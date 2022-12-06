{
    'name': "Easywater Sale Order Custom",

    'summary': "Easywater Sale Order Custom",

    'description': """

 """,

    'author': "OYBI",
    'website': "https://www.oybi.com",
    'category': 'Extra Tools',
    'version': '15.0.0.14',
    'license': 'OPL-1',
    'application': False,
    'installable': True,

    'depends': [
        'base',
        'sale_management',
        'delivery',
    ],

    'data': [
        'views/sale_order_view.xml'
    ]
}