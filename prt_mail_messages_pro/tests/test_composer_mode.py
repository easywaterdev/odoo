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
from odoo.tools import email_split
from odoo.tools.misc import mute_logger


@common.tagged("post_install", "-at_install")
class TestMailComposer(common.TransactionCase):
    """
    Test mail composer 'Odoo' and 'Email' modes
    """

    def setUp(self):
        super(TestMailComposer, self).setUp()
        self.MailCompose = self.env["mail.compose.message"]
        Partner = self.env["res.partner"]

        # Monkey patch to keep sent mails for further check
        def unlink_replacement(self):
            return

        self.env["mail.mail"]._patch_method("unlink", unlink_replacement)

        # Our partners
        self.test_record = Partner.create({
            "name": "Partner Record", "email": "partner@example.com"
        })
        self.bob = Partner.create({"name": "Bob", "email": "bob@example.com"})
        self.kate = Partner.create({"name": "Kate", "email": "kate@example.com"})
        self.mike = Partner.create({"name": "Mike", "email": "mike@example.com"})
        self.john = Partner.create({"name": "John", "email": "john@example.com"})
        self.ann = Partner.create({"name": "Ann", "email": "ann@example.com"})

        # Subscribe Bob to Record
        self.test_record.message_subscribe(partner_ids=[self.bob.id])

    def tearDown(self):

        # Remove the monkey patch
        self.env["mail.mail"]._revert_method("unlink")
        super(TestMailComposer, self).tearDown()

    # @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_odoo_mode(self):
        """ Send a new message in Odoo mode """

        # Send new message
        # recipients: Kate and Mike
        composer = self.MailCompose.with_context({
            "default_composition_mode": "comment",
            "default_model": "res.partner",
            "default_res_id": self.test_record.id,
        }).create({
            "partner_ids": [
                (4, self.kate.id),
                (4, self.mike.id),
            ],
            "subject": "Test Odoo Mode",
            "body": "Test Odoo Mode",
            "wizard_type": "odoo",
        })
        composer.send_mail()

        mail = self.env["mail.mail"].search([])
        self.assertEqual(
            len(mail),
            1,
            msg="Must be 1 mail messages: one for the follower,"
            " another one for recipients",
        )

        recipients = mail.recipient_ids.ids
        self.assertEqual(len(recipients), 3)
        self.assertIn(self.bob.id, recipients, msg="Bob must be recipient")
        self.assertIn(self.kate.id, recipients, msg="Kate must be recipient")
        self.assertIn(self.mike.id, recipients, msg="Mike must be recipient")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_email_mode(self):
        """ Send a new message in Email mode"""

        # Send new message
        # record: partner Agrolait
        # recipients: Thomas Passot and Michel Fletcher
        # cc: Chao Wang
        # bcc: David Simpson
        composer = self.MailCompose.with_context({
            "default_composition_mode": "comment",
            "default_model": "res.partner",
            "default_res_id": self.test_record.id,
        }).create({
            "partner_ids": [
                (4, self.kate.id),
                (4, self.mike.id),
            ],
            "partner_cc_ids": [(4, self.john.id)],
            "partner_bcc_ids": [(4, self.ann.id)],
            "subject": "Test Email Mode",
            "body": "Test Email Mode",
            "wizard_type": "email",
        })
        composer.send_mail()

        mail = self.env["mail.mail"].search([])
        self.assertEqual(
            len(mail),
            1,
            msg="Must be 1 mail messages: one for all recipients",
        )

        # Recipients field must be empty
        # Because all recipients are now in email_to field
        self.assertFalse(mail.recipient_ids, msg="Must be no recipients")

        # Extract email addresses
        # To:
        to_addrs = email_split(mail.email_to)
        self.assertEqual(len(to_addrs), 2, msg="Must be 2 addresses in the 'to:' field")

        self.assertIn(
            "kate@example.com",
            to_addrs,
            msg="'kate@example.com' must be in the 'to:' field",
        )
        self.assertIn(
            "mike@example.com",
            to_addrs,
            msg="'mike@example.com' must be in the 'to:' field",
        )

        # Cc:
        cc_addrs = email_split(mail.email_cc)
        self.assertEqual(len(cc_addrs), 1, msg="Must be 1 address in the 'cc:' field")
        self.assertIn(
            "john@example.com",
            cc_addrs,
            msg="'john@example.com' must be in the 'cc:' field",
        )

        # Bcc:
        bcc_addrs = email_split(mail.email_bcc)
        self.assertEqual(len(bcc_addrs), 1, msg="Must be 1 address in the 'bcc:' field")
        self.assertIn(
            "ann@example.com",
            bcc_addrs,
            msg="'ann@example.com' must be in the 'bcc:' field",
        )
