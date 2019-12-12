# -*- coding: utf-8 -*-
{
    "name": "Send Message Composer",
    "version": "12.0.1.0.1",
    "category": "Discuss",
    "author": "Odoo Tools",
    "website": "https://odootools.com/apps/12.0/send-message-composer-379",
    "license": "Other proprietary",
    "application": True,
    "installable": True,
    "auto_install": False,
    "depends": [
        "base"
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/views.xml"
    ],
    "qweb": [
        
    ],
    "js": [
        
    ],
    "demo": [
        
    ],
    "external_dependencies": {},
    "summary": "The tool to always open a full composer on the button 'Send a Message'",
    "description": """
    In case you wanted to apply advanced styles for your message or you wanted to add a few recipients, in standard Odoo you should expand a message. Often quick messages are just out of use. In such a case this tool is for you: it let users avoid an excess click.

    The tool works for the button 'Send message' under any Odoo document
    As soon as the button 'Send message' is pressed, the app redirects to the full-featured pop-up email composer window
    Before (if the tool is NOT installed)
    After (as soon as the module is installed)
""",
    "images": [
        "static/description/main.png"
    ],
    "price": "0.0",
    "currency": "EUR",
}