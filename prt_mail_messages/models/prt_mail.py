from odoo import models, fields, api, _, tools, SUPERUSER_ID, registry
from odoo.exceptions import MissingError, AccessError
from odoo.tools.misc import split_every
from email.utils import parseaddr
import logging
import threading

_logger = logging.getLogger(__name__)

TREE_VIEW_ID = False
FORM_VIEW_ID = False

# List of forbidden models
FORBIDDEN_MODELS = ['mail.channel']

# Search for 'ghost' models is performed
GHOSTS_CHECKED = False


###############
# Mail.Thread #
###############
class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # -- Add context to unlink
    @api.multi
    def unlink(self):
        return super(MailThread, self.with_context(force_delete=True)).unlink()


################
# Mail.Message #
################
class PRTMailMessage(models.Model):
    _name = "mail.message"
    _inherit = "mail.message"

    author_display = fields.Char(string="Author", compute="_author_display")

    # Fields to avoid access check issues
    author_allowed_id = fields.Many2one(string="Author", comodel_name='res.partner',
                                        compute='_get_author_allowed',
                                        search='_search_author_allowed')

    partner_allowed_ids = fields.Many2many(string="Recipients", comodel_name='res.partner',
                                           compute='_get_partners_allowed')
    attachment_allowed_ids = fields.Many2many(string="Attachments", comodel_name='ir.attachment',
                                              compute='_get_attachments_allowed')
    subject_display = fields.Char(string="Subject", compute="_subject_display")
    partner_count = fields.Integer(string="Recipients count", compute='_partner_count')
    record_ref = fields.Reference(string="Message Record", selection='_referenceable_models',
                                  compute='_record_ref')
    attachment_count = fields.Integer(string="Attachments count", compute='_attachment_count')
    thread_messages_count = fields.Integer(string="Messages in thread", compute='_thread_messages_count',
                                           help="Total number of messages in thread")
    ref_partner_ids = fields.Many2many(string="Followers", comodel_name='res.partner',
                                       compute='_message_followers')
    ref_partner_count = fields.Integer(string="Followers", compute='_ref_partner_count')
    mail_mail_ids = fields.One2many(strting="Email Message", comodel_name='mail.mail', inverse_name='mail_message_id',
                                    auto_join=True)
    is_error = fields.Boolean(string="Sending Error", compute='_get_send_error')

    # -- Check if error while sending TODO check log
    @api.depends('notification_ids')
    @api.multi
    def _get_send_error(self):
        for rec in self.filtered(lambda m: m.notification_ids.mapped('email_status') not in ['sent']):
            if len(rec.mail_mail_ids.filtered(lambda m: m.state == 'exception')) > 0:
                rec.is_error = True

    # -- Unlink
    @api.multi
    def unlink(self):

        # Superuser?
        if self.env.user.id == SUPERUSER_ID:
            return super(PRTMailMessage, self).unlink()

        # Force delete ?
        if self._context.get('force_delete', False):
            return super(PRTMailMessage, self).unlink()

        # Can delete messages?
        if not self.env.user.has_group('prt_mail_messages.group_delete'):
            raise AccessError(_("You cannot delete messages!"))

        # Can delete any message
        if self.env.user.has_group('prt_mail_messages.group_delete_any'):
            return super(PRTMailMessage, self).unlink()

        partner_id = self.env.user.partner_id.id
        for rec in self:
            """
            Can delete if user:
            - Is Message Author for 'comment' message
            - Is the only 'recipient' for 'email' message            
            """
            # Sent
            if rec.message_type == 'comment':
                # Is Author?
                if not rec.author_allowed_id.id == partner_id:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display, _("You are not the message author"))))

            # Received
            if rec.message_type == 'email':
                # No recipients
                if not rec.partner_ids:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display,
                                                         _("Message recipients undefined"))))

                # Has several recipients?
                if len(rec.partner_ids) > 1:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display,
                                                         _("Message has multiple recipients"))))

                # Partner is not that one recipient
                if not rec.partner_ids[0].id == partner_id:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display,
                                                         _("You are not the message recipient"))))

        return super(PRTMailMessage, self).unlink()

    # -- Count ref Partners
    @api.multi
    def _ref_partner_count(self):
        for rec in self:
            rec.ref_partner_count = len(rec.ref_partner_ids)

    """
    Sometimes user has access to record but does not have access to author or recipients.
    Below is a workaround for author, recipient and followers
    """

    # -- Get allowed author
    @api.depends('author_id')
    @api.multi
    def _get_author_allowed(self):
        forbidden_partners = self.env['res.partner']
        for rec in self:
            author_id = rec.author_id
            if author_id not in forbidden_partners:
                try:
                    author_id.check_access_rule('read')
                    rec.author_allowed_id = author_id
                except:
                    forbidden_partners += author_id

    # -- Get allowed recipients
    @api.depends('attachment_ids')
    @api.multi
    def _get_attachments_allowed(self):
        forbidden_records = []
        for rec in self:
            attachments_allowed = self.env['ir.attachment']
            for attachment in rec.attachment_ids:
                att_obj = attachment.sudo().read(['res_model', 'res_id'])[0]
                model = att_obj.get('res_model', False)
                res_id = att_obj.get('res_id', False)
                if (model, res_id) in forbidden_records:
                    continue
                try:
                    self.env[model].browse(res_id).check_access_rule('read')
                except:
                    forbidden_records += (model, res_id)
                    continue
                attachments_allowed += attachment

            rec.attachment_allowed_ids = attachments_allowed

    # -- Get allowed recipients
    @api.depends('partner_ids')
    @api.multi
    def _get_partners_allowed(self):
        forbidden_partners = self.env['res.partner']
        for rec in self:
            recipients_allowed = self.env['res.partner']
            for partner in rec.partner_ids - forbidden_partners:
                try:
                    partner.check_access_rule('read')
                    recipients_allowed += partner
                except:
                    forbidden_partners += partner

            rec.partner_allowed_ids = recipients_allowed

    # -- Search allowed authors
    @api.model
    def _search_author_allowed(self, operator, value):
        return [('author_id', operator, value)]

    # -- Get related record followers
    """
    Check if model has 'followers' field and user has access to followers
    """

    @api.depends('record_ref')
    @api.multi
    def _message_followers(self):
        forbidden_partners = self.env['res.partner']
        approved_models = []
        for rec in self:
            if rec.record_ref:

                # Check model

                model = rec.model
                if model not in approved_models:
                    if 'message_partner_ids' in self.env[model]._fields:
                        approved_models.append(model)
                    else:
                        continue

                followers_allowed = self.env['res.partner']
                for follower in rec.record_ref.message_partner_ids - forbidden_partners:
                    try:
                        follower.check_access_rule('read')
                        followers_allowed += follower
                    except:
                        forbidden_partners += follower
                rec.ref_partner_ids = followers_allowed

    # -- Dummy
    @api.multi
    def dummy(self):
        return

    # -- Get Subject for tree view
    @api.depends('subject')
    @api.multi
    def _subject_display(self):

        # Get model names first. Use this method to get translated values
        ir_models = self.env['ir.model'].search([('model', 'in', list(set(self.mapped('model'))))])
        model_dict = {}
        for model in ir_models:
            # Check if model has "name" field
            has_name = self.env['ir.model.fields'].sudo().search_count([('model_id', '=', model.id),
                                                                        ('name', '=', 'name')])
            model_dict.update({model.model: [model.name, has_name]})

        # Compose subject
        for rec in self:
            if rec.subject:
                subject_display = rec.subject
            else:
                subject_display = '=== No Reference ==='

            # Has reference
            if rec.record_ref:
                subject_display = model_dict.get(rec.model)[0]

                # Has 'name' field
                if model_dict.get(rec.model, False)[1]:
                    subject_display = "%s: %s" % (subject_display, rec.record_ref.sudo().name)

                # Has subject
                if rec.subject:
                    subject_display = "%s => %s" % (subject_display, rec.subject)

            # Set subject
            rec.subject_display = subject_display

    # -- Get Author for tree view
    @api.depends('author_allowed_id')
    @api.multi
    def _author_display(self):
        for rec in self:
            rec.author_display = rec.author_allowed_id.name if rec.author_allowed_id else rec.email_from

    # -- Count recipients
    @api.depends('partner_allowed_ids')
    @api.multi
    def _partner_count(self):
        for rec in self:
            rec.partner_count = len(rec.partner_allowed_ids)

    # -- Count attachments
    @api.depends('attachment_ids')
    @api.multi
    def _attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    # -- Count messages in same thread
    @api.depends('res_id')
    @api.multi
    def _thread_messages_count(self):
        for rec in self:
            rec.thread_messages_count = self.search_count(['&', '&',
                                                           ('model', '=', rec.model),
                                                           ('res_id', '=', rec.res_id),
                                                           ('message_type', '!=', 'notification')])

    # -- Ref models
    @api.model
    def _referenceable_models(self):
        return [(x.model, x.name) for x in self.env['ir.model'].sudo().search([('transient', '=', False)])]

    # -- Compose reference
    @api.depends('res_id')
    @api.multi
    def _record_ref(self):
        for rec in self:
            if rec.model:
                if rec.res_id:
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
        self._cr.execute(""" SELECT model FROM ir_model
                                    WHERE transient = False
                                    AND NOT model = ANY(%s) """, (list(FORBIDDEN_MODELS),))

        # Check each model
        for msg_model in self._cr.fetchall():
            model = msg_model[0]
            if not self.env['ir.model'].sudo().search([('model', '=', model)]).modules:
                FORBIDDEN_MODELS.append(model)

        # Mark as checked
        GHOSTS_CHECKED = True
        return FORBIDDEN_MODELS[:]

    # -- Open messages of the same thread
    @api.multi
    def thread_messages(self):
        self.ensure_one()

        global TREE_VIEW_ID
        global FORM_VIEW_ID

        # Cache Tree View and Form View ids
        if not TREE_VIEW_ID:
            TREE_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_tree').id
            FORM_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_form').id

        return {
            'name': _("Messages"),
            "views": [[TREE_VIEW_ID, "tree"], [FORM_VIEW_ID, "form"]],
            'res_model': 'mail.message',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('message_type', '!=', 'notification'), ('model', '=', self.model), ('res_id', '=', self.res_id)]
        }

    # -- Override _search
    """
    mail.message overrides generic '_search' defined in 'model' to implement own logic for message access rights.
    However sometimes it does not work as expected.
    So we use generic method in 'model' and check access rights later in 'search' method.
    Following keys in context are used:
        - 'check_messages_access': if not set legacy 'search' is performed
    """
    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):

        if not self._context.get('check_messages_access', False):
            return super(PRTMailMessage, self)._search(args=args, offset=offset, limit=limit, order=order, count=count,
                                                       access_rights_uid=access_rights_uid)

        if expression.is_false(self, args):
            # optimization: no need to query, as no record satisfies the domain
            return 0 if count else []

        query = self._where_calc(args)
        order_by = self._generate_order_by(order, query)
        from_clause, where_clause, where_clause_params = query.get_sql()

        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        if count:
            # Ignore order, limit and offset when just counting, they don't make sense and could
            # hurt performance
            query_str = 'SELECT count(1) FROM ' + from_clause + where_str
            self._cr.execute(query_str, where_clause_params)
            res = self._cr.fetchone()
            return res[0]

        limit_str = limit and ' limit %d' % limit or ''
        offset_str = offset and ' offset %d' % offset or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by + limit_str + offset_str
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()

        # TDE note: with auto_join, we could have several lines about the same result
        # i.e. a lead with several unread messages; we uniquify the result using
        # a fast way to do it while preserving order (http://www.peterbe.com/plog/uniqifiers-benchmark)
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        return _uniquify_list([x[0] for x in res])

    # -- Override read
    """
    Avoid access rights check implemented in original mail.message
    Will check them later in "search"
    Using base model function instead
        Following keys in context are used:
        - 'check_messages_access': if not set legacy 'search' is performed
    """
    @api.multi
    def read(self, fields=None, load='_classic_read'):

        if not self._context.get('check_messages_access', False):
            return super(PRTMailMessage, self).read(fields=fields, load=load)

        """
        From here starts the original 'read' code
        """
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
        name_fields = [(name, self._fields[name]) for name in (stored + inherited + computed)]
        use_name_get = (load == '_classic_read')

        for record in self:
            try:
                values = {'id': record.id}
                for name, field in name_fields:
                    values[name] = field.convert_to_read(record[name], record, use_name_get)
                result.append(values)
            except MissingError:
                pass

        return result

    # -- Override Search
    """
    Mail message access rights/rules checked must be done based on the access rights/rules of the message record.
    As a workaround we are using 'search' method to filter messages from unavailable records.
    
    Display only messages where user has read access to related record.
    
    Following keys in context are used:
    - 'check_messages_access': if not set legacy 'search' is performed
    - 'force_record_reset': in case message refers to non-existing (e.g. removed) record model and res_id will be set NULL
    """
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):

        if not self._context.get('check_messages_access', False):
            return super(PRTMailMessage, self).search(args=args, offset=offset, limit=limit, order=order, count=count)

        # Store context keys
        force_record_reset = self._context.get('force_record_reset', False)
        # Store initial args in case we need them later
        modded_args = args

        # Define sort order
        if order and ('ASC' in order or 'asc' in order):
            sort_asc = True
        else:
            sort_asc = False

        # Check model access 1st
        forbidden_models = self._get_forbidden_models()

        # Get list of possible followed models
        self._cr.execute(""" SELECT model FROM ir_model
                                        WHERE is_mail_thread = True
                                        AND NOT model = ANY(%s) """, (list(forbidden_models),))

        # Check each model
        for msg_model in self._cr.fetchall():
            if not self.env['ir.model.access'].check(msg_model[0], 'read', raise_exception=False):
                forbidden_models.append(msg_model[0])

        # Add forbidden models condition to domain
        if len(forbidden_models) > 0:
            modded_args.append(['model', 'not in', forbidden_models])

        # Return Count
        if count:
            return super(PRTMailMessage, self).search(args=modded_args, offset=offset, limit=limit, order=order, count=True)

        # Get records
        res_ids = self._search(args=modded_args, offset=offset, limit=limit, order=order, count=False)
        res = self.browse(res_ids)

        # Cache allowed records and store last id
        rec_allowed = []
        rec_forbidden = []
        last_id = False

        # Now check record rules for each message
        res_allowed = self.env['mail.message']
        len_initial = limit if limit else len(res)
        len_filtered = 0

        # Check records
        """
        Check in we need include "lost" messages. These are messages with no model or res_id
        """
        get_lost = self._context.get('get_lost', False)

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
                    target_rec = self.env[model].search([('id', '=', res_id)])
                    if not target_rec:
                        # Reset model and res_id
                        if force_record_reset:
                            rec.sudo().write({'model': False, 'res_id': False})
                        continue
                    # Check message record
                    target_rec.check_access_rule('read')
                    rec_allowed.append((model, res_id))
                except:
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

        """
        Step 2+n in case need to get more records
        """
        # Get remaining recs
        while len_remaining > 0:

            new_args = modded_args.copy()
            if sort_asc:
                new_args.append(['id', '>', last_id])
            else:
                new_args.append(['id', '<', last_id])

            # Let's try!))
            res_2_ids = self._search(args=new_args, offset=0, limit=limit, order=order, count=False)
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
                        target_rec = self.env[model].search([('id', '=', res_id)])
                        if not target_rec:
                            # Reset model and res_id
                            if force_record_reset:
                                rec.sudo().write({'model': False, 'res_id': False})
                            continue
                        # Check message record
                        target_rec.check_access_rule('read')
                        rec_allowed.append((model, res_id))
                    except:
                        rec_forbidden.append((model, res_id))
                        continue

                res_allowed += rec
                len_remaining -= 1

        return res_allowed

    # -- Prepare context for reply or quote message
    @api.multi
    def reply_prep_context(self):
        self.ensure_one()
        body = False
        wizard_mode = self._context.get('wizard_mode', False)

        if wizard_mode in ['quote', 'forward']:
            body = (_(
                "<div font-style=normal;><br/></div><blockquote>----- Original message ----- <br/> Date: %s <br/> From: %s <br/> Subject: %s <br/><br/>%s</blockquote>") %
                    (str(self.date), self.author_display, self.subject_display, self.body))

        ctx = {
            'default_res_id': self.res_id,
            'default_parent_id': False if wizard_mode == 'forward' else self.id,
            'default_model': self.model,
            'default_partner_ids': [self.author_allowed_id.id] if self.author_allowed_id else [],
            'default_attachment_ids': self.attachment_ids.ids if wizard_mode == 'forward' else [],
            'default_is_log': False,
            'default_body': body,
            'default_wizard_mode': wizard_mode
        }
        return ctx

    # -- Reply or quote message
    @api.multi
    def reply(self):
        self.ensure_one()

        return {
            'name': _("New message"),
            "views": [[False, "form"]],
            'res_model': 'mail.compose.message',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.reply_prep_context()
        }


    # -- Move message
    @api.multi
    def move(self):
        self.ensure_one()

        return {
            'name': _("Move messages"),
            "views": [[False, "form"]],
            'res_model': 'prt.message.move.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    # -- Assign author
    @api.multi
    def assign_author(self):
        addr = parseaddr(self.email_from)
        return {
            'name': _("Assign Author"),
            "views": [[False, "form"]],
            'res_model': 'cx.message.partner.assign.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_name': addr[0],
                'default_email': addr[1]
            }
        }


#####################
# Mail Move Message #
#####################
class PRTMailMove(models.TransientModel):
    _name = 'prt.message.move.wiz'
    _description = 'Move Messages To Other Thread'

    model_to = fields.Reference(string="Move to", selection='_referenceable_models')
    lead_delete = fields.Boolean(string="Delete Empty Leads",
                                 help="If all messages are moved from lead and there are no other messages"
                                      " left except for notifications lead will be deleted")
    opp_delete = fields.Boolean(string="Delete Empty Opportunities",
                                help="If all messages are moved from opportunity and there are no other messages"
                                     " left except for notifications opportunity will be deleted")

    notify = fields.Selection([
        ('0', 'Do not notify'),
        ('1', 'Log internal note'),
        ('2', 'Send message'),
    ], string="Notify", required=True,
        default='0',
        help="Notify followers of destination record")

    # -- Ref models
    @api.model
    def _referenceable_models(self):
        return [(x.model, x.name) for x in self.env['ir.model'].sudo().search([('is_mail_thread', '=', True),
                                                                               ('model', '!=', 'mail.thread')])]


################
# Res.Partner #
################
class PRTPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    # -- Notify
    def _notify(self, message, rdata, record, force_send=False, send_after_commit=True, model_description=False, mail_auto_delete=True):
        """ Method to send email linked to notified messages. The recipients are
        the recordset on which this method is called.

        :param message: mail.message record to notify;
        :param rdata: recipient data (see mail.message _notify);
        :param record: optional record on which the message was posted;
        :param force_send: tells whether to send notification emails within the
          current transaction or to use the email queue;
        :param send_after_commit: if force_send, tells whether to send emails after
          the transaction has been committed using a post-commit hook;
        :param model_description: optional data used in notification process (see
          notification templates);
        :param mail_auto_delete: delete notification emails once sent;
        """
        if not rdata:
            return True

        # Cetmix. Check context.
        if not self._context.get("default_wizard_mode", False) in ['quote', 'forward']:
            return super(PRTPartner, self)._notify(message=message, rdata=rdata, record=record,
                                                   force_send=force_send,
                                                   send_after_commit=send_after_commit,
                                                   model_description=model_description,
                                                   mail_auto_delete=mail_auto_delete)

        # Get signature location
        signature_location = self._context.get("signature_location", False)

        # After quote
        if signature_location == 'a':
            return super(PRTPartner, self)._notify(message=message, rdata=rdata, record=record,
                                                   force_send=force_send,
                                                   send_after_commit=send_after_commit,
                                                   model_description=model_description,
                                                   mail_auto_delete=mail_auto_delete)

        base_template_ctx = self._notify_prepare_template_context(message, record, model_description=model_description)
        # Cetmix. Get signature
        signature = base_template_ctx.pop("signature", False)
        template_xmlid = message.layout if message.layout else 'mail.message_notification_email'
        try:
            base_template = self.env.ref(template_xmlid, raise_if_not_found=True).with_context(lang=base_template_ctx['lang'])
        except ValueError:
            _logger.warning('QWeb template %s not found when sending notification emails. Sending without layouting.' % (template_xmlid))
            base_template = False

        # prepare notification mail values
        base_mail_values = {
            'mail_message_id': message.id,
            'mail_server_id': message.mail_server_id.id,
            'auto_delete': mail_auto_delete,
            'references': message.parent_id.message_id if message.parent_id else False
        }
        if record:
            base_mail_values.update(self.env['mail.thread']._notify_specific_email_values_on_records(message, records=record))

        # classify recipients: actions / no action
        recipients = self.env['mail.thread']._notify_classify_recipients_on_records(message, rdata, records=record)

        Mail = self.env['mail.mail'].sudo()
        emails = self.env['mail.mail'].sudo()
        email_pids = set()
        recipients_nbr, recipients_max = 0, 50
        for group_tpl_values in [group for group in recipients.values() if group['recipients']]:
            # generate notification email content
            template_ctx = {**base_template_ctx, **group_tpl_values}
            mail_body = base_template.render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
            mail_body = self.env['mail.thread']._replace_local_links(mail_body)
            mail_subject = message.subject or (message.record_name and 'Re: %s' % message.record_name)

            # Cetmix. Put signature before quote
            if signature_location == 'b':
                quote_index = mail_body.find("<blockquote")
                if quote_index:
                    mail_body = "%s%s%s" % (
                        mail_body[:quote_index], signature, mail_body[quote_index:])  # legacy mode

            # send email
            for email_chunk in split_every(50, group_tpl_values['recipients']):
                recipient_values = self.env['mail.thread']._notify_email_recipients_on_records(message, email_chunk, records=record)
                create_values = {
                    'body_html': mail_body,
                    'subject': mail_subject,
                }
                create_values.update(base_mail_values)
                create_values.update(recipient_values)
                recipient_ids = [r[1] for r in create_values.get('recipient_ids', [])]
                email = Mail.create(create_values)

                if email and recipient_ids:
                    notifications = self.env['mail.notification'].sudo().search([
                        ('mail_message_id', '=', email.mail_message_id.id),
                        ('res_partner_id', 'in', list(recipient_ids))
                    ])
                    notifications.write({
                        'is_email': True,
                        'mail_id': email.id,
                        'is_read': True,  # handle by email discards Inbox notification
                        'email_status': 'ready',
                    })

                emails |= email
                email_pids.update(recipient_ids)

        # NOTE:
        #   1. for more than 50 followers, use the queue system
        #   2. do not send emails immediately if the registry is not loaded,
        #      to prevent sending email during a simple update of the database
        #      using the command-line.
        test_mode = getattr(threading.currentThread(), 'testing', False)
        if force_send and len(emails) < recipients_max and \
                (not self.pool._init or test_mode):
            email_ids = emails.ids
            dbname = self.env.cr.dbname
            _context = self._context

            def send_notifications():
                db_registry = registry(dbname)
                with api.Environment.manage(), db_registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, _context)
                    env['mail.mail'].browse(email_ids).send()

            # unless asked specifically, send emails after the transaction to
            # avoid side effects due to emails being sent while the transaction fails
            if not test_mode and send_after_commit:
                self._cr.after('commit', send_notifications)
            else:
                emails.send()

        return True

    messages_from_count = fields.Integer(string="Messages From", compute='_messages_from_count')
    messages_to_count = fields.Integer(string="Messages To", compute='_messages_to_count')

    # -- Count messages from
    @api.depends('message_ids')
    @api.multi
    def _messages_from_count(self):
        for rec in self:
            if rec.id:
                rec.messages_from_count = self.env['mail.message'].search_count([('author_id', 'child_of', rec.id),
                                                                                 ('message_type', '!=', 'notification'),
                                                                                 ('model', '!=', 'mail.channel')])
            else:
                rec.messages_from_count = 0

    # -- Count messages from
    @api.depends('message_ids')
    @api.multi
    def _messages_to_count(self):
        for rec in self:
            rec.messages_to_count = self.env['mail.message'].search_count([('partner_ids', 'in', [rec.id]),
                                                                           ('message_type', '!=', 'notification'),
                                                                           ('model', '!=', 'mail.channel')])

    # -- Open related
    @api.multi
    def partner_messages(self):
        self.ensure_one()

        # Choose what messages to display
        open_mode = self._context.get('open_mode', 'from')

        if open_mode == 'from':
            domain = [('message_type', '!=', 'notification'),
                      ('author_id', 'child_of', self.id),
                      ('model', '!=', 'mail.channel')]
        elif open_mode == 'to':
            domain = [('message_type', '!=', 'notification'),
                      ('partner_ids', 'in', [self.id]),
                      ('model', '!=', 'mail.channel')]
        else:
            domain = [('message_type', '!=', 'notification'),
                      ('model', '!=', 'mail.channel'),
                      '|', ('partner_ids', 'in', [self.id]), ('author_id', 'child_of', self.id)]

        # Cache Tree View and Form View ids
        global TREE_VIEW_ID
        global FORM_VIEW_ID

        if not TREE_VIEW_ID:
            TREE_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_tree').id
            FORM_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_form').id

        return {
            'name': _("Messages"),
            "views": [[TREE_VIEW_ID, "tree"], [FORM_VIEW_ID, "form"]],
            'res_model': 'mail.message',
            'type': 'ir.actions.act_window',
            'context': "{'check_messages_access': True}",
            'target': 'current',
            'domain': domain
        }

    # -- Send email from partner's form view
    @api.multi
    def send_email(self):
        self.ensure_one()

        return {
            'name': _("New message"),
            "views": [[False, "form"]],
            'res_model': 'mail.compose.message',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_res_id': False,
                'default_parent_id': False,
                'default_model': False,
                'default_partner_ids': [self.id],
                'default_attachment_ids': False,
                'default_is_log': False,
                'default_body': False,
                'default_wizard_mode': 'compose'
            }
        }


########################
# Mail.Compose Message #
########################
class PRTMailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'
    _name = 'mail.compose.message'

    wizard_mode = fields.Char(string="Wizard mode")
    forward_ref = fields.Reference(string="Attach to record", selection='_referenceable_models_fwd',
                                   readonly=False)
    signature_location = fields.Selection([
        ('b', 'Before quote'),
        ('a', 'Message bottom'),
        ('n', 'No signature')
    ], string='Signature Location', default='b', required=True,
        help='Whether to put signature before or after the quoted text.')

    # -- Send
    def send_mail(self, auto_commit=False):
        return super(PRTMailComposer, self.with_context(signature_location=self.signature_location)). \
            send_mail(auto_commit=auto_commit)

    # -- Ref models
    @api.model
    def _referenceable_models_fwd(self):
        return [(x.model, x.name) for x in self.env['ir.model'].sudo().search([('is_mail_thread', '=', True),
                                                                               ('model', '!=', 'mail.thread')])]

    # -- Record ref change
    @api.onchange('forward_ref')
    @api.multi
    def ref_change(self):
        self.ensure_one()
        if self.forward_ref:
            self.update({
                'model': self.forward_ref._name,
                'res_id': self.forward_ref.id
            })

    # -- Get record data
    @api.model
    def get_record_data(self, values):
        """
        Copy-pasted mail.compose.message original function so stay aware in case it is changed in Odoo core!

        Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        result = {}
        subj = self._context.get('default_subject', False)
        subject = tools.ustr(subj) if subj else False
        if not subject:
            if values.get('parent_id'):
                parent = self.env['mail.message'].browse(values.get('parent_id'))
                result['record_name'] = parent.record_name,
                subject = tools.ustr(parent.subject or parent.record_name or '')
                if not values.get('model'):
                    result['model'] = parent.model
                if not values.get('res_id'):
                    result['res_id'] = parent.res_id
                partner_ids = values.get('partner_ids', list()) + \
                              [(4, xid) for xid in parent.partner_ids.filtered(lambda rec: rec.email not in [self.env.user.email, self.env.user.company_id.email]).ids]
                if self._context.get('is_private') and parent.author_id:  # check message is private then add author also in partner list.
                    partner_ids += [(4, parent.author_id.id)]
                result['partner_ids'] = partner_ids
            elif values.get('model') and values.get('res_id'):
                doc_name_get = self.env[values.get('model')].browse(values.get('res_id')).name_get()
                result['record_name'] = doc_name_get and doc_name_get[0][1] or ''
                subject = tools.ustr(result['record_name'])

            # Change prefix in case we are forwarding
            re_prefix = _('Fwd:') if self._context.get('default_wizard_mode', False) == 'forward' else _('Re:')

            if subject and not (subject.startswith('Re:') or subject.startswith(re_prefix)):
                subject = "%s %s" % (re_prefix, subject)

        result['subject'] = subject

        return result


#################
# Author assign #
#################
class MessagePartnerAssign(models.TransientModel):
    _name = 'cx.message.partner.assign.wiz'
    _description = 'Assign Partner to Messages'

    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    same_email = fields.Boolean(string="Match Email", default=True,
                                help="Show Partners with same email address only")
    partner_id = fields.Many2one(string="Assign To", comodel_name='res.partner')

# Legacy! keep those imports here to avoid dependency cycle errors
from odoo.osv import expression