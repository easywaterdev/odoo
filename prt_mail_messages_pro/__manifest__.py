###################################################################################
# 
#    Copyright (C) Cetmix OÜ
#
#   Odoo Proprietary License v1.0
# 
#   This software and associated files (the "Software") may only be used (executed,
#   modified, executed after modifications) if you have purchased a valid license
#   from the authors, typically via Odoo Apps, or if you have received a written
#   agreement from the authors of the Software (see the COPYRIGHT file).
# 
#   You may develop Odoo modules that use the Software as a library (typically
#   by depending on it, importing it and using its resources), but without copying
#   any source code or material from the Software. You may distribute those
#   modules under the license of your choice, provided that this license is
#   compatible with the terms of the Odoo Proprietary License (For example:
#   LGPL, MIT, or proprietary licenses similar to this one).
# 
#   It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#   or modified copies of the Software.
# 
#   The above copyright notice and this permission notice must be included in all
#   copies or substantial portions of the Software.
# 
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#   DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#   ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#   DEALINGS IN THE SOFTWARE.
#
###################################################################################

{
    "name":
        "Mail Messages Easy Pro:"
        " Show Lost Message, Move Message, Reply, Forward,"
        " CC BCC Move or Delete from Chatter, Hide Messages in Chatter",
    "version": "12.0.6.1.1",
    "summary": """Message Preview Move Edit Delete CC BCC""",
    "author": "Ivan Sokolov, Cetmix",
    "license": "OPL-1",
    "price": 149.00,
    "currency": "EUR",
    "category": "Discuss",
    "support": "odooapps@cetmix.com",
    "website": "https://cetmix.com",
    "live_test_url": "https://demo.cetmix.com",
    "description":
        """
Show Lost Messages, Move Messages, Reply, Forward,
 Move or Delete from Chatter, Hide Messages Notes Notifications
  in Chatter, CC BCC
""",
    "depends": ["prt_mail_messages","base","bom_cost_price_hide", "dp_print_zpl"],
    "data": [
        "security/groups.xml",
        "data/templates.xml",
        "views/mail_mail.xml",
        "views/mail_message.xml",
        "views/res_company.xml",
        "views/res_users.xml",
        "wizard/message_assign_author.xml",
        "wizard/message_move.xml",
        "wizard/mail_composer.xml",
    ],
    "images": ["static/description/banner_pro.gif"],
    "qweb": ["static/src/xml/qweb.xml"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
