# -*- coding: utf-8 -*-
import dateutil
import datetime as dt
import pytz
import json
import babel

from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval
from collections import defaultdict
from datetime import datetime
from dateutil import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.ks_dashboard_ninja.lib.ks_date_filter_selections import ks_get_date, ks_convert_into_utc, ks_convert_into_local

# TODO : Check all imports if needed


read = fields.Many2one.read


def ks_read(self, records):
    if self.name == 'ks_list_view_fields' or self.name == 'ks_list_view_group_fields':
        comodel = records.env[self.comodel_name]

        # String domains are supposed to be dynamic and evaluated on client-side
        # only (thus ignored here).
        domain = self.domain if isinstance(self.domain, list) else []

        wquery = comodel._where_calc(domain)
        comodel._apply_ir_rules(wquery, 'read')
        from_c, where_c, where_params = wquery.get_sql()
        query = """ SELECT {rel}.{id1}, {rel}.{id2} FROM {rel}, {from_c}
                    WHERE {where_c} AND {rel}.{id1} IN %s AND {rel}.{id2} = {tbl}.id
                """.format(rel=self.relation, id1=self.column1, id2=self.column2,
                           tbl=comodel._table, from_c=from_c, where_c=where_c or '1=1',
                           limit=(' LIMIT %d' % self.limit) if self.limit else '',
                           )
        where_params.append(tuple(records.ids))

        # retrieve lines and group them by record
        group = defaultdict(list)
        records._cr.execute(query, where_params)
        rec_list = records._cr.fetchall()
        for row in rec_list:
            group[row[0]].append(row[1])

        # store result in cache
        cache = records.env.cache
        for record in records:
            if self.name == 'ks_list_view_fields':
                field = 'ks_list_view_fields'
            else:
                field = 'ks_list_view_group_fields'
            order = False
            if record.ks_many2many_field_ordering:
                order = json.loads(record.ks_many2many_field_ordering).get(field, False)

            if order:
                group[record.id].sort(key=lambda x: order.index(x))
            cache.set(record, self, tuple(group[record.id]))

    else:
        comodel = records.env[self.comodel_name]

        # String domains are supposed to be dynamic and evaluated on client-side
        # only (thus ignored here).
        domain = self.domain if isinstance(self.domain, list) else []

        wquery = comodel._where_calc(domain)
        comodel._apply_ir_rules(wquery, 'read')
        order_by = comodel._generate_order_by(None, wquery)
        from_c, where_c, where_params = wquery.get_sql()
        query = """ SELECT {rel}.{id1}, {rel}.{id2} FROM {rel}, {from_c}
                           WHERE {where_c} AND {rel}.{id1} IN %s AND {rel}.{id2} = {tbl}.id
                           {order_by} {limit} OFFSET {offset}
                       """.format(rel=self.relation, id1=self.column1, id2=self.column2,
                                  tbl=comodel._table, from_c=from_c, where_c=where_c or '1=1',
                                  limit=(' LIMIT %d' % self.limit) if self.limit else '',
                                  offset=0, order_by=order_by)
        where_params.append(tuple(records.ids))

        # retrieve lines and group them by record
        group = defaultdict(list)
        records._cr.execute(query, where_params)
        for row in records._cr.fetchall():
            group[row[0]].append(row[1])

        # store result in cache
        cache = records.env.cache
        for record in records:
            cache.set(record, self, tuple(group[record.id]))


fields.Many2many.read = ks_read

read_group = models.BaseModel._read_group_process_groupby


def ks_time_addition(self, gb, query):
    """
        Overwriting default to add minutes to Helper method to collect important
        information about groupbys: raw field name, type, time information, qualified name, ...
    """
    split = gb.split(':')
    field_type = self._fields[split[0]].type
    gb_function = split[1] if len(split) == 2 else None
    if gb_function == 'month_year':
        gb_function = 'month'
    temporal = field_type in ('date', 'datetime')
    tz_convert = field_type == 'datetime' and self._context.get('tz') in pytz.all_timezones
    qualified_field = self._inherits_join_calc(self._table, split[0], query)
    if temporal:
        display_formats = {
            'minute': 'hh:mm dd MMM',
            'hour': 'hh:00 dd MMM',
            'day': 'dd MMM yyyy',  # yyyy = normal year
            'week': "'W'w YYYY",  # w YYYY = ISO week-year
            'month': 'MMMM yyyy',
            'quarter': 'QQQ yyyy',
            'year': 'yyyy',
        }
        time_intervals = {
            'minute': dateutil.relativedelta.relativedelta(minutes=1),
            'hour': dateutil.relativedelta.relativedelta(hours=1),
            'day': dateutil.relativedelta.relativedelta(days=1),
            'week': dt.timedelta(days=7),
            'month': dateutil.relativedelta.relativedelta(months=1),
            'quarter': dateutil.relativedelta.relativedelta(months=3),
            'year': dateutil.relativedelta.relativedelta(years=1)
        }
        if tz_convert:
            qualified_field = "timezone('%s', timezone('UTC',%s))" % (self._context.get('tz', 'UTC'), qualified_field)
        qualified_field = "date_trunc('%s', %s::timestamp)" % (gb_function or 'month', qualified_field)
    if field_type == 'boolean':
        qualified_field = "coalesce(%s,false)" % qualified_field
    return {
        'field': split[0],
        'groupby': gb,
        'type': field_type,
        'display_format': display_formats[gb_function or 'month'] if temporal else None,
        'interval': time_intervals[gb_function or 'month'] if temporal else None,
        'tz_convert': tz_convert,
        'qualified_field': qualified_field,
    }


models.BaseModel._read_group_process_groupby = ks_time_addition


class KsDashboardNinjaItems(models.Model):
    _name = 'ks_dashboard_ninja.item'
    _description = 'Dashboard Ninja items'

    name = fields.Char(string="Name", size=256)
    ks_model_id = fields.Many2one('ir.model', string='Model',
                                  domain="[('access_ids','!=',False),('transient','=',False),"
                                         "('model','not ilike','base_import%'),'|',('model','not ilike','ir.%'),('model','=ilike','_%ir.%'),"
                                         "('model','not ilike','web_editor.%'),('model','not ilike','web_tour.%'),"
                                         "('model','!=','mail.thread'),('model','not ilike','ks_dash%')]")
    ks_domain = fields.Char(string="Domain")

    ks_model_id_2 = fields.Many2one('ir.model', string='Kpi Model',
                                    domain="[('access_ids','!=',False),('transient','=',False),"
                                           "('model','not ilike','base_import%'),'|',('model','not ilike','ir.%'),('model','=ilike','_%ir.%'),"
                                           "('model','not ilike','web_editor.%'),('model','not ilike','web_tour.%'),"
                                           "('model','!=','mail.thread'),('model','not ilike','ks_dash%')]")

    ks_model_name_2 = fields.Char(related='ks_model_id_2.model', string="Kpi Model Name")

    # This field main purpose is to store %UID as current user id. Mainly used in JS file as container.
    ks_domain_temp = fields.Char(string="Domain Substitute")
    ks_background_color = fields.Char(string="Background Color",
                                      default="#ffffff,0.99")
    ks_icon = fields.Binary(string="Upload Icon", attachment=True)
    ks_default_icon = fields.Char(string="Icon", default="bar-chart")
    ks_default_icon_color = fields.Char(default="#ffffff,0.99", string="Icon Color")
    ks_icon_select = fields.Char(string="Icon Option", default="Default")
    ks_font_color = fields.Char(default="#ffffff,0.99", string="Font Color")
    ks_dashboard_item_theme = fields.Char(string="Theme", default="white")
    ks_layout = fields.Selection([('layout1', 'Layout 1'),
                                  ('layout2', 'Layout 2'),
                                  ('layout3', 'Layout 3'),
                                  ('layout4', 'Layout 4'),
                                  ('layout5', 'Layout 5'),
                                  ('layout6', 'Layout 6'),
                                  ], default=('layout1'), required=True, string="Layout")
    ks_preview = fields.Integer(default=1, string="Preview")
    ks_model_name = fields.Char(related='ks_model_id.model', string="Model Name")

    ks_record_count_type_2 = fields.Selection([('count', 'Count'),
                                               ('sum', 'Sum'),
                                               ('average', 'Average')], string="Kpi Record Type", default="sum")
    ks_record_field_2 = fields.Many2one('ir.model.fields',
                                        domain="[('model_id','=',ks_model_id_2),('name','!=','id'),('name','!=','sequence'),('store','=',True),"
                                               "'|','|',('ttype','=','integer'),('ttype','=','float'),"
                                               "('ttype','=','monetary')]",
                                        string="Kpi Record Field")
    ks_record_count_2 = fields.Float(string="KPI Record Count", readonly=True, compute='ks_get_record_count_2')
    ks_record_count_type = fields.Selection([('count', 'Count'),
                                             ('sum', 'Sum'),
                                             ('average', 'Average')], string="Record Type", default="count")
    ks_record_count = fields.Float(string="Record Count", compute='ks_get_record_count', readonly=True)
    ks_record_field = fields.Many2one('ir.model.fields',
                                      domain="[('model_id','=',ks_model_id),('name','!=','id'),('store','=',True),'|',"
                                             "'|',('ttype','=','integer'),('ttype','=','float'),"
                                             "('ttype','=','monetary')]",
                                      string="Record Field")

    # Date Filter Fields
    # Condition to tell if date filter is applied or not
    ks_isDateFilterApplied = fields.Boolean(default=False)

    # ---------------------------- Date Filter Fields ------------------------------------------
    ks_date_filter_field = fields.Many2one('ir.model.fields',
                                           domain="[('model_id','=',ks_model_id),('store','=',True),'|',('ttype','=','date'),"
                                                  "('ttype','=','datetime')]",
                                           string="Date Filter Field")
    ks_date_filter_selection = fields.Selection([
        ('l_none', 'None'),
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
    ], string="Date Filter Selection", default="l_none", required=True)

    ks_item_start_date = fields.Datetime(string="Start Date")
    ks_item_end_date = fields.Datetime(string="End Date")

    ks_date_filter_field_2 = fields.Many2one('ir.model.fields',
                                             domain="[('model_id','=',ks_model_id_2),('store','=',True),'|',('ttype','=','date'),"
                                                    "('ttype','=','datetime')]",
                                             string="Kpi Date Filter Field")

    ks_item_start_date_2 = fields.Datetime(string="Kpi Start Date")
    ks_item_end_date_2 = fields.Datetime(string="Kpi End Date")

    ks_domain_2 = fields.Char(string="Kpi Domain")
    ks_domain_2_temp = fields.Char(string="Kpi Domain Substitute")

    ks_date_filter_selection_2 = fields.Selection([
        ('l_none', "None"),
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
    ], string="Kpi Date Filter Selection", required=True, default='l_none')

    ks_previous_period = fields.Boolean(string="Previous Period")

    # ------------------------ Pro Fields --------------------
    ks_dashboard_ninja_board_id = fields.Many2one('ks_dashboard_ninja.board', string="Dashboard",
                                                  default=lambda self: self._context[
                                                    'ks_dashboard_id'] if 'ks_dashboard_id' in self._context else False)

    # Chart related fields
    ks_dashboard_item_type = fields.Selection([('ks_tile', 'Tile'),
                                               ('ks_bar_chart', 'Bar Chart'),
                                               ('ks_horizontalBar_chart', 'Horizontal Bar Chart'),
                                               ('ks_line_chart', 'Line Chart'),
                                               ('ks_area_chart', 'Area Chart'),
                                               ('ks_pie_chart', 'Pie Chart'),
                                               ('ks_doughnut_chart', 'Doughnut Chart'),
                                               ('ks_polarArea_chart', 'Polar Area Chart'),
                                               ('ks_list_view', 'List View'),
                                               ('ks_kpi', 'KPI')
                                               ], default=lambda self: self._context.get('ks_dashboard_item_type',
                                                                                         'ks_tile'), required=True,
                                              string="Dashboard Item Type")
    ks_chart_groupby_type = fields.Char(compute='get_chart_groupby_type')
    ks_chart_sub_groupby_type = fields.Char(compute='get_chart_sub_groupby_type')
    ks_chart_relation_groupby = fields.Many2one('ir.model.fields',
                                                domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),"
                                                       "('store','=',True),('ttype','!=','binary'),"
                                                       "('ttype','!=','many2many'), ('ttype','!=','one2many')]",
                                                string="Group By")
    ks_chart_relation_sub_groupby = fields.Many2one('ir.model.fields',
                                                    domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),"
                                                           "('store','=',True),('ttype','!=','binary'),"
                                                           "('ttype','!=','many2many'), ('ttype','!=','one2many')]",
                                                    string=" Sub Group By")
    ks_chart_date_groupby = fields.Selection([('minute', 'Minute'),
                                              ('hour', 'Hour'),
                                              ('day', 'Day'),
                                              ('week', 'Week'),
                                              ('month', 'Month'),
                                              ('quarter', 'Quarter'),
                                              ('year', 'Year'),
                                              ('month_year', 'Month-Year'),
                                              ], string="Dashboard Item Chart Group By Type")
    ks_chart_date_sub_groupby = fields.Selection([('minute', 'Minute'),
                                                  ('hour', 'Hour'),
                                                  ('day', 'Day'),
                                                  ('week', 'Week'),
                                                  ('month', 'Month'),
                                                  ('quarter', 'Quarter'),
                                                  ('year', 'Year'),
                                                  ], string="Dashboard Item Chart Sub Group By Type")
    ks_graph_preview = fields.Char(string="Graph Preview", default="Graph Preview")
    ks_chart_data = fields.Char(string="Chart Data in string form", compute='ks_get_chart_data')
    ks_chart_data_count_type = fields.Selection([('count', 'Count'), ('sum', 'Sum'), ('average', 'Average')],
                                                string="Data Type", default="sum")
    ks_chart_measure_field = fields.Many2many('ir.model.fields', 'ks_dn_measure_field_rel', 'measure_field_id',
                                              'field_id',
                                              domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),"
                                                     "('store','=',True),'|','|',"
                                                     "('ttype','=','integer'),('ttype','=','float'),"
                                                     "('ttype','=','monetary')]",
                                              string="Measure 1")

    ks_chart_measure_field_2 = fields.Many2many('ir.model.fields', 'ks_dn_measure_field_rel_2', 'measure_field_id_2',
                                                'field_id',
                                                domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),"
                                                       "('store','=',True),'|','|',"
                                                       "('ttype','=','integer'),('ttype','=','float'),"
                                                       "('ttype','=','monetary')]",
                                                string="Line Measure")

    ks_bar_chart_stacked = fields.Boolean(string="Stacked Bar Chart")

    ks_semi_circle_chart = fields.Boolean(string="Semi Circle Chart")

    ks_sort_by_field = fields.Many2one('ir.model.fields',
                                       domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),('store','=',True),"
                                              "('ttype','!=','one2many'),('ttype','!=','binary')]",
                                       string="Sort By Field")
    ks_sort_by_order = fields.Selection([('ASC', 'Ascending'), ('DESC', 'Descending')],
                                        string="Sort Order")
    ks_record_data_limit = fields.Integer(string="Record Limit")

    ks_list_view_preview = fields.Char(string="List View Preview", default="List View Preview")

    ks_kpi_preview = fields.Char(string="Kpi Preview", default="KPI Preview")

    ks_kpi_type = fields.Selection([
        ('layout_1', 'KPI With Target'),
        ('layout_2', 'Data Comparison'),
    ], string="Kpi Layout", default="layout_1")

    ks_target_view = fields.Char(string="View", default="Number")

    ks_data_comparison = fields.Char(string="Kpi Data Type", default="None")

    ks_kpi_data = fields.Char(string="KPI Data", compute="ks_get_kpi_data")

    ks_chart_item_color = fields.Selection(
        [('default', 'Default'), ('cool', 'Cool'), ('warm', 'Warm'), ('neon', 'Neon')],
        string="Chart Color Palette", default="default")

    # ------------------------ List View Fields ------------------------------

    ks_list_view_type = fields.Selection([('ungrouped', 'Un-Grouped'), ('grouped', 'Grouped')], default="ungrouped",
                                         string="List View Type", required=True)
    ks_list_view_fields = fields.Many2many('ir.model.fields', 'ks_dn_list_field_rel', 'list_field_id', 'field_id',
                                           domain="[('model_id','=',ks_model_id),('ttype','!=','one2many'),"
                                                  "('ttype','!=','many2many'),('ttype','!=','binary')]",
                                           string="Fields to show in list")

    ks_list_view_group_fields = fields.Many2many('ir.model.fields', 'ks_dn_list_group_field_rel', 'list_field_id',
                                                 'field_id',
                                                 domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),"
                                                        "('store','=',True),'|','|',"
                                                        "('ttype','=','integer'),('ttype','=','float'),"
                                                        "('ttype','=','monetary')]",
                                                 string="List View Grouped Fields")

    ks_list_view_data = fields.Char(string="List View Data in JSon", compute='ks_get_list_view_data')

    # -------------------- Multi Company Feature ---------------------
    ks_company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    # -------------------- Target Company Feature ---------------------
    ks_goal_enable = fields.Boolean(string="Enable Target")
    ks_goal_bar_line = fields.Boolean(string="Show Target As Line")
    ks_standard_goal_value = fields.Float(string="Standard Target")
    ks_goal_lines = fields.One2many('ks_dashboard_ninja.item_goal', 'ks_dashboard_item', string="Target Lines")

    ks_list_target_deviation_field = fields.Many2one('ir.model.fields', 'list_field_id',
                                                     domain="[('model_id','=',ks_model_id),('name','!=','id'),('name','!=','sequence'),"
                                                            "('store','=',True),'|','|',"
                                                            "('ttype','=','integer'),('ttype','=','float'),"
                                                            "('ttype','=','monetary')]",
                                                     )

    ks_many2many_field_ordering = fields.Char()

    # TODO : Merge all these fields into one and show a widget to get output for these fields from JS
    ks_show_data_value = fields.Boolean(string="Show Data Value")

    ks_action_lines = fields.One2many('ks_dashboard_ninja.item_action', 'ks_dashboard_item_id', string="Action Lines")

    ks_actions = fields.Many2one('ir.actions.act_window', domain="[('res_model','=',ks_model_name)]",
                                 string="Actions", help="This Action will be Performed at the end of Drill Down Action")

    ks_compare_period = fields.Integer(string="Include Period")
    ks_year_period = fields.Integer(string="Same Period Previous Years")
    ks_compare_period_2 = fields.Integer(string="KPI Include Period")
    ks_year_period_2 = fields.Integer(string="KPI Same Period Previous Years")

    # Adding refresh per item override global update interval
    ks_update_items_data = fields.Selection([
        (15000, '15 Seconds'),
        (30000, '30 Seconds'),
        (45000, '45 Seconds'),
        (60000, '1 minute'),
        (120000, '2 minute'),
        (300000, '5 minute'),
        (600000, '10 minute'),
    ], string="Item Update Interval", default=lambda self: self._context.get('ks_set_interval', False))

    # User can select custom units for measure
    ks_unit = fields.Boolean(string="Show Custom Unit", default=False)
    ks_unit_selection = fields.Selection([
        ('monetary', 'Monetary'),
        ('custom', 'Custom'),
    ], string="Select Unit Type")
    ks_chart_unit = fields.Char(string="Enter Unit", size=5, default="",
                                help="Maximum limit 5 characters, for ex: km, m")

    # User can stop propagation of the tile item
    ks_show_records = fields.Boolean(string="Show Records", default=True, help="""This field Enable the click on 
                                                                                  Dashboard Items to view the Odoo 
                                                                                  default view of records""")
    ks_data_calculation_type = fields.Selection([('custom', 'Custom'),
                                                 ('query', 'Query')], string="Data Calculation Type", default="custom")

    #  Field for fill temp data
    ks_fill_temporal = fields.Boolean('Fill Temporal Value')

    # Domain Extension field
    ks_domain_extension = fields.Char('Domain Extension')
    ks_domain_extension_2 = fields.Char('KPI Domain Extension')

    # hide legend
    ks_hide_legend = fields.Boolean('Show Legend', help="Hide all legend from the chart item", default=True)


    @api.onchange('ks_fill_temporal', 'ks_chart_relation_sub_groupby')
    def ks_onchange_fill_temporal(self):
        for rec in self:
            if rec.ks_fill_temporal:
                rec.ks_sort_by_field = self.ks_chart_relation_groupby.id
                rec.ks_sort_by_order = 'ASC'
                rec.ks_record_data_limit = 0
            else:
                rec.ks_sort_by_field = False
                rec.ks_sort_by_order = False
                rec.ks_record_data_limit = 0

    @api.onchange('ks_goal_lines')
    def ks_date_target_line(self):
        for rec in self:
            rec.ks_sort_by_field = False
            rec.ks_sort_by_order = False
            rec.ks_record_data_limit = 0
            if rec.ks_chart_date_groupby in ('minute', 'hour') or rec.ks_chart_date_sub_groupby in ('minute', 'hour'):
                rec.ks_goal_lines = False
                return {'warning': {
                    'title': _('Groupby Field aggregation'),
                    'message': _(
                        'Cannot create target lines when Group By Date field is set to have aggregation in '
                        'Minute and Hour case.')
                }}

    @api.multi
    @api.onchange('ks_chart_date_groupby', 'ks_chart_date_sub_groupby')
    def ks_date_target(self):
        for rec in self:
            if (rec.ks_chart_date_groupby in ('minute', 'hour') or rec.ks_chart_date_sub_groupby in ('minute', 'hour'))\
                    and rec.ks_goal_lines:
                raise ValidationError(_(
                    "Cannot set aggregation having Date time (Hour, Minute) when target lines per date are being used."
                    " To proceed this, first delete target lines"))

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        if 'ks_action_lines' not in default:
            default['ks_action_lines'] = [(0, 0, line.copy_data()[0]) for line in self.ks_action_lines]

        if 'ks_goal_lines' not in default:
            default['ks_goal_lines'] = [(0, 0, line.copy_data()[0]) for line in self.ks_goal_lines]

        return super(KsDashboardNinjaItems, self).copy_data(default)

    @api.multi
    def name_get(self):
        res = []
        for rec in self:
            name = rec.name
            if not name:
                name = rec.ks_model_id.name
            res.append((rec.id, name))

        return res

    @api.model
    def create(self, values):
        """ Override to save list view fields ordering """
        if values.get('ks_list_view_fields', False) and values.get('ks_list_view_group_fields', False):
            ks_many2many_field_ordering = {
                'ks_list_view_fields': values['ks_list_view_fields'][0][2],
                'ks_list_view_group_fields': values['ks_list_view_group_fields'][0][2],
            }
            values['ks_many2many_field_ordering'] = json.dumps(ks_many2many_field_ordering)

        return super(KsDashboardNinjaItems, self).create(
            values)

    @api.multi
    def write(self, values):
        for rec in self:
            if rec['ks_many2many_field_ordering']:
                ks_many2many_field_ordering = json.loads(rec['ks_many2many_field_ordering'])
            else:
                ks_many2many_field_ordering = {}
            if values.get('ks_list_view_fields', False):
                ks_many2many_field_ordering['ks_list_view_fields'] = values['ks_list_view_fields'][0][2]
            if values.get('ks_list_view_group_fields', False):
                ks_many2many_field_ordering['ks_list_view_group_fields'] = values['ks_list_view_group_fields'][0][2]
            values['ks_many2many_field_ordering'] = json.dumps(ks_many2many_field_ordering)

        return super(KsDashboardNinjaItems, self).write(
            values)

    @api.onchange('ks_list_view_fields')
    def ks_set_list_view_fields_order(self):
        for rec in self:
            order = [res.id for res in rec.ks_list_view_fields]
            if rec.ks_many2many_field_ordering:
                ks_many2many_field_ordering = json.loads(rec.ks_many2many_field_ordering)
            else:
                ks_many2many_field_ordering = {}
            ks_many2many_field_ordering['ks_list_view_fields'] = order
            rec.ks_many2many_field_ordering = json.dumps(ks_many2many_field_ordering)

    @api.onchange('ks_list_view_group_fields')
    def ks_set_list_view_group_fields_order(self):
        for rec in self:
            order = [res.id for res in rec.ks_list_view_group_fields]
            if rec.ks_many2many_field_ordering:
                ks_many2many_field_ordering = json.loads(rec.ks_many2many_field_ordering)
            else:
                ks_many2many_field_ordering = {}
            ks_many2many_field_ordering['ks_list_view_group_fields'] = order
            rec.ks_many2many_field_ordering = json.dumps(ks_many2many_field_ordering)

    @api.onchange('ks_layout')
    def layout_four_font_change(self):
        if self.ks_dashboard_item_theme != "white":
            if self.ks_layout == 'layout4':
                self.ks_font_color = self.ks_background_color
                self.ks_default_icon_color = "#ffffff,0.99"
            elif self.ks_layout == 'layout6':
                self.ks_font_color = "#ffffff,0.99"
                self.ks_default_icon_color = self.ks_get_dark_color(self.ks_background_color.split(',')[0],
                                                                    self.ks_background_color.split(',')[1])
            else:
                self.ks_default_icon_color = "#ffffff,0.99"
                self.ks_font_color = "#ffffff,0.99"
        else:
            if self.ks_layout == 'layout4':
                self.ks_background_color = "#00000,0.99"
                self.ks_font_color = self.ks_background_color
                self.ks_default_icon_color = "#ffffff,0.99"
            else:
                self.ks_background_color = "#ffffff,0.99"
                self.ks_font_color = "#00000,0.99"
                self.ks_default_icon_color = "#00000,0.99"

    # To convert color into 10% darker. Percentage amount is hardcoded. Change amt if want to change percentage.
    def ks_get_dark_color(self, color, opacity):
        num = int(color[1:], 16)
        amt = -25
        R = (num >> 16) + amt
        R = (255 if R > 255 else 0 if R < 0 else R) * 0x10000
        G = (num >> 8 & 0x00FF) + amt
        G = (255 if G > 255 else 0 if G < 0 else G) * 0x100
        B = (num & 0x0000FF) + amt
        B = (255 if B > 255 else 0 if B < 0 else B)
        return "#" + hex(0x1000000 + R + G + B).split('x')[1][1:] + "," + opacity

    @api.onchange('ks_model_id')
    def make_record_field_empty(self):
        for rec in self:
            rec.ks_record_field = False
            rec.ks_domain = False
            rec.ks_date_filter_field = False
            # To show "created on" by default on date filter field on model select.
            if rec.ks_model_id:
                datetime_field_list = rec.ks_date_filter_field.search(
                    [('model_id', '=', rec.ks_model_id.id), '|', ('ttype', '=', 'date'),
                     ('ttype', '=', 'datetime')]).read(['id', 'name'])
                for field in datetime_field_list:
                    if field['name'] == 'create_date':
                        rec.ks_date_filter_field = field['id']
            else:
                rec.ks_date_filter_field = False
            # Pro
            rec.ks_record_field = False
            rec.ks_chart_measure_field = False
            rec.ks_chart_measure_field_2 = False
            rec.ks_chart_relation_sub_groupby = False
            rec.ks_chart_relation_groupby = False
            rec.ks_chart_date_sub_groupby = False
            rec.ks_chart_date_groupby = False
            rec.ks_sort_by_field = False
            rec.ks_sort_by_order = False
            rec.ks_record_data_limit = False
            rec.ks_list_view_fields = False
            rec.ks_list_view_group_fields = False
            rec.ks_action_lines = False
            rec.ks_actions = False
            rec.ks_domain_extension = False

    @api.onchange('ks_record_count', 'ks_layout', 'name', 'ks_model_id', 'ks_domain', 'ks_icon_select',
                  'ks_default_icon', 'ks_icon',
                  'ks_background_color', 'ks_font_color', 'ks_default_icon_color')
    def ks_preview_update(self):
        self.ks_preview += 1

    @api.onchange('ks_dashboard_item_theme')
    def change_dashboard_item_theme(self):
        if self.ks_dashboard_item_theme == "red":
            self.ks_background_color = "#d9534f,0.99"
            self.ks_default_icon_color = "#ffffff,0.99"
            self.ks_font_color = "#ffffff,0.99"
        elif self.ks_dashboard_item_theme == "blue":
            self.ks_background_color = "#337ab7,0.99"
            self.ks_default_icon_color = "#ffffff,0.99"
            self.ks_font_color = "#ffffff,0.99"
        elif self.ks_dashboard_item_theme == "yellow":
            self.ks_background_color = "#f0ad4e,0.99"
            self.ks_default_icon_color = "#ffffff,0.99"
            self.ks_font_color = "#ffffff,0.99"
        elif self.ks_dashboard_item_theme == "green":
            self.ks_background_color = "#5cb85c,0.99"
            self.ks_default_icon_color = "#ffffff,0.99"
            self.ks_font_color = "#ffffff,0.99"
        elif self.ks_dashboard_item_theme == "white":
            if self.ks_layout == 'layout4':
                self.ks_background_color = "#00000,0.99"
                self.ks_default_icon_color = "#ffffff,0.99"
            else:
                self.ks_background_color = "#ffffff,0.99"
                self.ks_default_icon_color = "#000000,0.99"
                self.ks_font_color = "#000000,0.99"

        if self.ks_layout == 'layout4':
            self.ks_font_color = self.ks_background_color

        elif self.ks_layout == 'layout6':
            self.ks_default_icon_color = self.ks_get_dark_color(self.ks_background_color.split(',')[0],
                                                                self.ks_background_color.split(',')[1])
            if self.ks_dashboard_item_theme == "white":
                self.ks_default_icon_color = "#000000,0.99"

    @api.multi
    @api.depends('ks_record_count_type', 'ks_model_id', 'ks_domain', 'ks_record_field', 'ks_date_filter_field',
                 'ks_item_end_date', 'ks_item_start_date', 'ks_compare_period', 'ks_year_period',
                 'ks_dashboard_item_type', 'ks_domain_extension')
    def ks_get_record_count(self):
        for rec in self:
            if rec.ks_record_count_type == 'count' or rec.ks_dashboard_item_type == 'ks_list_view':
                rec.ks_record_count = rec.ks_fetch_model_data(rec.ks_model_name, rec.ks_domain, 'search_count', rec)
            elif rec.ks_record_count_type in ['sum',
                                              'average'] and rec.ks_record_field and rec.ks_dashboard_item_type != 'ks_list_view':
                ks_records_grouped_data = rec.ks_fetch_model_data(rec.ks_model_name, rec.ks_domain, 'read_group', rec)
                if ks_records_grouped_data and len(ks_records_grouped_data) > 0:
                    ks_records_grouped_data = ks_records_grouped_data[0]
                    if rec.ks_record_count_type == 'sum' and ks_records_grouped_data.get('__count', False) and (
                            ks_records_grouped_data.get(rec.ks_record_field.name)):
                        rec.ks_record_count = ks_records_grouped_data.get(rec.ks_record_field.name, 0)
                    elif rec.ks_record_count_type == 'average' and ks_records_grouped_data.get(
                            '__count', False) and (ks_records_grouped_data.get(rec.ks_record_field.name)):
                        rec.ks_record_count = ks_records_grouped_data.get(rec.ks_record_field.name,
                                                                          0) / ks_records_grouped_data.get('__count',
                                                                                                           1)
                    else:
                        rec.ks_record_count = 0
                else:
                    rec.ks_record_count = 0
            else:
                rec.ks_record_count = 0

    # Writing separate function to fetch dashboard item data
    def ks_fetch_model_data(self, ks_model_name, ks_domain, ks_func, rec):
        data = 0
        try:
            if ks_domain and ks_domain != '[]' and ks_model_name:
                proper_domain = self.ks_convert_into_proper_domain(ks_domain, rec)
                if ks_func == 'search_count':
                    data = self.env[ks_model_name].search_count(proper_domain)
                elif ks_func == 'read_group':
                    data = self.env[ks_model_name].read_group(proper_domain, [rec.ks_record_field.name], [])
            elif ks_model_name:
                # Have to put extra if condition here because on load,model giving False value
                proper_domain = self.ks_convert_into_proper_domain(False, rec)
                if ks_func == 'search_count':
                    data = self.env[ks_model_name].search_count(proper_domain)

                elif ks_func == 'read_group':
                    data = self.env[ks_model_name].read_group(proper_domain, [rec.ks_record_field.name], [])
            else:
                return []
        except Exception as e:
            return []
        return data

    @api.constrains('ks_item_start_date_2', 'ks_item_end_date_2')
    def ks_check_datetime_2(self):
        for rec in self:
            if rec.ks_item_start_date_2 and rec.ks_item_end_date_2:
                if rec.ks_item_start_date_2 >= rec.ks_item_end_date_2:
                    raise ValidationError(_("Start Date should be less than End Date"))

    @api.constrains('ks_item_start_date', 'ks_item_end_date')
    def ks_check_valid_datetime(self):
        for rec in self:
            if rec.ks_item_start_date and rec.ks_item_end_date:
                if rec.ks_item_start_date >= rec.ks_item_end_date:
                    raise ValidationError(_("Start Date should be less than End Date"))


    def ks_convert_into_proper_domain(self, ks_domain, rec):
        if ks_domain and "%UID" in ks_domain:
            ks_domain = ks_domain.replace('"%UID"', str(self.env.user.id))

        if ks_domain and "%MYCOMPANY" in ks_domain:
            ks_domain = ks_domain.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))

        ks_date_domain = False
        if rec.ks_date_filter_field:
            if not rec.ks_date_filter_selection or rec.ks_date_filter_selection == "l_none":
                selected_start_date = self._context.get('ksDateFilterStartDate', False)
                selected_end_date = self._context.get('ksDateFilterEndDate', False)
                ks_is_def_custom_filter = self._context.get('ksIsDefultCustomDateFilter', False)
                ks_timezone = self._context.get('tz') or self.env.user.tz
                if selected_start_date and selected_end_date and rec.ks_date_filter_field.ttype == 'datetime' and not ks_is_def_custom_filter:
                    selected_start_date = ks_convert_into_utc(selected_start_date, ks_timezone)
                    selected_end_date = ks_convert_into_utc(selected_end_date, ks_timezone)
                if selected_start_date and selected_end_date and rec.ks_date_filter_field.ttype == 'date' and ks_is_def_custom_filter:
                    selected_start_date = ks_convert_into_local(selected_start_date, ks_timezone)
                    selected_end_date = ks_convert_into_local(selected_end_date, ks_timezone)

                if self._context.get('ksDateFilterSelection', False) and self._context['ksDateFilterSelection'] not in [
                    'l_none', 'l_custom']:
                    ks_date_data = ks_get_date(self._context.get('ksDateFilterSelection'), self,
                                               rec.ks_date_filter_field.ttype)
                    selected_start_date = ks_date_data["selected_start_date"]
                    selected_end_date = ks_date_data["selected_end_date"]

                if selected_end_date and not selected_start_date:
                    ks_date_domain = [
                        (rec.ks_date_filter_field.name, "<=",
                         selected_end_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
                elif selected_start_date and not selected_end_date:
                    ks_date_domain = [
                        (rec.ks_date_filter_field.name, ">=",
                         selected_start_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
                else:
                    if selected_end_date and selected_start_date:
                        ks_date_domain = [
                            (rec.ks_date_filter_field.name, ">=",
                             selected_start_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                            (rec.ks_date_filter_field.name, "<=",
                             selected_end_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
                        ]

            else:
                if rec.ks_date_filter_selection and rec.ks_date_filter_selection != 'l_custom':
                    ks_date_data = ks_get_date(rec.ks_date_filter_selection, self, rec.ks_date_filter_field.ttype)
                    selected_start_date = ks_date_data["selected_start_date"]
                    selected_end_date = ks_date_data["selected_end_date"]
                else:
                    selected_start_date = False
                    selected_end_date = False
                    if rec.ks_item_start_date or rec.ks_item_end_date:
                        selected_start_date = rec.ks_item_start_date
                        selected_end_date = rec.ks_item_end_date
                        if rec.ks_date_filter_field.ttype == 'date' and rec.ks_item_start_date and rec.ks_item_end_date:
                            ks_timezone = self._context.get('tz') or self.env.user.tz
                            selected_start_date = ks_convert_into_local(rec.ks_item_start_date, ks_timezone)
                            selected_end_date = ks_convert_into_local(rec.ks_item_end_date, ks_timezone)

                if selected_start_date and selected_end_date:
                    if rec.ks_compare_period:
                        ks_compare_period = abs(rec.ks_compare_period)
                        if ks_compare_period > 100:
                            ks_compare_period = 100
                        if rec.ks_compare_period > 0:
                            selected_end_date = selected_end_date + (
                                    selected_end_date - selected_start_date) * ks_compare_period
                        elif rec.ks_compare_period < 0:
                            selected_start_date = selected_start_date - (
                                    selected_end_date - selected_start_date) * ks_compare_period

                    if rec.ks_year_period and rec.ks_year_period != 0 and rec.ks_dashboard_item_type:
                        abs_year_period = abs(rec.ks_year_period)
                        sign_yp = rec.ks_year_period / abs_year_period
                        if abs_year_period > 100:
                            abs_year_period = 100
                        date_field_name = rec.ks_date_filter_field.name

                        ks_date_domain = ['&', (date_field_name, ">=",
                                                fields.datetime.strftime(selected_start_date,
                                                                         DEFAULT_SERVER_DATETIME_FORMAT)),
                                          (date_field_name, "<=",
                                           fields.datetime.strftime(selected_end_date, DEFAULT_SERVER_DATETIME_FORMAT))]

                        for p in range(1, abs_year_period + 1):
                            ks_date_domain.insert(0, '|')
                            ks_date_domain.extend(['&', (date_field_name, ">=", fields.datetime.strftime(
                                selected_start_date - relativedelta.relativedelta(years=p) * sign_yp,
                                DEFAULT_SERVER_DATETIME_FORMAT)),
                                                   (date_field_name, "<=", fields.datetime.strftime(
                                                       selected_end_date - relativedelta.relativedelta(years=p)
                                                       * sign_yp, DEFAULT_SERVER_DATETIME_FORMAT))])
                    else:
                        selected_start_date = fields.datetime.strftime(selected_start_date,
                                                                       DEFAULT_SERVER_DATETIME_FORMAT)
                        selected_end_date = fields.datetime.strftime(selected_end_date, DEFAULT_SERVER_DATETIME_FORMAT)
                        ks_date_domain = [(rec.ks_date_filter_field.name, ">=", selected_start_date),
                                          (rec.ks_date_filter_field.name, "<=", selected_end_date)]
                elif selected_start_date and not selected_end_date:
                    selected_start_date = fields.datetime.strftime(selected_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    ks_date_domain = [(rec.ks_date_filter_field.name, ">=", selected_start_date)]
                elif selected_end_date and not selected_start_date:
                    selected_end_date = fields.datetime.strftime(selected_end_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    ks_date_domain = [(rec.ks_date_filter_field.name, "<=", selected_end_date)]
        else:
            ks_date_domain = []

        proper_domain = safe_eval(ks_domain) if ks_domain else []
        if ks_date_domain:
            proper_domain.extend(ks_date_domain)
        if rec.ks_domain_extension:
            ks_domain_extension = rec.ks_convert_domain_extension(rec.ks_domain_extension, rec)
            proper_domain.extend(ks_domain_extension)

        return proper_domain

    def ks_convert_domain_extension(self, ks_domain_extension, rec):

        if "%UID" in ks_domain_extension:
            ks_domain_extension = ks_domain_extension.replace('"%UID"', str(self.env.user.id))
        if '%UID' in ks_domain_extension:
            ks_domain_extension = ks_domain_extension.replace("'%UID'", str(self.env.user.id))

        if ks_domain_extension and "%MYCOMPANY" in ks_domain_extension:
            ks_domain_extension = ks_domain_extension.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))
            if '%MYCOMPANY' in ks_domain_extension:
                ks_domain_extension = ks_domain_extension.replace("'%MYCOMPANY'", str(self.env.user.company_id.id))

        ks_domain = safe_eval(ks_domain_extension)
        return ks_domain

    @api.onchange('ks_domain_extension')
    def ks_onchange_domain_extension(self):
        if self.ks_domain_extension:
            proper_domain = []
            try:
                ks_domain_extension = self.ks_domain_extension
                if "%UID" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%UID"', str(self.env.user.id))
                if '%UID' in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace("'%UID'", str(self.env.user.id))

                if ks_domain_extension and "%MYCOMPANY" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))
                    if '%MYCOMPANY' in ks_domain_extension:
                        ks_domain_extension = ks_domain_extension.replace("'%MYCOMPANY'",
                                                                          str(self.env.user.company_id.id))
                self.env[self.ks_model_name].search_count(safe_eval(ks_domain_extension))
            except Exception:
                raise ValidationError(
                    "Domain Extension Syntax is wrong. \nProper Syntax Example :[['<field_name'>,'<operator>','"
                    "<value_to_compare>']]")

    @api.constrains('ks_domain_extension')
    def ks_check_domain_extension(self):
        if self.ks_domain_extension and self.ks_model_name:
            proper_domain = []
            try:
                ks_domain_extension = self.ks_domain_extension
                if "%UID" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%UID"', str(self.env.user.id))
                if '%UID' in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace("'%UID'", str(self.env.user.id))

                if ks_domain_extension and "%MYCOMPANY" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))
                    if '%MYCOMPANY' in ks_domain_extension:
                        ks_domain_extension = ks_domain_extension.replace("'%MYCOMPANY'",
                                                                          str(self.env.user.company_id.id))
                self.env[self.ks_model_name].search_count(safe_eval(ks_domain_extension))
            except Exception:
                raise ValidationError(
                    "Domain Extension Syntax is wrong. \nProper Syntax Example :[['<field_name'>,'<operator>',"
                    "'<value_to_compare>']]")

    @api.onchange('ks_domain_extension_2')
    def ks_onchange_domain_extension_2(self):
        if self.ks_domain_extension_2:
            proper_domain = []
            try:
                ks_domain_extension = self.ks_domain_extension_2
                if "%UID" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%UID"', str(self.env.user.id))
                if '%UID' in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace("'%UID'", str(self.env.user.id))

                if ks_domain_extension and "%MYCOMPANY" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))
                    if '%MYCOMPANY' in ks_domain_extension:
                        ks_domain_extension = ks_domain_extension.replace("'%MYCOMPANY'",
                                                                          str(self.env.user.company_id.id))
                self.env[self.ks_model_name_2].search_count(safe_eval(ks_domain_extension))
            except Exception:
                raise ValidationError(
                    "Domain Extension Syntax is wrong. \nProper Syntax Example :[['<field_name'>,'<operator>',"
                    "'<value_to_compare>']]")

    @api.constrains('ks_domain_extension_2')
    def ks_check_domain_extension_2(self):
        if self.ks_domain_extension_2 and self.ks_model_name_2:
            proper_domain = []
            try:
                ks_domain_extension = self.ks_domain_extension_2
                if "%UID" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%UID"', str(self.env.user.id))
                if '%UID' in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace("'%UID'", str(self.env.user.id))

                if ks_domain_extension and "%MYCOMPANY" in ks_domain_extension:
                    ks_domain_extension = ks_domain_extension.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))
                    if '%MYCOMPANY' in ks_domain_extension:
                        ks_domain_extension = ks_domain_extension.replace("'%MYCOMPANY'",
                                                                          str(self.env.user.company_id.id))
                self.env[self.ks_model_name_2].search_count(safe_eval(ks_domain_extension))
            except Exception:
                raise ValidationError(
                    "Domain Extension Syntax is wrong. \nProper Syntax Example :[['<field_name'>,'<operator>',"
                    "'<value_to_compare>']]")


    @api.multi
    @api.onchange('ks_chart_relation_groupby')
    def get_chart_groupby_type(self):
        for rec in self:
            if rec.ks_chart_relation_groupby.ttype == 'datetime' or rec.ks_chart_relation_groupby.ttype == 'date':
                rec.ks_chart_groupby_type = 'date_type'
            elif rec.ks_chart_relation_groupby.ttype == 'many2one':
                rec.ks_chart_groupby_type = 'relational_type'
            elif rec.ks_chart_relation_groupby.ttype == 'selection':
                rec.ks_chart_groupby_type = 'selection'
            else:
                rec.ks_chart_groupby_type = 'other'

    @api.onchange('ks_chart_relation_groupby')
    def ks_empty_sub_group_by(self):
        for rec in self:
            if not rec.ks_chart_relation_groupby or rec.ks_chart_groupby_type == "date_type" \
                    and not rec.ks_chart_date_groupby:
                rec.ks_chart_relation_sub_groupby = False
                rec.ks_chart_date_sub_groupby = False

    @api.depends('ks_chart_relation_sub_groupby')
    def get_chart_sub_groupby_type(self):
        for rec in self:
            if rec.ks_chart_relation_sub_groupby.ttype == 'datetime' or \
                    rec.ks_chart_relation_sub_groupby.ttype == 'date':
                rec.ks_chart_sub_groupby_type = 'date_type'
            elif rec.ks_chart_relation_sub_groupby.ttype == 'many2one':
                rec.ks_chart_sub_groupby_type = 'relational_type'

            elif rec.ks_chart_relation_sub_groupby.ttype == 'selection':
                rec.ks_chart_sub_groupby_type = 'selection'

            else:
                rec.ks_chart_sub_groupby_type = 'other'

    # Using this function just to let js call rpc to load some data later
    @api.model
    def ks_chart_load(self):
        return True

    @api.multi
    @api.depends('ks_chart_measure_field', 'ks_chart_relation_groupby', 'ks_chart_date_groupby', 'ks_domain',
                 'ks_dashboard_item_type', 'ks_model_id', 'ks_sort_by_field', 'ks_sort_by_order',
                 'ks_record_data_limit', 'ks_chart_data_count_type', 'ks_chart_measure_field_2', 'ks_goal_enable',
                 'ks_standard_goal_value', 'ks_goal_bar_line', 'ks_chart_relation_sub_groupby',
                 'ks_chart_date_sub_groupby', 'ks_date_filter_field', 'ks_item_start_date', 'ks_item_end_date',
                 'ks_compare_period', 'ks_year_period', 'ks_unit', 'ks_unit_selection', 'ks_chart_unit',
                 'ks_fill_temporal', 'ks_domain_extension')
    def ks_get_chart_data(self):
        for rec in self:

            if rec.ks_dashboard_item_type and rec.ks_dashboard_item_type != 'ks_tile' and \
                    rec.ks_dashboard_item_type != 'ks_list_view' and rec.ks_model_id and rec.ks_chart_data_count_type:
                ks_chart_data = {'labels': [], 'datasets': [], 'ks_currency': 0, 'ks_field': "", 'ks_selection': "",
                                 'ks_show_second_y_scale': False, 'domains': [], }
                ks_chart_measure_field = []
                ks_chart_measure_field_with_type = []
                ks_chart_measure_field_ids = []
                ks_chart_measure_field_2 = []
                ks_chart_measure_field_with_type_2 = []
                ks_chart_measure_field_2_ids = []

                if rec.ks_unit and rec.ks_unit_selection == 'monetary':
                    ks_chart_data['ks_selection'] += rec.ks_unit_selection
                    ks_chart_data['ks_currency'] += rec.env.user.company_id.currency_id.id
                elif rec.ks_unit and rec.ks_unit_selection == 'custom':
                    ks_chart_data['ks_selection'] += rec.ks_unit_selection
                    if rec.ks_chart_unit:
                        ks_chart_data['ks_field'] += rec.ks_chart_unit

                # If count chart data type:
                if rec.ks_chart_data_count_type == "count":
                    rec.ks_chart_measure_field = False
                    rec.ks_chart_measure_field_2 = False
                    ks_chart_measure_field_with_type.append('count:count(id)')
                    ks_chart_data['datasets'].append({'data': [], 'label': "Count"})
                else:
                    if rec.ks_dashboard_item_type == 'ks_bar_chart':
                        if rec.ks_chart_measure_field_2:
                            ks_chart_data['ks_show_second_y_scale'] = True

                        for res in rec.ks_chart_measure_field_2:
                            if rec.ks_chart_data_count_type == 'sum':
                                ks_data_count_type = 'sum'
                            elif rec.ks_chart_data_count_type == 'average':
                                ks_data_count_type = 'avg'
                            else:
                                raise ValidationError(_('Please chose any Data Type!'))
                            ks_chart_measure_field_2.append(res.name)
                            ks_chart_measure_field_with_type_2.append(res.name + ':' + ks_data_count_type)
                            ks_chart_measure_field_2_ids.append(res.id)
                            ks_chart_data['datasets'].append(
                                {'data': [], 'label': res.field_description, 'type': 'line', 'yAxisID': 'y-axis-1'})

                    for res in rec.ks_chart_measure_field:
                        if rec.ks_chart_data_count_type == 'sum':
                            ks_data_count_type = 'sum'
                        elif rec.ks_chart_data_count_type == 'average':
                            ks_data_count_type = 'avg'
                        else:
                            raise ValidationError(_('Please chose any Data Type!'))
                        ks_chart_measure_field_with_type.append(res.name + ':' + ks_data_count_type)
                        ks_chart_measure_field.append(res.name)
                        ks_chart_measure_field_ids.append(res.id)
                        ks_chart_data['datasets'].append({'data': [], 'label': res.field_description})

                # ks_chart_measure_field = [res.name for res in rec.ks_chart_measure_field]
                ks_chart_groupby_relation_field = rec.ks_chart_relation_groupby.name
                ks_chart_domain = self.ks_convert_into_proper_domain(rec.ks_domain, rec)
                ks_chart_data['previous_domain'] = ks_chart_domain
                if rec.ks_chart_data_count_type == "count" and not self.ks_fill_temporal and not rec.ks_sort_by_field:
                    orderby = 'count'
                else:
                    orderby = rec.ks_sort_by_field.name if rec.ks_sort_by_field else "id"
                if rec.ks_sort_by_order:
                    orderby = orderby + " " + rec.ks_sort_by_order
                limit = rec.ks_record_data_limit if rec.ks_record_data_limit and rec.ks_record_data_limit > 0 else False

                if ((rec.ks_chart_data_count_type != "count" and ks_chart_measure_field) or (
                        rec.ks_chart_data_count_type == "count" and not ks_chart_measure_field)) \
                        and not rec.ks_chart_relation_sub_groupby:
                    if rec.ks_chart_relation_groupby.ttype == 'date' and rec.ks_chart_date_groupby in (
                            'minute', 'hour'):
                        raise ValidationError(_('Groupby field: {} cannot be aggregated by {}').format(
                            rec.ks_chart_relation_groupby.display_name, rec.ks_chart_date_groupby))
                        ks_chart_date_groupby = 'day'
                    elif rec.ks_chart_date_groupby == 'month_year':
                            ks_chart_date_groupby = 'month'
                    else:
                        ks_chart_date_groupby = rec.ks_chart_date_groupby

                    if (rec.ks_chart_groupby_type == 'date_type' and rec.ks_chart_date_groupby) or\
                            rec.ks_chart_groupby_type != 'date_type':
                        ks_chart_data = rec.ks_fetch_chart_data(rec.ks_model_name, ks_chart_domain, ks_chart_measure_field_with_type, ks_chart_measure_field_with_type_2,
                                                                ks_chart_measure_field,
                                                                ks_chart_measure_field_2,
                                                                ks_chart_groupby_relation_field,
                                                                ks_chart_date_groupby,
                                                                rec.ks_chart_groupby_type, orderby, limit,
                                                                rec.ks_chart_data_count_type,
                                                                ks_chart_measure_field_ids,
                                                                ks_chart_measure_field_2_ids,
                                                                rec.ks_chart_relation_groupby.id, ks_chart_data)

                        if rec.ks_chart_groupby_type == 'date_type' and rec.ks_goal_enable and rec.ks_dashboard_item_type in [
                            'ks_bar_chart', 'ks_horizontalBar_chart', 'ks_line_chart',
                            'ks_area_chart'] and rec.ks_chart_groupby_type == "date_type":

                            if rec._context.get('current_id', False):
                                ks_item_id = rec._context['current_id']
                            else:
                                ks_item_id = rec.id

                            if rec.ks_date_filter_selection == "l_none":
                                selected_start_date = rec._context.get('ksDateFilterStartDate', False)
                                selected_end_date = rec._context.get('ksDateFilterEndDate', False)

                            else:
                                if rec.ks_date_filter_selection == "l_custom":
                                    selected_start_date  = rec.ks_item_start_date
                                    selected_end_date = rec.ks_item_start_date
                                else:
                                    ks_date_data = ks_get_date(rec.ks_date_filter_selection, self,
                                                               rec.ks_date_filter_field.ttype)
                                    selected_start_date = ks_date_data["selected_start_date"]
                                    selected_end_date = ks_date_data["selected_end_date"]

                            if selected_start_date and selected_end_date:
                                selected_start_date = selected_start_date.strftime('%Y-%m-%d')
                                selected_end_date = selected_end_date.strftime('%Y-%m-%d')
                            ks_goal_domain = [('ks_dashboard_item', '=', ks_item_id)]

                            if selected_start_date and selected_end_date:
                                ks_goal_domain.extend([('ks_goal_date', '>=', selected_start_date.split(" ")[0]),
                                                       ('ks_goal_date', '<=', selected_end_date.split(" ")[0])])

                            ks_date_data = rec.ks_get_start_end_date(rec.ks_model_name, ks_chart_groupby_relation_field,
                                                                     rec.ks_chart_relation_groupby.ttype,
                                                                     ks_chart_domain,
                                                                     ks_goal_domain)

                            labels = []
                            if rec.ks_chart_date_groupby == 'month_year':
                                ks_chart_date_groupby =  'month'
                            else:
                                ks_chart_date_groupby = rec.ks_chart_date_groupby
                            if ks_date_data['start_date'] and ks_date_data['end_date'] and rec.ks_goal_lines:
                                labels = self.generate_timeserise(ks_date_data['start_date'], ks_date_data['end_date'],
                                                                  ks_chart_date_groupby)

                            ks_goal_records = self.env['ks_dashboard_ninja.item_goal'].read_group(
                                ks_goal_domain, ['ks_goal_value'],
                                ['ks_goal_date' + ":" + ks_chart_date_groupby], lazy=False)
                            ks_goal_labels = []
                            ks_goal_dataset = []
                            goal_dataset = []

                            if rec.ks_goal_lines and len(rec.ks_goal_lines) != 0:
                                ks_goal_domains = {}
                                for res in ks_goal_records:
                                    if res['ks_goal_date' + ":" + ks_chart_date_groupby]:
                                        ks_goal_labels.append(res['ks_goal_date' + ":" + ks_chart_date_groupby])
                                        ks_goal_dataset.append(res['ks_goal_value'])
                                        ks_goal_domains[res['ks_goal_date' + ":" + ks_chart_date_groupby]] = res['__domain']

                                for goal_domain in ks_goal_domains.keys():
                                    ks_goal_doamins = []
                                    for item in ks_goal_domains[goal_domain]:

                                        if 'ks_goal_date' in item:
                                            domain = list(item)
                                            domain[0] = ks_chart_groupby_relation_field
                                            domain = tuple(domain)
                                            ks_goal_doamins.append(domain)
                                    ks_goal_doamins.insert(0, '&')
                                    ks_goal_domains[goal_domain] = ks_goal_doamins

                                domains = {}
                                counter = 0
                                for label in ks_chart_data['labels']:
                                    domains[label] = ks_chart_data['domains'][counter]
                                    counter += 1

                                ks_chart_records_dates = ks_chart_data['labels'] + list(
                                    set(ks_goal_labels) - set(ks_chart_data['labels']))

                                ks_chart_records = []
                                for label in labels:
                                    if label in ks_chart_records_dates:
                                        ks_chart_records.append(label)

                                ks_chart_data['domains'].clear()
                                datasets = []
                                for dataset in ks_chart_data['datasets']:
                                    datasets.append(dataset['data'].copy())

                                for dataset in ks_chart_data['datasets']:
                                    dataset['data'].clear()

                                for label in ks_chart_records:
                                    domain = domains.get(label, False)
                                    if domain:
                                        ks_chart_data['domains'].append(domain)
                                    else:
                                        ks_chart_data['domains'].append(ks_goal_domains.get(label, []))
                                    counterr = 0
                                    if label in ks_chart_data['labels']:
                                        index = ks_chart_data['labels'].index(label)

                                        for dataset in ks_chart_data['datasets']:
                                            dataset['data'].append(datasets[counterr][index])
                                            counterr += 1

                                    else:
                                        for dataset in ks_chart_data['datasets']:
                                            dataset['data'].append(0.00)

                                    if label in ks_goal_labels:
                                        index = ks_goal_labels.index(label)
                                        goal_dataset.append(ks_goal_dataset[index])
                                    else:
                                        goal_dataset.append(0.00)

                                ks_chart_data['labels'] = ks_chart_records
                            else:
                                if rec.ks_standard_goal_value:
                                    length = len(ks_chart_data['datasets'][0]['data'])
                                    for i in range(length):
                                        goal_dataset.append(rec.ks_standard_goal_value)
                            ks_goal_datasets = {
                                'label': 'Target',
                                'data': goal_dataset,
                            }
                            if rec.ks_goal_bar_line:
                                ks_goal_datasets['type'] = 'line'
                                ks_chart_data['datasets'].insert(0, ks_goal_datasets)
                            else:
                                ks_chart_data['datasets'].append(ks_goal_datasets)

                elif rec.ks_chart_relation_sub_groupby and ((rec.ks_chart_sub_groupby_type == 'relational_type') or
                                                            (rec.ks_chart_sub_groupby_type == 'selection') or
                                                            (rec.ks_chart_sub_groupby_type == 'date_type' and
                                                             rec.ks_chart_date_sub_groupby) or
                                                            (rec.ks_chart_sub_groupby_type == 'other')):
                    if rec.ks_chart_relation_sub_groupby.ttype == 'date':
                        if rec.ks_chart_date_sub_groupby in ('minute', 'hour'):
                            raise ValidationError(_('Sub Groupby field: {} cannot be aggregated by {}').format(
                                rec.ks_chart_relation_sub_groupby.display_name, rec.ks_chart_date_sub_groupby))
                        if rec.ks_chart_date_groupby in ('minute', 'hour'):
                            raise ValidationError(_('Groupby field: {} cannot be aggregated by {}').format(
                                rec.ks_chart_relation_sub_groupby.display_name, rec.ks_chart_date_groupby))
                        # doesn't have time in date
                        ks_chart_date_sub_groupby = rec.ks_chart_date_sub_groupby
                        ks_chart_date_groupby = rec.ks_chart_date_groupby
                    else:
                        ks_chart_date_sub_groupby = rec.ks_chart_date_sub_groupby
                        if rec.ks_chart_date_groupby == 'month_year':
                            ks_chart_date_groupby = 'month'
                        else:
                            ks_chart_date_groupby = rec.ks_chart_date_groupby
                    if len(ks_chart_measure_field) != 0 or rec.ks_chart_data_count_type == 'count':
                        if rec.ks_chart_groupby_type == 'date_type' and ks_chart_date_groupby:
                            ks_chart_group = rec.ks_chart_relation_groupby.name + ":" + ks_chart_date_groupby
                        else:
                            ks_chart_group = rec.ks_chart_relation_groupby.name

                        if rec.ks_chart_sub_groupby_type == 'date_type' and rec.ks_chart_date_sub_groupby:
                            ks_chart_sub_groupby_field = rec.ks_chart_relation_sub_groupby.name + ":" + \
                                                         ks_chart_date_sub_groupby
                        else:
                            ks_chart_sub_groupby_field = rec.ks_chart_relation_sub_groupby.name

                        ks_chart_groupby_relation_fields = [ks_chart_group, ks_chart_sub_groupby_field]
                        ks_chart_record = False
                        try:
                            ks_chart_record = self.env[rec.ks_model_name].read_group(ks_chart_domain,
                                                                                     list(set(ks_chart_measure_field_with_type +
                                                                                     ks_chart_measure_field_with_type_2 +
                                                                                     [ks_chart_groupby_relation_field,
                                                                              rec.ks_chart_relation_sub_groupby.name ])),
                                                                                 ks_chart_groupby_relation_fields,
                                                                                 orderby=orderby, limit=limit,
                                                                                 lazy=False)
                        except Exception:
                            ks_chart_record = {}
                        chart_data = []
                        chart_sub_data = []
                        for res in ks_chart_record:
                            domain = res.get('__domain', [])
                            if res.get(ks_chart_groupby_relation_fields[0], False):
                                if rec.ks_chart_groupby_type == 'date_type':
                                    # x-axis modification
                                    if rec.ks_chart_date_groupby == "day" \
                                            and rec.ks_chart_date_sub_groupby in ["quarter", "year"]:
                                        label = " ".join(res[ks_chart_groupby_relation_fields[0]].split(" ")[0:2])
                                    elif rec.ks_chart_date_groupby in ["minute", "hour"] and \
                                            rec.ks_chart_date_sub_groupby in ["month", "week", "quarter", "year"]:
                                        label = " ".join(res[ks_chart_groupby_relation_fields[0]].split(" ")[0:3])
                                    elif rec.ks_chart_date_groupby == 'month_year':
                                        label = res[ks_chart_groupby_relation_fields[0]]
                                    else:
                                        label = res[ks_chart_groupby_relation_fields[0]].split(" ")[0]
                                elif rec.ks_chart_groupby_type == 'selection':
                                    selection = res[ks_chart_groupby_relation_fields[0]]
                                    label = dict(self.env[rec.ks_model_name].fields_get(
                                        allfields=[ks_chart_groupby_relation_fields[0]])
                                                 [ks_chart_groupby_relation_fields[0]]['selection'])[selection]
                                elif rec.ks_chart_groupby_type == 'relational_type':
                                    label = res[ks_chart_groupby_relation_fields[0]][1]._value
                                elif rec.ks_chart_groupby_type == 'other':
                                    label = res[ks_chart_groupby_relation_fields[0]]

                                labels = []
                                value = []
                                value_2 = []
                                labels_2 = []
                                if rec.ks_chart_data_count_type != 'count':
                                    for ress in rec.ks_chart_measure_field:
                                        if rec.ks_chart_sub_groupby_type == 'date_type':
                                            if res[ks_chart_groupby_relation_fields[1]] is not False:
                                                labels.append(res[ks_chart_groupby_relation_fields[1]].split(" ")[
                                                                      0] + " " + ress.field_description)
                                            else:
                                                labels.append(str(res[ks_chart_groupby_relation_fields[1]]) + " " +
                                                              ress.field_description)
                                        elif rec.ks_chart_sub_groupby_type == 'selection':
                                            if res[ks_chart_groupby_relation_fields[1]] is not False:
                                                selection = res[ks_chart_groupby_relation_fields[1]]
                                                labels.append(dict(self.env[rec.ks_model_name].fields_get(
                                                    allfields=[ks_chart_groupby_relation_fields[1]])
                                                                   [ks_chart_groupby_relation_fields[1]]['selection'])[
                                                                  selection]
                                                              + " " + ress.field_description)
                                            else:
                                                labels.append(str(res[ks_chart_groupby_relation_fields[1]]))
                                        elif rec.ks_chart_sub_groupby_type == 'relational_type':
                                            if res[ks_chart_groupby_relation_fields[1]] is not False:
                                                labels.append(res[ks_chart_groupby_relation_fields[1]][1]._value
                                                              + " " + ress.field_description)
                                            else:
                                                labels.append(str(res[ks_chart_groupby_relation_fields[1]])
                                                              + " " +ress.field_description)
                                        elif rec.ks_chart_sub_groupby_type == 'other':
                                            if res[ks_chart_groupby_relation_fields[1]] is not False:
                                                labels.append(str(res[ks_chart_groupby_relation_fields[1]])
                                                          + "\'s " + ress.field_description)
                                            else:
                                                labels.append(str(res[ks_chart_groupby_relation_fields[1]])
                                                              + " " +ress.field_description)

                                        value.append(res.get(
                                            ress.name,0))

                                    if rec.ks_chart_measure_field_2 and rec.ks_dashboard_item_type == 'ks_bar_chart':
                                        for ress in rec.ks_chart_measure_field_2:
                                            if rec.ks_chart_sub_groupby_type == 'date_type':
                                                if res[ks_chart_groupby_relation_fields[1]] is not False:
                                                    labels_2.append(
                                                        res[ks_chart_groupby_relation_fields[1]].split(" ")[0] + " "
                                                        + ress.field_description)
                                                else:
                                                    labels_2.append(str(res[ks_chart_groupby_relation_fields[1]]) +
                                                                    " " + ress.field_description)
                                            elif rec.ks_chart_sub_groupby_type == 'selection':
                                                selection = res[ks_chart_groupby_relation_fields[1]]
                                                labels_2.append(dict(self.env[rec.ks_model_name].fields_get(
                                                    allfields=[ks_chart_groupby_relation_fields[1]])
                                                                     [ks_chart_groupby_relation_fields[1]][
                                                                         'selection'])[
                                                                    selection] + " " + ress.field_description)
                                            elif rec.ks_chart_sub_groupby_type == 'relational_type':
                                                if res[ks_chart_groupby_relation_fields[1]] is not False:
                                                    labels_2.append(
                                                        res[ks_chart_groupby_relation_fields[1]][1]._value + " " +
                                                        ress.field_description)
                                                else:
                                                    labels_2.append(str(res[ks_chart_groupby_relation_fields[1]]) +
                                                                     " " + ress.field_description)
                                            elif rec.ks_chart_sub_groupby_type == 'other':
                                                labels_2.append(str(
                                                    res[ks_chart_groupby_relation_fields[1]]) + " " +
                                                                ress.field_description)

                                            value_2.append(res.get(
                                                ress.name,0))

                                        chart_sub_data.append({
                                            'value': value_2,
                                            'labels': label,
                                            'series': labels_2,
                                            'domain': domain,
                                        })
                                else:
                                    if rec.ks_chart_sub_groupby_type == 'date_type':
                                        if res[ks_chart_groupby_relation_fields[1]] is not False:
                                            labels.append(res[ks_chart_groupby_relation_fields[1]].split(" ")[0])
                                        else:
                                            labels.append(str(res[ks_chart_groupby_relation_fields[1]]))
                                    elif rec.ks_chart_sub_groupby_type == 'selection':
                                        selection = res[ks_chart_groupby_relation_fields[1]]
                                        labels.append(dict(self.env[rec.ks_model_name].fields_get(
                                            allfields=[ks_chart_groupby_relation_fields[1]])
                                                           [ks_chart_groupby_relation_fields[1]]['selection'])[
                                                          selection])
                                    elif rec.ks_chart_sub_groupby_type == 'relational_type':
                                        if res[ks_chart_groupby_relation_fields[1]] is not False:
                                            labels.append(res[ks_chart_groupby_relation_fields[1]][1]._value)
                                        else:
                                            labels.append(str(res[ks_chart_groupby_relation_fields[1]]))
                                    elif rec.ks_chart_sub_groupby_type == 'other':
                                        labels.append(res[ks_chart_groupby_relation_fields[1]])
                                    value.append(res['__count'])

                                chart_data.append({
                                    'value': value,
                                    'labels': label,
                                    'series': labels,
                                    'domain': domain,
                                })

                        xlabels = []
                        series = []
                        values = {}
                        domains = {}
                        for data in chart_data:
                            label = data['labels']
                            serie = data['series']
                            domain = data['domain']

                            if (len(xlabels) == 0) or (label not in xlabels):
                                xlabels.append(label)

                            if (label not in domains):
                                domains[label] = domain
                            else:
                                domains[label].insert(0, '|')
                                domains[label] = domains[label] + domain

                            series = series + serie
                            value = data['value']
                            counter = 0
                            for seri in serie:
                                if seri not in values:
                                    values[seri] = {}
                                if label in values[seri]:
                                    values[seri][label] = values[seri][label] + value[counter]
                                else:
                                    values[seri][label] = value[counter]
                                counter += 1

                        final_datasets = []
                        for serie in series:
                            if serie not in final_datasets:
                                final_datasets.append(serie)

                        ks_data = []
                        for dataset in final_datasets:
                            ks_dataset = {
                                'value': [],
                                'key': dataset
                            }
                            for label in xlabels:
                                ks_dataset['value'].append({
                                    'domain': domains[label],
                                    'x': label,
                                    'y': values[dataset][label] if label in values[dataset] else 0
                                })
                            ks_data.append(ks_dataset)

                        if rec.ks_chart_relation_sub_groupby.name == rec.ks_chart_relation_groupby.name == rec.ks_sort_by_field.name:
                            ks_data = rec.ks_sort_sub_group_by_records(ks_data, rec.ks_chart_groupby_type,
                                                                       rec.ks_chart_date_groupby, rec.ks_sort_by_order,
                                                                       rec.ks_chart_date_sub_groupby)

                        ks_chart_data = {
                            'labels': [],
                            'datasets': [],
                            'domains': [],
                            'ks_selection': "",
                            'ks_currency': 0,
                            'ks_field': "",
                            'previous_domain': ks_chart_domain
                        }

                        if rec.ks_unit and rec.ks_unit_selection == 'monetary':
                            ks_chart_data['ks_selection'] += rec.ks_unit_selection
                            ks_chart_data['ks_currency'] += rec.env.user.company_id.currency_id.id
                        elif rec.ks_unit and rec.ks_unit_selection == 'custom':
                            ks_chart_data['ks_selection'] += rec.ks_unit_selection
                            if rec.ks_chart_unit:
                                ks_chart_data['ks_field'] += rec.ks_chart_unit

                        if len(ks_data) != 0:
                            for res in ks_data[0]['value']:
                                ks_chart_data['labels'].append(res['x'])
                                ks_chart_data['domains'].append(res['domain'])
                            if rec.ks_chart_measure_field_2 and rec.ks_dashboard_item_type == 'ks_bar_chart':
                                ks_chart_data['ks_show_second_y_scale'] = True
                                values_2 = {}
                                series_2 = []
                                for data in chart_sub_data:
                                    label = data['labels']
                                    serie = data['series']
                                    series_2 = series_2 + serie
                                    value = data['value']

                                    counter = 0
                                    for seri in serie:
                                        if seri not in values_2:
                                            values_2[seri] = {}
                                        if label in values_2[seri]:
                                            values_2[seri][label] = values_2[seri][label] + value[counter]
                                        else:
                                            values_2[seri][label] = value[counter]
                                        counter += 1
                                final_datasets_2 = []
                                for serie in series_2:
                                    if serie not in final_datasets_2:
                                        final_datasets_2.append(serie)
                                ks_data_2 = []
                                for dataset in final_datasets_2:
                                    ks_dataset = {
                                        'value': [],
                                        'key': dataset
                                    }
                                    for label in xlabels:
                                        ks_dataset['value'].append({
                                            'x': label,
                                            'y': values_2[dataset][label] if label in values_2[dataset] else 0
                                        })
                                    ks_data_2.append(ks_dataset)

                                for ks_dat in ks_data_2:
                                    dataset = {
                                        'label': ks_dat['key'],
                                        'data': [],
                                        'type': 'line',
                                        'yAxisID': 'y-axis-1'

                                    }
                                    for res in ks_dat['value']:
                                        dataset['data'].append(res['y'])

                                    ks_chart_data['datasets'].append(dataset)
                            for ks_dat in ks_data:
                                dataset = {
                                    'label': ks_dat['key'],
                                    'data': []
                                }
                                for res in ks_dat['value']:
                                    dataset['data'].append(res['y'])

                                ks_chart_data['datasets'].append(dataset)

                            if rec.ks_goal_enable and rec.ks_standard_goal_value and rec.ks_dashboard_item_type in [
                                'ks_bar_chart', 'ks_line_chart', 'ks_area_chart', 'ks_horizontalBar_chart']:
                                goal_dataset = []
                                length = len(ks_chart_data['datasets'][0]['data'])
                                for i in range(length):
                                    goal_dataset.append(rec.ks_standard_goal_value)
                                ks_goal_datasets = {
                                    'label': 'Target',
                                    'data': goal_dataset,
                                }
                                if rec.ks_goal_bar_line and rec.ks_dashboard_item_type != 'ks_horizontalBar_chart':
                                    ks_goal_datasets['type'] = 'line'
                                    ks_chart_data['datasets'].insert(0, ks_goal_datasets)
                                else:
                                    ks_chart_data['datasets'].append(ks_goal_datasets)
                    else:
                        ks_chart_data = False

                rec.ks_chart_data = json.dumps(ks_chart_data)
            elif not rec.ks_dashboard_item_type or rec.ks_dashboard_item_type == 'ks_tile':
                rec.ks_chart_measure_field = False
                rec.ks_chart_measure_field_2 = False
                rec.ks_chart_relation_groupby = False

    @api.multi
    @api.depends('ks_domain', 'ks_dashboard_item_type', 'ks_model_id', 'ks_sort_by_field', 'ks_sort_by_order',
                 'ks_record_data_limit', 'ks_list_view_fields', 'ks_list_view_type', 'ks_list_view_group_fields',
                 'ks_chart_groupby_type', 'ks_chart_date_groupby', 'ks_date_filter_field', 'ks_item_end_date',
                 'ks_item_start_date', 'ks_compare_period', 'ks_year_period', 'ks_list_target_deviation_field',
                 'ks_goal_enable', 'ks_standard_goal_value', 'ks_goal_lines', 'ks_domain_extension')
    def ks_get_list_view_data(self):
        for rec in self:
            if rec.ks_list_view_type and rec.ks_dashboard_item_type and rec.ks_dashboard_item_type == 'ks_list_view' and \
                    rec.ks_model_id:
                ks_list_view_data = {'label': [],
                                     'data_rows': [], 'model': rec.ks_model_name, 'fields_type': []}

                ks_chart_domain = self.ks_convert_into_proper_domain(rec.ks_domain, rec)
                orderby = rec.ks_sort_by_field.name if rec.ks_sort_by_field else "id"
                if rec.ks_sort_by_order:
                    orderby = orderby + " " + rec.ks_sort_by_order
                limit = rec.ks_record_data_limit if rec.ks_record_data_limit and rec.ks_record_data_limit > 0 else False

                if rec.ks_list_view_type == "ungrouped":
                    if rec.ks_list_view_fields:
                        ks_list_view_data = rec.ks_fetch_list_view_data(rec)

                elif rec.ks_list_view_type == "grouped" and rec.ks_list_view_group_fields and rec.ks_chart_relation_groupby:
                    ks_list_fields = []

                    if rec.ks_chart_groupby_type == 'relational_type':
                        ks_list_view_data['list_view_type'] = 'relational_type'
                        ks_list_view_data['groupby'] = rec.ks_chart_relation_groupby.name
                        ks_list_fields.append(rec.ks_chart_relation_groupby.name)
                        ks_list_view_data['label'].append(rec.ks_chart_relation_groupby.field_description)
                        ks_list_view_data['fields_type'].append(self.ks_chart_relation_groupby.ttype)
                        for res in rec.ks_list_view_group_fields:
                            ks_list_fields.append(res.name)
                            ks_list_view_data['label'].append(res.field_description)
                            ks_list_view_data['fields_type'].append(res.ttype)

                        ks_list_view_records = self.env[rec.ks_model_name].read_group(ks_chart_domain, ks_list_fields,
                                                                                      [rec.ks_chart_relation_groupby.name],
                                                                                      orderby=orderby, limit=limit)
                        for res in ks_list_view_records:
                            if all(list_fields in res for list_fields in ks_list_fields) and res[
                                rec.ks_chart_relation_groupby.name]:
                                counter = 0
                                data_row = {'id': res[rec.ks_chart_relation_groupby.name][0], 'data': [],
                                            'domain': json.dumps(res['__domain'])}
                                for field_rec in ks_list_fields:
                                    if counter == 0:
                                        data_row['data'].append(res[field_rec][1]._value)
                                    else:
                                        data_row['data'].append(res[field_rec])
                                    counter += 1
                                ks_list_view_data['data_rows'].append(data_row)

                    elif rec.ks_chart_groupby_type == 'date_type' and rec.ks_chart_date_groupby:
                        ks_list_view_data['list_view_type'] = 'date_type'
                        ks_list_field = []
                        ks_chart_date_groupby = rec.ks_chart_date_groupby
                        if rec.ks_chart_date_groupby == 'month_year':
                            ks_chart_date_groupby = 'month'
                        ks_list_view_data[
                            'groupby'] = rec.ks_chart_relation_groupby.name + ':' + ks_chart_date_groupby
                        ks_list_field.append(rec.ks_chart_relation_groupby.name)
                        ks_list_fields.append(rec.ks_chart_relation_groupby.name + ':' + ks_chart_date_groupby)
                        ks_list_view_data['label'].append(
                            rec.ks_chart_relation_groupby.field_description + ' : ' + ks_chart_date_groupby.capitalize())
                        ks_list_view_data['fields_type'].append(self.ks_chart_relation_groupby.ttype)
                        for res in rec.ks_list_view_group_fields:
                            ks_list_fields.append(res.name)
                            ks_list_field.append(res.name)
                            ks_list_view_data['label'].append(res.field_description)
                            ks_list_view_data['fields_type'].append(res.ttype)

                        list_target_deviation_field = []
                        if rec.ks_goal_enable and rec.ks_list_target_deviation_field:
                            list_target_deviation_field.append(rec.ks_list_target_deviation_field.name)
                            if rec.ks_list_target_deviation_field.name in ks_list_field:
                                ks_list_field.remove(rec.ks_list_target_deviation_field.name)
                                ks_list_fields.remove(rec.ks_list_target_deviation_field.name)
                                ks_list_view_data['label'].remove(rec.ks_list_target_deviation_field.field_description)

                        ks_list_view_records = self.env[rec.ks_model_name].read_group(ks_chart_domain,
                                                                                      ks_list_field
                                                                                      + list_target_deviation_field,
                                                                              [rec.ks_chart_relation_groupby.name + ':'
                                                                               + ks_chart_date_groupby],
                                                                                      orderby=orderby, limit=limit)
                        if all(list_fields in res for res in ks_list_view_records for list_fields in
                               ks_list_fields + list_target_deviation_field):
                            for res in ks_list_view_records:
                                counter = 0
                                data_row = {'id': 0, 'data': [], 'domain': json.dumps(res['__domain'])}
                                for field_rec in ks_list_fields:
                                    data_row['data'].append(res[field_rec])
                                ks_list_view_data['data_rows'].append(data_row)

                            if rec.ks_goal_enable:
                                ks_list_labels = []
                                ks_list_view_data['label'].append("Target")

                                if rec.ks_list_target_deviation_field:
                                    ks_list_view_data['label'].append(rec.ks_list_target_deviation_field.field_description)
                                    ks_list_view_data['label'].append("Achievement")
                                    ks_list_view_data['label'].append("Deviation")

                                for res in ks_list_view_records:
                                    ks_list_labels.append(res[ks_list_view_data['groupby']])
                                ks_list_view_data2 = rec.get_target_list_view_data(ks_list_view_records, rec,
                                                                                   ks_list_fields,
                                                                                   ks_list_view_data['groupby'],
                                                                                   list_target_deviation_field,
                                                                                   ks_chart_domain)
                                ks_list_view_data['data_rows'] = ks_list_view_data2['data_rows']

                    elif rec.ks_chart_groupby_type == 'selection':
                        ks_list_view_data['list_view_type'] = 'selection'
                        ks_list_view_data['groupby'] = rec.ks_chart_relation_groupby.name
                        ks_selection_field = rec.ks_chart_relation_groupby.name
                        ks_list_view_data['label'].append(rec.ks_chart_relation_groupby.field_description)
                        ks_list_view_data['fields_type'].append(self.ks_chart_relation_groupby.ttype)
                        for res in rec.ks_list_view_group_fields:
                            ks_list_fields.append(res.name)
                            ks_list_view_data['label'].append(res.field_description)
                            ks_list_view_data['fields_type'].append(res.ttype)

                        ks_list_view_records = self.env[rec.ks_model_name].read_group(ks_chart_domain, ks_list_fields,
                                                                                      [
                                                                                          rec.ks_chart_relation_groupby.name],
                                                                                      orderby=orderby, limit=limit)
                        for res in ks_list_view_records:
                            if all(list_fields in res for list_fields in ks_list_fields):
                                counter = 0
                                data_row = {'id': 0, 'data': [], 'domain': json.dumps(res['__domain'])}
                                if res[ks_selection_field]:
                                    data_row['data'].append(dict(
                                    self.env[rec.ks_model_name].fields_get(allfields=ks_selection_field)
                                    [ks_selection_field]['selection'])[res[ks_selection_field]])
                                else:
                                    data_row['data'].append(" ")
                                for field_rec in ks_list_fields:
                                    data_row['data'].append(res[field_rec])
                                ks_list_view_data['data_rows'].append(data_row)

                    elif rec.ks_chart_groupby_type == 'other':
                        ks_list_view_data['list_view_type'] = 'other'
                        ks_list_view_data['groupby'] = rec.ks_chart_relation_groupby.name
                        ks_list_fields.append(rec.ks_chart_relation_groupby.name)
                        ks_list_view_data['label'].append(rec.ks_chart_relation_groupby.field_description)
                        ks_list_view_data['fields_type'].append(self.ks_chart_relation_groupby.ttype)
                        for res in rec.ks_list_view_group_fields:
                            if rec.ks_chart_relation_groupby.name!= res.name:
                                ks_list_fields.append(res.name)
                                ks_list_view_data['label'].append(res.field_description)
                                ks_list_view_data['fields_type'].append(res.ttype)

                        ks_list_view_records = self.env[rec.ks_model_name].read_group(ks_chart_domain, ks_list_fields,
                                                                                      [
                                                                                          rec.ks_chart_relation_groupby.name],
                                                                                      orderby=orderby, limit=limit)
                        for res in ks_list_view_records:
                            if all(list_fields in res for list_fields in ks_list_fields):
                                counter = 0
                                data_row = {'id': 0, 'data': [],'domain': json.dumps(res['__domain'])}

                                for field_rec in ks_list_fields:
                                    if counter == 0:
                                        data_row['data'].append(res[field_rec])
                                    else:
                                        if rec.ks_chart_relation_groupby.name == field_rec:
                                            data_row['data'].append(res[field_rec] * res[field_rec + '_count'])
                                        else:
                                            data_row['data'].append(res[field_rec])
                                    counter += 1
                                ks_list_view_data['data_rows'].append(data_row)

                rec.ks_list_view_data = json.dumps(ks_list_view_data)
            else:
                rec.ks_list_view_data = False

    def get_target_list_view_data(self, ks_list_view_records, rec, ks_list_fields, ks_group_by,
                                  target_deviation_field, ks_chart_domain):
        ks_list_view_data = {}
        ks_list_labels = []
        ks_list_records = {}
        ks_domains = {}
        for res in ks_list_view_records:
            ks_list_labels.append(res[ks_group_by])
            ks_domains[res[ks_group_by]] = res['__domain']
            ks_list_records[res[ks_group_by]] = {'measure_field': [], 'deviation_value': 0.0}
            ks_list_records[res[ks_group_by]]['measure_field'] = []
            for fields in ks_list_fields[1:]:
                ks_list_records[res[ks_group_by]]['measure_field'].append(res[fields])
            for field in target_deviation_field:
                ks_list_records[res[ks_group_by]]['deviation'] = res[field]

        if rec._context.get('current_id', False):
            ks_item_id = rec._context['current_id']
        else:
            ks_item_id = rec.id

        if rec.ks_date_filter_selection_2 == "l_none":
            selected_start_date = rec._context.get('ksDateFilterStartDate', False)
            selected_end_date = rec._context.get('ksDateFilterEndDate', False)
        else:
            selected_start_date = rec.ks_item_start_date
            selected_end_date = rec.ks_item_end_date

        ks_goal_domain = [('ks_dashboard_item', '=', ks_item_id)]

        if selected_start_date and selected_end_date:
            ks_goal_domain.extend([('ks_goal_date', '>=', selected_start_date.strftime("%Y-%m-%d")),
                                   ('ks_goal_date', '<=', selected_end_date.strftime("%Y-%m-%d"))])

        ks_date_data = rec.ks_get_start_end_date(rec.ks_model_name, rec.ks_chart_relation_groupby.name,
                                                 rec.ks_chart_relation_groupby.ttype,
                                                 ks_chart_domain,
                                                 ks_goal_domain)

        labels = []
        ks_chart_date_groupby = rec.ks_chart_date_groupby
        if rec.ks_chart_date_groupby == 'month_year':
            ks_chart_date_groupby = 'month'
        if ks_date_data['start_date'] and ks_date_data['end_date'] and rec.ks_goal_lines:
            labels = self.generate_timeserise(ks_date_data['start_date'], ks_date_data['end_date'],
                                              ks_chart_date_groupby)
        ks_goal_records = self.env['ks_dashboard_ninja.item_goal'].read_group(
            ks_goal_domain, ['ks_goal_value'],
            ['ks_goal_date' + ":" + ks_chart_date_groupby], )

        ks_goal_labels = []
        ks_goal_dataset = {}
        ks_list_view_data['data_rows'] = []
        if rec.ks_goal_lines and len(rec.ks_goal_lines) != 0:
            ks_goal_domains = {}
            for res in ks_goal_records:
                if res['ks_goal_date' + ":" + ks_chart_date_groupby]:
                    ks_goal_labels.append(res['ks_goal_date' + ":" + ks_chart_date_groupby])
                    ks_goal_dataset[res['ks_goal_date' + ":" + ks_chart_date_groupby]] = res['ks_goal_value']
                    ks_goal_domains[res['ks_goal_date' + ":" + ks_chart_date_groupby]] = res['__domain']

            for goal_domain in ks_goal_domains.keys():
                ks_goal_doamins = []
                for item in ks_goal_domains[goal_domain]:

                    if 'ks_goal_date' in item:
                        domain = list(item)
                        domain[0] = ks_group_by.split(":")[0]
                        domain = tuple(domain)
                        ks_goal_doamins.append(domain)
                ks_goal_doamins.insert(0, '&')
                ks_goal_domains[goal_domain] = ks_goal_doamins

            ks_chart_records_dates = ks_list_labels + list(
                set(ks_goal_labels) - set(ks_list_labels))

            ks_list_labels_dates = []
            for label in labels:
                if label in ks_chart_records_dates:
                    ks_list_labels_dates.append(label)

            for label in ks_list_labels_dates:
                data_rows = {'data': [label]}
                data = ks_list_records.get(label, False)
                if data:
                    data_rows['data'] = data_rows['data'] + data['measure_field']
                    data_rows['domain'] = json.dumps(ks_domains[label])
                else:
                    for fields in ks_list_fields[1:]:
                        data_rows['data'].append(0.0)
                    data_rows['domain'] = json.dumps(ks_goal_domains[label])

                target_value = (ks_goal_dataset.get(label, 0.0))
                data_rows['data'].append(target_value)

                for field in target_deviation_field:
                    if data:
                        data_rows['data'].append(data['deviation'])
                        value = data['deviation']
                    else:
                        data_rows['data'].append(0.0)
                        value = 0
                    if target_value:
                        acheivement = round(((value) / target_value) * 100)
                        acheivement = str(acheivement) + "%"
                    else:
                        acheivement = ""
                    deviation = (value - target_value)

                    data_rows['data'].append(acheivement)
                    data_rows['data'].append(deviation)

                ks_list_view_data['data_rows'].append(data_rows)

        else:
            for res in ks_list_view_records:
                if all(list_fields in res for list_fields in ks_list_fields):
                    counter = 0
                    data_row = {'id': 0, 'data': [],}
                    for field_rec in ks_list_fields:
                        data_row['data'].append(res[field_rec])
                    data_row['data'].append(rec.ks_standard_goal_value)
                    data_row['domain'] = json.dumps(res['__domain'])
                    for field in target_deviation_field:
                        value = res[field]
                        data_row['data'].append(res[field])
                        target_value = rec.ks_standard_goal_value

                        if target_value:
                            acheivement = round(((value) / target_value) * 100)
                            acheivement = str(acheivement) + "%"
                        else:
                            acheivement = ""

                        deviation = (value - target_value)
                        data_row['data'].append(acheivement)
                        data_row['data'].append(deviation)
                    ks_list_view_data['data_rows'].append(data_row)

        return ks_list_view_data

    @api.model
    def ks_fetch_list_view_data(self, rec,  limit=15, offset=0):
        ks_list_view_data = {'label': [],
                             'data_rows': [], 'model': rec.ks_model_name, 'fields_type': []}

        ks_chart_domain = rec.ks_convert_into_proper_domain(rec.ks_domain, rec)
        orderby = rec.ks_sort_by_field.name if rec.ks_sort_by_field else "id"
        if rec.ks_sort_by_order:
            orderby = orderby + " " + rec.ks_sort_by_order
        ks_limit = rec.ks_record_data_limit if rec.ks_record_data_limit and rec.ks_record_data_limit > 0 else False

        if ks_limit:
            ks_limit = ks_limit - offset
            if ks_limit  < 15:
                limit = ks_limit
            else:
                limit = 15
        if rec.ks_list_view_fields:
            ks_list_view_data['list_view_type'] = 'other'
            ks_list_view_data['groupby'] = False
            ks_list_view_data['label'] = []
            ks_list_view_data['date_index'] = []
            for res in rec.ks_list_view_fields:
                if (res.ttype == "datetime" or res.ttype == "date"):
                    index = len(ks_list_view_data['label'])
                    ks_list_view_data['label'].append(res.field_description)
                    ks_list_view_data['date_index'].append(index)
                    ks_list_view_data['fields_type'].append(res.ttype)
                else:
                    ks_list_view_data['label'].append(res.field_description)
                    ks_list_view_data['fields_type'].append(res.ttype)

            ks_list_view_fields = [res.name for res in rec.ks_list_view_fields]
            ks_list_view_field_type = [res.ttype for res in rec.ks_list_view_fields]
        try:
            ks_list_view_records = self.env[rec.ks_model_name].search_read(ks_chart_domain,
                                                                       ks_list_view_fields,
                                                                       order=orderby, limit=limit, offset=offset)
        except Exception as e:
            ks_list_view_data = False
            return ks_list_view_data
        for res in ks_list_view_records:
            counter = 0
            data_row = {'id': res['id'], 'data': []}
            for field_rec in ks_list_view_fields:
                if type(res[field_rec]) == fields.datetime or type(res[field_rec]) == fields.date:
                    res[field_rec] = res[field_rec].strftime("%D %T")
                elif ks_list_view_field_type[counter] == "many2one":
                    if res[field_rec]:
                        res[field_rec] = res[field_rec][1]
                data_row['data'].append(res[field_rec])
                counter += 1
            ks_list_view_data['data_rows'].append(data_row)

        return ks_list_view_data

    @api.onchange('ks_dashboard_item_type')
    def set_color_palette(self):
        for rec in self:
            if rec.ks_dashboard_item_type == "ks_bar_chart" or rec.ks_dashboard_item_type == "ks_horizontalBar_chart" or rec.ks_dashboard_item_type == "ks_line_chart" or rec.ks_dashboard_item_type == "ks_area_chart":
                rec.ks_chart_item_color = "cool"
            else:
                rec.ks_chart_item_color = "default"

    #  Time Filter Calculation
    @api.multi
    @api.onchange('ks_date_filter_selection')
    def ks_set_date_filter(self):
        for rec in self:
            if (not rec.ks_date_filter_selection) or rec.ks_date_filter_selection == "l_none":
                rec.ks_item_start_date = rec.ks_item_end_date = False
            elif rec.ks_date_filter_selection != 'l_custom':
                ks_date_data = ks_get_date(rec.ks_date_filter_selection, self,
                                           rec.ks_date_filter_field.ttype)
                rec.ks_item_start_date = ks_date_data["selected_start_date"]
                rec.ks_item_end_date = ks_date_data["selected_end_date"]

    @api.multi
    @api.depends('ks_dashboard_item_type', 'ks_goal_enable', 'ks_standard_goal_value', 'ks_record_count',
                 'ks_record_count_2', 'ks_previous_period', 'ks_compare_period', 'ks_year_period',
                 'ks_compare_period_2', 'ks_year_period_2')
    def ks_get_kpi_data(self):
        for rec in self:
            if rec.ks_dashboard_item_type and rec.ks_dashboard_item_type == 'ks_kpi' and rec.ks_model_id:
                ks_kpi_data = []
                ks_record_count = 0.0
                ks_kpi_data_model_1 = {}
                ks_record_count = rec.ks_record_count
                ks_kpi_data_model_1['model'] = rec.ks_model_name
                ks_kpi_data_model_1['record_field'] = rec.ks_record_field.field_description
                ks_kpi_data_model_1['record_data'] = ks_record_count

                if rec.ks_goal_enable:
                    ks_kpi_data_model_1['target'] = rec.ks_standard_goal_value
                ks_kpi_data.append(ks_kpi_data_model_1)

                if rec.ks_previous_period:
                    ks_previous_period_data = rec.ks_get_previous_period_data(rec)
                    ks_kpi_data_model_1['previous_period'] = ks_previous_period_data

                if rec.ks_model_id_2 and rec.ks_record_count_type_2:
                    ks_kpi_data_model_2 = {}
                    ks_kpi_data_model_2['model'] = rec.ks_model_name_2
                    ks_kpi_data_model_2[
                        'record_field'] = 'count' if rec.ks_record_count_type_2 == 'count' else rec.ks_record_field_2.field_description
                    ks_kpi_data_model_2['record_data'] = rec.ks_record_count_2
                    ks_kpi_data.append(ks_kpi_data_model_2)

                rec.ks_kpi_data = json.dumps(ks_kpi_data)
            else:
                rec.ks_kpi_data = False

    # writing separate function for fetching previous period data
    def ks_get_previous_period_data(self, rec):
        switcher = {
            'l_day': 'ls_day',
            't_week': 'ls_week',
            't_month': 'ls_month',
            't_quarter': 'ls_quarter',
            't_year': 'ls_year',
        }
        ks_previous_period = False
        ks_date_data = False
        if rec.ks_date_filter_selection == "l_none":
            date_filter_selection = rec.ks_dashboard_ninja_board_id.ks_date_filter_selection
        else:
            date_filter_selection = rec.ks_date_filter_selection
            ks_previous_period = switcher.get(date_filter_selection, False)
        if ks_previous_period:
            ks_date_data = ks_get_date(ks_previous_period, self, self.ks_date_filter_field.ttype)

        if (ks_date_data):
            previous_period_start_date = ks_date_data["selected_start_date"]
            previous_period_end_date = ks_date_data["selected_end_date"]
            proper_domain = rec.ks_get_previous_period_domain(rec.ks_domain, previous_period_start_date,
                                                              previous_period_end_date, rec.ks_date_filter_field)
            ks_record_count = 0.0

            if rec.ks_record_count_type == 'count':
                ks_record_count = self.env[rec.ks_model_name].search_count(proper_domain)
                return ks_record_count
            elif rec.ks_record_field:
                data = self.env[rec.ks_model_name].read_group(proper_domain, [rec.ks_record_field.name], [])[0]
                if rec.ks_record_count_type == 'sum':
                    return data.get(rec.ks_record_field.name, 0) if data.get('__count', False) and (
                        data.get(rec.ks_record_field.name)) else 0
                else:
                    return data.get(rec.ks_record_field.name, 0) / data.get('__count', 1) if data.get('__count',
                                                                                                      False) and (
                                                                                                 data.get(
                                                                                                     rec.ks_record_field.name)) else 0
            else:
                return False
        else:
            return False

    def ks_get_previous_period_domain(self, ks_domain, ks_start_date, ks_end_date, date_filter_field):
        if ks_domain and "%UID" in ks_domain:
            ks_domain = ks_domain.replace('"%UID"', str(self.env.user.id))
        if ks_domain:
            # try:
            proper_domain = safe_eval(ks_domain)
            if ks_start_date and ks_end_date and date_filter_field:
                proper_domain.extend([(date_filter_field.name, ">=", ks_start_date),
                                      (date_filter_field.name, "<=", ks_end_date)])

        else:
            if ks_start_date and ks_end_date and date_filter_field:
                proper_domain = ([(date_filter_field.name, ">=", ks_start_date),
                                  (date_filter_field.name, "<=", ks_end_date)])
            else:
                proper_domain = []
        return proper_domain

    @api.depends('ks_domain_2', 'ks_model_id_2', 'ks_record_field_2', 'ks_record_count_type_2', 'ks_item_start_date_2',
                 'ks_date_filter_selection_2', 'ks_record_count_type_2', 'ks_compare_period_2', 'ks_year_period_2',
                 'ks_domain_extension_2')
    def ks_get_record_count_2(self):
        for rec in self:
            if rec.ks_record_count_type_2 == 'count':
                ks_record_count = rec.ks_fetch_model_data_2(rec.ks_model_name_2, rec.ks_domain_2, 'search_count', rec)

            elif rec.ks_record_count_type_2 in ['sum', 'average'] and rec.ks_record_field_2:
                ks_records_grouped_data = rec.ks_fetch_model_data_2(rec.ks_model_name_2, rec.ks_domain_2, 'read_group',
                                                                    rec)
                if ks_records_grouped_data and len(ks_records_grouped_data) > 0:
                    ks_records_grouped_data = ks_records_grouped_data[0]
                    if rec.ks_record_count_type_2 == 'sum' and ks_records_grouped_data.get('__count', False) and (
                            ks_records_grouped_data.get(rec.ks_record_field_2.name)):
                        ks_record_count = ks_records_grouped_data.get(rec.ks_record_field_2.name, 0)
                    elif rec.ks_record_count_type_2 == 'average' and ks_records_grouped_data.get(
                            '__count', False) and (ks_records_grouped_data.get(rec.ks_record_field_2.name)):
                        ks_record_count = ks_records_grouped_data.get(rec.ks_record_field_2.name,
                                                                      0) / ks_records_grouped_data.get('__count',
                                                                                                       1)
                    else:
                        ks_record_count = 0
                else:
                    ks_record_count = 0
            else:
                ks_record_count = False

            rec.ks_record_count_2 = ks_record_count

    @api.onchange('ks_model_id_2')
    def make_record_field_empty_2(self):
        for rec in self:
            rec.ks_record_field_2 = False
            rec.ks_domain_2 = False
            rec.ks_date_filter_field_2 = False
            rec.ks_domain_extension_2 = False
            # To show "created on" by default on date filter field on model select.
            if rec.ks_model_id:
                datetime_field_list = rec.ks_date_filter_field_2.search(
                    [('model_id', '=', rec.ks_model_id.id), '|', ('ttype', '=', 'date'),
                     ('ttype', '=', 'datetime')]).read(['id', 'name'])
                for field in datetime_field_list:
                    if field['name'] == 'create_date':
                        rec.ks_date_filter_field_2 = field['id']
            else:
                rec.ks_date_filter_field_2 = False

    # Writing separate function to fetch dashboard item data
    def ks_fetch_model_data_2(self, ks_model_name, ks_domain, ks_func, rec):
        data = 0
        try:
            if ks_domain and ks_domain != '[]' and ks_model_name:
                proper_domain = self.ks_convert_into_proper_domain_2(ks_domain, rec)
                if ks_func == 'search_count':
                    data = self.env[ks_model_name].search_count(proper_domain)
                elif ks_func == 'read_group':
                    data = self.env[ks_model_name].read_group(proper_domain, [rec.ks_record_field_2.name], [])
            elif ks_model_name:
                # Have to put extra if condition here because on load,model giving False value
                proper_domain = self.ks_convert_into_proper_domain_2(False, rec)
                if ks_func == 'search_count':
                    data = self.env[ks_model_name].search_count(proper_domain)

                elif ks_func == 'read_group':
                    data = self.env[ks_model_name].read_group(proper_domain, [rec.ks_record_field_2.name], [])
            else:
                return []
        except Exception as e:
            return []
        return data

    @api.multi
    @api.onchange('ks_date_filter_selection_2')
    def ks_set_date_filter_2(self):
        for rec in self:
            if (not rec.ks_date_filter_selection_2) or rec.ks_date_filter_selection_2 == "l_none":
                rec.ks_item_start_date_2 = rec.ks_item_end_date = False
            elif rec.ks_date_filter_selection_2 != 'l_custom':
                ks_date_data = ks_get_date(rec.ks_date_filter_selection_2, self)
                rec.ks_item_start_date_2 = ks_date_data["selected_start_date"]
                rec.ks_item_end_date_2 = ks_date_data["selected_end_date"]

    def ks_convert_into_proper_domain_2(self, ks_domain_2, rec):

        if ks_domain_2 and "%UID" in ks_domain_2:
            ks_domain_2 = ks_domain_2.replace('"%UID"', str(self.env.user.id))
        if ks_domain_2 and "%MYCOMPANY" in ks_domain_2:
            ks_domain_2 = ks_domain_2.replace('"%MYCOMPANY"', str(self.env.user.company_id.id))

        ks_date_domain = False

        if not rec.ks_date_filter_selection_2 or rec.ks_date_filter_selection_2 == "l_none":
            selected_start_date = self._context.get('ksDateFilterStartDate', False)
            selected_end_date = self._context.get('ksDateFilterEndDate', False)
            ks_is_def_custom_filter = self._context.get('ksIsDefultCustomDateFilter', False)
            ks_timezone = self._context.get('tz') or self.env.user.tz
            if selected_start_date and selected_end_date and rec.ks_date_filter_field_2.ttype == 'datetime' and not ks_is_def_custom_filter:
                selected_start_date = ks_convert_into_utc(selected_start_date, ks_timezone)
                selected_end_date = ks_convert_into_utc(selected_end_date, ks_timezone)
            if selected_start_date and selected_end_date and rec.ks_date_filter_field_2.ttype == 'date' and ks_is_def_custom_filter:
                selected_start_date = ks_convert_into_local(selected_start_date, ks_timezone)
                selected_end_date = ks_convert_into_local(selected_end_date, ks_timezone)
            if self._context.get('ksDateFilterSelection', False) and self._context['ksDateFilterSelection'] not in [
                'l_none', 'l_custom']:
                ks_date_data = ks_get_date(self._context.get('ksDateFilterSelection'), self,
                                           rec.ks_date_filter_field_2.ttype)
                selected_start_date = ks_date_data["selected_start_date"]
                selected_end_date = ks_date_data["selected_end_date"]

            if selected_end_date and not selected_start_date:
                ks_date_domain = [
                    (rec.ks_date_filter_field_2.name, "<=",
                     selected_end_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
            elif selected_start_date and not selected_end_date:
                ks_date_domain = [
                    (rec.ks_date_filter_field_2.name, ">=",
                     selected_start_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
            else:
                if selected_end_date and selected_start_date:
                    ks_date_domain = [
                        (rec.ks_date_filter_field_2.name, ">=",
                         selected_start_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                        (rec.ks_date_filter_field_2.name, "<=",
                         selected_end_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
                    ]
        else:
            if rec.ks_date_filter_selection_2 and rec.ks_date_filter_selection_2 != 'l_custom':
                ks_date_data = ks_get_date(rec.ks_date_filter_selection_2, self, rec.ks_date_filter_field_2.ttype)
                selected_start_date = ks_date_data["selected_start_date"]
                selected_end_date = ks_date_data["selected_end_date"]
            else:
                selected_start_date = False
                selected_end_date = False
                if rec.ks_item_start_date_2 or rec.ks_item_end_date_2:
                    selected_start_date = rec.ks_item_start_date
                    selected_end_date = rec.ks_item_end_date
                    if rec.ks_date_filter_field_2.ttype == 'date' and rec.ks_item_start_date_2 and rec.ks_item_end_date_2:
                        ks_timezone = self._context.get('tz') or self.env.user.tz
                        selected_start_date = ks_convert_into_local(rec.ks_item_start_date_2, ks_timezone)
                        selected_end_date = ks_convert_into_local(rec.ks_item_end_date_2, ks_timezone)

            if selected_start_date and selected_end_date:
                if rec.ks_compare_period_2:
                    ks_compare_period_2 = abs(rec.ks_compare_period_2)
                    if ks_compare_period_2 > 100:
                        ks_compare_period_2 = 100
                    if rec.ks_compare_period_2 > 0:
                        selected_end_date = selected_end_date + (
                                selected_end_date - selected_start_date) * ks_compare_period_2
                    elif rec.ks_compare_period_2 < 0:
                        selected_start_date = selected_start_date - (
                                selected_end_date - selected_start_date) * ks_compare_period_2

                if rec.ks_year_period_2 and rec.ks_year_period_2 != 0:
                    abs_year_period_2 = abs(rec.ks_year_period_2)
                    sign_yp = rec.ks_year_period_2 / abs_year_period_2
                    if abs_year_period_2 > 100:
                        abs_year_period_2 = 100
                    date_field_name = rec.ks_date_filter_field_2.name

                    ks_date_domain = ['&', (date_field_name, ">=",
                                            fields.datetime.strftime(selected_start_date,
                                                                     DEFAULT_SERVER_DATETIME_FORMAT)),
                                      (date_field_name, "<=",
                                       fields.datetime.strftime(selected_end_date, DEFAULT_SERVER_DATETIME_FORMAT))]

                    for p in range(1, abs_year_period_2 + 1):
                        ks_date_domain.insert(0, '|')
                        ks_date_domain.extend(['&', (date_field_name, ">=", fields.datetime.strftime(
                            selected_start_date - relativedelta.relativedelta(years=p) * sign_yp,
                            DEFAULT_SERVER_DATETIME_FORMAT)),
                                               (date_field_name, "<=", fields.datetime.strftime(
                                                   selected_end_date - relativedelta.relativedelta(
                                                       years=p) * sign_yp,
                                                   DEFAULT_SERVER_DATETIME_FORMAT))])
                else:
                    if rec.ks_date_filter_field_2:
                        selected_start_date = fields.datetime.strftime(selected_start_date,
                                                                       DEFAULT_SERVER_DATETIME_FORMAT)
                        selected_end_date = fields.datetime.strftime(selected_end_date,
                                                                     DEFAULT_SERVER_DATETIME_FORMAT)
                        ks_date_domain = [(rec.ks_date_filter_field_2.name, ">=", selected_start_date),
                                          (rec.ks_date_filter_field_2.name, "<=", selected_end_date)]
                    else:
                        ks_date_domain = []
            elif selected_start_date and rec.ks_date_filter_field_2:
                selected_start_date = fields.datetime.strftime(selected_start_date, DEFAULT_SERVER_DATETIME_FORMAT)
                ks_date_domain = [(rec.ks_date_filter_field_2.name, ">=", selected_start_date)]
            elif selected_end_date and rec.ks_date_filter_field_2:
                selected_end_date = fields.datetime.strftime(selected_end_date, DEFAULT_SERVER_DATETIME_FORMAT)
                ks_date_domain = [(rec.ks_date_filter_field_2.name, "<=", selected_end_date)]

        proper_domain = safe_eval(ks_domain_2) if ks_domain_2 else []
        if ks_date_domain:
            proper_domain.extend(ks_date_domain)
        if rec.ks_domain_extension_2:
            ks_domain_extension = rec.ks_convert_domain_extension(rec.ks_domain_extension_2, rec)
            proper_domain.extend(ks_domain_extension)

        return proper_domain

    def ks_fetch_chart_data(self, ks_model_name, ks_chart_domain,ks_chart_measure_field_with_type,
                            ks_chart_measure_field_with_type_2,
                            ks_chart_measure_field, ks_chart_measure_field_2,
                            ks_chart_groupby_relation_field, ks_chart_date_groupby, ks_chart_groupby_type, orderby,
                            limit, chart_count, ks_chart_measure_field_ids, ks_chart_measure_field_2_ids,
                            ks_chart_groupby_relation_field_id, ks_chart_data):

        if ks_chart_groupby_type == "date_type":
            ks_chart_groupby_field = ks_chart_groupby_relation_field + ":" + ks_chart_date_groupby
        else:
            ks_chart_groupby_field = ks_chart_groupby_relation_field

        try:
            if self.ks_fill_temporal and ks_chart_date_groupby not in ['minute', 'hour']:
                ks_chart_records = self.env[ks_model_name].with_context(fill_temporal=True) \
                    .read_group(ks_chart_domain, list(set(ks_chart_measure_field_with_type + ks_chart_measure_field_with_type_2 +
                                                     [ks_chart_groupby_relation_field])), [ks_chart_groupby_field],
                                orderby=orderby, limit=limit, lazy=False)
            else:
                ks_chart_records = self.env[ks_model_name] \
                    .read_group(ks_chart_domain, list(set(ks_chart_measure_field_with_type + ks_chart_measure_field_with_type_2 +
                                                     [ks_chart_groupby_relation_field])), [ks_chart_groupby_field],
                                orderby=orderby, limit=limit, lazy=False)
        except Exception as e:
            ks_chart_records = []
            pass
        ks_chart_data['groupby'] = ks_chart_groupby_field
        if ks_chart_groupby_type == "relational_type":
            ks_chart_data['groupByIds'] = []

        for res in ks_chart_records:
            is_ks_index = False
            ks_index = False
            if all(measure_field in res for measure_field in ks_chart_measure_field):
                if ks_chart_groupby_type == "relational_type":
                    if res[ks_chart_groupby_field]:
                        ks_chart_data['groupByIds'].append(res[ks_chart_groupby_field][0])
                        label = res[ks_chart_groupby_field][1]._value
                    else:
                        label = res[ks_chart_groupby_field]
                elif ks_chart_groupby_type == "selection":
                    selection = res[ks_chart_groupby_field]
                    if selection:
                        label = dict(self.env[ks_model_name].fields_get(allfields=[ks_chart_groupby_field])
                                 [ks_chart_groupby_field]['selection'])[selection]
                    else:
                        label = selection
                else:
                    label = res[ks_chart_groupby_field]

                ks_chart_data['domains'].append(res.get('__domain', []))
                if label in ks_chart_data['labels']:
                    ks_index = ks_chart_data['labels'].index(label)
                    is_ks_index = True

                else:
                    ks_chart_data['labels'].append(label)

                counter = 0
                if ks_chart_measure_field:
                    if ks_chart_measure_field_2:
                        index = 0
                        for field_rec in ks_chart_measure_field_2:
                            ks_groupby_equal_measures = res.get(ks_chart_groupby_relation_field + "_count", False) or res.get("__count", False)\
                                if res.get(ks_chart_groupby_relation_field + "_count", False) or res.get("__count", False) \
                                   and  ks_chart_measure_field_2_ids[index] == ks_chart_groupby_relation_field_id \
                                else 1
                            try:
                                if res.get('__count', False):
                                    data = res[field_rec] * ks_groupby_equal_measures \
                                        if chart_count == 'sum' else \
                                        res[field_rec]
                                else:
                                    data = 0
                                if is_ks_index:
                                    if chart_count == 'sum':
                                        ks_chart_data['datasets'][counter]['data'][ks_index] += data
                                    else:
                                        ks_chart_data['datasets'][counter]['data'][ks_index] = \
                                            (ks_chart_data['datasets'][counter]['data'][ks_index] + data) / 2
                                    counter += 1
                                    index += 1
                                    continue
                            except ZeroDivisionError:
                                data = 0
                            ks_chart_data['datasets'][counter]['data'].append(data)
                            counter += 1
                            index += 1

                    index = 0
                    for field_rec in ks_chart_measure_field:
                        ks_groupby_equal_measures = res.get(ks_chart_groupby_relation_field + "_count", False) or res.get("__count", False)\
                            if res.get(ks_chart_groupby_relation_field + "_count", False)  or res.get("__count", False)\
                               and  ks_chart_measure_field_ids[index] == ks_chart_groupby_relation_field_id \
                            else 1
                        try:
                            if res.get('__count', False):
                                data = res[field_rec] * ks_groupby_equal_measures \
                                    if chart_count == 'sum' else \
                                    res[field_rec]
                            else:
                                data = 0
                            if is_ks_index:
                                if chart_count == 'sum':
                                    ks_chart_data['datasets'][counter]['data'][ks_index] +=  data
                                else:
                                    ks_chart_data['datasets'][counter]['data'][ks_index] = \
                                        (ks_chart_data['datasets'][counter]['data'][ks_index] + data)/2
                                counter += 1
                                index += 1
                                continue
                        except ZeroDivisionError:
                            data = 0
                        ks_chart_data['datasets'][counter]['data'].append(data)
                        counter += 1
                        index += 1

                else:
                    if res.get('__count'):
                        count = res[ks_chart_groupby_relation_field + "_count"] \
                            if res.get((ks_chart_groupby_relation_field + "_count"), False) else res['__count']
                    else:
                        count = 0
                    data = count
                    ks_chart_data['datasets'][0]['data'].append(data)

        return ks_chart_data

    @api.model
    def ks_fetch_drill_down_data(self, item_id, domain, sequence):

        record = self.browse(int(item_id))
        ks_chart_data = {'labels': [], 'datasets': [], 'ks_show_second_y_scale': False, 'domains': [],
                         'previous_domain': domain, 'ks_currency': 0, 'ks_field': "", 'ks_selection': ""}
        if record.ks_unit and record.ks_unit_selection == 'monetary':
            ks_chart_data['ks_selection'] += record.ks_unit_selection
            ks_chart_data['ks_currency'] += record.env.user.company_id.currency_id.id
        elif record.ks_unit and record.ks_unit_selection == 'custom':
            ks_chart_data['ks_selection'] += record.ks_unit_selection
            if record.ks_chart_unit:
                ks_chart_data['ks_field'] += record.ks_chart_unit

        # If count chart data type:
        action_lines = record.ks_action_lines.sorted(key=lambda r: r.sequence)
        action_line = action_lines[sequence]
        ks_chart_type = action_line.ks_chart_type if action_line.ks_chart_type else record.ks_dashboard_item_type
        ks_list_view_data = {'label': [],
                             'data_rows': [], 'model': record.ks_model_name, 'previous_domain': domain, }
        if action_line.ks_chart_type == 'ks_list_view':
            if record.ks_dashboard_item_type == 'ks_list_view':
                ks_chart_list_measure = record.ks_list_view_group_fields
            else :
                ks_chart_list_measure = record.ks_chart_measure_field

            ks_list_fields = []
            orderby = action_line.ks_sort_by_field.name if action_line.ks_sort_by_field else "id"
            if action_line.ks_sort_by_order:
                orderby = orderby + " " + action_line.ks_sort_by_order
            limit = action_line.ks_record_limit if action_line.ks_record_limit \
                                                   and action_line.ks_record_limit > 0 else False
            ks_count = 0
            for ks in record.ks_action_lines:
                ks_count += 1
            if action_line.ks_item_action_field.ttype == 'many2one':
                ks_list_view_data['groupby'] = action_line.ks_item_action_field.name
                ks_list_fields.append(action_line.ks_item_action_field.name)
                ks_list_view_data['label'].append(action_line.ks_item_action_field.field_description)
                for res in ks_chart_list_measure:
                    ks_list_fields.append(res.name)
                    ks_list_view_data['label'].append(res.field_description)

                ks_list_view_records = self.env[record.ks_model_name].read_group(domain, ks_list_fields,
                                                                                 [action_line.ks_item_action_field.name],
                                                                                 orderby=orderby, limit=limit)
                for res in ks_list_view_records:

                    counter = 0
                    data_row = {'id': res[action_line.ks_item_action_field.name][0] if res[action_line.ks_item_action_field.name] else res[action_line.ks_item_action_field.name] ,
                                'data': [],
                                'domain': json.dumps(res['__domain']), 'sequence': sequence + 1,
                                'last_seq': ks_count}
                    for field_rec in ks_list_fields:
                        if counter == 0:
                            data_row['data'].append(res[field_rec][1]._value if res[field_rec] else "False")
                        else:
                            data_row['data'].append(res[field_rec])
                        counter += 1
                    ks_list_view_data['data_rows'].append(data_row)

            elif action_line.ks_item_action_field.ttype == 'date' or \
                    action_line.ks_item_action_field.ttype == 'datetime':
                ks_list_view_data['list_view_type'] = 'date_type'
                ks_list_field = []
                ks_list_view_data['groupby'] = action_line.ks_item_action_field.name
                ks_list_field.append(action_line.ks_item_action_field.name  + ':' + action_line.ks_item_action_date_groupby)
                ks_list_fields.append(action_line.ks_item_action_field.name)
                ks_list_view_data['label'].append(
                    action_line.ks_item_action_field.field_description)
                for res in ks_chart_list_measure:
                    ks_list_fields.append(res.name)
                    ks_list_field.append(res.name)
                    ks_list_view_data['label'].append(res.field_description)

                ks_list_view_records = self.env[record.ks_model_name].read_group(domain, ks_list_fields,
                                                                                 [action_line.ks_item_action_field.name
                                                                                  + ':' + action_line.ks_item_action_date_groupby],
                                                                                 orderby=orderby, limit=limit)

                for res in ks_list_view_records:
                    counter = 0
                    data_row = { 'data': [],
                                'domain': json.dumps(res['__domain']), 'sequence': sequence + 1,
                                'last_seq': ks_count}
                    for field_rec in ks_list_field:
                        data_row['data'].append(res[field_rec])
                    ks_list_view_data['data_rows'].append(data_row)

            elif action_line.ks_item_action_field.ttype == 'selection':
                ks_list_view_data['list_view_type'] = 'selection'
                ks_list_view_data['groupby'] = action_line.ks_item_action_field.name
                ks_selection_field = action_line.ks_item_action_field.name
                ks_list_view_data['label'].append(action_line.ks_item_action_field.field_description)
                for res in ks_chart_list_measure:
                    ks_list_fields.append(res.name)
                    ks_list_view_data['label'].append(res.field_description)

                ks_list_view_records = self.env[record.ks_model_name].read_group(domain, ks_list_fields,
                                                                                 [
                                                                                     action_line.ks_item_action_field.name],
                                                                                 orderby=orderby, limit=limit)
                for res in ks_list_view_records:
                    counter = 0
                    data_row = { 'data': [],
                                'domain': json.dumps(res['__domain']), 'sequence': sequence + 1,
                                'last_seq': ks_count}
                    if res[ks_selection_field]:
                        data_row['data'].append(dict(
                            self.env[record.ks_model_name].fields_get(allfields=ks_selection_field)
                            [ks_selection_field]['selection'])[res[ks_selection_field]])
                    else:
                        data_row['data'].append(" ")
                    for field_rec in ks_list_fields:
                        data_row['data'].append(res[field_rec])
                    ks_list_view_data['data_rows'].append(data_row)

            else:
                ks_list_view_data['list_view_type'] = 'other'
                ks_list_view_data['groupby'] = action_line.ks_item_action_field.name
                ks_list_fields.append(action_line.ks_item_action_field.name)
                ks_list_view_data['label'].append(action_line.ks_item_action_field.field_description)
                for res in ks_chart_list_measure:
                    ks_list_fields.append(res.name)
                    ks_list_view_data['label'].append(res.field_description)

                ks_list_view_records = self.env[record.ks_model_name].read_group(domain, ks_list_fields,
                                                                                 [
                                                                                     action_line.ks_item_action_field.name],
                                                                                 orderby=orderby, limit=limit)
                for res in ks_list_view_records:
                    if all(list_fields in res for list_fields in ks_list_fields):
                        counter = 0
                        data_row = {'id': action_line.ks_item_action_field.name, 'data': [],
                                    'domain': json.dumps(res['__domain']), 'sequence': sequence + 1,
                                    'last_seq': ks_count}

                        for field_rec in ks_list_fields:
                            if counter == 0:
                                data_row['data'].append(res[field_rec])
                            else:
                                if action_line.ks_item_action_field.name == field_rec:
                                    data_row['data'].append(res[field_rec] * res[field_rec + '_count'])
                                else:
                                    data_row['data'].append(res[field_rec])
                            counter += 1
                        ks_list_view_data['data_rows'].append(data_row)


            return { "ks_list_view_data": json.dumps(ks_list_view_data), "ks_list_view_type": "grouped",
                    'sequence': sequence + 1,}
        else:
            ks_chart_measure_field = []
            ks_chart_measure_field_with_type = []
            ks_chart_measure_field_ids = []
            ks_chart_measure_field_2 = []
            ks_chart_measure_field_with_type_2 = []
            ks_chart_measure_field_2_ids = []
            if record.ks_chart_data_count_type == "count":
                ks_chart_measure_field_with_type.append('count:count(id)')

                ks_chart_data['datasets'].append({'data': [], 'label': "Count"})
            else:
                if ks_chart_type == 'ks_bar_chart':
                    if record.ks_chart_measure_field_2:
                        ks_chart_data['ks_show_second_y_scale'] = True

                    for res in record.ks_chart_measure_field_2:
                        if record.ks_chart_data_count_type == 'sum':
                            ks_data_count_type = 'sum'
                        elif record.ks_chart_data_count_type == 'average':
                            ks_data_count_type = 'avg'
                        else:
                            raise ValidationError(_('Please chose any Data Type!'))
                        ks_chart_measure_field_2.append(res.name)
                        ks_chart_measure_field_with_type_2.append(res.name + ':' + ks_data_count_type)
                        ks_chart_measure_field_2_ids.append(res.id)
                        ks_chart_data['datasets'].append(
                            {'data': [], 'label': res.field_description, 'type': 'line', 'yAxisID': 'y-axis-1'})
                if record.ks_dashboard_item_type == 'ks_list_view':
                    for res in record.ks_list_view_group_fields:
                        ks_chart_measure_field.append(res.name)
                        ks_chart_measure_field_with_type.append(res.name + ':' + 'sum')
                        ks_chart_measure_field_ids.append(res.id)
                        ks_chart_data['datasets'].append({'data': [], 'label': res.field_description})
                else:
                    for res in record.ks_chart_measure_field:
                        if record.ks_chart_data_count_type == 'sum':
                            ks_data_count_type = 'sum'
                        elif record.ks_chart_data_count_type == 'average':
                            ks_data_count_type = 'avg'
                        else:
                            raise ValidationError(_('Please chose any Data Type!'))
                        ks_chart_measure_field.append(res.name)
                        ks_chart_measure_field_with_type.append(res.name + ':' + ks_data_count_type)
                        ks_chart_measure_field_ids.append(res.id)
                        ks_chart_data['datasets'].append({'data': [], 'label': res.field_description})

            ks_chart_groupby_relation_field = action_line.ks_item_action_field.name
            ks_chart_relation_type = action_line.ks_item_action_field_type
            ks_chart_date_group_by = action_line.ks_item_action_date_groupby
            ks_chart_groupby_relation_field_id = action_line.ks_item_action_field.id
            orderby = action_line.ks_sort_by_field.name if action_line.ks_sort_by_field else "id"
            if record.ks_chart_data_count_type == "count" and not self.ks_fill_temporal and not record.ks_sort_by_field:
                orderby = 'count'
            if action_line.ks_sort_by_order:
                orderby = orderby + " " + action_line.ks_sort_by_order
            limit = action_line.ks_record_limit if action_line.ks_record_limit and action_line.ks_record_limit > 0 else False

            if ks_chart_type != "ks_bar_chart":
                ks_chart_measure_field_2 = []
                ks_chart_measure_field_2_ids = []

            ks_chart_data = record.ks_fetch_chart_data(record.ks_model_name, domain,
                                                       ks_chart_measure_field_with_type,
                                                       ks_chart_measure_field_with_type_2,
                                                       ks_chart_measure_field,
                                                       ks_chart_measure_field_2,
                                                       ks_chart_groupby_relation_field, ks_chart_date_group_by,
                                                       ks_chart_relation_type,
                                                       orderby, limit, record.ks_chart_data_count_type,
                                                       ks_chart_measure_field_ids,
                                                       ks_chart_measure_field_2_ids, ks_chart_groupby_relation_field_id,
                                                       ks_chart_data)

            return {
                'ks_chart_data': json.dumps(ks_chart_data),
                'ks_chart_type': ks_chart_type,
                'sequence': sequence + 1,
            }

    @api.model
    def ks_get_start_end_date(self, model_name, ks_chart_groupby_relation_field, ttype, ks_chart_domain,
                              ks_goal_domain):
        ks_start_end_date = {}
        try:
            model_field_start_date = \
                self.env[model_name].search(ks_chart_domain + [(ks_chart_groupby_relation_field, '!=', False)], limit=1,
                                            order=ks_chart_groupby_relation_field + " ASC")[
                    ks_chart_groupby_relation_field]
            model_field_end_date = \
                self.env[model_name].search(ks_chart_domain + [(ks_chart_groupby_relation_field, '!=', False)], limit=1,
                                            order=ks_chart_groupby_relation_field + " DESC")[
                    ks_chart_groupby_relation_field]
        except Exception as e:
            model_field_start_date = model_field_end_date = False
            pass

        goal_model_start_date = \
            self.env['ks_dashboard_ninja.item_goal'].search(ks_goal_domain, limit=1,
                                                            order='ks_goal_date ASC')['ks_goal_date']
        goal_model_end_date = \
            self.env['ks_dashboard_ninja.item_goal'].search(ks_goal_domain, limit=1,
                                                            order='ks_goal_date DESC')['ks_goal_date']

        if model_field_start_date and ttype == "date":
            model_field_end_date = datetime.combine(model_field_end_date, datetime.min.time())
            model_field_start_date = datetime.combine(model_field_start_date, datetime.min.time())

        if model_field_start_date and goal_model_start_date:
            goal_model_start_date = datetime.combine(goal_model_start_date, datetime.min.time())
            goal_model_end_date = datetime.combine(goal_model_end_date, datetime.max.time())
            if model_field_start_date < goal_model_start_date:
                ks_start_end_date['start_date'] = model_field_start_date.strftime("%Y-%m-%d 00:00:00")
            else:
                ks_start_end_date['start_date'] = goal_model_start_date.strftime("%Y-%m-%d 00:00:00")
            if model_field_end_date > goal_model_end_date:
                ks_start_end_date['end_date'] = model_field_end_date.strftime("%Y-%m-%d 23:59:59")
            else:
                ks_start_end_date['end_date'] = goal_model_end_date.strftime("%Y-%m-%d 23:59:59")

        elif model_field_start_date and not goal_model_start_date:
            ks_start_end_date['start_date'] = model_field_start_date.strftime("%Y-%m-%d 00:00:00")
            ks_start_end_date['end_date'] = model_field_end_date.strftime("%Y-%m-%d 23:59:59")

        elif goal_model_start_date and not model_field_start_date:
            ks_start_end_date['start_date'] = goal_model_start_date.strftime("%Y-%m-%d 00:00:00")
            ks_start_end_date['end_date'] = goal_model_start_date.strftime("%Y-%m-%d 23:59:59")
        else:
            ks_start_end_date['start_date'] = False
            ks_start_end_date['end_date'] = False

        return ks_start_end_date

     #List View pagination
    @api.model
    def ks_get_next_offset(self, ks_item_id, offset):
        record = self.browse(ks_item_id)
        ks_offset = offset['offset']
        ks_list_view_data = self.ks_fetch_list_view_data(record,offset=int(ks_offset))

        return {
            'ks_list_view_data': json.dumps(ks_list_view_data),
            'offset': int(ks_offset) + 1,
            'next_offset': int(ks_offset) + len(ks_list_view_data['data_rows']),
        }


    @api.model
    def get_sorted_month(self, display_format, ftype='date'):
        query = """
                    with d as (SELECT date_trunc(%(aggr)s, generate_series) AS timestamp FROM generate_series
                    (%(timestamp_begin)s::TIMESTAMP , %(timestamp_end)s::TIMESTAMP , %(aggr1)s::interval ))
                     select timestamp from d group by timestamp order by timestamp
                        """
        self.env.cr.execute(query, {
            'timestamp_begin': "2020-01-01 00:00:00",
            'timestamp_end': "2020-12-31 00:00:00",
            'aggr': 'month',
            'aggr1': '1 month'
        })

        dates = self.env.cr.fetchall()
        locale = self._context.get('lang') or 'en_US'
        tz_convert = self._context.get('tz')
        return [self.format_label(d[0], ftype, display_format, tz_convert, locale) for d in dates]

    # Fix Order BY : maybe revert old code
    @api.model
    def generate_timeserise(self, date_begin, date_end, aggr, ftype='date'):
        query = """
                    with d as (SELECT date_trunc(%(aggr)s, generate_series) AS timestamp FROM generate_series
                    (%(timestamp_begin)s::TIMESTAMP , %(timestamp_end)s::TIMESTAMP , '1 hour'::interval )) 
                    select timestamp from d group by timestamp order by timestamp
                """

        self.env.cr.execute(query, {
            'timestamp_begin': date_begin,
            'timestamp_end': date_end,
            'aggr': aggr,
            'aggr1': '1 ' + aggr
        })
        dates = self.env.cr.fetchall()
        display_formats = {
            # Careful with week/year formats:
            #  - yyyy (lower) must always be used, except for week+year formats
            #  - YYYY (upper) must always be used for week+year format
            #         e.g. 2006-01-01 is W52 2005 in some locales (de_DE),
            #                         and W1 2006 for others
            #
            # Mixing both formats, e.g. 'MMM YYYY' would yield wrong results,
            # such as 2006-01-01 being formatted as "January 2005" in some locales.
            # Cfr: http://babel.pocoo.org/en/latest/dates.html#date-fields
            'minute': 'hh:mm dd MMM',
            'hour': 'hh:00 dd MMM',
            'day': 'dd MMM yyyy',  # yyyy = normal year
            'week': "'W'w YYYY",  # w YYYY = ISO week-year
            'month': 'MMMM yyyy',
            'quarter': 'QQQ yyyy',
            'year': 'yyyy',
        }

        display_format = display_formats[aggr]
        locale = self._context.get('lang') or 'en_US'
        tz_convert = self._context.get('tz')
        return [self.format_label(d[0], ftype, display_format, tz_convert, locale) for d in dates]

    @api.model
    def format_label(self, value, ftype, display_format, tz_convert, locale):

        tzinfo = None
        if ftype == 'datetime':

            if tz_convert:
                value = pytz.timezone(self._context['tz']).localize(value)
                tzinfo = value.tzinfo
            return babel.dates.format_datetime(value, format=display_format, tzinfo=tzinfo, locale=locale)
        else:

            if tz_convert:
                value = pytz.timezone(self._context['tz']).localize(value)
                tzinfo = value.tzinfo
            return babel.dates.format_date(value, format=display_format, locale=locale)

    def ks_sort_sub_group_by_records(self, ks_data, field_type, ks_chart_date_groupby, ks_sort_by_order,
                                     ks_chart_date_sub_groupby):
        if ks_data:
            reverse = False
            if ks_sort_by_order == 'DESC':
                reverse = True

            for data in ks_data:
                if field_type == 'date_type':
                    if ks_chart_date_groupby in ['minute', 'hour']:
                        if ks_chart_date_sub_groupby in ["month", "week", "quarter", "year"]:
                            ks_sorted_months = self.get_sorted_month("MMM")
                            data['value'].sort(key=lambda x: int(
                                str(ks_sorted_months.index(x['x'].split(" ")[2]) + 1) + x['x'].split(" ")[1] +
                                x['x'].split(" ")[0].replace(":", "")), reverse=reverse)
                        else:
                            data['value'].sort(key=lambda x: int(x['x'].replace(":", "")), reverse=reverse)
                    elif ks_chart_date_groupby == 'day' and ks_chart_date_sub_groupby in ["quarter", "year"]:
                        ks_sorted_days = self.generate_timeserise("2020-01-01 00:00:00", "2020-12-31 00:00:00",
                                                                  'day', "date")
                        b = [" ".join(x.split(" ")[0:2]) for x in ks_sorted_days]
                        data['value'].sort(key=lambda x: b.index(x['x']), reverse=reverse)
                    elif ks_chart_date_groupby == 'day' and ks_chart_date_sub_groupby not in ["quarter", "year"]:
                        data['value'].sort(key=lambda i: int(i['x']), reverse=reverse)
                    elif ks_chart_date_groupby == 'week':
                        data['value'].sort(key=lambda i: int(i['x'][1:]), reverse=reverse)
                    elif ks_chart_date_groupby == 'month':
                        ks_sorted_months = self.generate_timeserise("2020-01-01 00:00:00", "2020-12-31 00:00:00",
                                                                    'month', "date")
                        b = [" ".join(x.split(" ")[0:1]) for x in ks_sorted_months]
                        data['value'].sort(key=lambda x: b.index(x['x']), reverse=reverse)
                    elif ks_chart_date_groupby == 'quarter':
                        data['value'].sort(key=lambda i: int(i['x'][1:]), reverse=reverse)
                    elif ks_chart_date_groupby == 'year':
                        data['value'].sort(key=lambda i: int(i['x']), reverse=reverse)
                else:
                    data['value'].sort(key=lambda i: i['x'], reverse=reverse)

        return ks_data

    @api.onchange('ks_domain_2')
    def ks_onchange_check_domain_2_onchange(self):
        if self.ks_domain_2:
            proper_domain_2 = []
            try:
                ks_domain_2 = self.ks_domain_2
                if "%UID" in ks_domain_2:
                    ks_domain_2 = ks_domain_2.replace("%UID", str(self.env.user.id))
                if "%MYCOMPANY" in ks_domain_2:
                    ks_domain_2 = ks_domain_2.replace("%MYCOMPANY", str(self.env.user.company_id.id))
                ks_domain_2 = safe_eval(ks_domain_2)

                for element in ks_domain_2:
                    proper_domain_2.append(element) if type(element) != list else proper_domain_2.append(tuple(element))
                self.env[self.ks_model_name_2].search_count(proper_domain_2)
            except Exception:
                raise UserError("Invalid Domain")

    @api.onchange('ks_domain')
    def ks_onchange_check_domain_onchange(self):
        if self.ks_domain:
            proper_domain = []
            try:
                ks_domain = self.ks_domain
                if "%UID" in ks_domain:
                    ks_domain = ks_domain.replace("%UID", str(self.env.user.id))
                if "%MYCOMPANY" in ks_domain:
                    ks_domain = ks_domain.replace("%MYCOMPANY", str(self.env.user.company_id.id))
                ks_domain = safe_eval(ks_domain)
                for element in ks_domain:
                    proper_domain.append(element) if type(element) != list else proper_domain.append(tuple(element))
                self.env[self.ks_model_name].search_count(proper_domain)
            except Exception as e:
                raise UserError("Invalid Domain")


class KsDashboardItemsGoal(models.Model):
    _name = 'ks_dashboard_ninja.item_goal'
    _description = 'Dashboard Ninja Items Goal Lines'

    ks_goal_date = fields.Date(string="Date")
    ks_goal_value = fields.Float(string="Value")

    ks_dashboard_item = fields.Many2one('ks_dashboard_ninja.item', string="Dashboard Item")


class KsDashboardItemsActions(models.Model):
    _name = 'ks_dashboard_ninja.item_action'
    _description = 'Dashboard Ninja Items Action Lines'

    ks_item_action_field = fields.Many2one('ir.model.fields',
                                           domain="[('model_id','=',ks_model_id),('name','!=','id'),('store','=',True),"
                                                  "('ttype','!=','binary'),('ttype','!=','many2many'), "
                                                  "('ttype','!=','one2many')]",
                                           string="Action Group By")

    ks_item_action_field_type = fields.Char(compute="ks_get_item_action_type")

    ks_item_action_date_groupby = fields.Selection([('minute', 'Minute'),
                                                    ('hour', 'Hour'),
                                                    ('day', 'Day'),
                                                    ('week', 'Week'),
                                                    ('month', 'Month'),
                                                    ('quarter', 'Quarter'),
                                                    ('year', 'Year'),
                                                    ], string="Group By Date")

    ks_chart_type = fields.Selection([('ks_bar_chart', 'Bar Chart'),
                                      ('ks_horizontalBar_chart', 'Horizontal Bar Chart'),
                                      ('ks_line_chart', 'Line Chart'),
                                      ('ks_area_chart', 'Area Chart'),
                                      ('ks_pie_chart', 'Pie Chart'),
                                      ('ks_doughnut_chart', 'Doughnut Chart'),
                                      ('ks_polarArea_chart', 'Polar Area Chart'),
                                      ('ks_list_view', 'List View')],
                                     string="Item Type")

    ks_dashboard_item_id = fields.Many2one('ks_dashboard_ninja.item', string="Dashboard Item")
    ks_model_id = fields.Many2one('ir.model', related='ks_dashboard_item_id.ks_model_id')
    sequence = fields.Integer(string="Sequence")
    # For sorting and record limit
    ks_record_limit = fields.Integer(string="Record Limit")
    ks_sort_by_field = fields.Many2one('ir.model.fields',
                                       domain="[('model_id','=',ks_model_id),('name','!=','id'),('store','=',True),"
                                              "('ttype','!=','one2many'),('ttype','!=','binary')]",
                                       string="Sort By Field")
    ks_sort_by_order = fields.Selection([('ASC', 'Ascending'), ('DESC', 'Descending')],
                                        string="Sort Order")

    @api.depends('ks_item_action_field')
    def ks_get_item_action_type(self):
        for rec in self:
            if rec.ks_item_action_field.ttype == 'datetime' or rec.ks_item_action_field.ttype == 'date':
                rec.ks_item_action_field_type = 'date_type'
            elif rec.ks_item_action_field.ttype == 'many2one':
                rec.ks_item_action_field_type = 'relational_type'
                rec.ks_item_action_date_groupby = False
            elif rec.ks_item_action_field.ttype == 'selection':
                rec.ks_item_action_field_type = 'selection'
                rec.ks_item_action_date_groupby = False
            else:
                rec.ks_item_action_field_type = 'none'
                rec.ks_item_action_date_groupby = False

    @api.onchange('ks_item_action_date_groupby')
    def ks_check_date_group_by(self):
        for rec in self:
            if rec.ks_item_action_field.ttype == 'date' and rec.ks_item_action_date_groupby in ['hour', 'minute']:
                raise ValidationError(_('Action field: {} cannot be aggregated by {}').format(
                    rec.ks_item_action_field.display_name, rec.ks_item_action_date_groupby))

    @api.onchange('ks_item_action_field')
    def ks_onchange_item_action(self):
        for rec in self:
            if not (rec.ks_item_action_field.ttype == 'datetime' or rec.ks_item_action_field.ttype == 'date'):
                rec.ks_item_action_date_groupby = False