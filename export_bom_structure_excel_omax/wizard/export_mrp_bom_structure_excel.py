# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import xlwt
import base64


class ExportMrpBomStructureExcel(models.TransientModel):
    _name= "export.mrp.bom.structure.excel"
    _description= "export.mrp.bom.structure.excel"

    excel_file = fields.Binary("Excel Report")
    file_name = fields.Char("Report File Name", size=64, readonly=True)


#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
