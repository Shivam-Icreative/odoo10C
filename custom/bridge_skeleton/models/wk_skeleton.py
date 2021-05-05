#!/usr/bin/env python
# -*- coding: utf-8 -*-
##########################################################################
#
#    Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
##########################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


def _unescape(text):
    from urllib import unquote_plus
    try:
        string = unquote_plus(text.encode('utf8'))
    except:
        string = text
    return string


class WkSkeleton(models.TransientModel):
    _name = "wk.skeleton"
    _description = " Skeleton for all XML RPC imports in Odoo"

    @api.model
    def turn_odoo_connection_off(self):
        """ To be inherited by bridge module for making connection Inactive on Odoo End"""
        return {}

    @api.model
    def turn_odoo_connection_on(self):
        """ To be inherited by bridge module for making connection Active on Odoo End"""
        return {}

    @api.model
    def set_extra_values(self):
        """ Add extra values"""
        return True
    # Order Status Updates

    @api.model
    def set_order_cancel(self, order_id):
        """Cancel the order in Odoo via requests from XML-RPC  
                @param order_id: Odoo Order ID
                @param context: Mandatory Dictionary with key 'ecommerce' to identify the request from E-Commerce
                @return: A dictionary of status and status message of transaction"""
        context = dict(self._context or {})
        status = True
        status_message = "Order Successfully Cancelled."
        try:
            sale = self.env['sale.order'].browse(order_id)
            if sale.invoice_ids:
                for invoice in sale.invoice_ids:
                    invoice.journal_id.update_posted = True
                    if invoice.state == "paid":
                        for payment in invoice.payment_ids:
                            voucher_ids = self.env['account.voucher'].search(
                                [('move_ids.name', '=', payment.name)])
                            if voucher_ids:
                                for voucher in voucher_ids:
                                    voucher.journal_id.update_posted = True
                                    voucher.cancel_voucher()
                    invoice.action_cancel()
            if sale.picking_ids:
                for picking in sale.picking_ids:
                    if picking.state == "done":
                        status = False
                        status_message = 'Cannot cancel a Shipped Order!!!'
                        break
                    picking.action_cancel()
            sale.action_cancel()
        except Exception, e:
            status = False
            status_message = "Error in Cancelling Order: " % str(e)
        finally:
            return {
                'status_message': status_message,
                'status': status
            }

    @api.model
    def set_order_shipped(self, order_id):
        """Cancel the order in Odoo via requests from XML-RPC  
        @param order_id: Odoo Order ID
        @param context: Mandatory Dictionary with key 'ecommerce' to identify the request from E-Commerce
        @return:  A dictionary of status and status message of transaction"""
        context = dict(self._context or {})
        status = True
        ctx={}
        status_message = "Order Successfully Shipped."
        try:
            sale = self.env['sale.order'].browse(order_id)
            _logger.info("=========sale================>%r",[sale,order_id])
            sale.with_context(context).pob_generate_picking()
            if sale.state == 'draft':
                self.confirm_odoo_order([order_id])
            # _logger.info("===========sale========+>%r",sale.read())
            if sale.picking_ids:
                _logger.info("=========sale.picking_ids================>%r",sale.picking_ids)
                config_id=self.turn_odoo_connection_off()
                ctx={}
                ctx['config_id']=config_id
                for picking in sale.picking_ids:
                    backorder = False
                    if picking.state != 'done':
                        context['active_id'] = picking.id
                        context['picking_id'] = picking.id
                        _logger.info("=========================>%r",picking.pack_operation_ids)
                        picking.force_assign()
                        for pack in picking.pack_operation_ids:
                            _logger.info("=========================>%r",pack)
                            if pack.qty_done and pack.qty_done < pack.product_qty:
                                backorder = True
                                continue
                            elif pack.product_qty > 0:
                                pack.write({'qty_done': pack.product_qty})
                            else:
                                pack.unlink()
                        if backorder:
                            backorder_obj = self.env['stock.backorder.confirmation'].create(
                                {'pick_id': picking.id})
                            backorder_obj.process_cancel_backorder()
                        else:
                            picking.do_transfer()
                        self.set_extra_values()
        except Exception, e:
            status = False
            status_message = "Error in Delivering Order: " % str(e)
        finally:
            self.with_context(ctx).turn_odoo_connection_on()
            return {
                'status_message': status_message,
                'status': status
            }

    @api.model
    def set_order_paid(self, payment_data):
        """Make the order Paid in Odoo via requests from XML-RPC  
        @param payment_data: A standard dictionary consisting of 'order_id', 'journal_id', 'amount'
        @param context: A Dictionary with key 'ecommerce' to identify the request from E-Commerce
        @return:  A dictionary of status and status message of transaction"""
        context = dict(self._context or {})
        status = True
        counter = 0
        draft_invoice_ids = []
        invoice_id = False
        ecommerce_invoice_id = False
        status_message = "Payment Successfully made for Order."
        try:
            # Turn off active connection so that invoice sync will stop fro
            config_id=self.turn_odoo_connection_off()
            ctxt={}
            ctxt['config_id']=config_id
            journal_id = payment_data.get('journal_id', False)
            sale_obj = self.env['sale.order'].browse(payment_data['order_id'])
            if not sale_obj.invoice_ids:
                if payment_data.has_key('ecommerce_invoice_id'):
                    ecommerce_invoice_id = payment_data['ecommerce_invoice_id']

                create_invoice = self.create_order_invoice(
                    payment_data['order_id'], ecommerce_invoice_id)
                if create_invoice['status']:
                    draft_invoice_ids.append(create_invoice['invoice_id'])
                    draft_amount = self.env['account.invoice'].browse(
                        create_invoice['invoice_id']).amount_total
            elif sale_obj.invoice_ids:
                # currently supporting only one invoice per sale order to be
                # paid
                for invoice in sale_obj.invoice_ids:
                    if invoice.state == 'open':
                        invoice_id = invoice.id
                    elif invoice.state == 'draft':
                        draft_invoice_ids.append(invoice.id)
                    counter += 1
            if counter <= 1:
                if draft_invoice_ids:
                    invoice_id = draft_invoice_ids[0]
                    invoice_obj = self.env[
                        'account.invoice'].browse(invoice_id)
                    invoice_obj.action_invoice_open()
                # Setting Context for Payment Wizard
                ctx = {'default_invoice_ids': [[4, invoice_id, None]], 'active_model': 'account.invoice', 'journal_type': 'sale','config_id':config_id.id,
                       'search_disable_custom_filters': True, 'active_ids': [invoice_id], 'type': 'out_invoice', 'active_id': invoice_id}
                context.update(ctx)
                # Getting all default field values for Payment Wizard
                fields = ['communication', 'currency_id', 'invoice_ids', 'payment_difference', 'partner_id', 'payment_method_id', 'payment_difference_handling',
                          'journal_id', 'state', 'writeoff_account_id', 'payment_date', 'partner_type', 'hide_payment_method', 'payment_method_code', 'amount', 'payment_type']
                default_vals = self.env['account.payment'].with_context(
                    context).default_get(fields)
                payment_method_id = self.with_context(
                    context).get_default_payment_method(journal_id)
                default_vals.update(
                    {'journal_id': journal_id, 'payment_method_id': payment_method_id})
                invoice_date = self.env['account.invoice'].browse(
                    invoice_id).date_invoice
                default_vals['payment_date'] = invoice_date
                payment = self.env['account.payment'].create(default_vals)
                paid = payment.post()
            else:
                status = False
                status_message = "Multiple validated Invoices found for the Odoo order. Cannot make Payment"
        except Exception, e:
            status_message = "Error in creating Payments for Invoice: " % str(
                e)
            status = False
        finally:
            self.with_context(ctxt).turn_odoo_connection_on()
            return {
                'status_message': status_message,
                'status': status
            }

    @api.model
    def get_default_payment_method(self, journal_id):
        """ @params journal_id: Journal Id for making payment
                @params context : Must have key 'ecommerce' and then return payment payment method based on Odoo Bridge used else return the default payment method for Journal
                @return: Payment method ID(integer)"""
        payment_method_ids = self.env['account.journal'].browse(
            journal_id)._default_inbound_payment_methods()
        if payment_method_ids:
            return payment_method_ids[0].id
        return False

    @api.model
    def get_default_configuration_data(self, ecommerce_channel):
        """@return: Return a dictionary of Sale Order keys by browsing the Configuration of Bridge Module Installed"""
        if hasattr(self, 'get_%s_configuration_data' % ecommerce_channel):
            return getattr(self, 'get_%s_configuration_data' % ecommerce_channel)()
        else:
            return False

    @api.model
    def create_order_mapping(self, map_data):
        """Create Mapping on Odoo end for newly created order
        @param order_id: Odoo Order ID
        @context : A dictionary consisting of e-commerce Order ID"""

        self.env['wk.order.mapping'].create(map_data)
        return True

    @api.model
    def create_order(self, sale_data):
        """ Create Order on Odoo along with creating Mapping
        @param sale_data: dictionary of Odoo sale.order model fields
        @param context: Standard dictionary with 'ecommerce' key to identify the origin of request and
                                        e-commerce order ID.	
        @return: A dictionary with status, order_id, and status_message"""
        context = dict(self._context or {})
        # check sale_data for min no of keys presen or not
        order_name, order_id, status, status_message = "", False, True, "Order Successfully Created."
        config_data = self.get_default_configuration_data(
            sale_data['ecommerce_channel'])
        sale_data.update(config_data)

        try:
            _logger.info('-----------sale_data----------%r',sale_data)
            if 'presta_module' in sale_data:
                payment_mapping = self.env['prestashop.payment.mode'].search([
                    ('payment_mode_id', '!=', False),
                    ('presta_payment', '=', sale_data['presta_module'])
                ])
                if payment_mapping:
                    sale_data['payment_mode_id'] = payment_mapping.payment_mode_id.id
            order_obj = self.env['sale.order'].create(sale_data)
            order_id = order_obj.id
            order_name = order_obj.name
            self.create_order_mapping({
                'ecommerce_channel': sale_data['ecommerce_channel'],
                'erp_order_id': order_id,
                'ecommerce_order_id': sale_data['ecommerce_order_id'],
                'name': sale_data['origin'],
            })
        except Exception, e:
            status_message = "Error in creating order on Odoo: %s" % str(e)
            status = False
        finally:
            return {
                'order_id': order_id,
                'order_name': order_name,
                'status_message': status_message,
                'status': status
            }

    @api.model
    def create_sale_order_line(self, order_line_data):
        """Create Sale Order Lines from XML-RPC
        @param order_line_data: A dictionary of Sale Order line fields in which required field(s) are 'order_id', `product_uom_qty`, `price_unit`
                `product_id`: mandatory for non shipping/voucher order lines
        @return: A dictionary of Status, Order Line ID, Status Message  """
        context = dict(self._context or {})
        status = True
        order_line_id = False
        status_message = "Order Line Successfully Created."
        try:
            # To FIX:
            # Cannot call Onchange in sale order line
            product_obj = self.env['product.product'].browse(
                order_line_data['product_id'])
            order_line_data.update({'product_uom': product_obj.uom_id.id})
            if 'name' in order_line_data:
                brand_name = ''
                if product_obj and product_obj.brand_details:
                    brand_name = product_obj.brand_details.brand_name + ' '
                order_line_data['name'] =  _unescape(
                    brand_name + order_line_data['name'])
            else:
                if product_obj and product_obj.brand_details:
                    brand_name = product_obj.brand_details.brand_name
                    name = brand_name + ' ' + (product_obj.description_sale or \
                                               product_obj.name)
                else:
                    name = product_obj.description_sale or product_obj.name
                order_line_data.update({'name': name})
            order_line_id = self.env['sale.order.line'].create(
                order_line_data).id
        except Exception, e:
            status_message = "Error in creating order Line on Odoo: " % str(e)
            status = False
        finally:
            return {
                'order_line_id': order_line_id,
                'status': status,
                'status_message': status_message
            }

    @api.model
    def create_order_shipping_and_voucher_line(self, order_line):
        """ @params order_line: A dictionary of sale ordre line fields
                @params context: a standard odoo Dictionary with context having keyword to check origin of fumction call and identify type of line for shipping and vaoucher
                @return : A dictionary with updated values of order line"""
        product_id = self.get_default_virtual_product_id(order_line)
        if type(product_id)!= int:
            order_line['product_id'] = product_id.id
        else:
            order_line['product_id'] = product_id
        res = self.create_sale_order_line(order_line)
        return res


    @api.model
    def get_default_virtual_product_id(self, order_line):
        ecommerce_channel = order_line['ecommerce_channel']
        if hasattr(self, 'get_%s_virtual_product_id' % ecommerce_channel):
            return getattr(self, 'get_%s_virtual_product_id' % ecommerce_channel)(order_line)
        else:
            return False

    @api.model
    def confirm_odoo_order(self, order_id):
        """ Confirms Odoo Order from E-Commerce
        @param order_id: Odoo/ERP Sale Order ID
        @return: a dictionary of True or False based on Transaction Result with status_message"""
        if isinstance(order_id, (int, long)):
            order_id = [order_id]
        context = dict(self._context or {})
        status = True
        status_message = "Order Successfully Confirmed!!!"
        try:
            sale_obj = self.env['sale.order'].browse(order_id)
            sale_obj.action_confirm()
        except Exception, e:
            status_message = "Error in Confirming Order on Odoo: " % str(e)
            status = False
        finally:
            return {
                'status': status,
                'status_message': status_message
            }

    @api.model
    def create_order_invoice(self, order_id, ecommerce_invoice_id=False):
        """Creates Order Invoice by request from XML-RPC.
        @param order_id: Odoo Order ID
        @return: a dictionary containig Odoo Invoice IDs and Status with Status Message
        """
        context = dict(self._context or {})
        invoice_id = False
        status = True
        status_message = "Invoice Successfully Created."
        try:
            sale_obj = self.env['sale.order'].browse(order_id)
            invoice_id = sale_obj.invoice_ids.ids
            if sale_obj.state == 'draft':
                self.confirm_odoo_order(order_id)
            if not invoice_id:
                invoice_id = sale_obj.action_invoice_create()
                if ecommerce_invoice_id and invoice_id:
                    invoice_obj = self.env[
                        'account.invoice'].browse(invoice_id)
                    # EDIT BY QUBIQ
                    invoice_obj.write({'name': "e-commerce: jcApotecari.com"})
            else:
                status = False
                status_message = "Invoice Already Created"
        except Exception, e:
            status = False
            status_message = "Error in creating Invoice: " % str(e)
        finally:
            if invoice_id:
                return {
                    'status': status,
                    'status_message': status_message,
                    'invoice_id': invoice_id[0]
                }
            else:
                return {
                    'status': status,
                    'status_message': status_message
                }


############## Mapping classes #################
class WkOrderMapping(models.Model):
	_name="wk.order.mapping"

# _columns = {
	name = fields.Char('eCommerce Order Ref.',size=100)
	ecommerce_channel = fields.Selection(related= 'erp_order_id.ecommerce_channel', string="eCommerce Channel")
	erp_order_id = fields.Many2one('sale.order', 'ODOO Order Id',required=1)
	ecommerce_order_id = fields.Integer('eCommerce Order Id',required=1)
# }
WkOrderMapping()