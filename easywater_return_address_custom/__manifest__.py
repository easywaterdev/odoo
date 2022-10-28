{
    'name': "Easywater Return Address Customization",

    'summary': "Easywater Return Address Customization",

    'description': """

 """,

    'author': "OYBI",
    'website': "https://www.oybi.com",
    'category': 'Extra Tools',
    'version': '15.0.0.54',
    'license': 'OPL-1',
    'application': False,
    'installable': True,

    'depends': [
        'base',
        'sale',
        'delivery_ups',
    ],

    'data': [
        'views/res_users_views_custom.xml',
    ]
}