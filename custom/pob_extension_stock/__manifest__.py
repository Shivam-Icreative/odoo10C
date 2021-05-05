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
    'name': 'POB Stock Extension',
    'version': '1.0',
	'sequence': 1,
	'summary':'Stock Extension for POB',
    'category': 'A Module of WEBKUL Software Pvt Ltd.',
    'description': """	
    This Module helps in maintaining stock between openerp and prestashop with real time.
	
	NOTE : This module works very well with latest version of prestashop 1.5.4 and latest version of OpenErp 7.0.
    """,
    'author': 'Webkul Software Pvt Ltd.',
    'depends': ['pob'],
    'website': 'http://www.webkul.com',
    #'data': ['prestashop_openerp_stock_view.xml'],
    'installable': True,
    'auto_install': False,
    #'certificate': '0084849360985',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
