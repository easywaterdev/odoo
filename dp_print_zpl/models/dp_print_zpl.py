# -*- coding: utf-8 -*-
# Copyright 2018-Today datenpol gmbh (<http://www.datenpol.at>)
# License OPL-1 or later (https://www.odoo.com/documentation/user/12.0/legal/licenses/licenses.html#licenses).

import logging
import socket

from jinja2 import Template as JinjaTemplate

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DpPrintZpl(models.Model):
    _name = 'dp.print.zpl'
    _description = 'Print ZPL'

    name = fields.Char('Name', required=True)
    ip_address = fields.Char('IP-Address', required=True, help='IP-Address of Zebra-Printer')
    model = fields.Many2one('ir.model', 'Model', required=True)
    port = fields.Integer('Port', required=True, default=9100, help='FTP-Port of Zebra-Printer')
    zpl_code = fields.Text('ZPL Code', required=True, help='Additional information about ZPL can for instance be '
                                                           'found at http://labelary.com or https://www.zebra.com/')
    ir_action_id = fields.Many2one('ir.actions.server', 'Action ID')
    print_visible = fields.Boolean('Print is Visible', default=False, copy=False)
    configuration_code = fields.Text('Configuration Code', help='Configuration')

#     @api.multi
    def create_action(self):
        """ Create a contextual action for each server action. """
        zpl_model = self.env['ir.model'].search([('model', '=', 'dp.print.zpl')])
        for record in self:
            if record.ir_action_id:
                record.ir_action_id.unlink()
            action = self.env['ir.actions.server'].sudo().create({
                'name': 'ZPL %s' % record.name,
                'model_id': zpl_model.id,
                'type': 'ir.actions.server',
                'state': 'code',
                'code': 'env["dp.print.zpl"].browse(%d).start_printing()' % record.id,
                'binding_model_id': record.model.id,
                'binding_type': 'report'
            })

            record.write({
                'ir_action_id': action.id,
                'print_visible': True
            })

        return True

#     @api.multi
    def unlink_action(self):
        for record in self:
            if record.ir_action_id:
                record.ir_action_id.unlink()
            record.print_visible = False
        return True

#     @api.multi
    def start_printing(self):
        if not self:
            raise ValidationError(_('Configuration Error: Please configure the ZPL right'))

        records = None
        if self.env.context.get('active_ids', False):
            model_obj = self.env[self._context.get('active_model')]
            records = model_obj.browse(self.env.context.get('active_ids'))

        self.print_model(records)

#     @api.multi
    def send_configuration(self):
        self.ensure_one()
        if self.configuration_code:
            self.print_zpl(self.configuration_code)

#     @api.multi
    def print_model(self, record):
        self.ensure_one()

        src = "{% for model in models -%}" + self.zpl_code + "{% endfor %}"
        src = JinjaTemplate(src)

        zpl_code = src.render(models=record)
        _logger.debug(zpl_code)
        self.print_zpl(zpl_code)

    @api.model
    def print_zpl(self, zpl_to_print):
        # send by socket to raw printer port 9100 to Zebra
        host = self.ip_address
        try:
            host = socket.gethostbyname(self.ip_address)
            _logger.debug("connecting to %s:%s" % (host, self.port))
        except socket.gaierror:
            _logger.error('hostname "%s" failed' % (host,))
            raise ValidationError(
                _('The IP-address or the hostname "%s" is not correct (cannot be resolved).') % (host,))

        try:
            device = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            device.settimeout(5)
            device.connect((host, self.port))
            device.sendall(zpl_to_print.encode('utf-8'))
            device.close()
        except Exception as e:
            # could raise socket.error, maybe (?) socket.herror, socket.gaierror, socket.timeout
            _logger.warning(e)
            raise ValidationError(
                _('The printer with the IP-address "%s" and port "%s" cannot be reached! (%s)') % (
                    host, self.port, e))
        return True
