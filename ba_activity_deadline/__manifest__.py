# -*- coding: utf-8 -*-
{
    'name': 'Activity Reminder',
    'version': '12.0.1.0',
    'author': 'AppsTG',
    'website': 'https://appstg.com',
    'category': 'Sales',
    'support': 'info@appstg.com',
    'summary': 'Activity Due Date in datetime format. Reminder of Due Date',
    'description': '',
    'license': 'OPL-1',
    'price': 34.90,
    'currency': 'EUR',
    'images': ['static/description/banner.jpg'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/email_template.xml',
        'views/views.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'depends': ['mail'],
    'application': True,
}
