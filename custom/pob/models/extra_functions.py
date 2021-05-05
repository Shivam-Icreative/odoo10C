#!/usr/bin/env python
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
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import tools
from odoo import SUPERUSER_ID
from odoo import workflow

def _unescape(text):
	from urllib import unquote_plus
	return unquote_plus(text.encode('utf8'))

############## PrestaShop classes #################
class force_done(models.Model):
	_name="force.done"

	@api.model
	def add_tracking_number(self, data):
		order_name=self.env['sale.order'].name_get(data['order_id'])
		pick_id = self.env['stock.picking'].search([('origin','=',order_name[0][1])])		
		if pick_id:
			pick_id[0].write({'carrier_tracking_ref':data['track_no']})
		return True

	@api.multi
	def action_multiple_synchronize_reference(self):
		selected_ids = self._context.get('active_ids')		
		up_length = 0		
		error_message = ''
		message = ''
		to_be_updated = []
		presta_id = []
		config_id = self.env['prestashop.configure'].search([('active', '=', True)])
		if not config_id:
			raise UserError(_("Connection needs one Active Configuration setting."))
		if len(config_id)>1:
			raise UserError(_("Sorry, only one Active Configuration setting is allowed."))
		else:
			# obj = self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
			url = config_id.api_url
			key = config_id.api_key
			try:
				prestashop = PrestaShopWebServiceDict(url, key)
			except Exception, e:
				raise UserError(_('Error %s')%str(e))		
			if prestashop:			 				
				for k in self.env['stock.picking'].browse(selected_ids):
					sale_order_id = k.sale_id.id
					track_ref = k.carrier_tracking_ref
					if not track_ref:
						track_ref = ''
					if sale_order_id:
						check = self.env['prestashop.order'].search([('erp_id', '=', sale_order_id)])
						if check:
							presta_id = check[0].presta_id
						if presta_id:
							try:
								get_carrier_data = prestashop.get('order_carriers', options={'filter[id_order]':presta_id})
							except Exception,e:
								error_message="Error %s, Error in getting Carrier Data"%str(e)
							try:
								if get_carrier_data['order_carriers']:
									order_carrier_id = get_carrier_data['order_carriers']['order_carrier']['attrs']['id']
								if order_carrier_id:
									data = prestashop.get('order_carriers', order_carrier_id)
									data['order_carrier'].update({
										'tracking_number' : track_ref,					
										})
									try:
										return_id = prestashop.edit('order_carriers', order_carrier_id, data)
										up_length = up_length + 1
									except Exception,e:
										error_message = error_message + str(e)

							except Exception,e:
								error_message = error_message + str(e)
			if not error_message:				
				if up_length==0:
					message = "No Prestashop Order records fetched in selected stock movement records!!!"
				else:
					message = '%s Carrier Tracking Reference Number Updated to Prestashop!!!'%(up_length)
			else:				
				message = "Error in Updating: %s"%(error_message)
			partial_id = self.env['pob.message'].create({'text':message})
			return {'name':_("Message"),
					'view_mode': 'form',
					'view_id': False,
					'view_type': 'form',
					'res_model': 'pob.message',
					'res_id': partial_id.id,
					'type': 'ir.actions.act_window',
					'nodestroy': True,
					'target': 'new',
					'domain': self._context,
				}

	@api.model
	def create_attribute_value(self, data):
		check = self.env['product.attribute.value'].search([('attribute_id', '=', data['erp_attribute_id']), ('name', '=', data['name'])])
		if check:
			erp_id = check[0]
		else:
			temp = {}
			temp['name'] = _unescape(data['name'])
			temp['attribute_id'] = data['erp_attribute_id']
			temp['sequence'] = data['sequence']
			erp_id = self.env['product.attribute.value'].create(temp)
		self.env['prestashop.product.attribute.value'].create({'name':erp_id.id, 'erp_id':erp_id.id, 'presta_id':data['presta_attribute_value_id'], 'erp_attr_id':data['erp_attribute_id'], 'presta_attr_id':data['presta_attribute_id']})
		return erp_id.id

	# @api.model
	# def export_all_customers(self, cus_data, add_data, presta_user):
	# 	cus = {}
	# 	add = {}
	# 	cus_merge = []
	# 	add_merge = []
	# 	cus_synch_merge = []
	# 	add_synch_merge = []
	
	# 	for i in range(len(cus_data)):
	# 		cus['name'] = _unescape(cus_data[i]['firstname'] + ' ' + cus_data[i]['lastname'])
	# 		cus['email'] = cus_data[i]['email']
	# 		cus['is_company'] = True
	# 		if int(cus_data[i]['is_synch']):
	# 			if self.env['res.partner'].exists(int(cus_data[i]['erp_customer_id'])):
	# 				self.env['res.partner').write(uid,int(cus_data[i]['erp_customer_id']),cus)
	# 				cus_synch_merge.append(cus_data[i]['id_customer'])
	# 				erp_customer_id=cus_data[i]['erp_customer_id']
	# 		else:
	# 			erp_customer_id=self.env['res.partner').create(cr,uid,cus)
	# 			cus_merge.append({'erp_customer_id':erp_customer_id,'prestashop_customer_id':cus_data[i]['id_customer'],'created_by':presta_user})
	# 			self.pool.get('prestashop.customer').create(cr,uid,{'customer_name':erp_customer_id,'erp_customer_id':erp_customer_id,'presta_customer_id':cus_data[i]['id_customer'],'presta_address_id':'-'})
	# 		for data in filter(lambda x: x['id_customer']==cus_data[i]['id_customer'], add_data):
	# 			if data['country'] and data['country_iso']:
	# 				erp_country_id=self._get_country_id(cr,uid,{'name':_unescape(data['country']),'iso':data['country_iso']})
	# 				if data['state'] and data['state_iso']:
	# 					erp_state_id=self._get_state_id(cr,uid,{'name':_unescape(data['state']),'iso':data['state_iso'],'country_id':erp_country_id})
	# 				else:
	# 					erp_state_id=False
	# 			else:
	# 				erp_country_id=False
	# 			add.update({'parent_id':erp_customer_id,
	# 						'name':_unescape(data['firstname']+' '+data['lastname']),
	# 						'email':cus['email'],
	# 						'street':_unescape(data['address1']),
	# 						'street2':_unescape(data['address2']),
	# 						'phone':data['phone'],
	# 						'mobile':data['phone_mobile'],
	# 						'zip':data['postcode'],
	# 						'city':_unescape(data['city']),
	# 						'country_id':erp_country_id,
	# 						'state_id':erp_state_id,
	# 						'customer':False,
	# 						'use_parent_address':False,
	# 						})
	# 			if int(data['is_synch']):
	# 				if self.pool.get('res.partner').exists(cr,uid,int(data['erp_address_id'])):
	# 					self.pool.get('res.partner').write(cr,uid,int(data['erp_address_id']),add)
	# 					add_synch_merge.append(data['id_address'])
	# 			else:
	# 				erp_address_id=self.pool.get('res.partner').create(cr,uid,add)
	# 				add_merge.append({'erp_address_id':erp_address_id,'prestashop_address_id':data['id_address'],'id_customer':cus_data[i]['id_customer'],'created_by':presta_user})
	# 				self.pool.get('prestashop.customer').create(cr,uid,{'customer_name':erp_address_id,'erp_customer_id':erp_address_id,'presta_customer_id':cus_data[i]['id_customer'],'presta_address_id':data['id_address']})
	# 	return [cus_merge,add_merge,cus_synch_merge,add_synch_merge]

	# @api.model
	# def _get_country_id(self, data):
	# 	erp_country_id=self.env['res.country'].search([('code', '=',data.get('iso'))])
	# 	if not erp_country_id:
	# 		erp_country_id=self.env['res.country'].create({'name':data.get('name'),'code':data.get('iso')})
	# 		return erp_country_id.id
	# 	return erp_country_id[0].id

	# @api.model
	# def _get_state_id(self, data):
	# 	erp_state_id = self.env['res.country.state'].search([('code', '=',data.get('iso')),('country_id', '=',data.get('country_id'))])
	# 	if not erp_state_id:
	# 		erp_state_id=self.env['res.country.state'].create({'name':data.get('name'),'code':data.get('iso'),'country_id':data.get('country_id')})
	# 		return erp_state_id.id
	# 	return erp_state_id[0].id

	@api.model
	def _get_journal_id(self):
		# if context is None: context = {}
		if self._context.get('invoice_id', False):
			currency_id = self.env['account.invoice'].browse(context['invoice_id']).currency_id.id
			journal_id = self.env['account.journal'].search([('currency', '=', currency_id)], limit=1)
			return journal_id and journal_id[0] or False
		res = self.env['account.journal'].search([('type', '=','bank')], limit=1)
		return res and res[0] or False

	@api.model
	def _get_tax_id(self, journal_id):
		# if context is None: context = {}
		journal = self.env['account.journal'].browse(journal_id)
		account_id = journal.default_credit_account_id or journal.default_debit_account_id
		if account_id and account_id.tax_ids:
			tax_id = account_id.tax_ids[0].id
			return tax_id
		return False

	@api.model
	def _get_currency_id(self, journal_id):
		# if context is None: context = {}
		journal = self.env['account.journal'].browse(journal_id)
		if journal.currency:
			return journal.currency.id
		return self.env['res.users'].browse(uid).company_id.currency_id.id

	@api.model
	def update_product_mapping(self, data):
		# if context is None:
			# context = {}
		map_ids=self.env['prestashop.product'].search([('presta_product_id','=',int(data['presta_id']))])
		if map_ids:
			for obj in map_ids:
				obj.write({'base_price':data['base_price']})
			return True
		return False

	@api.model
	def pricelist_currency(self, currency_name, currency_code):
		# currency_id=self.env['res.currency'].search([('name','=',currency_code),('active', '=', '1')]).id
		currency_id=self.env['res.currency'].search([('name','=',currency_code),('active', '=', '1')])
		if currency_id.id:
			pricelist = {
						   'name': currency_name,
						   'active': '1',
						   'type': 'sale',
						   'currency_id': currency_id[0].id,
						}
			pricelist_id=self.env["product.pricelist"].create(pricelist)
			return pricelist_id.id
		else:
			return -1

	@api.model
	def _get_journal_code(self, string, sep=' '):
		tl = []
		for t in string.split(sep):
			tl.append(t.title()[0])
		code = ''.join(tl)
		code = code[0:3]
		is_exist = self.env['account.journal'].search([('code', '=', code)])
		if is_exist:
			for i in range(99):
				is_exist=self.env['account.journal'].search([('code', '=',code+str(i))])
				if not is_exist:
					return code+str(i)[-5:]
		return code
	
	@api.model
	def _get_journal_name(self, string):
		is_exist=self.env['account.journal'].search([('name', '=',string)])
		if is_exist:
			for i in range(99):
				is_exist=self.env['account.journal'].search([('name', '=',string+str(i))])
				if not is_exist:
					return string+str(i)
		return string

	@api.model
	def _get_virtual_product_id(self, data):
		ir_values = self.env['ir.values']
		erp_product_id = False
		if data['name'].startswith('S'):
			erp_product_id = ir_values.sudo().get_default('product.product', 'pob_delivery_product')
		if data['name'].startswith('D'):
			erp_product_id = ir_values.sudo().get_default('product.product', 'pob_discount_product')
		if not erp_product_id:
			temp_dic = {'sale_ok':False, 'name':data.get('name'), 'type':'service', 'description_sale':'', 'list_price':0.0,}
			object_name = ''
			if data['name'].startswith('S'):
				object_name = 'pob_delivery_product'
				temp_dic['description'] = 'Service Type product used by POB for Shipping Purposes'
			if data['name'].startswith('D'):
				object_name = 'pob_discount_product'
				temp_dic['description'] = 'Service Type product used by POB for Discount Purposes'
			erp_product_id=self.env['product.product'].create(temp_dic)
			ir_values.sudo().set_default('product.product',object_name,erp_product_id)
			self._cr.commit()
		return erp_product_id

	@api.model
	def create_payment_method(self, data):
		# if context is None: context = {}
		res = self.env['account.journal'].search([('type', '=','bank')], limit=1)[0]
		credit_account_id = res.default_credit_account_id.id
		debit_account_id = res.default_debit_account_id.id
		journal = {
					   'name': self._get_journal_name(data.get('name')),
					   'code': self._get_journal_code(data.get('name')),
					   'type': 'cash',
					   #'company_id': 1,
					   #'user_id':1,
					   'default_credit_account_id':credit_account_id,
					   'default_debit_account_id':debit_account_id,
					  	}
		journal_id=self.env['account.journal'].create(journal)
		return journal_id.id


	@api.model
	def update_quantity(self, data):
		""" Changes the Product Quantity by making a Physical Inventory through any service like xmlrpc.
		@param data: Dictionary of product_id and new_quantity
		@param context: A standard dictionary
		@return: True
		"""
		context = self.env.context.copy() or {}
		context['prestashop'] = 'prestashop'
		rec_id = data.get('product_id')
		assert rec_id, _('Active ID is not set in Context')
		if int(data.get('new_quantity')) < 0:
			raise UserError(_('Quantity cannot be negative.'))
		if int(data.get('new_quantity')) == 0:
			return True
		inventory_obj = self.env['stock.inventory']
		inventory_line_obj = self.env['stock.inventory.line']
		prod_obj_pool = self.env['product.product']
		res_original = prod_obj_pool.with_context(context).browse(rec_id)
		if int(data.get('new_quantity')) == int(res_original.qty_available):
			return True
		config_id=self.env['prestashop.configure'].search([('active','=',True)])
		if config_id:
			location_id = config_id[0].pob_default_stock_location.id
		else:
			location_id = self.env['stock.location'].search([('name','=','Stock')])
			location_id = location_id[0].id
		if location_id:
			th_qty = res_original.qty_available
			inventory_id = inventory_obj.with_context(context).create({
			            'name': _('INV: %s') % tools.ustr(res_original.name),
			            'product_id': rec_id,
			            'location_id': location_id,
			            'filter':'product'
		            })
			line_data = {
		        'inventory_id': inventory_id.id,
		        'product_qty': data.get('new_quantity'),
		        'location_id': location_id,
		        'product_id': rec_id,
		        'product_uom_id': res_original.uom_id.id,
		        'theoretical_qty': th_qty
			}
			inventory_line_obj.with_context(context).create(line_data)
			inventory_id.with_context(context).action_done()
		else:
			return "Sorry, Default Stock Location not found!!!"
		return True
