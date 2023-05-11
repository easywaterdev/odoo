# -*- coding: utf-8 -*-

from odoo import fields, models

class ProductProduct(models.Model):
    _inherit = "product.product"

    def name_get(self):
        res = super().name_get()
        record_index = -1
        remove_index = []
        for record in self:
            variant_attributes = {}
            record_index += 1
            if 'Commercial Products' in record.product_tmpl_id.categ_id.complete_name and record.product_tmpl_id.product_short_code:
                default_code = record.product_tmpl_id.product_short_code
                product_name = False
                for product_template_attribute_value_id in record.product_template_attribute_value_ids:
                    if product_template_attribute_value_id.attribute_id.name:
                        variant_attributes[product_template_attribute_value_id.attribute_id.name] = \
                            product_template_attribute_value_id.name
                        value_description = self._get_attribute_value(product_template_attribute_value_id.name, False)
                        if not product_name and value_description:
                            product_name = value_description
                        elif value_description:
                            product_name += ', ' + value_description
                if 'Flow Rate' in variant_attributes.keys():
                    return_string = self._get_attribute_value(variant_attributes['Flow Rate'], True)
                    if not isinstance(return_string, bool):
                        default_code += '-' + return_string
                if 'Array' in variant_attributes.keys():
                    return_string = self._get_attribute_value(variant_attributes['Array'], True)
                    if not isinstance(return_string, bool):
                        default_code += '-' + return_string
                if default_code and product_name:
                    record.default_code = default_code
                    record.display_name = product_name
                    display_string = '[' + default_code + '] ' + record.product_tmpl_id.name + ' (' + product_name + ')'
                    res.append((record.id, display_string))
                    remove_index.append(record_index)
            while len(remove_index) > 0:    
                res.pop(remove_index.pop())
        return res

    def _get_attribute_value(self, value, part_number):
        string_return = False
        if part_number and '(' in value and ')' in value:
            data_start = value.index('(')
            data_end = value.index(')', data_start)
            string_return = value[(data_start + 1):data_end]
        elif '~' in value and not part_number:
            data_end = value.index('~')
            string_return = value[0:data_end]
        elif not part_number:
            string_return = value
        return string_return
