# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models, fields

class ProductBrand(models.Model):
    _inherit = 'product.brand'

    prestashop_id = fields.Char(string='Prestashop ID')

