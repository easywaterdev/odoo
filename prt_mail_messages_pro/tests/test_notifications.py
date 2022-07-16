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

from odoo.tests import common


class TestMessageNotification(common.TransactionCase):

    def setUp(self):
        super(TestMessageNotification, self).setUp()
        Partner = self.env["res.partner"]

        self.partner_test_1 = Partner.create({
            "name": "Geomer Max", "email": "geomer198@gmail.com"
        })

        self.partner_test_2 = Partner.create({
            "name": "Test Partner", "email": "geomer.test@gmail.com"
        })

    def test_base_send_notification_without_wizard(self):
        self.message_test = self.env["mail.message"].create({
            "author_allowed_id": self.partner_test_1.id,
            "author_display": "Geomer Max",
            "author_id": self.partner_test_1.id,
            "body": "TEST#1",
            "display_name": "Quote for 600 Chairs",
            "email_from": '"Geomer Max" <geomer198@gmail.com>',
        })

        state_notify = self.partner_test_1._notify(
            self.message_test,
            [{
                "id": self.partner_test_2.id,
                "active": True,
                "share": True,
                "groups": [None],
                "notif": "email",
                "type": "customer",
            }],
            self.partner_test_2,
            force_send=True,
            mail_auto_delete=True,
            send_after_commit=True,
        )
        self.assertTrue(state_notify)
