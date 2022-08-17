{
    'name': "Easywater Redirect Email",

    'summary': "Easywater Redirect Email",

    'description': """

 """,

    'author': "OYBI",
    'website': "https://www.oybi.com",
    'category': 'Extra Tools',
    'version': '0.1',
    'license': 'OPL-1',
    'application': True,
    'installable': True,

    'depends': [
        'base',
        'contacts',
        'crm',
    ],

    'data': [
        'views/redirect_automated_action.xml'
    ]
}