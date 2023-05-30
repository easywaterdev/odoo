# -*- coding: utf-8 -*-
from odoo import fields, models


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    question_type = fields.Selection(selection_add=[('upload_file', 'Upload File')])
    upload_multiple_file = fields.Boolean('Upload Multiple File')

    def validate_question(self, answer, comment=None):
        if self.constr_mandatory and self.question_type == 'upload_file':
            if 'values' in answer and len(answer.get('values')) > 0:
                return {}
            else:
                return {self.id: self.constr_error_msg}
        return super(SurveyQuestion, self).validate_question(answer)
