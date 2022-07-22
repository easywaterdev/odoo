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

from odoo import _
from odoo.tests import common


@common.tagged("post_install", "-at_install")
class TestUserAccessMessage(common.TransactionCase):
    """
    TEST 1 : Check user has group
        - user hasn't group

    TEST 2 : Check conversation access for user
        - user doesn't have access to conversation #1
        - user doesn't have access to conversation #2

    TEST 3 : Add user groups conversation own
        [Add group to user]
        [Add user to conversation #1]
        - user has access to conversation #1
        - user doesn't have access to conversation #2

    TEST 4 : Add user groups conversation all
        [Add group to user]
        [Add user to conversation #1]
        - user has access to conversation #1
        - user has access to conversation #2
    """

    def setUp(self):
        super(TestUserAccessMessage, self).setUp()
        self.Users = self.env["res.users"]
        self.CetmixConversation = self.env["cetmix.conversation"]
        self.MailMessage = self.env["mail.message"]

        self.res_users_test = self.Users.create(
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
                "partner_ids": [(4, self.res_users_test.partner_id.id)],
            }
        )

        self.cetmix_conversation_2 = self.CetmixConversation.create(
            {
                "active": True,
                "name": "Test Conversation #2",
            }
        )

        self.mail_message_conversation_1 = self.cetmix_conversation_1.message_post(
            body=_("Test message #1 for Conversation 1")
        )

        self.mail_message_conversation_2 = self.cetmix_conversation_2.message_post(
            body=_("Test message #1 for Conversation 2")
        )

    def _message_accessible(self, user_id, model_name, res_id, _id):
        """
        Check record accessible
        :return: record or False
        """
        return (
            self.MailMessage.with_context(check_messages_access=True)
            .with_user(user_id)
            .search(
                [
                    ("model", "=", model_name),
                    ("res_id", "=", res_id),
                    ("id", "=", _id),
                ]
            )
        )

    # -- TEST 1 : Check user has group
    def test_check_not_have_group(self):
        """User not have conversation own group"""
        self.assertFalse(
            self.res_users_test.has_group("prt_mail_messages.group_conversation_own")
        )

    # -- TEST 2 : Check conversation access for user
    def test_no_conversation_access(self):
        """User does not have access to Conversations"""
        conversation_1 = self._message_accessible(
            self.res_users_test.id,
            self.CetmixConversation._name,
            self.cetmix_conversation_1.id,
            self.mail_message_conversation_1.id,
        )
        conversation_2 = self._message_accessible(
            self.res_users_test.id,
            self.CetmixConversation._name,
            self.cetmix_conversation_2.id,
            self.mail_message_conversation_2.id,
        )
        self.assertFalse(conversation_1)
        self.assertFalse(conversation_2)

    # -- TEST 3 : Add user groups conversation own
    def test_own_conversations_only(self):
        """User has access to own Conversations only"""
        self.res_users_test.write(
            {"groups_id": [(4, self.ref("prt_mail_messages.group_conversation_own"))]}
        )
        self.cetmix_conversation_1.write(
            {"partner_ids": [(4, self.res_users_test.partner_id.id)]}
        )
        conversation_1 = self._message_accessible(
            self.res_users_test.id,
            self.CetmixConversation._name,
            self.cetmix_conversation_1.id,
            self.mail_message_conversation_1.id,
        )
        conversation_2 = self._message_accessible(
            self.res_users_test.id,
            self.CetmixConversation._name,
            self.cetmix_conversation_2.id,
            self.mail_message_conversation_2.id,
        )
        self.assertTrue(conversation_1)
        self.assertFalse(conversation_2)

    # -- TEST 4 : Add user groups conversation all
    def test_all_conversations(self):
        """User has access to all Conversations"""
        self.res_users_test.write(
            {"groups_id": [(4, self.ref("prt_mail_messages.group_conversation_all"))]}
        )
        self.cetmix_conversation_1.write(
            {"partner_ids": [(4, self.res_users_test.partner_id.id)]}
        )
        conversation_1 = self._message_accessible(
            self.res_users_test.id,
            self.CetmixConversation._name,
            self.cetmix_conversation_1.id,
            self.mail_message_conversation_1.id,
        )
        conversation_2 = self._message_accessible(
            self.res_users_test.id,
            self.CetmixConversation._name,
            self.cetmix_conversation_2.id,
            self.mail_message_conversation_2.id,
        )
        self.assertTrue(conversation_1)
        self.assertTrue(conversation_2)
