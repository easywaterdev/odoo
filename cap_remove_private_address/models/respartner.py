# coding: utf-8
# Part of CAPTIVEA. Odoo 12 EE.

from odoo import fields, models


class ResPartner(models.Model):
	_inherit = 'res.partner'
    
	type = fields.Selection(
	[('contact', 'Contact'),
	 ('invoice', 'Billing address'),
	 ('delivery', 'Delivery address'),
	 ('other', 'Installation address'),
	 ('private', 'Private address'),
	], string='Address Type',
	default='contact',
        help="Used by Sales and Purchase Apps to select the relevant address depending on the context.")
	

