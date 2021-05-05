# -*- coding: utf-8 -*-
# Copyright 2015 Antiun Ingeniería, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class LeadCase(TransactionCase):
    def setUp(self):
        super(LeadCase, self).setUp()
        self.lead = self.env["crm.lead"].create({
            "name": __file__,
            "partner_name": u"HÎ"
        })
        self.partner = self.env["res.partner"].create({
            "name": __file__,
            "comercial": u"öooo",
        })
        self.test_field = u"custom trade näme"

    def test_transfered_values(self):

        self.lead.trade_name = self.test_field
        self.lead.handle_partner_assignation()
        self.assertEqual(self.lead.partner_id.comercial, self.test_field)

    def test_onchange_partner_id(self):
        """Lead gets trade_name from partner when linked to it."""
        self.partner.comercial = self.test_field
        self.lead.partner_id = self.partner
        self.lead._onchange_partner_id()
        self.assertEqual(self.lead.trade_name, self.test_field)
