# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'POB - PrestaShop-Odoo Bridge',
    'version': '0.1',
    'author': 'Webkul Software Pvt. Ltd.',
    'summary': 'Bi-directional synchronization with PrestaShop',
    'description': """
POB - PrestaShop-Odoo Bridge
==============================
This module connects your between the Odoo and PrestaShop and allows bi-directional synchronization of your data between them. 

NOTE: You need to install a corresponding 'Prestashop-Odoo Bridge' plugin on your prestashop too,
in order to work this module perfectly. 

Key Features
------------
* export/update "all" or "selected" or "multi-selected" products,with images, from Odoo to Prestashop with a single click.
* export/update "all" or "selected" or "multi-selected" categories from Odoo to Prestashop with a single click.
* export/update "all" or "selected" or "multi-selected" customers with their addresses from Odoo to Prestashop with a single click.
* maintain order`s statusses with corressponding orders on prestashop.(if the order is created from prestashop)
* export/update "all" or "selected" or "multi-selected" categories from Odoo to Prestashop with a single click.

Dashboard / Reports:
------------------------------------------------------
* Orders created from Prestashop on specific date-range

For any doubt or query email us at support@webkul.com or raise a Ticket on http://webkul.com/ticket/
    """,
    'website': 'http://www.webkul.com',
    'images': [],
    'depends': ['base','sale','product','stock','account_accountant','account_cancel', 'account_voucher','delivery','bridge_skeleton'],
    'category': 'POB',
    'sequence': 1,
    'data': [
        'security/pob_connector_security.xml',
        'security/ir.model.access.csv',
        'views/pob_view.xml',
        'views/res_config_view.xml', 
        'pob_scheduler_data.xml',
        # 'pob_scheduler.xml',
        'wizard/pob_message_view.xml',
        'data/pob_data.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}