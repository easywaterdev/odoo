# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import pdf

from .ups_request import UPSRequest, Package


class ProviderUPS(models.Model):
    _inherit = 'delivery.carrier'

    def ups_get_return_label(self, picking, tracking_number=None, origin_date=None):
        res = []
        superself = self.sudo()
        srm = UPSRequest(self.log_xml, superself.ups_username, superself.ups_passwd, superself.ups_shipper_number, superself.ups_access_number, self.prod_environment)
        ResCurrency = self.env['res.currency']
        packages = []
        package_names = []
        if picking.is_return_picking:
            weight = picking._get_estimated_weight()
            packages.append(Package(self, weight))
        else:
            if picking.package_ids:
                # Create all packages
                for package in picking.package_ids:
                    packages.append(Package(self, package.shipping_weight, quant_pack=package.package_type_id, name=package.name))
                    package_names.append(package.name)
            # Create one package with the rest (the content that is not in a package)
            if picking.weight_bulk:
                packages.append(Package(self, picking.weight_bulk))

        invoice_line_total = 0
        for move in picking.move_lines:
            invoice_line_total += picking.company_id.currency_id.round(move.product_id.lst_price * move.product_qty)

        shipment_info = {
            'description': picking.origin,
            'total_qty': sum(sml.qty_done for sml in picking.move_line_ids),
            'ilt_monetary_value': '%d' % invoice_line_total,
            'itl_currency_code': self.env.company.currency_id.name,
            'phone': picking.partner_id.mobile or picking.partner_id.phone or picking.sale_id.partner_id.mobile or picking.sale_id.partner_id.phone,
        }
        if picking.sale_id and picking.sale_id.carrier_id != picking.carrier_id:
            ups_service_type = picking.carrier_id.ups_default_service_type or self.ups_default_service_type
        else:
            ups_service_type = self.ups_default_service_type
        ups_carrier_account = False
        if self.ups_bill_my_account:
            ups_carrier_account = picking.partner_id.with_company(picking.company_id).property_ups_carrier_account

        if picking.carrier_id.ups_cod:
            cod_info = {
                'currency': picking.partner_id.country_id.currency_id.name,
                'monetary_value': picking.sale_id.amount_total,
                'funds_code': self.ups_cod_funds_code,
            }
        else:
            cod_info = None

        check_value = srm.check_required_value(picking.partner_id, picking.partner_id, picking.picking_type_id.warehouse_id.partner_id)
        if check_value:
            raise UserError(check_value)

        package_type = picking.package_ids and picking.package_ids[0].package_type_id.shipper_package_code or self.ups_default_package_type_id.shipper_package_code
        srm.send_shipping(
            shipment_info=shipment_info, packages=packages, shipper=picking.partner_id, ship_from=picking.partner_id,
            ship_to=picking.partner_id, packaging_type=package_type,
            service_type=ups_service_type, duty_payment='RECIPIENT', label_file_type=self.ups_label_file_type,
            ups_carrier_account=ups_carrier_account,
            saturday_delivery=picking.carrier_id.ups_saturday_delivery, cod_info=cod_info)
        srm.return_label()
        result = srm.process_shipment()
        if result.get('error_message'):
            raise UserError(result['error_message'].__str__())

        order = picking.sale_id
        company = order.company_id or picking.company_id or self.env.company
        currency_order = picking.sale_id.currency_id
        if not currency_order:
            currency_order = picking.company_id.currency_id

        if currency_order.name == result['currency_code']:
            price = float(result['price'])
        else:
            quote_currency = ResCurrency.search([('name', '=', result['currency_code'])], limit=1)
            price = quote_currency._convert(
                float(result['price']), currency_order, company, order.date_order or fields.Date.today())

        package_labels = []
        for track_number, label_binary_data in result.get('label_binary_data').items():
            package_labels = package_labels + [(track_number, label_binary_data)]

        carrier_tracking_ref = "+".join([pl[0] for pl in package_labels])
        logmessage = _("Return label generated<br/>"
                       "<b>Tracking Numbers:</b> %s<br/>"
                       "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join(package_names))
        if self.ups_label_file_type != 'GIF':
            attachments = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), pl[0], index, self.ups_label_file_type), pl[1]) for index, pl in enumerate(package_labels)]
        if self.ups_label_file_type == 'GIF':
            attachments = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), package_labels[0][0], 1, 'pdf'), pdf.merge_pdf([pl[1] for pl in package_labels]))]
        picking.message_post(body=logmessage, attachments=attachments)
        shipping_data = {
            'exact_price': price,
            'tracking_number': carrier_tracking_ref}
        res = res + [shipping_data]
        return res