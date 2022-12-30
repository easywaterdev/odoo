{
    'name': "Easywater Sale Order Custom",

    'summary': "Easywater Sale Order Custom",

    'description': """
        This customization was written by OYBI for Easywater. The purpose of this customization is to add validation to the Delivery Method on sales orders. 
        1. You cannot mark a quotation as sent until you have selected a Delivery Method. (Unless the sales team is "Commercial Sales")
        2. You cannot confirm a quotation until you have selected a Delivery Method. (Unless the sales team is "Commercial Sales")
        3. Adds the delivery method (Carrier ID) to the sales order form view underneath payment method.
        4. Defaults the delivery method to blank. If the sales team is "Commercial Sales" then the delivery method is defaulted to "Custom Freight Quote".
 """,

    'author': "OYBI",
    'website': "https://www.oybi.com",
    'category': 'Extra Tools',
    'version': '15.0.0.23',
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