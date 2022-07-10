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

from odoo import _, api, models
from odoo.exceptions import AccessError


################
# Mail.Message #
################
class MailMessage(models.Model):
    _inherit = "mail.message"

    # -- Check installed crm module
    @api.model
    def crm_not_installed(self):
        """ Check installed crm module """
        if self.env["ir.model"].sudo().search_count([("model", "=", "crm.lead")]) == 0:
            return True
        return False

    # -- Undelete
    def undelete(self):
        """ Undelete crm.lead message """
        if self.crm_not_installed():
            return super(MailMessage, self).undelete()
        model = "crm.lead"
        for rec in self.sudo():
            if rec.model == model:
                lead_ids = self.env[model].search([
                    ("active", "=", False),
                    ("id", "=", rec.res_id),
                ])
                lead_ids.write({"active": True})
        return super(MailMessage, self).undelete()

    # -- Archive crm lead messages
    @api.model
    def archive_lead_message(self, lead_id):
        """ Set archive state for related mail messages """
        msg = self.env["mail.message"].search([
            ("active", "=", not lead_id.active),
            ("model", "=", "crm.lead"),
            ("res_id", "=", lead_id.id),
            ("message_type", "!=", "notification"),
        ])
        if lead_id.active:
            msg.write({
                "active": lead_id.active, "delete_uid": False, "delete_date": False
            })
            return
        msg.write({"active": lead_id.active})

    # -- Delete empty Leads
    def _delete_leads(self, leads_ids):
        """
        Deletes all leads with no messages left.
        Notifications are not considered!
        :param leads_ids: List of lead ids
        :return: empty.
        """
        if self.crm_not_installed():
            return

        if len(leads_ids) == 0:
            return

        # Delete empty Leads
        lead_archive = []
        lead_delete = []
        model = "crm.lead"

        for lead in leads_ids:
            message_all = self.with_context(active_test=False).search([
                ("res_id", "=", lead),
                ("model", "=", model),
                ("message_type", "!=", "notification"),
            ])
            message_archive = message_all.filtered(lambda msg: msg.active)

            if len(message_all) == 0:
                lead_delete.append(lead)
            elif len(message_archive) == 0:
                lead_archive.append(lead)

        if len(lead_delete) > 0:
            self.env[model].browse(lead_delete).unlink()
        if len(lead_archive) > 0:
            crm_leads_ids = self.env[model].browse(lead_archive)
            crm_leads_ids.write({"active": False})
            for lead_id in crm_leads_ids:
                self.archive_lead_message(lead_id)

    # -- Unlink
    def unlink_pro(self):

        # Check access rights
        self.unlink_rights_check()

        # Update notifications
        notifications = []
        partner_ids = [partner.id for partner in self.mapped("ref_partner_ids")]
        if self.env.user.partner_id.id not in partner_ids:
            partner_ids.append(self.env.user.partner_id.id)
        for partner_id in partner_ids:
            notifications.append([
                (self._cr.dbname, "res.partner", partner_id),
                {"type": "deletion", "message_ids": list(self.ids)},
            ])
        self.env["bus.bus"].sendmany(notifications)

        # Store lead ids from messages in case we want to delete empty leads later
        lead_ids = []
        for rec in self.sudo():
            if rec.model == "crm.lead":
                lead_ids.append(rec.res_id)

        # Unlink
        if self.env.user.has_group("prt_mail_messages_pro.group_lost"):
            # Check is deleting lost messages
            all_lost = True
            for rec in self.sudo():
                if rec.model and rec.res_id:
                    all_lost = False
                    break

            # All messages are "lost". Unlink them with sudo
            if all_lost:
                super(MailMessage, self.sudo()).unlink()
            else:
                super(MailMessage, self).unlink_pro()
        else:
            super(MailMessage, self).unlink_pro()

        # All done if CRM Lead is not presented in models (eg CRM not installed)
        if self.crm_not_installed():
            return

        # Delete empty leads
        leads = (
            self.env["crm.lead"].browse(lead_ids)
            .filtered(lambda l: l.company_id.lead_delete and l.type == "lead")
        )

        # Add opportunities to delete
        leads += (
            self.env["crm.lead"].browse(lead_ids)
            .filtered(lambda l: l.company_id.opp_delete and l.type == "opportunity")
        )
        if len(leads.ids) > 0:
            self._delete_leads(leads.ids)

    # -- Move messages
    def message_move(
        self, dest_model, dest_res_id, notify="0", lead_delete=False, opp_delete=False
    ):
        """
        Moves messages to a new record
        :return:
        :param Char dest_model: name of the new record model
        :param Integer dest_res_id: id of the new record
        :param Char notify: add notification to destination thread
            '0': 'Do not notify'
            '1': 'Log internal note'
            '2': 'Send message'
        :param Boolean lead_delete: delete CRM Leads with no messages left
        :param Boolean opp_delete: delete CRM Opportunities with no messages left
        :return: nothing, just return)
        """

        # -- Can move messages?
        if not self.env.user.has_group("prt_mail_messages.group_move"):
            raise AccessError(_("You cannot move messages!"))

        # Prepare data for notifications. Store old record data
        old_records = []
        for message in self:
            old_records.append([
                message.id,
                "{}_{}".format(message.model, str(message.res_id)),
                "{}_{}".format(dest_model, str(dest_res_id)),
                [message.model, message.res_id],
                [dest_model, dest_res_id],
            ])

        # Store leads from messages in case we want to delete empty leads later
        leads = False
        if lead_delete:
            lead_messages = self.env["mail.message"].search([
                ("id", "in", self.ids), ("model", "=", "crm.lead")
            ])

            # Check if Opportunities are deleted as well
            if opp_delete:
                domain = [("id", "in", lead_messages.mapped("res_id"))]
            else:
                domain = [
                    ("id", "in", lead_messages.mapped("res_id")),
                    ("type", "=", "lead"),
                ]

            leads = self.env["crm.lead"].search(domain)

        # Get Conversations. Will check and delete empty ones later
        conversations = False
        conversation_messages = self.filtered(
            lambda m: m.model == "cetmix.conversation"
        )
        if len(conversation_messages) > 0:
            conversations = self.env["cetmix.conversation"].search([
                ("id", "in", conversation_messages.mapped("res_id"))
            ])

        # Get new parent message
        parent_message = self.env["mail.message"].search(
            [
                ("model", "=", dest_model),
                ("res_id", "=", dest_res_id),
                ("parent_id", "=", False),
            ],
            order="id asc",
            limit=1,
        )

        # Move messages
        if parent_message:
            self.sudo().write({
                "model": dest_model,
                "res_id": dest_res_id,
                "parent_id": parent_message.id,
            })
        else:
            self.sudo().write({
                "model": dest_model, "res_id": dest_res_id, "parent_id": False
            })

        # Move attachments. Use sudo() to override access rules issues
        self.mapped("attachment_ids").sudo().write({
            "res_model": dest_model, "res_id": dest_res_id
        })

        # Notify followers of destination record
        if notify and notify != "0":
            subtype = "mail.mt_note" if notify == "1" else "mail.mt_comment"
            body = _("%s messages moved to this record:") % (str(len(self)))
            # Add messages ref to body:
            i = 1
            url = (
                self.env["ir.config_parameter"].sudo().get_param("web.base.url") +
                "/web#id="
            )
            for message in self:
                body += ((' <a target="_blank" href="%s">') %
                         (url + str(message.id) + "&model=mail.message&view_type=form")
                         + (_("Message %s") % (str(i))) + "</a>")
                i += 1
            self.env[dest_model].browse([dest_res_id]).message_post(
                body=body,
                subject=_("Messages moved"),
                message_type="notification",
                subtype=subtype,
            )
        # Delete empty Conversations
        if conversations:
            self.env["mail.message"]._delete_conversations(conversations.ids)

        # Update notifications
        notifications = []
        partner_ids = [partner.id for partner in self.mapped("ref_partner_ids")]
        if self.env.user.partner_id.id not in partner_ids:
            partner_ids.append(self.env.user.partner_id.id)
        for partner_id in partner_ids:
            notifications.append([
                (self._cr.dbname, "res.partner", partner_id),
                {"type": "move_messages", "message_moved_ids": list(old_records)},
            ])
        self.env["bus.bus"].sendmany(notifications)

        # Update Conversation last message data if moved to Conversation
        if dest_model == "cetmix.conversation":
            conversation = self.env["cetmix.conversation"].browse(dest_res_id)
            if conversation.message_ids:  # To ensure
                messages = conversation.message_ids.sorted(
                    key=lambda m: m.id, reverse=True
                )
                conversation.update({
                    "last_message_post": messages[0].date,
                    "last_message_by": messages[0].author_id.id,
                })

        # Delete empty leads
        if not leads:
            return

        # Compose list of leads to unlink
        leads_2_delete = self.env["crm.lead"]
        for lead in leads:
            message_count = self.env["mail.message"].search_count([
                ("res_id", "=", lead.id),
                ("model", "=", "crm.lead"),
                ("message_type", "!=", "notification"),
            ])
            if message_count == 0:
                leads_2_delete += lead

        # Delete leads with no messages
        if len(leads_2_delete) > 0:
            leads_2_delete.unlink()
