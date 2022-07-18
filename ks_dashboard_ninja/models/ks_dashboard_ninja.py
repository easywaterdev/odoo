# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
import datetime
import json
from odoo.addons.ks_dashboard_ninja.lib.ks_date_filter_selections import ks_get_date

class KsDashboardNinjaBoard(models.Model):
    _name = 'ks_dashboard_ninja.board'
    _description = 'Dashboard Ninja'

    name = fields.Char(string="Dashboard Name", required=True, size=35)
    ks_dashboard_items_ids = fields.One2many('ks_dashboard_ninja.item', 'ks_dashboard_ninja_board_id',
                                             string='Dashboard Items')
    ks_dashboard_menu_name = fields.Char(string="Menu Name")
    ks_dashboard_top_menu_id = fields.Many2one('ir.ui.menu', domain="[('parent_id','=',False)]",
                                               string="Show Under Menu")
    ks_dashboard_client_action_id = fields.Many2one('ir.actions.client')
    ks_dashboard_menu_id = fields.Many2one('ir.ui.menu')
    ks_dashboard_state = fields.Char()
    ks_dashboard_active = fields.Boolean(string="Active", default=True)
    ks_dashboard_group_access = fields.Many2many('res.groups', string="Group Access")

    # DateFilter Fields
    ks_dashboard_start_date = fields.Datetime(string="Start Date")
    ks_dashboard_end_date = fields.Datetime(string="End Date")
    ks_date_filter_selection = fields.Selection([
        ('l_none', 'All Time'),
        ('l_day', 'Today'),
        ('t_week', 'This Week'),
        ('t_month', 'This Month'),
        ('t_quarter', 'This Quarter'),
        ('t_year', 'This Year'),
        ('n_day', 'Next Day'),
        ('n_week', 'Next Week'),
        ('n_month', 'Next Month'),
        ('n_quarter', 'Next Quarter'),
        ('n_year', 'Next Year'),
        ('ls_day', 'Last Day'),
        ('ls_week', 'Last Week'),
        ('ls_month', 'Last Month'),
        ('ls_quarter', 'Last Quarter'),
        ('ls_year', 'Last Year'),
        ('l_week', 'Last 7 days'),
        ('l_month', 'Last 30 days'),
        ('l_quarter', 'Last 90 days'),
        ('l_year', 'Last 365 days'),
        ('ls_past_until_now', 'Past Till Now'),
        ('ls_pastwithout_now', ' Past Excluding Today'),
        ('n_future_starting_now', 'Future Starting Now'),
        ('n_futurestarting_tomorrow', 'Future Starting Tomorrow'),
        ('l_custom', 'Custom Filter'),
    ], default='l_none', string="Default Date Filter")

    ks_gridstack_config = fields.Char('Item Configurations')
    ks_dashboard_default_template = fields.Many2one('ks_dashboard_ninja.board_template',
                                                    default=lambda self: self.env.ref('ks_dashboard_ninja.ks_blank',
                                                                                      False),
                                                    string="Dashboard Template")

    ks_set_interval = fields.Selection([
        (15000, '15 Seconds'),
        (30000, '30 Seconds'),
        (45000, '45 Seconds'),
        (60000, '1 minute'),
        (120000, '2 minute'),
        (300000, '5 minute'),
        (600000, '10 minute'),
    ], string="Default Update Interval", help="Update Interval for new items only")
    ks_dashboard_menu_sequence = fields.Integer(string="Menu Sequence", default=10,
                                                help="Smallest sequence give high priority and Highest sequence give "
                                                     "low priority")

    @api.model
    def create(self, vals):
        record = super(KsDashboardNinjaBoard, self).create(vals)
        if 'ks_dashboard_top_menu_id' in vals and 'ks_dashboard_menu_name' in vals:
            action_id = {
                'name': vals['ks_dashboard_menu_name'] + " Action",
                'res_model': 'ks_dashboard_ninja.board',
                'tag': 'ks_dashboard_ninja',
                'params': {'ks_dashboard_id': record.id},
            }
            record.ks_dashboard_client_action_id = self.env['ir.actions.client'].sudo().create(action_id)

            record.ks_dashboard_menu_id = self.env['ir.ui.menu'].sudo().create({
                'name': vals['ks_dashboard_menu_name'],
                'active': vals.get('ks_dashboard_active', True),
                'parent_id': vals['ks_dashboard_top_menu_id'],
                'action': "ir.actions.client," + str(record.ks_dashboard_client_action_id.id),
                'groups_id': vals.get('ks_dashboard_group_access', False),
                'sequence': vals.get('ks_dashboard_menu_sequence', 10)
            })

        if record.ks_dashboard_default_template and record.ks_dashboard_default_template.ks_item_count:
            ks_gridstack_config = {}
            template_data = json.loads(record.ks_dashboard_default_template.ks_gridstack_config)
            for item_data in template_data:
                dashboard_item = self.env.ref(item_data['item_id']).copy({'ks_dashboard_ninja_board_id': record.id})
                ks_gridstack_config[dashboard_item.id] = item_data['data']
            record.ks_gridstack_config = json.dumps(ks_gridstack_config)
        return record

    @api.onchange('ks_date_filter_selection')
    def ks_date_filter_selection_onchange(self):
        for rec in self:
            if rec.ks_date_filter_selection and rec.ks_date_filter_selection != 'l_custom':
                rec.ks_dashboard_start_date = False
                rec.ks_dashboard_end_date = False

    @api.constrains('ks_dashboard_start_date', 'ks_dashboard_end_date')
    def ks_validate_dashboard_datetime(self):
        for rec in self:
            if rec.ks_dashboard_start_date and rec.ks_dashboard_end_date:
                if rec.ks_dashboard_start_date >= rec.ks_dashboard_end_date:
                    raise ValidationError(_("Start Date should be less than End Date"))

    @api.multi
    def write(self, vals):
        if vals.get('ks_date_filter_selection', False) and vals.get('ks_date_filter_selection') != 'l_custom':
            vals.update({
                'ks_dashboard_start_date': False,
                'ks_dashboard_end_date': False

            })
        record = super(KsDashboardNinjaBoard, self).write(vals)
        for rec in self:
            if 'ks_dashboard_menu_name' in vals:
                if self.env.ref('ks_dashboard_ninja.ks_my_default_dashboard_board') and self.env.ref(
                        'ks_dashboard_ninja.ks_my_default_dashboard_board').sudo().id == rec.id:
                    if self.env.ref('ks_dashboard_ninja.board_menu_root', False):
                        self.env.ref('ks_dashboard_ninja.board_menu_root').sudo().name = vals['ks_dashboard_menu_name']
                else:
                    rec.ks_dashboard_menu_id.sudo().name = vals['ks_dashboard_menu_name']
            if 'ks_dashboard_group_access' in vals:
                if self.env.ref('ks_dashboard_ninja.ks_my_default_dashboard_board').id == rec.id:
                    if self.env.ref('ks_dashboard_ninja.board_menu_root', False):
                        self.env.ref('ks_dashboard_ninja.board_menu_root').groups_id = vals['ks_dashboard_group_access']
                else:
                    rec.ks_dashboard_menu_id.sudo().groups_id = vals['ks_dashboard_group_access']
            if 'ks_dashboard_active' in vals and rec.ks_dashboard_menu_id:
                rec.ks_dashboard_menu_id.sudo().active = vals['ks_dashboard_active']

            if 'ks_dashboard_top_menu_id' in vals:
                rec.ks_dashboard_menu_id.write(
                    {'parent_id': vals['ks_dashboard_top_menu_id']}
                )

            if 'ks_dashboard_menu_sequence' in vals:
                rec.ks_dashboard_menu_id.sudo().sequence = vals['ks_dashboard_menu_sequence']

        return record

    @api.multi
    def unlink(self):
        if self.env.ref('ks_dashboard_ninja.ks_my_default_dashboard_board').id in self.ids:
            raise ValidationError(_("Default Dashboard can't be deleted."))
        else:
            for rec in self:
                rec.ks_dashboard_client_action_id.sudo().unlink()
                rec.ks_dashboard_menu_id.sudo().unlink()
                rec.ks_dashboard_items_ids.unlink()
        res = super(KsDashboardNinjaBoard, self).unlink()
        return res

    @api.model
    def ks_fetch_dashboard_data(self, ks_dashboard_id, ks_item_domain=False):
        """
        Return Dictionary of Dashboard Data.
        :param ks_dashboard_id: Integer
        :param ks_item_domain: List[List]
        :return: dict
        """
        has_group_ks_dashboard_manager = self.env.user.has_group('ks_dashboard_ninja.ks_dashboard_ninja_group_manager')
        dashboard_data = {
            'name': self.browse(ks_dashboard_id).name,
            'ks_dashboard_manager': has_group_ks_dashboard_manager,
            'ks_dashboard_list': self.search_read([], ['id', 'name']),
            'ks_dashboard_start_date': self._context.get('ksDateFilterStartDate', False) or self.browse(
                ks_dashboard_id).ks_dashboard_start_date,
            'ks_dashboard_end_date': self._context.get('ksDateFilterEndDate', False) or self.browse(
                ks_dashboard_id).ks_dashboard_end_date,
            'ks_date_filter_selection': self._context.get('ksDateFilterSelection', False) or self.browse(
                ks_dashboard_id).ks_date_filter_selection,
            'ks_gridstack_config': self.browse(ks_dashboard_id).ks_gridstack_config,
            'ks_set_interval': self.browse(ks_dashboard_id).ks_set_interval,
            'ks_dashboard_items_ids': self.browse(ks_dashboard_id).ks_dashboard_items_ids.ids,
            'ks_item_data': {}
        }

        ks_item_domain = ks_item_domain or []
        try:
            items = self.ks_dashboard_items_ids.search(
                [['ks_dashboard_ninja_board_id', '=', ks_dashboard_id]] + ks_item_domain).ids
        except Exception as e:
            items = self.ks_dashboard_items_ids.search(
                [['ks_dashboard_ninja_board_id', '=', ks_dashboard_id]] + ks_item_domain).ids
        dashboard_data['ks_dashboard_items_ids'] = items

        return dashboard_data

    @api.model
    def ks_fetch_item(self, item_list, ks_dashboard_id):
        """
        :rtype: object
        :param item_list: list of item ids.
        :return: {'id':[item_data]}
        """
        self = self.ks_set_date(ks_dashboard_id)
        items = {}
        item_model = self.env['ks_dashboard_ninja.item']
        for item_id in item_list:
            item = self.ks_fetch_item_data(item_model.browse(item_id))
            items[item['id']] = item
        return items

    # fetching Item info (Divided to make function inherit easily)
    def ks_fetch_item_data(self, rec):
        """
        :rtype: object
        :param item_id: item object
        :return: object with formatted item data
        """
        if rec.ks_actions:
            action = {}
            context = {}
            try:
                context = eval(rec.ks_actions.context)
            except Exception:
                context = {}

            action['name'] = rec.ks_actions.name
            action['type'] = rec.ks_actions.type
            action['res_model'] = rec.ks_actions.res_model
            action['views'] = rec.ks_actions.views
            action['view_mode'] = rec.ks_actions.view_mode
            action['search_view_id'] = rec.ks_actions.search_view_id.id
            action['context'] = context
            action['target'] = 'current'
        else:
            action = False
        item = {
            'name': rec.name if rec.name else rec.ks_model_id.name if rec.ks_model_id else "Name",
            'ks_background_color': rec.ks_background_color,
            'ks_font_color': rec.ks_font_color,
            # 'ks_domain': rec.ks_domain.replace('"%UID"', str(
            #     self.env.user.id)) if rec.ks_domain and "%UID" in rec.ks_domain else rec.ks_domain,
            'ks_domain': rec.ks_convert_into_proper_domain(rec.ks_domain, rec),
            'ks_dashboard_id': rec.ks_dashboard_ninja_board_id.id,
            'ks_icon': rec.ks_icon,
            'ks_model_id': rec.ks_model_id.id,
            'ks_model_name': rec.ks_model_name,
            'ks_model_display_name': rec.ks_model_id.name,
            'ks_record_count_type': rec.ks_record_count_type,
            'ks_record_count': rec.ks_record_count,
            'id': rec.id,
            'ks_layout': rec.ks_layout,
            'ks_icon_select': rec.ks_icon_select,
            'ks_default_icon': rec.ks_default_icon,
            'ks_default_icon_color': rec.ks_default_icon_color,
            # Pro Fields
            'ks_dashboard_item_type': rec.ks_dashboard_item_type,
            'ks_chart_item_color': rec.ks_chart_item_color,
            'ks_chart_groupby_type': rec.ks_chart_groupby_type,
            'ks_chart_relation_groupby': rec.ks_chart_relation_groupby.id,
            'ks_chart_relation_groupby_name': rec.ks_chart_relation_groupby.name,
            'ks_chart_date_groupby': rec.ks_chart_date_groupby,
            'ks_record_field': rec.ks_record_field.id if rec.ks_record_field else False,
            'ks_chart_data': rec.ks_chart_data,
            'ks_list_view_data': rec.ks_list_view_data,
            'ks_chart_data_count_type': rec.ks_chart_data_count_type,
            'ks_bar_chart_stacked': rec.ks_bar_chart_stacked,
            'ks_semi_circle_chart': rec.ks_semi_circle_chart,
            'ks_list_view_type': rec.ks_list_view_type,
            'ks_list_view_group_fields': rec.ks_list_view_group_fields.ids if rec.ks_list_view_group_fields else False,
            'ks_previous_period': rec.ks_previous_period,
            'ks_kpi_data': rec.ks_kpi_data,
            'ks_goal_enable': rec.ks_goal_enable,
            'ks_model_id_2': rec.ks_model_id_2.id,
            'ks_record_field_2': rec.ks_record_field_2.id,
            'ks_data_comparison': rec.ks_data_comparison,
            'ks_target_view': rec.ks_target_view,
            'ks_date_filter_selection': rec.ks_date_filter_selection,
            'ks_show_data_value': rec.ks_show_data_value,
            'ks_update_items_data': rec.ks_update_items_data,
            'ks_show_records': rec.ks_show_records,
            # 'action_id': rec.ks_actions.id if rec.ks_actions else False,
            'sequence': 0,
            'max_sequnce': len(rec.ks_action_lines) if rec.ks_action_lines else False,
            'action': action,
            'ks_chart_sub_groupby_type': rec.ks_chart_sub_groupby_type,
            'ks_chart_relation_sub_groupby': rec.ks_chart_relation_sub_groupby.id,
            'ks_chart_relation_sub_groupby_name': rec.ks_chart_relation_sub_groupby.name,
            'ks_chart_date_sub_groupby': rec.ks_chart_date_sub_groupby,
            'ks_hide_legend': rec.ks_hide_legend,

        }
        return item

    def ks_set_date(self, ks_dashboard_id):
        if self._context.get('ksDateFilterSelection', False):
            ks_date_filter_selection = self._context['ksDateFilterSelection']
            if ks_date_filter_selection == 'l_custom':
                self = self.with_context(
                    ksDateFilterStartDate=fields.datetime.strptime(self._context['ksDateFilterStartDate'],
                                                                   "%Y-%m-%d %H:%M:%S"))
                self = self.with_context(
                    ksDateFilterEndDate=fields.datetime.strptime(self._context['ksDateFilterEndDate'],
                                                                 "%Y-%m-%d %H:%M:%S"))
                self = self.with_context(ksIsDefultCustomDateFilter=False)

        else:
            ks_date_filter_selection = self.browse(ks_dashboard_id).ks_date_filter_selection
            self = self.with_context(ksDateFilterStartDate=self.browse(ks_dashboard_id).ks_dashboard_start_date)
            self = self.with_context(ksDateFilterEndDate=self.browse(ks_dashboard_id).ks_dashboard_end_date)
            self = self.with_context(ksDateFilterSelection=ks_date_filter_selection)
            self = self.with_context(ksIsDefultCustomDateFilter=True)


        if ks_date_filter_selection not in ['l_custom', 'l_none']:
            ks_date_data = ks_get_date(ks_date_filter_selection, self, 'datetime')
            self = self.with_context(ksDateFilterStartDate=ks_date_data["selected_start_date"])
            self = self.with_context(ksDateFilterEndDate=ks_date_data["selected_end_date"])

        return self

    def ks_view_items_view(self):
        self.ensure_one()
        return {
            'name': _("Dashboard Items"),
            'res_model': 'ks_dashboard_ninja.item',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'views': [(False, 'tree'), (False, 'form')],
            'type': 'ir.actions.act_window',
            'domain': [('ks_dashboard_ninja_board_id', '!=', False)],
            'search_view_id': self.env.ref('ks_dashboard_ninja.ks_item_search_view').id,
            'context': {
                'search_default_ks_dashboard_ninja_board_id': self.id,
                'group_by': 'ks_dashboard_ninja_board_id',
            },
            'help': _('''<p class="o_view_nocontent_smiling_face">
                                        You can find all items related to Dashboard Here.</p>
                                    '''),

        }

    def ks_export_item(self,item_id):
        return {
            'ks_file_format': 'ks_dashboard_ninja_item_export',
            'item': self.ks_export_item_data(self.ks_dashboard_items_ids.browse(int(item_id)))
        }
    # fetching Item info (Divided to make function inherit easily)
    def ks_export_item_data(self, rec):
        ks_chart_measure_field = []
        ks_chart_measure_field_2 = []
        for res in rec.ks_chart_measure_field:
            ks_chart_measure_field.append(res.name)
        for res in rec.ks_chart_measure_field_2:
            ks_chart_measure_field_2.append(res.name)

        ks_list_view_group_fields = []
        for res in rec.ks_list_view_group_fields:
            ks_list_view_group_fields.append(res.name)

        ks_goal_lines = []
        for res in rec.ks_goal_lines:
            goal_line = {
                'ks_goal_date': datetime.datetime.strftime(res.ks_goal_date, "%Y-%m-%d"),
                'ks_goal_value': res.ks_goal_value,
            }
            ks_goal_lines.append(goal_line)

        ks_action_lines = []
        for res in rec.ks_action_lines:
            action_line = {
                'ks_item_action_field': res.ks_item_action_field.name,
                'ks_item_action_date_groupby': res.ks_item_action_date_groupby,
                'ks_chart_type': res.ks_chart_type,
                'ks_sort_by_field': res.ks_sort_by_field.name,
                'ks_sort_by_order': res.ks_sort_by_order,
                'ks_record_limit': res.ks_record_limit,
                'sequence': res.sequence,
            }
            ks_action_lines.append(action_line)

        ks_list_view_field = []
        for res in rec.ks_list_view_fields:
            ks_list_view_field.append(res.name)
        item = {
            'name': rec.name if rec.name else rec.ks_model_id.name if rec.ks_model_id else "Name",
            'ks_background_color': rec.ks_background_color,
            'ks_font_color': rec.ks_font_color,
            'ks_domain': rec.ks_domain,
            'ks_icon': str(rec.ks_icon) if rec.ks_icon else False,
            'ks_id': rec.id,
            'ks_model_id': rec.ks_model_name,
            'ks_record_count': rec.ks_record_count,
            'ks_layout': rec.ks_layout,
            'ks_icon_select': rec.ks_icon_select,
            'ks_default_icon': rec.ks_default_icon,
            'ks_default_icon_color': rec.ks_default_icon_color,
            'ks_record_count_type': rec.ks_record_count_type,
            # Pro Fields
            'ks_dashboard_item_type': rec.ks_dashboard_item_type,
            'ks_chart_item_color': rec.ks_chart_item_color,
            'ks_chart_groupby_type': rec.ks_chart_groupby_type,
            'ks_chart_relation_groupby': rec.ks_chart_relation_groupby.name,
            'ks_chart_date_groupby': rec.ks_chart_date_groupby,
            'ks_record_field': rec.ks_record_field.name,
            'ks_chart_sub_groupby_type': rec.ks_chart_sub_groupby_type,
            'ks_chart_relation_sub_groupby': rec.ks_chart_relation_sub_groupby.name,
            'ks_chart_date_sub_groupby': rec.ks_chart_date_sub_groupby,
            'ks_chart_data_count_type': rec.ks_chart_data_count_type,
            'ks_chart_measure_field': ks_chart_measure_field,
            'ks_chart_measure_field_2': ks_chart_measure_field_2,
            'ks_list_view_fields': ks_list_view_field,
            'ks_list_view_group_fields': ks_list_view_group_fields,
            'ks_list_view_type': rec.ks_list_view_type,
            'ks_record_data_limit': rec.ks_record_data_limit,
            'ks_sort_by_order': rec.ks_sort_by_order,
            'ks_sort_by_field': rec.ks_sort_by_field.name,
            'ks_date_filter_field': rec.ks_date_filter_field.name,
            'ks_goal_enable': rec.ks_goal_enable,
            'ks_standard_goal_value': rec.ks_standard_goal_value,
            'ks_goal_liness': ks_goal_lines,
            'ks_date_filter_selection': rec.ks_date_filter_selection,
            'ks_item_start_date': rec.ks_item_start_date.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.ks_item_start_date else False,
            'ks_item_end_date': rec.ks_item_end_date.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.ks_item_end_date else False,
            'ks_date_filter_selection_2': rec.ks_date_filter_selection_2,
            'ks_item_start_date_2': rec.ks_item_start_date_2.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.ks_item_start_date_2 else False,
            'ks_item_end_date_2': rec.ks_item_end_date_2.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if rec.ks_item_end_date_2 else False,
            'ks_previous_period': rec.ks_previous_period,
            'ks_target_view': rec.ks_target_view,
            'ks_data_comparison': rec.ks_data_comparison,
            'ks_record_count_type_2': rec.ks_record_count_type_2,
            'ks_record_field_2': rec.ks_record_field_2.name,
            'ks_model_id_2': rec.ks_model_id_2.model,
            'ks_date_filter_field_2': rec.ks_date_filter_field_2.name,
            'ks_action_liness': ks_action_lines,
            'ks_compare_period': rec.ks_compare_period,
            'ks_year_period': rec.ks_year_period,
            'ks_compare_period_2': rec.ks_compare_period_2,
            'ks_semi_circle_chart': rec.ks_semi_circle_chart,
            'ks_year_period_2': rec.ks_year_period_2,
            'ks_domain_2': rec.ks_domain_2,
            'ks_show_data_value': rec.ks_show_data_value,
            'ks_update_items_data': rec.ks_update_items_data,
            'ks_list_target_deviation_field': rec.ks_list_target_deviation_field.name,
            'ks_unit': rec.ks_unit,
            'ks_show_records': rec.ks_show_records,
            'ks_hide_legend': rec.ks_hide_legend,
            'ks_fill_temporal': rec.ks_fill_temporal,
            'ks_domain_extension': rec.ks_domain_extension,
            'ks_domain_extension_2': rec.ks_domain_extension_2,
            'ks_unit_selection': rec.ks_unit_selection,
            'ks_chart_unit': rec.ks_chart_unit,
            'ks_bar_chart_stacked': rec.ks_bar_chart_stacked,
            'ks_goal_bar_line': rec.ks_goal_bar_line,
        }
        return item


    def ks_import_item(self, dashboard_id, **kwargs):
        try:
            # ks_dashboard_data = json.loads(file)
            file = kwargs.get('file', False)
            ks_dashboard_file_read = json.loads(file)
        except:
            raise ValidationError(_("This file is not supported"))

        if 'ks_file_format' in ks_dashboard_file_read and ks_dashboard_file_read[
            'ks_file_format'] == 'ks_dashboard_ninja_item_export':
            item = ks_dashboard_file_read['item']
        else:
            raise ValidationError(_("Current Json File is not properly formatted according to Dashboard Ninja Model."))

        item['ks_dashboard_ninja_board_id'] = int(dashboard_id)
        self.ks_create_item(item)

        return "Success"

    @api.model
    def ks_dashboard_export(self, ks_dashboard_ids):
        ks_dashboard_data = []
        ks_dashboard_export_data = {}
        ks_dashboard_ids = json.loads(ks_dashboard_ids)
        for ks_dashboard_id in ks_dashboard_ids:
            dashboard_data = {
                'name': self.browse(ks_dashboard_id).name,
                'ks_dashboard_menu_name': self.browse(ks_dashboard_id).ks_dashboard_menu_name,
                'ks_gridstack_config': self.browse(ks_dashboard_id).ks_gridstack_config,
                'ks_set_interval': self.browse(ks_dashboard_id).ks_set_interval,
                'ks_date_filter_selection': self.browse(ks_dashboard_id).ks_date_filter_selection,
                'ks_dashboard_start_date': self.browse(ks_dashboard_id).ks_dashboard_start_date,
                'ks_dashboard_end_date': self.browse(ks_dashboard_id).ks_dashboard_end_date,
                'ks_dashboard_top_menu_id': self.browse(ks_dashboard_id).ks_dashboard_top_menu_id.id,
            }
            if len(self.browse(ks_dashboard_id).ks_dashboard_items_ids) < 1:
                dashboard_data['ks_item_data'] = False
            else:
                items = []
                for rec in self.browse(ks_dashboard_id).ks_dashboard_items_ids:
                    item = self.ks_export_item_data(rec)
                    items.append(item)

                dashboard_data['ks_item_data'] = items

            ks_dashboard_data.append(dashboard_data)

            ks_dashboard_export_data = {
                'ks_file_format': 'ks_dashboard_ninja_export_file',
                'ks_dashboard_data': ks_dashboard_data
            }
        return ks_dashboard_export_data

    @api.model
    def ks_import_dashboard(self, file):
        try:
            # ks_dashboard_data = json.loads(file)
            ks_dashboard_file_read = json.loads(file)
        except:
            raise ValidationError(_("This file is not supported"))

        if 'ks_file_format' in ks_dashboard_file_read and ks_dashboard_file_read[
            'ks_file_format'] == 'ks_dashboard_ninja_export_file':
            ks_dashboard_data = ks_dashboard_file_read['ks_dashboard_data']
        else:
            raise ValidationError(_("Current Json File is not properly formatted according to Dashboard Ninja Model."))

        ks_dashboard_key = ['name', 'ks_dashboard_menu_name', 'ks_gridstack_config']
        ks_dashboard_item_key = ['ks_model_id', 'ks_chart_measure_field', 'ks_list_view_fields', 'ks_record_field',
                                 'ks_chart_relation_groupby', 'ks_id']

        # Fetching dashboard model info
        for data in ks_dashboard_data:
            if not all(key in data for key in ks_dashboard_key):
                raise ValidationError(
                    _("Current Json File is not properly formatted according to Dashboard Ninja Model."))
            ks_dashboard_top_menu_id = data.get('ks_dashboard_top_menu_id', False)
            if ks_dashboard_top_menu_id:
                try:
                    self.env['ir.ui.menu'].browse(ks_dashboard_top_menu_id).name
                    ks_dashboard_top_menu_id = self.env['ir.ui.menu'].browse(ks_dashboard_top_menu_id)
                except Exception:
                    ks_dashboard_top_menu_id = False
            vals = {
                'name': data.get('name'),
                'ks_dashboard_menu_name': data.get('ks_dashboard_menu_name'),
                'ks_dashboard_top_menu_id': ks_dashboard_top_menu_id.id if ks_dashboard_top_menu_id else self.env.ref("ks_dashboard_ninja.board_menu_root").id,
                'ks_dashboard_active': True,
                'ks_gridstack_config': data.get('ks_gridstack_config'),
                'ks_dashboard_default_template': self.env.ref("ks_dashboard_ninja.ks_blank").id,
                'ks_dashboard_group_access': False,
                'ks_set_interval': data.get('ks_set_interval'),
                'ks_date_filter_selection': data.get('ks_date_filter_selection'),
                'ks_dashboard_start_date': data.get('ks_dashboard_start_date'),
                'ks_dashboard_end_date': data.get('ks_dashboard_end_date'),
            }
            # Creating Dashboard
            dashboard_id = self.create(vals)

            if data['ks_gridstack_config']:
                ks_gridstack_config = eval(data['ks_gridstack_config'])
            ks_grid_stack_config = {}

            item_ids = []
            item_new_ids = []
            if data['ks_item_data']:
                # Fetching dashboard item info
                for item in data['ks_item_data']:
                    if not all(key in item for key in ks_dashboard_item_key):
                        raise ValidationError(
                            _("Current Json File is not properly formatted according to Dashboard Ninja Model."))

                    # Creating dashboard items
                    item['ks_dashboard_ninja_board_id'] = dashboard_id.id
                    item_ids.append(item['ks_id'])
                    del item['ks_id']
                    ks_item = self.ks_create_item(item)
                    item_new_ids.append(ks_item.id)

            for id_index, id in enumerate(item_ids):
                if data['ks_gridstack_config'] and str(id) in ks_gridstack_config:
                    ks_grid_stack_config[str(item_new_ids[id_index])] = ks_gridstack_config[str(id)]

            self.browse(dashboard_id.id).write({
                'ks_gridstack_config': json.dumps(ks_grid_stack_config)
            })

        return "Success"
        # separate function to make item for import

    def ks_create_item(self,item):
        model = self.env['ir.model'].search([('model', '=', item['ks_model_id'])])

        if item.get('ks_data_calculation_type')  is not None and item['ks_model_id'] == False:
            raise ValidationError(_(
                "That Item contain properties of the Dashboard Ninja Adavance, Please Install the Module "
                "Dashboard Ninja Advance."))

        if not model:
            raise ValidationError(_(
                "Please Install the Module which contains the following Model : %s " % item['ks_model_id']))

        ks_model_name = item['ks_model_id']

        ks_goal_lines = item['ks_goal_liness'].copy() if item.get('ks_goal_liness', False) else False
        ks_action_lines = item['ks_action_liness'].copy() if item.get('ks_action_liness', False) else False

        # Creating dashboard items
        item = self.ks_prepare_item(item)

        if 'ks_goal_liness' in item:
            del item['ks_goal_liness']
        if 'ks_id' in item:
            del item['ks_id']
        if 'ks_action_liness' in item:
            del item['ks_action_liness']
        if 'ks_icon' in item:
            item['ks_icon_select'] = "Default"
            item['ks_icon'] = False

        ks_item = self.env['ks_dashboard_ninja.item'].create(item)

        if ks_goal_lines and len(ks_goal_lines) != 0:
            for line in ks_goal_lines:
                line['ks_goal_date'] = datetime.datetime.strptime(line['ks_goal_date'].split(" ")[0],
                                                                  '%Y-%m-%d')
                line['ks_dashboard_item'] = ks_item.id
                self.env['ks_dashboard_ninja.item_goal'].create(line)

        if ks_action_lines and len(ks_action_lines) != 0:

            for line in ks_action_lines:
                if line['ks_sort_by_field']:
                    ks_sort_by_field = line['ks_sort_by_field']
                    ks_sort_record_id = self.env['ir.model.fields'].search(
                        [('model', '=', ks_model_name), ('name', '=', ks_sort_by_field)])
                    if ks_sort_record_id:
                        line['ks_sort_by_field'] = ks_sort_record_id.id
                    else:
                        line['ks_sort_by_field'] = False
                if line['ks_item_action_field']:
                    ks_item_action_field = line['ks_item_action_field']
                    ks_record_id = self.env['ir.model.fields'].search(
                        [('model', '=', ks_model_name), ('name', '=', ks_item_action_field)])
                    if ks_record_id:
                        line['ks_item_action_field'] = ks_record_id.id
                        line['ks_dashboard_item_id'] = ks_item.id
                        self.env['ks_dashboard_ninja.item_action'].create(line)

        return ks_item

    def ks_prepare_item(self, item):
        ks_measure_field_ids = []
        ks_measure_field_2_ids = []

        for ks_measure in item['ks_chart_measure_field']:
            ks_measure_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_measure), ('model', '=', item['ks_model_id'])])
            if ks_measure_id:
                ks_measure_field_ids.append(ks_measure_id.id)
        item['ks_chart_measure_field'] = [(6, 0, ks_measure_field_ids)]

        for ks_measure in item['ks_chart_measure_field_2']:
            ks_measure_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_measure), ('model', '=', item['ks_model_id'])])
            if ks_measure_id:
                ks_measure_field_2_ids.append(ks_measure_id.id)
        item['ks_chart_measure_field_2'] = [(6, 0, ks_measure_field_2_ids)]

        ks_list_view_group_fields = []
        for ks_measure in item['ks_list_view_group_fields']:
            ks_measure_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_measure), ('model', '=', item['ks_model_id'])])

            if ks_measure_id:
                ks_list_view_group_fields.append(ks_measure_id.id)
        item['ks_list_view_group_fields'] = [(6, 0, ks_list_view_group_fields)]

        ks_list_view_field_ids = []
        for ks_list_field in item['ks_list_view_fields']:
            ks_list_field_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_list_field), ('model', '=', item['ks_model_id'])])
            if ks_list_field_id:
                ks_list_view_field_ids.append(ks_list_field_id.id)
        item['ks_list_view_fields'] = [(6, 0, ks_list_view_field_ids)]

        if item['ks_record_field']:
            ks_record_field = item['ks_record_field']
            ks_record_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_record_field), ('model', '=', item['ks_model_id'])])
            if ks_record_id:
                item['ks_record_field'] = ks_record_id.id
            else:
                item['ks_record_field'] = False

        if item['ks_date_filter_field']:
            ks_date_filter_field = item['ks_date_filter_field']
            ks_record_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_date_filter_field), ('model', '=', item['ks_model_id'])])
            if ks_record_id:
                item['ks_date_filter_field'] = ks_record_id.id
            else:
                item['ks_date_filter_field'] = False

        if item['ks_chart_relation_groupby']:
            ks_group_by = item['ks_chart_relation_groupby']
            ks_record_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_group_by), ('model', '=', item['ks_model_id'])])
            if ks_record_id:
                item['ks_chart_relation_groupby'] = ks_record_id.id
            else:
                item['ks_chart_relation_groupby'] = False

        if item['ks_chart_relation_sub_groupby']:
            ks_group_by = item['ks_chart_relation_sub_groupby']
            ks_chart_relation_sub_groupby = self.env['ir.model.fields'].search(
                [('name', '=', ks_group_by), ('model', '=', item['ks_model_id'])])
            if ks_chart_relation_sub_groupby:
                item['ks_chart_relation_sub_groupby'] = ks_chart_relation_sub_groupby.id
            else:
                item['ks_chart_relation_sub_groupby'] = False

        # Sort by field : Many2one Entery
        if item['ks_sort_by_field']:
            ks_group_by = item['ks_sort_by_field']
            ks_sort_by_field = self.env['ir.model.fields'].search(
                [('name', '=', ks_group_by), ('model', '=', item['ks_model_id'])])
            if ks_sort_by_field:
                item['ks_sort_by_field'] = ks_sort_by_field.id
            else:
                item['ks_sort_by_field'] = False

        if item['ks_list_target_deviation_field']:
            ks_list_target_deviation_field = item['ks_list_target_deviation_field']
            record_id = self.env['ir.model.fields'].search(
                [('name', '=', ks_list_target_deviation_field), ('model', '=', item['ks_model_id'])])
            if record_id:
                item['ks_list_target_deviation_field'] = record_id.id
            else:
                item['ks_list_target_deviation_field'] = False

        ks_model_id = self.env['ir.model'].search([('model', '=', item['ks_model_id'])]).id

        if (item['ks_model_id_2']):
            ks_model_2 = item['ks_model_id_2'].replace(".", "_")
            ks_model_id_2 = self.env['ir.model'].search([('model', '=', item['ks_model_id_2'])]).id
            if item['ks_record_field_2']:
                ks_record_field = item['ks_record_field_2']
                ks_record_id = self.env['ir.model.fields'].search(
                    [('model', '=', item['ks_model_id_2']), ('name', '=', ks_record_field)])

                if ks_record_id:
                    item['ks_record_field_2'] = ks_record_id.id
                else:
                    item['ks_record_field_2'] = False
            if item['ks_date_filter_field_2']:
                ks_record_id = self.env['ir.model.fields'].search(
                    [('model', '=', item['ks_model_id_2']), ('name', '=', item['ks_date_filter_field_2'])])

                if ks_record_id:
                    item['ks_date_filter_field_2'] = ks_record_id.id
                else:
                    item['ks_date_filter_field_2'] = False

            item['ks_model_id_2'] = ks_model_id_2
        else:
            item['ks_date_filter_field_2'] = False
            item['ks_record_field_2'] = False

        item['ks_model_id'] = ks_model_id

        item['ks_goal_liness'] = False
        item['ks_item_start_date'] = datetime.datetime.strptime(item['ks_item_start_date'].split(" ")[0], '%Y-%m-%d') if \
            item['ks_item_start_date'] else False
        item['ks_item_end_date'] = datetime.datetime.strptime(item['ks_item_end_date'].split(" ")[0], '%Y-%m-%d') if \
            item['ks_item_end_date'] else False
        item['ks_item_start_date_2'] = datetime.datetime.strptime(item['ks_item_start_date_2'].split(" ")[0],
                                                                  '%Y-%m-%d') if \
            item['ks_item_start_date_2'] else False
        item['ks_item_end_date_2'] = datetime.datetime.strptime(item['ks_item_end_date_2'].split(" ")[0], '%Y-%m-%d') if \
            item['ks_item_end_date_2'] else False

        return item



    # List view pagination
    @api.model
    def ks_get_list_view_data_offset(self, ks_dashboard_item_id, offset, dashboard_id):
        self = self.ks_set_date(dashboard_id)
        item = self.ks_dashboard_items_ids.browse(ks_dashboard_item_id)

        return item.ks_get_next_offset(ks_dashboard_item_id, offset)

class KsDashboardNinjaTemplate(models.Model):
    _name = 'ks_dashboard_ninja.board_template'
    _description = 'Dashboard Ninja Template'
    name = fields.Char()
    ks_gridstack_config = fields.Char()
    ks_item_count = fields.Integer()
