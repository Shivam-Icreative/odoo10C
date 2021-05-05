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
from pob import _unescape
from odoo import workflow
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID, api
import prestapi
from prestapi import PrestaShopWebService,PrestaShopWebServiceDict,PrestaShopWebServiceError,PrestaShopAuthenticationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import logging
_logger = logging.getLogger(__name__)
############## Override classes #################

class ProductTemplate(models.Model):	
	_inherit = 'product.template'

	
	@api.model
	def create_product_template_dict(self,vals):
		template_id=self.create(vals)
		variant_ids_ids = template_id.product_variant_ids
		temp = {'template_id':template_id.id}
		if len(variant_ids_ids)==1:
			temp['product_id'] = variant_ids_ids[0].id
		else:
			temp['product_id'] = -1
		self.env['prestashop.product.template'].sudo().create({'template_name':template_id.id,'erp_template_id':template_id.id,'presta_product_id':self._context['presta_id']})
		self.env['prestashop.product'].sudo().create({'product_name':temp['product_id'],'erp_template_id':template_id.id,'presta_product_id':self._context['presta_id'],'erp_product_id':temp['product_id']})
		return temp	



	@api.model
	def create(self, vals):
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
			if vals.has_key('description'):
				vals['description'] = _unescape(vals['description'])
			if vals.has_key('description_sale'):
				vals['description_sale'] = _unescape(vals['description_sale'])
		template_id = super(ProductTemplate, self).create(vals)
		return template_id

	@api.multi
	def write(self, vals):
		map_obj = self.env['prestashop.product.template']
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
			if vals.has_key('description'):
				vals['description'] = _unescape(vals['description'])
			if vals.has_key('description_sale'):
				vals['description_sale'] = _unescape(vals['description_sale'])
		return super(ProductTemplate,self).write(vals)

	template_mapping_id = fields.One2many('prestashop.product.template', 'template_name', string='PrestaShop Information',readonly="1")
	extra_categ_ids = fields.Many2many('product.category','product_categ_rel','product_id','categ_id',string='Product Categories', domain="[('type', '=', 'normal')]",help="Select additional categories for the current product")

class ProductProduct(models.Model):	
	_inherit = 'product.product'

	@api.multi
	def check_for_new_price(self, template_id, value_id, price_extra):
		product_attribute_price=self.env['product.attribute.price']
		exists = product_attribute_price.search([('product_tmpl_id','=',template_id),('value_id','=',value_id)])
		if not exists:
			temp ={'product_tmpl_id':template_id,'value_id':value_id,'price_extra':price_extra}
			pal_id = product_attribute_price.create(temp)
			return True
		else:
			pal_id = exists[0]
			pal_id.write({'price_extra':price_extra})
			return True

	@api.multi
	def check_for_new_attrs(self, template_id, ps_attributes):
		product_template=self.env['product.template']
		product_attribute_line=self.env['product.attribute.line']
		all_values = []
		for attribute_id in ps_attributes:
			exists = product_attribute_line.search([('product_tmpl_id','=',template_id),('attribute_id','=',int(attribute_id))])
			if not exists:
				temp ={'product_tmpl_id':template_id,'attribute_id':attribute_id}
				pal_id = product_attribute_line.create(temp)
			else:
				pal_id = exists[0]
			pal_id.write({'value_ids':[[4,int(ps_attributes[attribute_id][0])]]})
			all_values.append(int(ps_attributes[attribute_id][0]))
		return [[6,0,all_values]]

	@api.model
	def create(self, vals):
		if self._context.has_key('prestashop_variant'):
			template_obj = self.env['product.template'].sudo().browse(vals['product_tmpl_id'])
			vals['name'] = template_obj.name
			vals['description'] = template_obj.description
			vals['description_sale'] = template_obj.description_sale
			vals['type'] = template_obj.type
			vals['categ_id'] = template_obj.categ_id.id
			vals['uom_id'] = template_obj.uom_id.id
			vals['uom_po_id'] = template_obj.uom_po_id.id
			vals['default_code'] = _unescape(vals['default_code'])
			if vals.has_key('ps_attributes'):
				vals['attribute_value_ids']=self.sudo().check_for_new_attrs(template_obj.id,vals['ps_attributes'])
		erp_id =  super(ProductProduct, self).create(vals)
		if self._context.has_key('prestashop_variant'):
			prestashop_product = self.env['prestashop.product']
			exists = prestashop_product.search([('erp_template_id','=',vals['product_tmpl_id']),('presta_product_attr_id','=',0)])
			if exists:
				pp_map = prestashop_product.browse(exists[0].id)
				if pp_map.product_name:
					pp_map.product_name.write({'active':False})
				exists.unlink()
			prestashop_product.sudo().create({'product_name':erp_id.id,'erp_template_id':template_obj.id,'presta_product_id':self._context['presta_id'],'erp_product_id':erp_id.id,'presta_product_attr_id':self._context['presta_attr_id']})
		return erp_id
	
	@api.multi
	def write(self, vals):
		# if context is None:
			# context = {}
		map_obj = self.env['prestashop.product']
		if not self._context.has_key('prestashop'):
			if self._ids:
				if type(self._ids) == list:
					erp_id=self._ids[0]
				else:
					erp_id=self._ids
				map_ids = map_obj.search([('erp_product_id', '=',erp_id)])
				if map_ids:
					map_ids[0].write({'need_sync':'yes'})
		if self._context.has_key('prestashop_variant'):
			if type(self._ids) == list:
				erp_id=self._ids[0]
			else:
				erp_id=self._ids
			template_obj = self.env['product.product'].browse(erp_id).product_tmpl_id
			vals['name'] = template_obj.name
			vals['description'] = template_obj.description
			vals['description_sale'] = template_obj.description_sale
			vals['type'] = template_obj.type
			vals['categ_id'] = template_obj.categ_id.id
			vals['uom_id'] = template_obj.uom_id.id
			vals['uom_po_id'] = template_obj.uom_po_id.id
			# vals['default_code'] = _unescape(vals['default_code'])
			if vals.has_key('ps_attributes'):
				vals['attribute_value_ids']=self.check_for_new_attrs(template_obj.id,vals['ps_attributes'])
			if vals.has_key('wk_extra_price'):
				if type(self._ids) == list:
					erp_id=self._ids[0]
				else:
					erp_id=self._ids
				obj = self.browse(erp_id)
				if not vals['wk_extra_price']:
					vals['wk_extra_price'] = '0.0'
				vals['wk_extra_price'] =(obj.wk_extra_price) + (float(vals['wk_extra_price'])- (obj.price_extra))

		return super(ProductProduct,self).write(vals)
	# _columns = {
	product_mapping_id = fields.One2many('prestashop.product', 'product_name', string='PrestaShop Information',readonly="1")
	# }

class ProductCategory(models.Model):	
	_inherit = 'product.category'
	
	@api.model
	def create(self, vals):
		# if context is None:
			# context = {}
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
		return super(ProductCategory, self).create(vals)
		
	@api.multi
	def write(self, vals):
		# if context is None:
			# context = {}
		map_obj = self.env['prestashop.category']
		if not self._context.has_key('prestashop'):
			if self._ids:
				if type(self._ids) == list:
					erp_id=self._ids[0]
				else:
					erp_id=self._ids
				map_ids = map_obj.search([('erp_category_id', '=',erp_id)])
				if map_ids:
					map_ids[0].write({'need_sync':'yes'})
		else:
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
		return super(ProductCategory,self).write(vals)

class ResPartner(models.Model):
	_inherit = 'res.partner'
	

	@api.model
	def create(self, vals):
		# if context is None:
			# context = {}
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
			if vals.has_key('street'):
				vals['street'] = _unescape(vals['street'])
			if vals.has_key('street2'):
				vals['street2'] = _unescape(vals['street2'])
			if vals.has_key('city'):
				vals['city'] = _unescape(vals['city'])
			partner_id = super(ResPartner, self).create(vals)
			if partner_id:
				self.env['prestashop.customer'].create({'customer_name':partner_id.id,'erp_customer_id':partner_id.id,'presta_customer_id':self._context.get('customer_id'),'presta_address_id':self._context.get('address_id')})
			return partner_id
		return super(ResPartner, self).create(vals)
	
	@api.multi
	def write(self, vals):
		# if context is None:
			# context = {}
		map_obj = self.env['prestashop.customer']
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
			if vals.has_key('street'):
				vals['street'] = _unescape(vals['street'])
			if vals.has_key('street2'):
				vals['street2'] = _unescape(vals['street2'])
			if vals.has_key('city'):
				vals['city'] = _unescape(vals['city'])
		if not self._context.has_key('prestashop'):
			record=self.env['prestashop.customer'].search([('erp_customer_id','=',self.id)])
			record.write({'need_sync':'yes'})
				
		return super(ResPartner,self).write(vals)


class DeliveryCarrier(models.Model):
	_inherit = 'delivery.carrier'
	
	@api.model
	def create(self, vals):
		if self._context.has_key('prestashop'):
			vals['name'] = _unescape(vals['name'])
			temp=self.env['res.users'].browse(self._uid)
			vals['partner_id'] = temp.company_id
			vals['product_type'] = 'service'
			vals['taxes_id'] = False
			vals['supplier_taxes_id'] = False
		return super(DeliveryCarrier, self).create(vals)

	@api.multi
	def write(self, vals):
		if self._context.has_key('prestashop'):
			vals['name'] = _unescape(vals['name'])
		return super(DeliveryCarrier, self).write(vals)	


class ProductAttribute(models.Model):	
	_inherit = 'product.attribute'
	
	@api.model
	def create(self, vals):
		# if context is None:
			# context = {}
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
		return super(ProductAttribute, self).create(vals)
		
	@api.multi
	def write(self, vals):
		# if context is None:
			# context = {}						
		if self._context.has_key('prestashop'):
			if vals.has_key('name'):
				vals['name'] = _unescape(vals['name'])
		return super(ProductAttribute,self).write(vals)

class SaleOrderLine(models.Model):
	
	_inherit = ['sale.order.line']

	@api.multi
	def _action_procurement_create(self):

		for line in self:
			if (line.order_id.ecommerce_channel == 'prestashop'):
				continue
			else:
				super(SaleOrderLine,line)._action_procurement_create()

			


class SaleOrder(models.Model):
	_inherit = "sale.order"


	def _get_ecommerces(self):
		res = super(SaleOrder, self)._get_ecommerces()
		res.append(('prestashop','Prestashop'))
		return res

	# @api.multi
	# def action_confirm(self):
	# 	for order in self:
	# 		if not (order.ecommerce_channel == 'prestashop'):
	# 			super(SaleOrder.self).action_confirm()
	# 		else:
	# 		order.state = 'sale'
	# 		order.confirmation_date = fields.Datetime.now()
	# 		if self.env.context.get('send_email'):
	# 			self.force_quotation_send()
			
	# 			order.order_line._action_procurement_create()
	# 	if self.env['ir.values'].get_default('sale.config.settings', 'auto_done_setting'):
	# 		self.action_done()
	# 	return True
	
	

	@api.multi
	def pob_generate_picking(self):
		_logger.info("=========sale================>%r",self)
		for order in self:
			_logger.info("========================>%r",order)
			conf_record = self.env['prestashop.configure'].search([('active','=',True)])
			if 'marketplace' in self._context:
				warehouse_id = conf_record.marketplace_warehouse.id
				order.warehouse_id = warehouse_id
			# order.order_line._action_procurement_create()
			precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
			new_procs = self.env['procurement.order']  # Empty recordset
			for line in order.order_line:
				_logger.info("=====================++>%r",line)
				qty = 0.0
				for proc in line.procurement_ids:
					qty += proc.product_qty
				if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
					continue

				if not line.order_id.procurement_group_id:
					vals = line.order_id._prepare_procurement_group()
					line.order_id.procurement_group_id = self.env["procurement.group"].create(vals)

				vals = line._prepare_order_line_procurement(group_id=line.order_id.procurement_group_id.id)
				vals['product_qty'] = line.product_uom_qty - qty
				new_proc = self.env["procurement.order"].create(vals)
				new_proc.message_post_with_view('mail.message_origin_link',
					values={'self': new_proc, 'origin': line.order_id},
					subtype_id=self.env.ref('mail.mt_note').id)
				new_procs += new_proc
			new_procs.run()
		# return new_procs
		return True


	def manual_prestashop_invoice(self):
		error_message=''
		status='no'
		config_id=self.env['prestashop.configure'].search([('active','=',True)])
		if not config_id:
			error_message='Connection needs one Active Configuration setting.'
			status='no'
		if len(config_id)>1:
			error_message='Sorry, only one Active Configuration setting is allowed.'
			status='no'
		else:
			# obj=self.env['prestashop.configure').browse(cr,uid,config_id[0])
			url=config_id.api_url
			key=config_id.api_key
			try:
				prestashop = PrestaShopWebServiceDict(url,key)
			except PrestaShopWebServiceError,e:
				error_message='Invalid Information, Error %s'%e
				status='no'
			except IOError, e:
				error_message='Error %s'%e
				status='no'
			except Exception,e:
				error_message="Error,Prestashop Connection in connecting: %s" % e
				status='no'
			if prestashop:
				order_id=self.env['wk.order.mapping'].get_id('prestashop','prestashop',self.ids[0])
				if order_id:
					try:
						inv_data = prestashop.get('order_invoices', options={'schema': 'blank'})
						data=prestashop.get('orders',order_id)
						inv_data['order_invoice'].update({
														'id_order' : order_id,
														'total_wrapping_tax_incl': data['order']['total_wrapping_tax_incl'],
														'total_products': data['order']['total_products'],
														'total_wrapping_tax_excl': data['order']['total_wrapping_tax_excl'],
														'total_paid_tax_incl': data['order']['total_paid_tax_incl'],
														'total_products_wt': data['order']['total_products_wt'],
														'total_paid_tax_excl': data['order']['total_paid_tax_excl'],
														'total_shipping_tax_incl': data['order']['total_shipping_tax_incl'],
														'total_shipping_tax_excl': data['order']['total_shipping_tax_excl'],
														 'delivery_number': data['order']['delivery_number'],
														 'number' : '1'
														})
						invoice=prestashop.add('order_invoices', inv_data)
					except Exception,e:
						error_message="Error %s, Error in getting Blank XML"%str(e)
						status='no'
						
				else:
					return True


	@api.multi
	def action_invoice_create(self, grouped=False, final=False):
		temp = super(SaleOrder, self).action_invoice_create(grouped, final)
		#manual_prestashop_invoice method is used to create an invoice on prestashop end...
		# if not context.has_key('prestashop'):
		# 	config_id=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])
		# 	if len(config_id)>0:
		# 		self.manual_prestashop_invoice(cr,uid,ids,context)
		return temp
	
	def manual_prestashop_invoice_cancel(self):
		error_message = ''
		status = 'yes'
		config_id = self.env['prestashop.configure'].search([('active','=',True)])
		if not config_id:
			error_message = 'Connection needs one Active Configuration setting.'
			status = 'no'
		if len(config_id) > 1:
			error_message = 'Sorry, only one Active Configuration setting is allowed.'
			status = 'no'
		else:
			# obj=self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
			url = config_id.api_url
			key = config_id.api_key
			try:
				prestashop = PrestaShopWebServiceDict(url, key)
			except PrestaShopWebServiceError,e:
				error_message = 'Invalid Information, Error %s'%e
				status = 'no'
			except IOError, e:
				error_message = 'Error %s'%e
				status = 'no'
			except Exception,e:
				error_message = "Error,Prestashop Connection in connecting: %s" % e
				status = 'no'
			if prestashop:
				_logger.info('---------------wk----------------order------------%d',self.ids[0])
				sale_id = self.env['wk.order.mapping'].search([('erp_order_id', '=', self.ids[0])])
				order_id = self.env['wk.order.mapping'].get_id('prestashop','prestashop',sale_id[0].id)
				_logger.info('---------------wk----------------%r',order_id)
				if order_id:
					try:
						order_his_data = prestashop.get('order_histories', options={'schema': 'blank'})
						order_his_data['order_history'].update({
						'id_order' : order_id,
						'id_order_state' : 6
						})
						state_update = prestashop.add('order_histories?sendemail=1', order_his_data)
					except Exception,e:
						error_message = "Error %s, Error in getting Blank XML"%str(e)
						status = 'no'
				else:
					return True

	@api.one
	def action_cancel(self):
		res = super(SaleOrder, self).action_cancel()
		config_id = self.env['prestashop.configure'].search([('active','=',True)])
		update_order_cancel = config_id.cancelled
		if self.ecommerce_channel == "prestashop" and update_order_cancel:
			self.manual_prestashop_invoice_cancel()
		return res

	def manual_prestashop_paid(self):
		# order_name = self.browse(self._ids).origin	
		sale_id = self.env['wk.order.mapping'].search([('erp_order_id', '=', self.ids[0])])
		if sale_id:
			error_message = ''
			status = 'yes'
			config_id = self.env['prestashop.configure'].search([('active','=',True)])
			if not config_id:
				error_message = 'Connection needs one Active Configuration setting.'
				status = 'no'
			if len(config_id) > 1:
				error_message = 'Sorry, only one Active Configuration setting is allowed.'
				status = 'no'
			else:
				# obj=self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
				url = config_id.api_url
				key = config_id.api_key
				try:
					prestashop = PrestaShopWebServiceDict(url, key)
				except PrestaShopWebServiceError,e:
					error_message = 'Invalid Information, Error %s'%e
					status = 'no'
				except IOError, e:
					error_message = 'Error %s'%e
					status = 'no'
				except Exception,e:
					error_message = "Error,Prestashop Connection in connecting: %s" % e
					status = 'no'
				if prestashop:
					order_id = self.env['wk.order.mapping'].get_id('prestashop','prestashop',sale_id[0].id)
					if order_id:
						try:
							order_his_data = prestashop.get('order_histories', options={'schema': 'blank'})
							order_his_data['order_history'].update({
							'id_order' : order_id,
							'id_order_state' : 2
							})
							state_update = prestashop.add('order_histories?sendemail=1', order_his_data)
						except Exception,e:
							error_message = "Error %s, Error in getting Blank XML"%str(e)
							status = 'no'							
					else:
						return True


class account_payment(models.Model):
	_inherit = "account.payment"

	@api.multi
	def post(self):
		res = super(account_payment, self).post()
		sale_obj = self.env['sale.order']
		config_id = self.env['prestashop.configure'].search([('active','=',True)])
		update_order_invoice = config_id.invoiced
		for rec in self:
			invoice_ids = rec.invoice_ids
			for inv_obj in invoice_ids:
				invoices = inv_obj.read(['origin', 'state'])
				if invoices[0]['origin']:
					sale_ids = sale_obj.search(
						[('name', '=', invoices[0]['origin'])])
					for sale_order_obj in sale_ids:
						order_id = self.env['wk.order.mapping'].search(
							[('erp_order_id', '=', sale_order_obj.id)])
						if order_id and sale_order_obj.ecommerce_channel == "prestashop" and update_order_invoice and sale_order_obj.is_invoiced:
							sale_order_obj.manual_prestashop_paid()
		return res



class account_invoice(models.Model):
	_inherit="account.invoice"


	# def confirm_paid(self):
	# 	res = super(account_invoice, self).confirm_paid()
	# 	if not context.has_key('prestashop'):
	# 		config_id = self.env['prestashop.configure'].search([('active','=',True)])
	# 		paid = config_id.invoiced
	# 		if paid:	
	# 			if len(config_id)>0:
	# 				return self.pool.get('account.invoice').manual_prestashop_paid()

	
	ps_inv_ref = fields.Char('Prestashop invoice Ref.',size=100)


class Picking(models.Model):
	_name = "stock.picking"
	_inherit = "stock.picking"

	def manual_prestashop_shipment(self):
		order_name=self.env['stock.picking'].browse(self._ids[0]).origin				
		sale_id=self.env['sale.order'].search([('name','=',order_name)])
		if sale_id:
			error_message = ''
			status = 'yes'
			config_id = self.env['prestashop.configure'].search([('active','=',True)])
			if not config_id:
				error_message = 'Connection needs one Active Configuration setting.'
				status = 'no'
			if len(config_id) > 1:
				error_message = 'Sorry, only one Active Configuration setting is allowed.'
				status = 'no'
			else:
				# obj=self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
				url = config_id.api_url
				key = config_id.api_key
				try:
					prestashop = PrestaShopWebServiceDict(url, key)
				except PrestaShopWebServiceError,e:
					error_message = 'Invalid Information, Error %s'%e
					status = 'no'
				except IOError, e:
					error_message = 'Error %s'%e
					status = 'no'
				except Exception,e:
					error_message = "Error,Prestashop Connection in connecting: %s" % e
					status = 'no'
				if prestashop:
					order_id = False
					got_id=self.env['wk.order.mapping'].search([('ecommerce_channel','=','prestashop'),('erp_order_id','=',sale_id[0].id)])
					if got_id:
						order_id = got_id[0].ecommerce_order_id
					if order_id:
						try:
							order_his_data = prestashop.get('order_histories', options={'schema': 'blank'})
							order_his_data['order_history'].update({
							'id_order' : order_id,
							'id_order_state' : 4
							})
							state_update = prestashop.add('order_histories?sendemail=1', order_his_data)
						except Exception,e:
							error_message = "Error %s, Error in getting Blank XML"%str(e)
							status = 'no'
		return True


	@api.multi
	def do_transfer(self):		
		# res = super(StockPicking, self).do_transfer()
		res = super(Picking, self).do_transfer()
		if not self._context.has_key('prestashop'):
			config_id=self.env['prestashop.configure'].search([('active','=',True)])
			shipped = config_id.delivered
			if shipped:
				if len(config_id)>0:
					self.manual_prestashop_shipment()
		return True



	# def export_tracking_no_to_prestashop(self, cr, uid, ids, context=None):
	# 	if context is None:
	# 		context = {}
	# 	get_carrier_data = []
	# 	presta_id = []
	# 	order_carrier_id = False
	# 	error_message = ''
	# 	message = ''
	# 	up_length = 0
	# 	config_id=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])
	# 	if not config_id:
	# 		raise Warning("Connection needs one Active Configuration setting.")
	# 	if len(config_id)>1:
	# 		raise Warning("Sorry, only one Active Configuration setting is allowed.")
	# 	else:
	# 		obj = self.pool.get('prestashop.configure').browse(cr,uid,config_id[0])
	# 		url = obj.api_url
	# 		key = obj.api_key
	# 		try:
	# 			prestashop = PrestaShopWebServiceDict(url,key)
	# 		except Exception,e:
	# 			raise UserError(_('Error %s' +'Invalid Information')%str(e))
	# 		if prestashop:				
	# 			picking_obj = self.pool.get('stock.picking').browse(cr, uid, ids[0])
	# 			sale_order_id = picking_obj.sale_id.id
	# 			track_ref = picking_obj.carrier_tracking_ref
	# 			if not track_ref:
	# 				track_ref = ''
	# 			if sale_order_id:
	# 				check = self.pool.get('wk.order.mapping').search(cr, uid, [('erp_order_id','=',sale_order_id)])
	# 				if check:
	# 					presta_id = self.pool.get('wk.order.mapping').browse(cr, uid, check[0]).ecommerce_order_id
	# 				if presta_id:
	# 					try:
	# 						get_carrier_data = prestashop.get('order_carriers',options={'filter[id_order]':presta_id})
	# 					except Exception,e:
	# 						error_message="Error %s, Error in getting Carrier Data"%str(e)
	# 					try:
	# 						if get_carrier_data['order_carriers']:
	# 							order_carrier_id = get_carrier_data['order_carriers']['order_carrier']['attrs']['id']
	# 						if order_carrier_id:
	# 							data = prestashop.get('order_carriers',order_carrier_id)
	# 							data['order_carrier'].update({
	# 								'tracking_number' : track_ref,					
	# 								})
	# 							try:
	# 								return_id = prestashop.edit('order_carriers',order_carrier_id, data)
	# 								up_length = up_length + 1
	# 							except Exception,e:
	# 								error_message = error_message + str(e)

	# 					except Exception,e:
	# 						error_message = error_message + str(e)
	# 		if not error_message:				
	# 			if up_length == 0:
	# 				message = "No Prestashop Order record fetched in selected stock movement record!!!"
	# 			else:
	# 				message = 'Carrier Tracking Reference Number Successfully Updated to Prestashop!!!'
	# 		else:				
	# 			message = "Error in Updating: %s"%(error_message)
	# 		partial_id = self.pool.get('pob.message').create(cr, uid, {'text':message}, context=context)
	# 		return {'name':_("Message"),
	# 				'view_mode': 'form',
	# 				'view_id': False,
	# 				'view_type': 'form',
	# 				'res_model': 'pob.message',
	# 				'res_id': partial_id,
	# 				'type': 'ir.actions.act_window',
	# 				'nodestroy': True,
	# 				'target': 'new',
	# 				'domain': context,								 
	# 			}


# class account_voucher(models.Model):
# 	_inherit="account.voucher"
	
# 	def button_proforma_voucher(self, cr, uid, ids, context=None):
# 		if context is None:
# 			context = {}
# 		# raise osv.except_osv(_('Error!'),_('context=%s')%(context))	
# 		self.signal_workflow(cr, uid, ids, 'proforma_voucher')
# 		if not context.has_key('prestashop'):
# 			config_id=self.pool.get('prestashop.configure').search(cr,uid,[('active','=',True)])	
# 			if len(config_id)>0:						
# 				self.pool.get('account.invoice').manual_prestashop_paid(cr,uid,[context['invoice_id']],context)

# 		return {'type': 'ir.actions.act_window_close'}


# Skeleton Overrides:

class wk_order_mapping(models.Model):
	_inherit = "wk.order.mapping"

	def get_id(self, shop, object, ur_id):
		ur_id = self.browse(ur_id)
		if shop == 'prestashop':
			presta_id = False
			if ur_id:
				presta_id = ur_id.ecommerce_order_id
			return presta_id
		elif shop == 'openerp':
			erp_id = False
			if ur_id:
				erp_id = ur_id.erp_order_id
			return erp_id
		else:
			return "Shop not found"
	
	def get_all_ids(self, shop, object):
		all_ids = []
		if shop == 'prestashop':
			got_ids = self.search([('ecommerce_channel','=',object)])
			for i in got_ids:
				all_ids.append(i.ecommerce_order_id)
			return all_ids
		elif shop == 'openerp':
			got_ids = self.search([('ecommerce_channel','=',object)])
			for i in got_ids:
				all_ids.append(i.erp_order_id)
			return all_ids
		else:
			return "Shop not found"

class WkSkeleton(models.TransientModel):
	_inherit = "wk.skeleton"

	def get_prestashop_configuration_data(self):
		res = {}
		search_config = self.env['prestashop.configure'].search([('active','=',True)])
		if search_config:
			# obj = self.pool.get('prestashop.configure').browse(cr, uid, search_config[0])
			_logger.info('-----------search_wh------%r-----',search_config.pob_default_stock_location.id)
			search_wh = self.env['stock.warehouse'].search([('lot_stock_id','=',search_config.pob_default_stock_location.id)])
			_logger.info('-----------search_wh------%r-----%r',search_wh.id,search_wh.name)
			res = {
					'ecommerce_channel':'prestashop',
					'order_policy':'manual',
					'team_id': search_config.team_id.id,
					'user_id': search_config.salesperson.id,
					'payment_term_id' : search_config.payment_term.id,
					'warehouse_id': search_wh.id and search_wh[0].id or False
				}
		return res

	
	def get_prestashop_virtual_product_id(self, order_line):
		if self._context.has_key('ecommerce') and self._context['ecommerce'] == "prestashop":
			if self._context.has_key('type') and self._context['type'] == 'shipping':
				carrier = self._context.get('carrier_id', False)
				if carrier:
					obj = self.env['delivery.carrier'].browse(carrier)
					erp_product_id = obj.product_id.id
			if self._context.has_key('type') and self._context['type'] == 'voucher':
				ir_values = self.env['ir.values']
				erp_product_id = ir_values.sudo().get_default('product.product', 'pob_discount_product')
				if not erp_product_id:
					erp_product_id = self.env['product.product'].create({'sale_ok':False, 'name':'Voucher', 'taxes_id':False, 'supplier_taxes_id': False,'type':'service', 'description_sale':'', 'list_price':0.0,})
					ir_values.sudo().set_default('product.product', 'pob_discount_product', erp_product_id.id)
		return erp_product_id
		# return True

	
	def turn_odoo_connection_off(self):
		""" To be inherited by bridge module for making connection Inactive on Odoo End"""
		config_values = self.env['prestashop.configure'].search([('active','=',True)])
		if config_values:
			config_values.sudo().write({'active':False})
		return config_values[0]

	def turn_odoo_connection_on(self):
		""" To be inherited by bridge module for making connection Active on Odoo End"""
		if self._context.has_key('config_id'):
			config_id=self._context['config_id']
			config_id.write({'active':True})
		return True


	# def turn_odoo_connection_off(self):
	# 	""" To be inherited by bridge module for making connection Inactive on Odoo End"""
	# 	config_values = self.env['prestashop.configure'].search([('active','=',True)])
	# 	if config_values:
	# 		config_values.sudo().write({'active':False})
	# 		self._context.update({
	# 			'config_id' : config_values[0]
	# 			})
	# 	return self._context

	# def turn_odoo_connection_on(self):
	# 	""" To be inherited by bridge module for making connection Active on Odoo End"""
	# 	if self._context.has_key('config_id'): 
	# 		config_id.write({'active':True})
	# 	return True