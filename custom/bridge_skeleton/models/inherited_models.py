# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#	See LICENSE file for full copyright and licensing details.
#
##########################################################################

from odoo import models, fields, api, _
from odoo.osv import osv


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = "sale.order"

    @api.depends('picking_ids')
    def _shipped_status_compute(self):
        is_shipped = False
        for sale_obj in self:
            if sale_obj.state not in ['draft', 'sent']:
                is_shipped = True
                for pick_obj in sale_obj.picking_ids:
                    if pick_obj.state != "done":
                        is_shipped = False
                        break
            sale_obj.is_shipped = is_shipped

    @api.depends('invoice_status')
    def _invoiced_status_compute(self):
        for sale_obj in self:
            if sale_obj.invoice_status == "invoiced":
                sale_obj.is_invoiced = True

    def _get_ecommerces(self):
        return [('test', 'TEST')]
    _ecommerce_selection = lambda self, * \
        args, **kwargs: self._get_ecommerces(*args, **kwargs)

    ecommerce_channel = fields.Selection(string='eCommerce Channel', selection=_ecommerce_selection,
                                         help="Name of ecommerce from where this Order is generated.", default='test')
    payment_method = fields.Many2one('account.payment.method', domain=[(
        'payment_type', '=', 'inbound')], help='Name of Payment Method used in eCommerce by the Customer.', string="Payment Method")
    is_shipped = fields.Boolean(compute='_shipped_status_compute')
    is_invoiced = fields.Boolean(compute='_invoiced_status_compute')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _handle_first_contact_creation(self):
        """ On creation of first contact for a company (or root) that has no address, assume contact address
        was meant to be company address """
        parent = self.parent_id
        address_fields = self._address_fields()
        if parent and (parent.is_company or not parent.parent_id) and len(parent.child_ids) == 1 and \
                any(self[f] for f in address_fields) and not any(parent[f] for f in address_fields):
            addr_vals = self._update_fields_values(address_fields)
            parent.update_address(addr_vals)

    # wk_company = fields.Char(string='Company', size=128)