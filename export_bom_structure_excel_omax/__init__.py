# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import wizard
from . import models

def pre_init_check(cr):
    from odoo.service import common
    from odoo.exceptions import ValidationError
    version_info = common.exp_version()
    server_serie =version_info.get('server_serie')
    if server_serie!='15.0':raise ValidationError('Module support Odoo series 15.0 found {}.'.format(server_serie))
    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
