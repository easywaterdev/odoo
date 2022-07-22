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

from datetime import datetime
from email.utils import getaddresses

import pytz

from odoo import _, api, fields, models
from odoo.tools import html2plaintext

from .common import DEFAULT_MESSAGE_PREVIEW_LENGTH, IMAGE_PLACEHOLDER, MONTHS

# Used to render html field in TreeView
TREE_TEMPLATE = (
    '<table style="width: 100%%; border: none;" title="Conversation">'
    "<tbody>"
    "<tr>"
    '<td style="width: 1%%;"><img class="rounded-circle" '
    'style="height: auto; width: 64px; padding:10px;"'
    ' src="data:image/png;base64, %s" alt="Avatar" '
    'title="%s" width="100" border="0" /></td>'
    '<td style="width: 99%%;">'
    '<table style="width: 100%%; border: none;">'
    "<tbody>"
    "<tr>"
    '<td id="author"><strong>%s</strong> &nbsp; '
    '<span id="subject">%s</span></td>'
    '<td id="date" style="text-align: right;" title="%s">%s</td>'
    "</tr>"
    "<tr>"
    '<td><p id="notifications" style="font-size: x-small;">'
    "<strong>%s</strong></p></td>"
    '<td id="participants" style="text-align: right;">%s</td>'
    "</tr>"
    "</tbody>"
    "</table>"
    "%s"
    "</td>"
    "</tr>"
    "</tbody>"
    "</table>"
)


# -- Sanitize name. In case name contains @. Use to keep html working
def sanitize_name(name):
    return name.split("@")[0] if "@" in name else name


################
# Conversation #
################
class Conversation(models.Model):
    _name = "cetmix.conversation"
    _description = "Conversation"
    _inherit = ["mail.thread"]
    _order = "last_message_post desc, id desc"

    # -- User is a participant by default. Override in case any custom logic is needed
    def _default_participants(self):
        return [(4, self.env.user.partner_id.id)]

    active = fields.Boolean(string="Active", default=True)
    name = fields.Char(string="Subject", required=True, tracking=True)
    author_id = fields.Many2one(
        string="Author",
        comodel_name="res.partner",
        ondelete="set null",
        default=lambda self: self.env.user.partner_id.id,
    )
    partner_ids = fields.Many2many(
        string="Participants", comodel_name="res.partner", default=_default_participants
    )
    last_message_post = fields.Datetime(string="Last Message")
    last_message_by = fields.Many2one(
        string="Last Message", comodel_name="res.partner", ondelete="set null"
    )
    is_participant = fields.Boolean(
        string="I participate", compute="_compute_is_participant"
    )

    subject_display = fields.Html(string="Subject", compute="_compute_subject_display")
    message_count = fields.Integer(string="Messages", compute="_compute_message_count")
    message_needaction_count = fields.Integer(
        string="Messages", compute="_compute_message_count"
    )

    # -- Name get. Currently using it only for Move Wizard!
    def name_get(self):
        if not self._context.get("message_move_wiz", False):
            return super(Conversation, self).name_get()
        res = [(rec.id, "{} - {}".format(rec.name, rec.author_id.name)) for rec in self]
        return res

    # -- Count messages. All messages except for notifications are counted
    @api.depends("message_ids")
    def _compute_message_count(self):
        for rec in self:
            message_count = 0
            message_needaction_count = 0
            for message in rec.message_ids:
                if message.message_type != "notification":
                    message_count += 1
                    if message.needaction:
                        message_needaction_count += 1
            rec.update(
                {
                    "message_count": message_count,
                    "message_needaction_count": message_needaction_count,
                }
            )

    # -- Get HTML view for Tree View
    @api.depends("name")
    def _compute_subject_display(self):

        # Get preview length. Will use it for message body preview
        body_preview_length = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "cetmix.messages_easy_text_preview", DEFAULT_MESSAGE_PREVIEW_LENGTH
            )
        )

        # Get current timezone
        tz = self.env.user.tz
        if tz:
            local_tz = pytz.timezone(tz)
        else:
            local_tz = pytz.utc

        # Get current time
        now = datetime.now(local_tz)
        # Compose subject
        for rec in self.with_context(bin_size=False):
            # Get message date with timezone
            if rec.last_message_post:
                message_date = pytz.utc.localize(rec.last_message_post).astimezone(
                    local_tz
                )
                # Compose displayed date/time
                days_diff = (now.date() - message_date.date()).days
                if days_diff == 0:
                    date_display = datetime.strftime(message_date, "%H:%M")
                elif days_diff == 1:
                    date_display = "{} {}".format(
                        _("Yesterday"),
                        datetime.strftime(message_date, "%H:%M"),
                    )
                elif now.year == message_date.year:
                    date_display = "{} {}".format(
                        str(message_date.day),
                        _(MONTHS.get(message_date.month)),
                    )
                else:
                    date_display = str(message_date.date())
            else:
                date_display = ""

            # Compose messages count
            message_count = rec.message_count
            # Total messages
            if message_count == 0:
                message_count_text = _("No messages")
            else:
                message_count_text = "{} {}".format(
                    str(message_count),
                    _("message") if message_count == 1 else _("messages"),
                )
                # New messages
                message_needaction_count = rec.message_needaction_count
                if message_needaction_count > 0:
                    message_count_text = "{}, {} {}".format(
                        message_count_text,
                        str(message_needaction_count),
                        _("new"),
                    )

            # Participants
            participant_text = ""
            for participant in rec.partner_ids:
                participant_text = "{} {}".format(
                    participant_text,
                    '<img class="rounded-circle"'
                    ' style="width:24px;max-height:24px;margin:2px;"'
                    ' title="%s" src="data:image/png;base64, %s"/>'
                    % (
                        sanitize_name(participant.name),
                        participant.image_128.decode("utf-8")
                        if participant.image_128
                        else IMAGE_PLACEHOLDER,
                    ),
                )
            # Compose preview body
            plain_body = ""
            for message in rec.message_ids:
                if message.message_type != "notification":
                    message_body = html2plaintext(message.body)
                    if len(message_body) > body_preview_length:
                        message_body = "%s..." % message_body[:body_preview_length]
                    plain_body = (
                        '<img class="rounded-circle"'
                        ' style="width:16px;max-height:16px;margin:2px;"'
                        ' title="%s" src="data:image/png;base64, %s"/>'
                        ' <span id="text-preview"'
                        ' style="color:#808080;vertical-align:middle;">%s</p>'
                        % (
                            sanitize_name(message.author_id.name)
                            if message.author_id
                            else "",
                            message.author_avatar.decode("utf-8")
                            if message.author_avatar
                            else IMAGE_PLACEHOLDER,
                            message_body,
                        )
                    )
                    break

            rec.subject_display = TREE_TEMPLATE % (
                rec.author_id.image_128.decode("utf-8")
                if rec.author_id and rec.author_id.image_128
                else IMAGE_PLACEHOLDER,
                sanitize_name(rec.author_id.name) if rec.author_id else "",
                rec.author_id.name if rec.author_id else "",
                rec.name if rec.name else "",
                str(message_date.replace(tzinfo=None)) if rec.last_message_post else "",
                date_display,
                message_count_text,
                participant_text,
                plain_body,
            )

    # -- Move messages
    def move(self):
        self.ensure_one()

        return {
            "name": _("Move messages"),
            "views": [[False, "form"]],
            "res_model": "prt.message.move.wiz",
            "type": "ir.actions.act_window",
            "target": "new",
        }

    # -- Is participant?
    def _compute_is_participant(self):
        my_id = self.env.user.partner_id.id
        for rec in self:
            if my_id in rec.partner_ids.ids:
                rec.is_participant = True
            else:
                rec.is_participant = False

    # -- Join conversation
    def join(self):
        self.update({"partner_ids": [(4, self.env.user.partner_id.id, False)]})

    # -- Leave conversation
    def leave(self):
        self.update({"partner_ids": [(3, self.env.user.partner_id.id, False)]})

    # -- Create
    @api.model
    def create(self, vals):
        # Set current user as author if not defined.
        # Use current date as firs message post
        if not vals.get("author_id", False):
            vals.update({"author_id": self.env.user.partner_id.id})

        res = super(Conversation, self.sudo()).create(vals)

        # Subscribe participants
        res.message_subscribe(partner_ids=res.partner_ids.ids)
        return res

    # -- Write
    # Use 'skip_followers_test=True' in context
    # to skip checking for followers/participants

    def write(self, vals):
        res = super(Conversation, self).write(vals)
        if "active" in vals.keys() and not self._context.get(
            "only_conversation", False
        ):
            for rec in self:
                rec.archive_conversion_message(vals.get("active"))

        if self._context.get("skip_followers_test", False):
            return res

        # Check if participants changed
        for rec in self:

            # New followers added?
            followers_add = [
                partner.id
                for partner in rec.partner_ids
                if partner not in rec.message_partner_ids
            ]
            if len(followers_add) > 0:
                rec.message_subscribe(partner_ids=followers_add)

            # Existing followers removed?
            followers_remove = [
                partner.id
                for partner in rec.message_partner_ids
                if partner not in rec.partner_ids
            ]
            if len(followers_remove) > 0:
                rec.message_unsubscribe(partner_ids=followers_remove)

        return res

    # -- Check if partner has access to Conversations
    # or partner is external user or not a user at all
    def has_conversations(self, partner):
        """
         Check if Partner is internal user AND has access to Conversations.
        :param res.partner partner: partner to check
        :return: 1 - has access to Conversations,
         2 - is not an internal User,
          False - none of above
        """

        if partner.user_ids:
            for user in partner.user_ids:
                if user.has_group("base.group_user"):
                    if user.has_group("prt_mail_messages.group_conversation_own"):
                        # Has access to Conversations
                        return 1
            # Does not have access to Conversations
            return False

        # Not an internal user
        return 2

    def archive_conversion_message(self, active_state):
        """Set archive state for related mail messages"""
        msg = self.env["mail.message"].search(
            [
                ("active", "=", not active_state),
                ("model", "=", self._name),
                ("res_id", "=", self.id),
                ("message_type", "!=", "notification"),
            ]
        )
        if active_state:
            msg.write(
                {"active": active_state, "delete_uid": False, "delete_date": False}
            )
            return
        msg.write({"active": active_state})
        return

    # -- Archive/unarchive conversation
    def archive(self):
        for rec in self:
            if rec.active:
                rec.active = False
            else:
                rec.active = True

    # -- Search for partners by email.
    def partner_by_email(self, email_addresses):
        """
        Override this method to implement custom search
         (e.g. if using prt_phone_numbers module)
        :param list email_addresses: List of email addresses
        :return: res.partner obj if found.
        Please pay attention to the fact that only
         the first (newest) partner found is returned!
        """
        # Use loop with '=ilike' to resolve MyEmail@GMail.com cases
        for address in email_addresses:
            partner = self.env["res.partner"].search(
                [("email", "=ilike", address)], limit=1, order="id desc"
            )
            if len(partner) == 1:
                return partner

    # -- Parse incoming email
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}

        # 1. Check for author. If does not exist create new partner.
        author_id = msg_dict.get("author_id", False)
        if not author_id:
            email_from = msg_dict.get("email_from", False)
            partner_name, email_address = getaddresses([email_from])[0]
            partner = self.partner_by_email([email_address])
            author_id = (
                partner.id
                if partner
                else self.env["res.partner"]
                .create(
                    {
                        "name": partner_name
                        if partner_name and len(partner_name) > 0
                        else email_address.split("@")[0],
                        "email": email_address,
                        "category_id": [
                            (
                                4,
                                self.env.ref(
                                    "prt_mail_messages.cetmix_conversations_partner_cat"
                                ).id,  # noqa
                            )
                        ]
                        if self.env.ref(
                            "prt_mail_messages.cetmix_conversations_partner_cat"
                        )
                        else False,  # noqa
                    }
                )
                .id
            )
            # Update message author
            msg_dict.update({"author_id": author_id})

        # 2. Check for recipients in both 'to' and 'cc'.
        # Can be separated lately to implement custom logic.
        partner_ids = []
        # Partners who does not have access to conversations.
        # Will subscribe them later so they will not get the first message
        other_partner_ids = []

        # To
        to = msg_dict.get("to", False)
        if len(to) > 0:
            for email in to.split(","):
                partner_name, email_address = getaddresses([email])[0]
                partner = self.partner_by_email([email_address])
                # Create new partner if not found
                if not partner:
                    partner = self.env["res.partner"].create(
                        {
                            "name": partner_name
                            if partner_name and len(partner_name) > 0
                            else email_address.split("@")[0],
                            "email": email_address,
                            "category_id": [
                                (
                                    4,
                                    self.env.ref(
                                        "prt_mail_messages."
                                        "cetmix_conversations_partner_cat"
                                    ).id,
                                )
                            ]
                            if self.env.ref(
                                "prt_mail_messages.cetmix_conversations_partner_cat"
                            )
                            else False,
                        }
                    )
                # Check if Partner is internal user AND has access to Conversations.
                # Append to partner_ids if yes
                # External users and Partners with no users assigned are subscribed ONLY
                #  after the initial message is posted to avoid unwanted notifications.
                partner_type = self.has_conversations(partner)
                if partner_type == 1:
                    partner_ids.append(partner.id)
                elif partner_type == 2:
                    other_partner_ids.append(partner.id)

        # Cc
        cc = msg_dict.get("cc", False)
        if len(cc) > 0:
            for email in cc.split(","):
                partner_name, email_address = getaddresses([email])[0]
                partner = self.partner_by_email([email_address])
                # Create new partner if not found
                if not partner:
                    partner = self.env["res.partner"].create(
                        {
                            "name": partner_name
                            if partner_name and len(partner_name) > 0
                            else email_address.split("@")[0],
                            "email": email_address,
                            "category_id": [
                                (
                                    4,
                                    self.env.ref(
                                        "prt_mail_messages."
                                        "cetmix_conversations_partner_cat"
                                    ).id,
                                )
                            ]
                            if self.env.ref(
                                "prt_mail_messages.cetmix_conversations_partner_cat"
                            )
                            else False,
                        }
                    )
                partner_id = partner.id

                # Do not add Partner twice
                if partner_id in partner_ids or partner_id in other_partner_ids:
                    continue
                # Check if Partner is internal user AND has access to Conversations.
                # Append to partner_ids if yes
                # External users and Partners with no users assigned are subscribed ONLY
                #  after the initial message is posted to avoid unwanted notifications.
                partner_type = self.has_conversations(partner)
                if partner_type == 1:
                    partner_ids.append(partner_id)
                elif partner_type == 2:
                    other_partner_ids.append(partner_id)

        # Append author to participants (partners)
        partner_ids.append(author_id)
        # Update custom values
        custom_values.update(
            {
                "name": msg_dict.get("subject", "").strip(),
                "author_id": author_id,
                "partner_ids": [(4, pid) for pid in partner_ids],
            }
        )
        return super(
            Conversation,
            self.with_context(
                other_partner_ids=other_partner_ids
                if len(other_partner_ids) > 0
                else False,
                mail_create_nolog=True,
            ),
        ).message_new(msg_dict, custom_values)

    # -- Post message
    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *, message_type="notification", **kwargs):
        res = super(Conversation, self).message_post(
            message_type=message_type, **kwargs
        )
        if message_type not in ["comment", "email"]:  # Skip notifications
            return res
        # Add other_partner_ids as followers.
        # We do it here to avoid them being notified on initial message post
        other_partner_ids = self._context.get("other_partner_ids", False)
        if other_partner_ids:
            self.write({"partner_ids": [(4, p) for p in other_partner_ids]})

        return res
