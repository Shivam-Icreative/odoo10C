# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import tools
from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _sales_count_pos(self):
        r = {}
        domain = [('product_id', 'in', self.ids),]
        for group in self.env['report.pos.order'].read_group(domain, ['product_id', 'product_qty'], ['product_id']):
            r[group['product_id'][0]] = group['product_qty']
        for product in self:
            product.sales_count_pos = r.get(product.id, 0)
        return r

    @api.multi
    def _sales_count_total(self):
        for product in self:
            product.sales_count_total = product.sales_count_pos + product.sales_count
        return product.sales_count_total

    sales_count_pos = fields.Integer(compute='_sales_count_pos', string='# Ventas POS')
    sales_count_total = fields.Integer(compute='_sales_count_total', string='# Ventas Totales')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    @api.depends('product_variant_ids.sales_count_pos')
    def _sales_count_pos(self):
        for product in self:
            product.sales_count_pos = sum([p.sales_count_pos for p in product.product_variant_ids])

    @api.multi
    def action_view_sales_pos(self):
        self.ensure_one()
        action = self.env.ref('product_sale_ext.action_product_sale_list_pos')
        product_ids = self.with_context(active_test=False).product_variant_ids.ids

        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': "{'default_product_id': " + str(product_ids[0]) + "}",
            'res_model': action.res_model,
            'domain': [('product_id.product_tmpl_id', '=', self.id)],
        }

    @api.multi
    @api.depends('product_variant_ids.sales_count_pos')
    def _sales_count_total(self):
        for product in self:
            product.sales_count_total = sum([p.sales_count_pos for p in product.product_variant_ids]) + sum([p.sales_count for p in product.product_variant_ids])

    sales_count_pos = fields.Integer(compute='_sales_count_pos', string='# Ventas POS')
    sales_count_total = fields.Integer(compute='_sales_count_total', string='# Ventas Totales')

class ProductoReport(models.Model):
    _name = "producto.report"
    _description = "Product Sale Statistics"
    _auto = False
    _order = 'fecha desc'

    nbr = fields.Integer(string='# Lineas', readonly=True, oldname='nbr')
    fecha = fields.Datetime(string='Fecha Pedido', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    ctd_pedida = fields.Float(string='Cantidad Pedida', readonly=True)
    ctd_entregada = fields.Float(string='Cantidad Entregada', readonly=True)
    ctd_facturada = fields.Float(string='Cantidad Facturada', readonly=True)
    price_sub_total = fields.Float(string='Subtotal', readonly=True)
    price_total = fields.Float(string='Precio Total', readonly=True)
    total_discount = fields.Float(string='Descuento Total', readonly=True)
    name = fields.Char('Pedido', readonly=True)
    state = fields.Selection(
        [('draft', 'Borrador'), ('paid', 'Pagado'), ('sale', 'Pedido de Venta'), ('done', 'Publicado o Confirmado'),
         ('invoiced', 'Facturado'), ('cancel', 'Cancelado')],
        string='Estado')
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    user_id = fields.Many2one('res.users', string='Comercial', readonly=True)
    categ_id = fields.Many2one('product.category', string='Categoria de Productos', readonly=True)
    marca = fields.Many2one('product.brand', string='Marca', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Plantilla Producto', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Lista de Precios', readonly=True)
    tipo_venta = fields.Selection([('tpv', 'TPV'), ('sale', 'Venta Directa o Web')], string='Tipo Venta', readonly=True)
    precio_costo = fields.Float(string='Precio Costo', readonly=True)
    precio_venta = fields.Float(string='Precio Venta', readonly=True)
    margen_facturado = fields.Float(string='Margen Facturado', readonly=True)
    margen_generado = fields.Float(string='Margen Generado', readonly=True)

    def _select(self) :
        select_str = """SELECT row_number() OVER (ORDER BY s.date_order) AS id,
    s.date_order AS fecha,
    l.product_id,
    round(sum(l.product_uom_qty / u.factor), 2) AS ctd_pedida,
    round(sum(l.qty_delivered / u.factor), 2) AS ctd_entregada,
    round(sum(l.qty_invoiced / u.factor), 2) AS ctd_facturada,
    round(sum(l.price_subtotal / COALESCE(1.0)), 2) AS price_sub_total,
    round(sum(l.price_total / COALESCE(1.0)), 2) AS price_total,
    round(sum(l.qty_invoiced * l.price_unit * (l.discount / 100::numeric)), 2) AS total_discount,
    s.name,
    s.state,
    s.partner_id,
    s.user_id,
    t.categ_id,
    xx.id AS marca,
    t.id AS product_tmpl_id,
    s.pricelist_id,
    'sale'::text AS tipo_venta,
    ( SELECT ff.cost
           FROM product_price_history ff
          WHERE l.product_id = ff.product_id
          ORDER BY ff.cost DESC
         LIMIT 1) AS precio_costo,
    l.price_unit AS precio_venta,
    round((l.price_unit - (( SELECT ff.cost
           FROM product_price_history ff
          WHERE l.product_id = ff.product_id
          ORDER BY ff.cost DESC
         LIMIT 1))) / NULLIF(sum(l.qty_invoiced / u.factor), 0::numeric), 2) AS margen_facturado,
    round((l.price_unit - (( SELECT ff.cost
           FROM product_price_history ff
          WHERE l.product_id = ff.product_id
          ORDER BY ff.cost DESC
         LIMIT 1))) / NULLIF(sum(l.product_uom_qty / u.factor), 0::numeric), 2) AS margen_generado
   FROM sale_order_line l
     JOIN sale_order s ON l.order_id = s.id
     JOIN res_partner partner ON s.partner_id = partner.id
     LEFT JOIN product_product p ON l.product_id = p.id
     LEFT JOIN product_template t ON p.product_tmpl_id = t.id
     LEFT JOIN product_brand xx ON t.brand_details = xx.id
     LEFT JOIN product_uom u ON u.id = l.product_uom
     LEFT JOIN product_pricelist pp ON s.pricelist_id = pp.id
  WHERE l.state::text = 'sale'::text
  GROUP BY s.name, s.date_order, s.partner_id, s.state, xx.id, s.user_id, s.company_id, s.pricelist_id, s.create_date,
  l.product_id, p.product_tmpl_id, partner.id, partner.commercial_partner_id, l.price_unit, p.id, t.categ_id, t.id, pp.id
UNION ALL
 SELECT row_number() OVER (ORDER BY s.date_order) + (( SELECT count(*) AS count
           FROM sale_order_line)) AS id,
    s.date_order AS fecha,
    l.product_id,
    round(sum(l.qty), 2) AS ctd_pedida,
    round(sum(l.qty), 2) AS ctd_entregada,
    round(sum(l.qty), 2) AS ctd_facturada,
    round(sum(l.qty * l.price_unit), 2) AS price_sub_total,
    round(sum(l.qty * l.price_unit * (100::numeric - l.discount) / 100::numeric), 2) AS price_total,
    round(sum(l.qty * l.price_unit * (l.discount / 100::numeric)), 2) AS total_discount,
    s.name,
    s.state,
    s.partner_id,
    s.user_id,
    pt.categ_id,
    xx.id AS marca,
    pt.id AS product_tmpl_id,
    s.pricelist_id,
    'tpv'::text AS tipo_venta,
    COALESCE(( SELECT ff.cost
           FROM product_price_history ff
          WHERE l.product_id = ff.product_id
          ORDER BY ff.cost DESC
         LIMIT 1), 0.0) AS precio_costo,
    l.price_unit AS precio_venta,
    round(l.price_unit - (( SELECT ff.cost
           FROM product_price_history ff
          WHERE l.product_id = ff.product_id
          ORDER BY ff.cost DESC
         LIMIT 1)) / NULLIF(sum(l.qty / u.factor), 0::numeric), 2) AS margen_facturado,
    round(l.price_unit - (( SELECT ff.cost
           FROM product_price_history ff
          WHERE l.product_id = ff.product_id
          ORDER BY ff.cost DESC
         LIMIT 1)) / NULLIF(sum(l.qty / u.factor), 0::numeric), 2) AS margen_generado
   FROM pos_order_line l
     LEFT JOIN pos_order s ON s.id = l.order_id
     LEFT JOIN res_partner part ON s.partner_id = part.id
     LEFT JOIN product_product p ON l.product_id = p.id
     LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
     LEFT JOIN product_brand xx ON pt.brand_details = xx.id
     LEFT JOIN product_uom u ON u.id = pt.uom_id
     LEFT JOIN pos_session ps ON s.session_id = ps.id
     LEFT JOIN pos_config pc ON ps.config_id = pc.id
  GROUP BY s.name, s.date_order, s.partner_id, s.state, pt.id, pt.categ_id, xx.id, s.user_id, s.pricelist_id,
  s.create_date, l.product_id, p.product_tmpl_id, part.id, part.commercial_partner_id, l.price_unit, p.id"""
        return select_str

    def _from(self) :
        from_str = """

            """
        return from_str

    def _group_by(self) :
        group_by_str = """

            """
        return group_by_str

    @api.model_cr
    def init(self) :
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
                %s

                )""" % (self._table, self._select()))
