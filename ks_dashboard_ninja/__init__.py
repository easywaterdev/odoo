# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import lib

from odoo.api import Environment, SUPERUSER_ID


def uninstall_hook(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})
    for rec in env['ks_dashboard_ninja.board'].search([]):
        rec.ks_dashboard_client_action_id.unlink()
        rec.ks_dashboard_menu_id.unlink()
