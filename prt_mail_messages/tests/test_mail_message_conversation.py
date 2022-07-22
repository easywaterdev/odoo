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

from datetime import timedelta

from odoo import fields
from odoo.tests import common


@common.tagged("post_install", "-at_install")
class TestMailMessageConversation(common.TransactionCase):
    """
    TEST 1 : Unlink all messages from conversation
        [Get conversation messages]
        - count messages is 2
        [Messages move to trash (unlink_pro)]
        - conversation active is False
        - conversation message #1 active is False
        - conversation message #1 delete uid is not empty
        - conversation message #1 delete date is not empty
        - conversation message #2 active is False
        - conversation message #2 delete uid is not empty
        - conversation message #2 delete date is not empty
        [Get conversation messages]
        [Message delete (unlink_pro)]
        - message #1 not found
        - message #2 not found

    TEST 2 : Get (undelete) message from trash
        [Get conversation messages]
        [messages moveto trash]
        - conversation # 1 active is False
        - conversation message #1 active is False
        - conversation message #1 delete uid is not empty
        - conversation message #1 delete date is not empty
        - conversation message #2 active is False
        - conversation message #2 delete uid is not empty
        - conversation message #2 delete date is not empty
        [Message undelete]
        - conversation #1 active is True
        - conversation message #1 active is True
        - conversation message #2 active is True

    TEST 3 : Delete message by cron
        [Set config delete trash days = 1]
        [compute date on three days ago]
        [Create mail message]
        [Start cron unlink function (_unlink_trash_message)]
        [Get message by field 'reply to']
        - message is not found

    TEST 4 : Unlink empty conversation
        [Set config delete trash days = 1]
        [Move to trash conversation message #1 and #2]
        [Unlink messages by cron from trash]
        - conversation not found
    """

    def setUp(self):
        super(TestMailMessageConversation, self).setUp()
        self.Users = self.env["res.users"]
        self.CetmixConversation = self.env["cetmix.conversation"]
        self.MailMessage = self.env["mail.message"]

        self.res_users = self.Users.create(
            {
                "name": "Test User #1",
                "login": "test_user",
                "email": "testuser1@example.com",
                "groups_id": [(4, self.ref("base.group_user"))],
            }
        )

        self.cetmix_conversation_1 = self.CetmixConversation.create(
            {
                "active": True,
                "name": "Test Conversation #1",
                "partner_ids": [(4, self.res_users.partner_id.id)],
            }
        )

        self.mail_message_1 = self.MailMessage.with_user(self.env.user.id).create(
            {
                "res_id": self.cetmix_conversation_1.id,
                "model": self.CetmixConversation._name,
                "reply_to": "test.reply@example.com",
                "email_from": "test.from@example.com",
                "body": "Mail message Body #1",
            }
        )

        self.mail_message_2 = self.MailMessage.with_user(self.env.user.id).create(
            {
                "res_id": self.cetmix_conversation_1.id,
                "model": self.CetmixConversation._name,
                "reply_to": "test.reply@example.com",
                "email_from": "test.from@example.com",
                "body": "Mail message Body #2",
            }
        )

    def _get_messages_by_conversation_id(self, conversation_id):
        return self.MailMessage.with_context(active_test=False).search(
            [
                ("res_id", "=", conversation_id),
                ("message_type", "!=", "notification"),
            ]
        )

    # -- TEST 1 : Unlink all messages from conversation
    def test_unlink_conversation_message(self):
        """Unlink all messages from conversation"""
        messages = self._get_messages_by_conversation_id(self.cetmix_conversation_1.id)
        messages.unlink_pro()

        self.assertFalse(self.cetmix_conversation_1.active)
        self.assertFalse(self.mail_message_1.active)
        self.assertNotEqual(self.mail_message_1.delete_uid, False)
        self.assertNotEqual(self.mail_message_1.delete_date, False)
        self.assertFalse(self.mail_message_2.active)
        self.assertNotEqual(self.mail_message_2.delete_uid, False)
        self.assertNotEqual(self.mail_message_2.delete_date, False)
        messages = self._get_messages_by_conversation_id(self.cetmix_conversation_1.id)
        messages.unlink_pro()
        self.assertFalse(self.MailMessage.search([("id", "=", self.mail_message_1.id)]))
        self.assertFalse(self.MailMessage.search([("id", "=", self.mail_message_2.id)]))

    # -- TEST 2 : Get (undelete) message from trash
    def test_undelete_conversation(self):
        """Get (undelete) message from trash"""
        messages = self._get_messages_by_conversation_id(self.cetmix_conversation_1.id)
        messages.unlink_pro()
        self.assertFalse(self.cetmix_conversation_1.active)
        self.assertFalse(self.mail_message_1.active)
        self.assertNotEqual(self.mail_message_1.delete_uid, False)
        self.assertNotEqual(self.mail_message_1.delete_date, False)
        self.assertFalse(self.mail_message_2.active)
        self.assertNotEqual(self.mail_message_2.delete_uid, False)
        self.assertNotEqual(self.mail_message_2.delete_date, False)
        messages.undelete()
        self.assertTrue(self.cetmix_conversation_1.active)
        self.assertTrue(self.mail_message_1.active)
        self.assertTrue(self.mail_message_2.active)

    # -- TEST 3 : Delete message by cron
    def test_unlink_trash_message(self):
        """Delete message by cron"""
        self.env["ir.config_parameter"].sudo().set_param(
            "cetmix.messages_easy_empty_trash", 1
        )
        compute_datetime = fields.Datetime.now() - timedelta(days=3)

        self.MailMessage.sudo().create(
            {
                "reply_to": "test.expl@example.com",
                "email_from": "test.from@example.com",
                "active": False,
                "delete_uid": self.res_users.id,
                "delete_date": compute_datetime,
            }
        )

        self.MailMessage._unlink_trash_message()
        mail_message = self.MailMessage.sudo().search(
            [("reply_to", "=", "test.expl@example.com")]
        )
        self.assertFalse(mail_message)

    # -- TEST 4 : Unlink empty conversation
    def test_unlink_all_conversation_message(self):
        """Unlink empty conversation"""
        self.env["ir.config_parameter"].sudo().set_param(
            "cetmix.messages_easy_empty_trash", 1
        )
        self.mail_message_1.unlink_pro()
        self.mail_message_2.unlink_pro()
        self.MailMessage._unlink_trash_message(
            test_custom_datetime=fields.Datetime.now()
        )
        empty_conversation_1 = self.CetmixConversation.with_context(
            active_test=False
        ).search(
            [
                ("id", "=", self.cetmix_conversation_1.id),
            ]
        )
        self.assertFalse(empty_conversation_1)
