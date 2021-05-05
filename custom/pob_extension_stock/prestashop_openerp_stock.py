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

from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.addons.pob.models import prestapi
from odoo.addons.pob.models.prestapi import PrestaShopWebService, PrestaShopWebServiceDict, PrestaShopWebServiceError, PrestaShopAuthenticationError
import logging
_logger = logging.getLogger(__name__)

def _unescape(text):
	##
	# Replaces all encoded characters by urlib with plain utf8 string.
	#
	# @param text source text.
	# @return The plain text.
	from urllib import unquote_plus
	return unquote_plus(text.encode('utf8'))
################## .............prestashop-openerp stock.............##################
			
# Overriding this class in order to handle Stock Management b/w OpenERP n PrestaShop. 
class StockMove(models.Model):
	_inherit="stock.move"
	
	@api.multi
	def action_done(self):
		""" Makes the move done and if all moves are done, it will finish the picking.
		@return:
		"""
		context = self.env.context.copy() or {}
		_logger.info('-----stock---!!!!!!!!!!!!!!---------context--%r',context)
		super(StockMove, self).action_done()
		todo = [move.id for move in self if move.state == "draft"]
		ids = self
		if todo:
			ids = self.action_confirm(todo)
		if not context.has_key('prestashop') :
			check_out,check_in = [False, False]
			product_qty = 0
			pob_conf = self.env['prestashop.configure'].search([('active', '=', True)])
			if pob_conf:
				pob_location = pob_conf[0].pob_default_stock_location.id
			else:
				pob_location = -1
			for id in ids:
				data = self.browse(id.id)
				erp_product_id = data.product_id.id
				flag = 2 # means there is some origin.
				if data.origin != False:
					# Check if origin is 'Sale' and channel is 'prestashop',no need to update quantity.			
					sale_id = self.env['sale.order'].search([('name', '=', data.origin)])
					if sale_id:
						get_channel = sale_id[0].ecommerce_channel
						if get_channel == 'prestashop':
							flag = 0 # no need to update quantity.
				# else:
				# 	flag = 2 # no origin.

				# if flag == 1:
				# 	if data.picking_type_id:
				# 		check_pos = self.env['ir.model'].search([('model','=','pos.order')])
				# 		if check_pos:
				# 			pos_order_data = self.env['pos.order'].search([('name', '=', data.origin)])
				# 			if pos_order_data:
				# 				lines = pos_order_data[0].lines
				# 				for line in lines:
				# 					get_line_data = self.env['pos.order.line'].search([('product_id', '=', erp_product_id), ('id', '=', line.id)])
				# 					if get_line_data:
				# 						data.product_qty = get_line_data[0].qty
				# 		if data.picking_type_id.code == 'incoming':
				# 			if data.location_dest_id.id == pob_location:
				# 				check_in = True
				# 		if data.picking_type_id.code == 'outgoing':
				# 			if data.location_id.id == pob_location:
				# 				check_out = True							
				if flag == 2:						
					pob_conf = self.env['prestashop.configure'].search([('active', '=', True)])
					if pob_conf:
						pob_location = pob_conf[0].pob_default_stock_location.id
					else:
						pob_location = -1
					if data.location_dest_id.id == pob_location:
						check_in = True
					elif data.location_id.id == pob_location:
						check_out = True					
				if check_in:									
					product_qty = int(data.product_qty)					
				if check_out:												
					product_qty = int(-data.product_qty)
				if check_in or check_out:
					self.synch_quantity(erp_product_id, product_qty, pob_conf)
		return True
	
	# Extra function to update quantity(s) of product to prestashop`s end.
	@api.multi
	def synch_quantity(self, erp_product_id, product_qty, config_ids):
		response = self.update_quantity(erp_product_id, product_qty, config_ids[0])
		if response[0]==1:
			return True
			
	# Function to update quantity of products to prestashop`s end. 	
	@api.multi
	def update_quantity(self, erp_product_id, quantity, config_id):
		check_mapping=self.env['prestashop.product'].search([('erp_product_id', '=', erp_product_id)])
		if check_mapping:
			presta_product_id = check_mapping[0].presta_product_id
			presta_product_attribute_id = check_mapping[0].presta_product_attr_id
			
			if config_id:
				url = config_id.api_url
				key = config_id.api_key
				try:
					prestashop = PrestaShopWebServiceDict(url, key)
				except Exception, e:
					return [0,' Error in connection',check_mapping[0]]
				try:
					stock_search = prestashop.get('stock_availables',options={'filter[id_product]':presta_product_id,'filter[id_product_attribute]':presta_product_attribute_id})
				except Exception,e:
					return [0,' Unable to search given stock id', check_mapping[0]]
				if type(stock_search['stock_availables']) == dict:
					stock_id = stock_search['stock_availables']['stock_available']['attrs']['id']
					try:
						stock_data = prestashop.get('stock_availables', stock_id)
					except Exception,e:
						return [0,' Error in Updating Quantity,can`t get stock_available data.',check_mapping[0]]
					if type(quantity) == str:
						quantity = quantity.split('.')[0]
					if type(quantity) == float:
						quantity = int(quantity)
					stock_data['stock_available']['quantity'] = int(stock_data['stock_available']['quantity'])+int(quantity)
					try:
						up = prestashop.edit('stock_availables', stock_id, stock_data)
					except:
						pass
					return [1,'']
				else:
					return [0,' No stock`s entry found in prestashop for given combination (Product id:%s ; Attribute id:%s)'%(str(presta_product_id),str(presta_product_attribute_id)),check_mapping[0]]
		else:
			return [1,'']
