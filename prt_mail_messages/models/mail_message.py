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

import logging
from datetime import datetime, timedelta
from email.utils import parseaddr

import pytz

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import AccessError, MissingError
from odoo.osv import expression
from odoo.tools import html2plaintext

from .common import DEFAULT_MESSAGE_PREVIEW_LENGTH, IMAGE_PLACEHOLDER, MONTHS

# Used to render html field in TreeView
TREE_TEMPLATE = (
    '<table style="width:100%%;border:none;%s" title="%s">'
    "<tbody>"
    "<tr>"
    '<td style="width: 1%%;"><img class="rounded-circle"'
    ' style="width: 64px; padding:10px;" '
    'src="data:image/png;base64,%s" alt="Avatar"'
    ' title="%s" width="100" border="0" /></td>'
    '<td style="width: 99%%;">'
    '<table style="width: 100%%; border: none;">'
    "<tbody>"
    "<tr>"
    '<td id="author"><strong>%s</strong>'
    ' &nbsp; <span id="subject">%s</span></td>'
    '<td id="date" style="text-align:right;">'
    '<span title="%s" id="date">%s</span></td>'
    "</tr>"
    "<tr>"
    '<td><p id="related-record" '
    'style="font-size: x-small;"><strong>%s</strong></p></td>'
    '<td id="notifications" style="text-align: right;">%s</td>'
    "</tr>"
    "</tbody>"
    "</table>"
    "<b id='daleted-days' class='text-danger'>%s</b>"
    '<p id="text-preview" style="color: #808080;">%s</p>'
    "</td>"
    "</tr>"
    "</tbody>"
    "</table>"
)

_logger = logging.getLogger(__name__)

# List of forbidden models
FORBIDDEN_MODELS = ["mail.channel", "mail.message"]

# Search for 'ghost' models is performed
GHOSTS_CHECKED = False


################
# Mail.Message #
################
class MailMessage(models.Model):
    _inherit = "mail.message"

    author_display = fields.Char(string="Author", compute="_compute_author_display")

    # Fields to avoid access check issues
    author_allowed_id = fields.Many2one(
        string="Author",
        comodel_name="res.partner",
        compute="_compute_author_allowed_id",
        search="_search_author_allowed",
    )
    subject_display = fields.Html(string="Subject", compute="_compute_subject_display")
    partner_count = fields.Integer(
        string="Recipients count", compute="_compute_partner_count"
    )
    record_ref = fields.Reference(
        string="Message Record",
        selection="_referencable_models",
        compute="_compute_record_ref",
    )
    attachment_count = fields.Integer(
        string="Attachments count", compute="_compute_attachment_count"
    )
    thread_messages_count = fields.Integer(
        string="Messages in thread",
        compute="_compute_thread_messages_count",
        help="Total number of messages in thread",
    )
    ref_partner_ids = fields.Many2many(
        string="Followers",
        comodel_name="res.partner",
        compute="_compute_ref_partner_ids",
    )
    ref_partner_count = fields.Integer(
        string="Followers", compute="_compute_ref_partner_count"
    )

    mail_mail_ids = fields.One2many(
        string="Email Message",
        comodel_name="mail.mail",
        inverse_name="mail_message_id",
        auto_join=True,
    )
    is_error = fields.Boolean(string="Sending Error", compute="_compute_send_error")
    model_name = fields.Char(string="Model", compute="_compute_model_name")
    shared_inbox = fields.Boolean(
        string="Shared Inbox",
        compute="_compute_dummy",
        help="Used for Shared Inbox filter only",
        search="_search_shared_inbox",
    )
    cx_edit_uid = fields.Many2one(string="Edited by", comodel_name="res.users")
    cx_edit_date = fields.Datetime(string="Edited on")
    cx_edit_message = fields.Char(
        string="Edited by", compute="_compute_cx_edit_message"
    )

    active = fields.Boolean(string="Active", default=True)
    delete_uid = fields.Many2one("res.users", string="Deleted by")
    delete_date = fields.Datetime(string="Deleted on")
    deleted_days = fields.Integer(
        string="Deleted days", compute="_compute_deleted_days"
    )

    # -- Compute count deleted days for message
    def _compute_deleted_days(self):
        for rec in self:
            if rec.delete_date:
                delete_date = rec.delete_date
                date_now = fields.Datetime.now()
                rec.deleted_days = (date_now - delete_date).days

    # -- Compute text shown as last edit message
    @api.depends("cx_edit_uid")
    def _compute_cx_edit_message(self):
        # Get current timezone
        tz = self.env.user.tz
        if tz:
            local_tz = pytz.timezone(tz)
        else:
            local_tz = pytz.utc

        # Get current time
        now = datetime.now(local_tz)

        # Check messages
        for rec in self:
            if not rec.cx_edit_uid:
                rec.cx_edit_message = False
                continue

            # Get message date with timezone
            message_date = pytz.utc.localize(rec.cx_edit_date).astimezone(local_tz)
            # Compose displayed date/time
            days_diff = (now.date() - message_date.date()).days
            if days_diff == 0:
                date_display = datetime.strftime(message_date, "%H:%M")
            elif days_diff == 1:
                date_display = " ".join(
                    (_("Yesterday"), datetime.strftime(message_date, "%H:%M"))
                )
            elif now.year == message_date.year:
                date_display = " ".join(
                    (str(message_date.day), _(MONTHS.get(message_date.month)))
                )
            else:
                date_display = str(message_date.date())
            rec.cx_edit_message = _("Edited by %s %s") % (
                rec.cx_edit_uid.name,
                date_display,
            )

    # -- Star several messages
    def mark_read_multi(self):
        for rec in self:
            if rec.needaction:
                rec.set_message_done()
            if rec.parent_id and rec.parent_id.needaction:
                rec.parent_id.set_message_done()

    # -- Star several messages
    def star_multi(self):
        for rec in self:
            rec.toggle_message_starred()

    # -- Archive/unarchive message
    def archive(self):
        for rec in self:
            if rec.active:
                rec.active = False
            else:
                rec.active = True

    def undelete(self):
        """ Undelete message from trash """
        # Store Conversation ids
        for rec in self.sudo():
            if rec.model == "cetmix.conversation":
                conversation_ids = self.env["cetmix.conversation"].search([
                    ("active", "=", False),
                    ("id", "=", rec.res_id),
                ])
                conversation_ids.with_context(only_conversation=True
                                              ).write({"active": True})
        self.with_context(undelete_action=True).write({
            "active": True, "delete_uid": False, "delete_date": False
        })
        return

    # -- Search private inbox
    def _search_shared_inbox(self, operator, operand):
        if operator == "=" and operand:
            return [
                "|",
                ("author_id", "=", False),
                ("author_id", "!=", self.env.user.partner_id.id),
            ]
        return [("author_id", "!=", False)]

    # -- Get model name for Form View
    def _compute_model_name(self):
        ir_models = (
            self.env["ir.model"].sudo().search([
                ("model", "in", list(set(self.mapped("model"))))
            ])
        )
        model_dict = {}
        for model in ir_models:
            model_dict.update({model.model: model.name})
        for rec in self:
            rec.model_name = model_dict[rec.model] if rec.model else _("Lost Message")

    @api.model
    def _unlink_trash_message(self, test_custom_datetime=None):
        """
        Delete old messages by cron
        :param test_custom_datetime - argument for testing
        :return True always
        """
        messages_easy_empty_trash = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "cetmix.messages_easy_empty_trash", 0
            )
        )
        if messages_easy_empty_trash > 0:
            compute_datetime = fields.Datetime.now() - timedelta(
                days=messages_easy_empty_trash
            )
            result = (
                self.env["mail.message"].sudo().search([
                    ("active", "=", False),
                    ("delete_uid", "!=", False),
                    ("delete_date", "<=", test_custom_datetime or compute_datetime),
                    ("message_type", "!=", "notification"),
                ])
            )
            result.unlink_pro()
        return True

    # -- Create
    @api.model
    def create(self, vals):

        # Update last message date if posting to Conversation
        message = super(MailMessage, self).create(vals)
        if (
            self._name == "mail.message" and message.model == "cetmix.conversation"
            and message.message_type != "notification"
        ):
            self.env["cetmix.conversation"].browse(message.res_id).update({
                "last_message_post": message.write_date,
                "last_message_by": message.author_id.id,
            })
        return message

    # -- Delete empty Conversations
    def _get_conversation_messages_to_delete_and_archive(self, conversation_ids):
        conversations_2_archive = []
        conversations_2_delete = []
        for conversation in conversation_ids:
            message_all = self.with_context(active_test=False).search([
                ("res_id", "=", conversation),
                ("model", "=", "cetmix.conversation"),
                ("message_type", "!=", "notification"),
            ])
            message_active = message_all.filtered(lambda msg: msg.active)

            if len(message_all) == 0:
                conversations_2_delete.append(conversation)
            elif len(message_active) == 0:
                conversations_2_archive.append(conversation)
        return conversations_2_archive, conversations_2_delete

    def _delete_conversation_record(self, conversation_ids):
        """
        Delete conversation without messages
        :param conversation_ids: List of Conversation ids
        :return: None
        """
        if not len(conversation_ids) > 0:
            return
        delete_conversations = (
            self.with_context(active_test=False).env["cetmix.conversation"].search([
                ("id", "in", conversation_ids)
            ])
        )
        if delete_conversations:
            delete_conversations.unlink()

    def _archive_conversation_record(self, conversation_ids):
        """
        Archive conversation
        :param conversation_ids: List of Conversation ids
        :return: None
        """
        if not len(conversation_ids) > 0:
            return
        archive_conversations = (
            self.with_context(active_test=False).env["cetmix.conversation"].search([
                ("id", "in", conversation_ids)
            ])
        )
        if archive_conversations:
            archive_conversations.write({"active": False})

    # -- Delete empty Conversations
    def _delete_conversations(self, conversation_ids):
        """
        Deletes all conversations with no messages left.
         Notifications are not considered!
        :param set conversation_ids: List of Conversation ids
        :return: just Return))
        """
        if len(conversation_ids) == 0:
            return
        # Delete empty Conversations
        (
            conversations_2_archive,
            conversations_2_delete,
        ) = self._get_conversation_messages_to_delete_and_archive(conversation_ids)
        # Delete conversations with no messages
        self._delete_conversation_record(conversations_2_delete)
        # Archive conversations
        self._archive_conversation_record(conversations_2_archive)

    # -- Check delete rights
    def unlink_rights_check(self):
        """
        Check if user has access right to delete messages
        Raises Access Error or returns True
        :return: True
        """
        # Root
        if self.env.user.id == SUPERUSER_ID:
            return True

        # Can delete messages?
        if not self.env.user.has_group("prt_mail_messages.group_delete"):
            raise AccessError(_("You cannot delete messages!"))

        # Can delete any message?
        if self.env.user.has_group("prt_mail_messages.group_delete_any"):
            return True

        # Check access rights
        partner_id = self.env.user.partner_id.id
        for rec in self:
            # Can delete if user:
            # - Is Message Author for 'comment' message
            # - Is the only 'recipient' for 'email' message
            # Sent
            if rec.message_type == "comment":
                # Is Author?
                if not rec.author_allowed_id.id == partner_id:
                    raise AccessError(
                        _(
                            "You cannot delete the following message"
                            "\n\n Subject: %s \n\n"
                            " Reason: %s" %
                            (rec.subject, _("You are not the message author"))
                        )
                    )

            # Received
            if rec.message_type == "email":
                # No recipients
                if not rec.partner_ids:
                    raise AccessError(
                        _(
                            "You cannot delete the following message"
                            "\n\n Subject: %s \n\n"
                            " Reason: %s" %
                            (rec.subject, _("Message recipients undefined"))
                        )
                    )

                # Has several recipients?
                if len(rec.partner_ids) > 1:
                    raise AccessError(
                        _(
                            "You cannot delete the following message"
                            "\n\n Subject: %s \n\n"
                            " Reason: %s" %
                            (rec.subject, _("Message has multiple recipients"))
                        )
                    )

                # Partner is not that one recipient
                if not rec.partner_ids[0].id == partner_id:
                    raise AccessError(
                        _(
                            "You cannot delete the following message"
                            "\n\n Subject: %s \n\n"
                            " Reason: %s" %
                            (rec.subject, _("You are not the message recipient"))
                        )
                    )

    # -- Logging
    @api.model
    def _logging_message_deleted(self, count):
        """ Logging: count message deleted """
        message_word = "messages" if count > 1 else "message"
        log_string = (
            "%d %s deleted from trash" %
            (count, message_word) if count > 0 else "No messages to delete"
        )
        _logger.info(log_string)

    def _messages_move_to_trash(self):
        """
        Move to trash messages from self
        :return: None
        """
        if not self:
            return
        self.mark_read_multi()
        self.write({
            "active": False,
            "delete_uid": self.env.user.id,
            "delete_date": fields.Datetime.now(),
        })

    def _delete_trashed_messages(self):
        """
        Delete trash message
        :return: None
        """
        if self:
            count_delete_message = len(self)
            self.unlink()
            self._logging_message_deleted(count_delete_message)

    # -- Unlink
    def unlink_pro(self):
        # Set state deleted

        # Store Conversation ids
        conversation_ids = {
            rec.res_id
            for rec in self.sudo()
            if rec.model == "cetmix.conversation"
        }
        # Check access rights
        self.unlink_rights_check()

        # Delete message
        messages_to_delete = self.filtered(
            lambda msg: not msg.active and msg.delete_uid and msg.delete_date
        )
        messages_to_delete._delete_trashed_messages()

        # Move to trash message
        messages_to_trash = self.filtered(
            lambda msg: msg.id not in messages_to_delete.ids
        )
        messages_to_trash._messages_move_to_trash()

        if len(conversation_ids) > 0:
            self._delete_conversations(conversation_ids)
        return

    # -- Check if error while sending TODO check log
    @api.depends("notification_ids")
    def _compute_send_error(self):
        for rec in self.filtered(
            lambda m: m.notification_ids.mapped("email_status") not in ["sent"]
        ):
            if len(rec.mail_mail_ids.filtered(lambda m: m.state == "exception")) > 0:
                rec.is_error = True

    # -- Count ref Partners
    def _compute_ref_partner_count(self):
        for rec in self:
            rec.ref_partner_count = len(rec.ref_partner_ids)

    # Sometimes user has access to record
    # but does not have access to author or recipients.
    # Below is a workaround for author, recipient and followers

    # -- Get allowed author
    @api.depends("author_id")
    def _compute_author_allowed_id(self):
        author_ids = self.mapped("author_id").ids
        author_allowed_ids = (
            self.env["res.partner"].search([("id", "in", author_ids)]).ids
        )
        for rec in self:
            author_id = rec.sudo().author_id.id
            if author_id in author_allowed_ids:
                rec.author_allowed_id = author_id
            else:
                rec.author_allowed_id = False

    # -- Search allowed authors
    @api.model
    def _search_author_allowed(self, operator, value):
        return [("author_id", operator, value)]

    # -- Get related record followers
    # Check if model has 'followers' field
    # and user has access to followers
    @api.depends("record_ref")
    def _compute_ref_partner_ids(self):
        rec_vals = {}
        # Compose dict of {model: [res_ids]}
        # Will be used to check access rights to followers
        for rec in self:
            rec_model = rec.model
            rec_res_id = rec.res_id
            model_vals = rec_vals.get(rec_model, False)
            if not model_vals:
                rec_vals.update({rec_model: [rec_res_id]})
            elif rec.res_id not in model_vals:
                model_vals.append(rec_res_id)
                rec_vals.update({rec_model: model_vals})
        # Get followers for each "model:records"
        follower_ids = []
        for model in rec_vals:
            if not model:
                continue
            for follower_id in (
                self.env[model].search([("id", "in", rec_vals[model])]
                                       ).mapped("message_partner_ids").ids
            ):
                if follower_id not in follower_ids:
                    follower_ids.append(follower_id)

        # Filter only partners we have access to
        follower_allowed_ids = (
            self.env["res.partner"].search([("id", "in", follower_ids)]).ids
        )
        for rec in self:
            if rec.record_ref:
                rec.ref_partner_ids = [
                    p for p in rec.record_ref.sudo().message_partner_ids.ids
                    if p in follower_allowed_ids
                ]
            else:
                rec.ref_partner_ids = False

    # -- Dummy
    def _compute_dummy(self):
        return

    def _display_number_days_after_deletion(self):
        """ Get string of display number days after deletion """
        if not self.delete_date:
            return ""
        return (
            "Deleted less than one day ago"
            if self.deleted_days == 0 else "Deleted %d days ago" % self.deleted_days
        )

    # -- Get Subject for tree view
    @api.depends("subject")
    def _compute_subject_display(self):

        # Get config data
        ICPSudo = self.env["ir.config_parameter"].sudo()

        # Get preview length. Will use it for message body preview
        body_preview_length = int(
            ICPSudo.get_param(
                "cetmix.messages_easy_text_preview", DEFAULT_MESSAGE_PREVIEW_LENGTH
            )
        )
        # Get message subtype colors
        messages_easy_color_note = ICPSudo.get_param(
            "cetmix.messages_easy_color_note", default=False
        )
        mt_note = self.env.ref("mail.mt_note").id

        # Get current timezone
        tz = self.env.user.tz
        if tz:
            local_tz = pytz.timezone(tz)
        else:
            local_tz = pytz.utc

        # Get current time
        now = datetime.now(local_tz)
        # Compose subject
        for rec in self:

            # Get message date with timezone
            message_date = pytz.utc.localize(rec.date).astimezone(local_tz)
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

            # Compose notification icons
            notification_icons = ""
            if rec.needaction:
                notification_icons = '<i class="fa fa-envelope" title="%s"></i>' % _(
                    "New message"
                )
            if rec.starred:
                notification_icons = (
                    '%s &nbsp;<i class="fa fa-star" title="%s"></i>' %
                    (notification_icons, _("Starred"))
                )
            if rec.is_error > 0:
                notification_icons = (
                    '%s &nbsp;<i class="fa fa-exclamation" title="%s"></i>' %
                    (notification_icons, _("Sending Error"))
                )
            # .. edited
            if rec.cx_edit_uid:
                notification_icons = (
                    '%s &nbsp;<i class="fa fa-edit" '
                    'style="color:#1D8348;" title="%s"></i>' %
                    (notification_icons, rec.cx_edit_message)
                )
            # .. attachments
            if rec.attachment_count > 0:
                notification_icons = (
                    '%s &nbsp;<i class="fa fa-paperclip" title="%s"></i>' % (
                        notification_icons,
                        "&#013;".join([a.name for a in rec.attachment_ids]),
                    )
                )

            # Compose preview body
            plain_body = html2plaintext(rec.body) if len(rec.body) > 10 else ""
            if len(plain_body) > body_preview_length:
                plain_body = "".join((plain_body[:body_preview_length], "..."))

            rec.subject_display = TREE_TEMPLATE % (
                ("background-color:%s;" % messages_easy_color_note)
                if messages_easy_color_note and rec.subtype_id.id == mt_note else "",
                _("Internal Note") if rec.subtype_id.id == mt_note else _("Message"),
                rec.author_avatar.decode("utf-8")
                if rec.author_avatar else IMAGE_PLACEHOLDER,
                rec.author_display,
                rec.author_display,
                rec.subject if rec.subject else "",
                str(message_date.replace(tzinfo=None)),
                date_display,
                "{}: {}".format(rec.model_name, rec.record_ref.sudo().name_get()[0][1])
                if rec.record_ref else "",
                notification_icons,
                rec._display_number_days_after_deletion(),
                plain_body,
            )

    # -- Get Author for tree view
    @api.depends("author_allowed_id")
    def _compute_author_display(self):
        """Get Author for tree view"""
        for rec in self:
            rec.author_display = (
                rec.author_allowed_id.name if rec.author_allowed_id else
                rec.email_from.replace(">", "").replace("<", "")
            )

    # -- Count recipients
    @api.depends("partner_ids")
    def _compute_partner_count(self):
        """Count recipients"""
        for rec in self:
            rec.partner_count = len(rec.partner_ids)

    # -- Count attachments
    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        """Count attachments"""
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    # -- Count messages in same thread
    @api.depends("res_id")
    def _compute_thread_messages_count(self):
        """Count messages in same thread"""
        for rec in self:
            rec.thread_messages_count = self.search_count([
                "&",
                "&",
                ("model", "=", rec.model),
                ("res_id", "=", rec.res_id),
                ("message_type", "!=", "notification"),
            ])

    # -- Ref models
    @api.model
    def _referencable_models(self):
        """List referencable Ref models"""
        return [(x.model, x.name)
                for x in self.env["ir.model"].sudo().search([("transient", "=", False)])
                ]

    # -- Compose reference
    @api.depends("res_id")
    def _compute_record_ref(self):
        transient_models = []  # Keep transient model names
        for rec in self:
            if rec.model:
                if rec.res_id:
                    model = self.env[rec.model]
                    if model in transient_models:
                        rec.record_ref = False
                        continue
                    if model._transient:
                        transient_models.append(model)
                        rec.record_ref = False
                        continue
                    res = self.env[rec.model].sudo().search([("id", "=", rec.res_id)])
                    if res:
                        rec.record_ref = res

    # -- Get forbidden models
    def _get_forbidden_models(self):

        # Use global vars
        global GHOSTS_CHECKED
        global FORBIDDEN_MODELS

        # Ghosts checked?
        if GHOSTS_CHECKED:
            return FORBIDDEN_MODELS[:]

        # Search for 'ghost' models. These are models left from uninstalled modules.
        self._cr.execute(
            """ SELECT model FROM ir_model
                                    WHERE transient = False
                                    AND NOT model = ANY(%s) """,
            (list(FORBIDDEN_MODELS), ),
        )

        # Check each model
        for msg_model in self._cr.fetchall():
            model = msg_model[0]
            if not self.env["ir.model"].sudo().search([("model", "=", model)]).modules:
                FORBIDDEN_MODELS.append(model)

        # Mark as checked
        GHOSTS_CHECKED = True
        return FORBIDDEN_MODELS[:]

    # -- Open messages of the same thread
    def thread_messages(self):
        self.ensure_one()

        tree_view_id = self.env.ref("prt_mail_messages.prt_mail_message_tree").id
        form_view_id = self.env.ref("prt_mail_messages.prt_mail_message_form").id

        return {
            "name": _("Messages"),
            "views": [[tree_view_id, "tree"], [form_view_id, "form"]],
            "res_model": "mail.message",
            "type": "ir.actions.act_window",
            "target": "current",
            "domain": [
                ("message_type", "!=", "notification"),
                ("model", "=", self.model),
                ("res_id", "=", self.res_id),
            ],
        }

    # -- Override _search
    # mail.message overrides generic '_search' defined in 'model'
    # to implement own logic for message access rights.
    # However sometimes it does not work as expected.
    # So we use generic method in 'model'
    # and check access rights later in 'search' method.
    # Following keys in context are used:
    # - 'check_messages_access': if not set legacy 'search' is performed
    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        """
        mail.message overrides generic '_search' defined in 'model'
         to implement own logic for message access rights.
        However sometimes it does not work as expected.
        So we use generic method in 'model' and check access
         rights later in 'search' method.
        Following keys in context are used:
         - 'check_messages_access': if not set legacy 'search' is performed
        """
        if not self._context.get("check_messages_access", False):
            return super(MailMessage, self)._search(
                args=args,
                offset=offset,
                limit=limit,
                order=order,
                count=count,
                access_rights_uid=access_rights_uid,
            )

        if expression.is_false(self, args):
            # optimization: no need to query, as no record satisfies the domain
            return 0 if count else []

        query = self._where_calc(args)
        order_by = self._generate_order_by(order, query)
        from_clause, where_clause, where_clause_params = query.get_sql()

        where_str = where_clause and (" WHERE %s" % where_clause) or ""

        if count:
            # Ignore order, limit and offset when just counting,
            # they don't make sense and could
            # hurt performance
            query_str = "SELECT count(1) FROM " + from_clause + where_str
            self._cr.execute(query_str, where_clause_params)
            res = self._cr.fetchone()
            return res[0]

        limit_str = limit and " limit %d" % limit or ""
        offset_str = offset and " offset %d" % offset or ""
        query_str = (
            'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by +
            limit_str + offset_str
        )
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()

        # TDE note: with auto_join, we could have
        # several lines about the same result
        # i.e. a lead with several unread messages;
        # we uniquify the result using
        # a fast way to do it while preserving order
        # (http://www.peterbe.com/plog/uniqifiers-benchmark)
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        return _uniquify_list([x[0] for x in res])

    # -- Override read
    # Avoid access rights check implemented in original mail.message
    # Will check them later in "search"
    # Using base model function instead
    #  Following keys in context are used:
    #  - 'check_messages_access': if not set legacy 'search' is performed
    def read(self, fields=None, load="_classic_read"):
        """
        Avoid access rights check implemented in original mail.message
        Will check them later in "search"
        Using base model function instead
            Following keys in context are used:
            - 'check_messages_access': if not set legacy 'search' is performed
        """
        if not self._context.get("check_messages_access", False):
            return super(MailMessage, self).read(fields=fields, load=load)

        # Cetmix. From here starts the original 'read' code
        # split fields into stored and computed fields
        stored, inherited, computed = [], [], []
        for name in fields:
            field = self._fields.get(name)
            if field:
                if field.store:
                    stored.append(name)
                elif field.base_field.store:
                    inherited.append(name)
                else:
                    computed.append(name)
            else:
                _logger.warning("%s.read() with unknown field '%s'", self._name, name)

        # fetch stored fields from the database to the cache; this should feed
        # the prefetching of secondary records
        self._read_from_database(stored, inherited)

        # retrieve results from records; this takes values from the cache and
        # computes remaining fields
        result = []
        name_fields = [(name, self._fields[name])
                       for name in (stored + inherited + computed)]
        use_name_get = load == "_classic_read"

        for record in self:
            try:
                values = {"id": record.id}
                for name, field in name_fields:
                    values[name] = field.convert_to_read(
                        record[name], record, use_name_get
                    )
                result.append(values)
            except MissingError:
                pass

        return result

    # -- Override Search
    # Mail message access rights/rules checked must be done
    # based on the access rights/rules of the message record.
    # As a workaround we are using 'search' method
    # to filter messages from unavailable records.
    #
    # Display only messages where user has read access to related record.
    #
    # Following keys in context are used:
    # - 'check_messages_access': if not set legacy 'search' is performed
    # - 'force_record_reset': in case message refers to non-existing
    # (e.g. removed) record model and res_id will be set NULL

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):

        if not self._context.get("check_messages_access", False):
            return super(MailMessage, self).search(
                args=args, offset=offset, limit=limit, order=order, count=count
            )

        # Store context keys
        force_record_reset = self._context.get("force_record_reset", False)
        # Store initial args in case we need them later
        modded_args = args

        # Define sort order
        if order and ("ASC" in order or "asc" in order):
            sort_asc = True
        else:
            sort_asc = False

        # Check model access 1st
        forbidden_models = self._get_forbidden_models()

        # Get list of possible followed models
        self._cr.execute(
            """ SELECT model FROM ir_model
                                        WHERE is_mail_thread = True
                                        AND NOT model = ANY(%s) """,
            (list(forbidden_models), ),
        )

        # Check each model
        for msg_model in self._cr.fetchall():
            if not self.env["ir.model.access"].check(
                msg_model[0], "read", raise_exception=False
            ):
                forbidden_models.append(msg_model[0])

        # Add forbidden models condition to domain
        if len(forbidden_models) > 0:
            modded_args.append(["model", "not in", forbidden_models])

        # Return Count
        if count:
            return super(MailMessage, self).search(
                args=modded_args, offset=offset, limit=limit, order=order, count=True
            )

        # Get records
        res_ids = self._search(
            args=modded_args, offset=offset, limit=limit, order=order, count=False
        )
        res = self.browse(res_ids)

        # Cache allowed records and store last id
        rec_allowed = []
        rec_forbidden = []
        last_id = False

        # Now check record rules for each message
        res_allowed = self.env["mail.message"]
        len_initial = limit if limit else len(res)
        len_filtered = 0

        # Check in we need include "lost" messages
        # These are messages with no model or res_id
        get_lost = self._context.get("get_lost", False)

        for rec in res:
            model = rec.model
            res_id = rec.res_id

            # Update last id
            rec_id = rec.id
            if sort_asc:
                if not last_id or rec_id > last_id:
                    last_id = rec_id
            else:
                if not last_id or rec_id < last_id:
                    last_id = rec_id

            # No model
            if not model:
                if get_lost:
                    res_allowed += rec
                    len_filtered += 1
                continue

            # No id
            if not res_id:
                if get_lost:
                    res_allowed += rec
                    len_filtered += 1
                continue

            # Check if record is forbidden already
            if (model, res_id) in rec_forbidden:
                continue
            # Check if record is allowed already
            if (model, res_id) not in rec_allowed:
                # Check access rules on record. Skip if refers to deleted record
                try:
                    target_rec = self.env[model].search([("id", "=", res_id)])
                    if not target_rec:
                        # Reset model and res_id
                        if force_record_reset:
                            rec.sudo().write({"model": False, "res_id": False})
                        continue
                    # Check message record
                    target_rec.check_access_rule("read")
                    rec_allowed.append((model, res_id))
                except AccessError:
                    rec_forbidden.append((model, res_id))
                    continue

            res_allowed += rec
            len_filtered += 1

        del res  # Hope Python will free memory asap!))

        # Return if initially got less then limit
        if limit is None or len_initial < limit:
            return res_allowed

        len_remaining = len_initial - len_filtered

        # Return if all allowed
        if len_remaining == 0:
            return res_allowed

        # Check last id
        if not last_id:
            return res_allowed

        # Step 2+n in case need to get more records
        # Get remaining recs
        while len_remaining > 0:

            new_args = modded_args.copy()
            if sort_asc:
                new_args.append(["id", ">", last_id])
            else:
                new_args.append(["id", "<", last_id])

            # Let's try!))
            res_2_ids = self._search(
                args=new_args, offset=0, limit=limit, order=order, count=False
            )
            res_2 = self.browse(res_2_ids)

            if len(res_2) < 1:
                break

            # Check records
            for rec in res_2:
                model = rec.model
                res_id = rec.res_id

                # Update last id
                rec_id = rec.id
                if sort_asc:
                    if not last_id or rec_id > last_id:
                        last_id = rec_id
                else:
                    if not last_id or rec_id < last_id:
                        last_id = rec_id

                # No model
                if not model:
                    if get_lost:
                        res_allowed += rec
                        len_filtered += 1
                    continue

                # No res_id
                if not res_id:
                    if get_lost:
                        res_allowed += rec
                        len_filtered += 1
                    continue

                # Check access rules on record. Skip if refers to deleted record
                # Check if record is forbidden already
                if (model, res_id) in rec_forbidden:
                    continue
                # Check if message already allowed
                if (model, res_id) not in rec_allowed:
                    try:
                        target_rec = self.env[model].search([("id", "=", res_id)])
                        if not target_rec:
                            # Reset model and res_id
                            if force_record_reset:
                                rec.sudo().write({"model": False, "res_id": False})
                            continue
                        # Check message record
                        target_rec.check_access_rule("read")
                        rec_allowed.append((model, res_id))
                    except AccessError:
                        rec_forbidden.append((model, res_id))
                        continue

                res_allowed += rec
                len_remaining -= 1

        return res_allowed

    # -- Prepare context for reply or quote message
    def reply_prep_context(self):
        self.ensure_one()

        # Mark as read
        self.mark_read_multi()

        body = False
        wizard_mode = self._context.get("wizard_mode", False)

        if wizard_mode in ["quote", "forward"]:
            # Get current timezone
            tz = self.env.user.tz
            if tz:
                local_tz = pytz.timezone(tz)
            else:
                local_tz = pytz.utc
            # Get date and time format
            language = (
                self.env["res.lang"].sudo().search([("code", "=", self.env.user.lang)],
                                                   limit=1)
            )
            # Compute tz-respecting date
            message_date = (
                pytz.utc.localize(self.date).astimezone(local_tz).strftime(
                    " ".join([language.date_format, language.time_format])
                )
            )
            body = _(
                "<div font-style=normal;><br/></div>"
                "<blockquote>----- Original message ----- <br/> Date: {} <br/>"
                " From: {} <br/> Subject: {} <br/><br/>{}</blockquote>".format(
                    message_date, self.author_display, self.subject, self.body
                )
            )

        ctx = {
            "default_res_id": self.res_id,
            "default_parent_id": False if wizard_mode == "forward" else self.id,
            "default_model": self.model,
            "default_partner_ids": [self.author_allowed_id.id]
                                   if self.author_allowed_id else [],  # noqa
            "default_attachment_ids":
                self.attachment_ids.ids if wizard_mode == "forward" else [],
            "default_is_log": False,
            "default_body": body,
            "default_wizard_mode": wizard_mode,
        }
        return ctx

    # -- Reply or quote message
    def reply(self):
        self.ensure_one()
        # Mark as read
        self.mark_read_multi()

        return {
            "name": _("New message"),
            "views": [[False, "form"]],
            "res_model": "mail.compose.message",
            "type": "ir.actions.act_window",
            "target": "new",
            "context": self.reply_prep_context(),
        }

    # -- Move message
    def move(self):
        self.ensure_one()
        # Mark as read
        self.mark_read_multi()

        return {
            "name": _("Move messages"),
            "views": [[False, "form"]],
            "res_model": "prt.message.move.wiz",
            "type": "ir.actions.act_window",
            "target": "new",
        }

    # -- Assign author
    def assign_author(self):
        # Mark as read
        self.mark_read_multi()
        addr = parseaddr(self.email_from)
        return {
            "name": _("Assign Author"),
            "views": [[False, "form"]],
            "res_model": "cx.message.partner.assign.wiz",
            "type": "ir.actions.act_window",
            "target": "new",
            "context": {"default_name": addr[0], "default_email": addr[1]},
        }

    # -- Edit message
    def message_edit(self):
        # Mark as read
        self.mark_read_multi()
        self.ensure_one()
        return {
            "name": _("Edit"),
            "views": [[False, "form"]],
            "res_model": "cx.message.edit.wiz",
            "type": "ir.actions.act_window",
            "target": "new",
        }

    # -- Fix data
    @api.model
    def fix_data(self):
        """
        Disable deprecated messages buttons view
        """
        buttons_view = self.env.ref(
            "prt_mail_messages_buttons.prt_mail_message_form_buttons", False
        )
        if buttons_view:
            buttons_view.active = False

    def write(self, vals):
        if vals.get("active",
                    False) and not self._context.get("undelete_action", False):
            new_self = self.env[self._name]
            for rec in self:
                if not rec.delete_uid and not rec.delete_date:
                    new_self |= rec
        else:
            new_self = self
        return super(MailMessage, new_self).write(vals)
