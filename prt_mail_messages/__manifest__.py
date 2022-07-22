###################################################################################
# 
#    Copyright (C) Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

{
    "name": "Mail Messages Easy."
    " Show all messages, Show sent messages,"
    " Reply to message, Forward message,"
    " Archive message, Delete Undelete message,"
    " Quote message, Move message",
    "version": "15.0.0.1.0",
    "summary": """Read and manage all Odoo messages in one place!""",
    "author": "Ivan Sokolov, Cetmix",
    "category": "Discuss",
    "license": "LGPL-3",
    "website": "https://cetmix.com",
    "description": """
 Show all messages, Show sent message, Reply to messages,
  Forward messages, Edit messages, Delete messages, Move messages, Quote messages
""",
    "depends": ["mail"],
    "live_test_url": "https://demo.cetmix.com",
    "images": ["static/description/banner.gif"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "data/data.xml",
        "data/data_cron.xml",
        "views/mail_message.xml",
        "views/conversation.xml",
        "views/partner.xml",
        "views/res_config_settings.xml",
        "views/actions.xml",
        "report/mail_message_paperformat.xml",
        "report/mail_message_report.xml",
        "wizard/message_edit.xml",
        "wizard/message_partner_assign.xml",
        "wizard/message_move.xml",
        "wizard/mail_compose_message.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "prt_mail_messages/static/src/js/list_mixin.js",
            "prt_mail_messages/static/src/js/mail_messages_update_view_list.js",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
