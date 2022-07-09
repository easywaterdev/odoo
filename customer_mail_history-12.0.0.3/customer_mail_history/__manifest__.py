# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Email/Message History Of Customers/Suppliers/Partners',
    'version': '12.0.0.3',
    'description': """
        This Module use for view customer email history customer message history Supplier email history supplier 
        vendor message history History of email customer email partner email history partner message history.
        Message history of customer Message history of supplier Message history of partner 
        Email history of customer email history of supplier email history of partner Email customer history
        Email supplier history  Email partner history customer send and receive message history
        customer send message history customer receive message history 
        customer send email history customer receive email history
        customer send mail history customer receive mail history
        vendor message history vendor mail history vendor email history
        partner message history partner mail history partner email history
        customer message history customer mail history customer email history
        supplier message history supplier mail history supplier email history
        vendor message history vendor mail history vendor email history
""",
    'category': 'Sales',
    'summary': 'Display Email/Message History of Customers/Suppliers/Partners',
    'author': 'BrowseInfo',
    "price": 10,
    "currency": 'EUR',
    'website': 'http://www.browseinfo.in',
    'depends': ['base','mail'],
    'data': [
             'views/partner_mail_views.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    "live_test_url": "https://youtu.be/BlJrvw3S7rg",
    "images":['static/description/Banner.png'],
    'license': 'LGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
