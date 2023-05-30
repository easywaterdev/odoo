# -*- coding: utf-8 -*-
from odoo import fields, api, models


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def save_lines(self, question, answer, comment=None):
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])
        if question.question_type == 'upload_file':
            self._save_line_upload_files(question, old_answers, answer, comment)
        else:
            return super(SurveyUserInput, self).save_lines(question, answer, comment)

    def _save_line_upload_files(self, question, old_answers, answers, comment):
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': question.question_type,
        }
        if answers and answers.get('values') and answers.get('is_answer_update'):
            user_binary_lines = [
                    (0, 0, {'binary_data': answer.get('data'), 'binary_filename': answer.get('file_name')})
                    for answer in answers.get('values')
                ]
            vals.update({'user_binary_line': user_binary_lines})
            if old_answers:
                old_answers.unlink()
            old_answers.create(vals)
        else:
            vals.update({'answer_type': None, 'skipped': True})

        return old_answers

class SurveyBinary(models.Model):
    _name = 'survey.binary'
    _description = 'Survey File Upload'

    user_input_line_id = fields.Many2one('survey.user_input.line', string="Answers")
    binary_filename = fields.Char(string="Upload File Name")
    binary_data = fields.Binary(string="Upload File Data")

class SurveyUserInputLine(models.Model):
    _inherit = "survey.user_input.line"

    user_binary_line = fields.One2many('survey.binary', 'user_input_line_id', string='Binary Files')
    answer_type = fields.Selection(selection_add=[('upload_file', 'Upload File')])
    value_upload_file = fields.Char('Upload Multiple File')

    @api.constrains('skipped', 'answer_type')
    def _check_answer_type_skipped(self):
        for line in self:
            if line.answer_type != 'upload_file':
                super(SurveyUserInputLine, line)._check_answer_type_skipped()
