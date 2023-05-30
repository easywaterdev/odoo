# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey


class Survey(Survey):

    @http.route(["/web/binary/download/<int:file_id>"], type='http', auth="public", website=True, sitemap=False)
    def binary_download(self, file_id=None, **post):
        if file_id:
            binary_file = request.env['survey.binary'].browse([file_id])
            if binary_file:
                status, headers, content = request.env['ir.http'].binary_content(model='survey.binary', id=binary_file.id, field='binary_data', filename_field=binary_file.binary_filename)
                content_base64 = base64.b64decode(content) if content else ''
                headers.append(('Content-Type', 'application/octet-stream'))
                headers.append(('Content-Length', len(content_base64)))
                headers.append(('Content-Disposition', 'attachment; filename=' + binary_file.binary_filename + ';'))
                return request.make_response(content_base64, headers)
        return False
