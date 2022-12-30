{
    'name': "Easywater Avatax Fix",

    'summary': "Easywater Avatax Fix",

    'description': """
        This customization was written by OYBI for Easywater. The purpose of this customization is to automatically click the Update Avatax on Sales Orders when the 
        user clicks "Mark Quotation as Sent". The core module account_avatax_sale does this when actually sending the quote, but not when manually marking as sent.
       
 """,

    'author': "OYBI",
    'website': "https://www.oybi.com",
    'category': 'Extra Tools',
    'version': '15.0.0.1',
    'license': 'OPL-1',
    'application': False,
    'installable': True,

    'depends': [
        'base',
        'account_avatax_sale'
    ],

    'data': [
    ]
}