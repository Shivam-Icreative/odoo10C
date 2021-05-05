# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals, context=None):
        new_id = super(ResPartner, self).create(vals)
        new_object = self.env['res.partner'].browse(new_id.id)
        res = self.env['res.partner'].search([('ref', '!=', False),('customer', '=', True)], order="id desc", limit=1)
        if new_object.customer == True:
            new_ref = int(res.ref)
            new_ref = new_ref + 1
            new_object.write({'ref': str(new_ref)})
        return new_id

    @api.one
    def b92_generate_num(self):
        if self.customer:
            if not self.ref:
                res = self.env['res.partner'].search([('ref', '!=', False), ('customer', '=', True)], order="ref desc", limit=1)
                if res:
                    new_ref = int(res.ref)
                    new_ref = new_ref + 1
                    self.write({'ref': str(new_ref)})