# -*- coding: utf-8 -*-
{
    'name': 'Mail Messages Easy Pro:'
            ' Show Lost Message, Move Message, Reply, Forward, Move or Delete from Chatter, Hide Notifications in Chatter',
    'version': '12.0.2.3',
    'summary': """Extra features for free 'Mail Messages Easy' app""",
    'author': 'Ivan Sokolov',
    'license': 'OPL-1',
    'price': 49.00,
    'currency': 'EUR',
    'category': 'Discuss',
    'support': 'odooapps@cetmix.com',
    'website': 'https://demo.cetmix.com',
    'live_test_url': 'https://demo.cetmix.com',
    'description': """
Show Lost Messages, Move Messages, Reply, Forward, Move or Delete from Chatter, Hide Notifications in Chatter and more
""",
    'depends': ['prt_mail_messages', 'mail'],
    'data': [
        'security/groups.xml',
        'views/prt_mail_pro.xml',
        'views/mail_assign.xml',
        'data/prt_templates.xml'
    ],

    'images': ['static/description/banner_pro.png'],

    'qweb': [
        'static/src/xml/qweb.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False
}
