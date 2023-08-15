# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import xlwt
import base64
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit= "mrp.bom" 
       
    excel_file = fields.Binary("Excel Report")

    def print_export_bom_details_xls(self):
        filename = "BoM Structure.xls"
        path = "/tmp/"
        workbook = xlwt.Workbook()
        left_bold = xlwt.easyxf('align: horiz left; font: bold on;')
        title = xlwt.easyxf('font: bold on;font:height 360;border: top medium, bottom medium, right medium, left medium;')
        
        #mrp code
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        if len(active_ids) > 1:
            multiple_bom = True
        else:
            multiple_bom = False
        print("self._context",self._context)
        repeat_bom_name = []
        for selected_id in active_ids:
            selected_record = self.env['mrp.bom'].browse(selected_id)            
            for bom in selected_record:
                main_products = bom.product_id or bom.product_tmpl_id.product_variant_ids
                row = 0
                col = 0
                worksheet_name = "test"
                ###manage sheet name
                if not multiple_bom:#when one BOM
                    worksheet_name = bom.display_name
                else:#multiple BOM
                    #bom_id = '('+str(bom.id)+')'
                    worksheet_name = str(bom.display_name)
                    worksheet_name_len = len(worksheet_name)# + len(bom_id)
                    if worksheet_name_len > 31:#when name is bigger than default length
                        length = worksheet_name_len - 31
                        worksheet_name = worksheet_name[:-length]
                    #worksheet_name =worksheet_name+bom_id
                    if worksheet_name not in repeat_bom_name:
                        repeat_bom_name.append(worksheet_name)
                    else:
                        #raise UserError(_("Duplicate worksheet name '%s'", worksheet_name))
                        raise UserError(_("Please make sure that BOM names are unique since we can not create same sheet names in one excel"))
                
                ####
                worksheet = workbook.add_sheet(worksheet_name)     
                new_row = row + 1
                worksheet.write_merge(row, new_row, 0, 6, 'BoM Structure & Cost' , title)
                #worksheet.write_merge(row, new_row, 0, 6, 'BoM Overview' , title)
                row += 2
                new_row = row + 1
                worksheet.write_merge(row, new_row, 0, 6, bom.display_name , left_bold)
                row += 3
                #Product
                worksheet.write(row, col, 'Product', left_bold)
                col += 1
                #Bom
                worksheet.write(row, col, 'BoM', left_bold)
                col += 1
                #Quantity
                worksheet.write(row, col, 'Quantity', left_bold)
                col += 1
                #Unit of Measure
                worksheet.write(row, col, 'Unit of Measure', left_bold)
                worksheet.col(col).width = 256 * 20 #20 characters wide (-ish)
                col += 1
                #Product Cost
                worksheet.write(row, col, 'Product Cost', left_bold)
                col += 1
                #Bom Cost
                worksheet.write(row, col, 'BoM Cost', left_bold)
                col = 0
                row += 1
                i = 0
                #for bom in main_product.bom_ids:
                docs = []
                for product_id in main_products.ids:
                    temp_data = {'report_type': 'pdf'}
                    docs.append(self.env["report.mrp.report_bom_structure"]._get_pdf_line(bom.id, product_id=product_id, qty=bom.product_qty, unfolded=True))
                    
                #print("docs===>>>",docs)
                for data in docs:
                    worksheet.write(row, col, data['bom_prod_name'])
                    col += 1
                    if data['code']:
                        #'code': bom and bom.display_name or '',
                        worksheet.write(row, col, data['code'])
                    col += 1
                    worksheet.write(row, col, str("{:,.2f}".format(data['bom_qty'])))
                    col += 1
                    if data['bom']:
                        worksheet.write(row, col, str(data['bom'].product_uom_id.name))
                    col += 1
                    if data['price']:
                        worksheet.write(row, col, str("{:,.2f}".format(data['price'])))
                    col += 1
                    if data['bom_cost']:
                        worksheet.write(row, col, str("{:,.2f}".format(data['bom_cost'])))
                    col = 0
                    row += 1
                    if 'lines' in list(data.keys()):
                        lines = data.get('lines')
                        blank_space = '    '#make blank space
                        for line in lines:
                            #manage blank_space
                            level = line.get('level')
                            new_blank_space = blank_space * level
                            worksheet.write(row, col, str(new_blank_space)+str(line.get('name')))
                            col += 1
                            if 'code' in list(line.keys()):
                                worksheet.write(row, col, str(line.get('code')))
                            col += 1
                            worksheet.write(row, col, str("{:,.2f}".format(line.get('quantity'))))
                            col += 1
                            worksheet.write(row, col, str(line.get('uom')))
                            col += 1
                            if 'prod_cost' in list(line.keys()):
                                worksheet.write(row, col, str("{:,.2f}".format(line.get('prod_cost'))))
                            col += 1
                            if 'bom_cost' in list(line.keys()):
                                worksheet.write(row, col, str("{:,.2f}".format(line.get('bom_cost'))))
                            col = 0
                            row += 1
                    col += 3
                    worksheet.write(row, col, 'Unit Cost', left_bold)
                    col += 1
                    #<t t-esc="data['price']/data['bom_qty']"/>
                    cost_2 = data['price']/data['bom_qty']
                    worksheet.write(row, col, str("{:,.2f}".format(cost_2)), left_bold)
                    col += 1
                    #<t t-esc="data['cost_share'] * data['total'] / data['bom_qty']"/>
                    cost_1 = data['cost_share'] * data['total'] / data['bom_qty']
                    worksheet.write(row, col, str("{:,.2f}".format(cost_1)), left_bold)

        workbook.save(path+filename)
        file = open(path+filename, "rb")
        file_data = file.read()
        out = base64.encodebytes(file_data)
        #excel_template_id.write({'excel_file':out})
        export_obj = self.env['export.mrp.bom.structure.excel'].create({'excel_file': out, 'file_name': filename})

        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=export.mrp.bom.structure.excel&download=true&field=excel_file&id=%s&filename=%s' % (export_obj.id, filename),
            'target': 'self',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
