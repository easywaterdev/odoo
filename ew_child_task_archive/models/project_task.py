# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Task(models.Model):
    _inherit = 'project.task'

    ancestor_id = fields.Many2one('project.task', string='Ancestor Task', compute='_compute_ancestor_id',
                                  index='btree_not_null', recursive=True, store=True)

    @api.depends('parent_id.ancestor_id')
    def _compute_ancestor_id(self):
        for task in self:
            task.ancestor_id = task.parent_id.ancestor_id or task.parent_id

        
    def write(self, vals):
        res = super(Task, self).write(vals)
        if 'tag_ids' in vals.keys():
            for record in self:
                sub_tasks = self.env['project.task'].sudo().search([('ancestor_id', '=', record.id), '|',
                                                                    ('active', '=', True), ('active', '=', False)])
                for task in sub_tasks:
                    if record.tag_ids:
                        matching_tags = task.tag_ids & record.tag_ids
                        if matching_tags or not task.tag_ids:
                            task.active = True
                        else:
                            task.active = False
                    else:
                        task.active = True
        return res

