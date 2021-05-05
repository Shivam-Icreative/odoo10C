# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountReportGeneralVentas(models.TransientModel):
    _name = "account.report.general.ventas"
    _description = "General Ledger Report Ventas"

    initial_date = fields.Date(string='Fecha del Informe')

    def print_report_ventas(self, data):
        if self.initial_date:
            fecha_init = str(self.initial_date) + ' 00:00:00'
            fecha_end = str(self.initial_date) + ' 23:59:59'
            records_sale = self.env['sale.order'].search([('confirmation_date', '>=', fecha_init),('confirmation_date', '<=', fecha_end)])
            if records_sale:
                lista = []
                for datos in records_sale:
                    lista.append(datos.id)
                records_sale_encont = self.env['sale.order'].browse(lista)
                data['fecha_wizard'] = self.initial_date
                return self.env['report'].with_context().get_action(records_sale_encont, 'b92_ventas.report_ventas_b92', data=data)
            else:
                raise UserError(_("No Existen Pedidos Confirmados en la Fecha Indicada."))
        else:
            raise UserError(_("Debe Indicar una Fecha de Informe."))

class ParticularReportVentas(models.AbstractModel):
    _name = 'report.b92_ventas.report_ventas_b92'

    @api.model
    def render_html(self, docids, data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('b92_ventas.report_ventas_b92')
        lista = []
        fecha_init = str(data['fecha_wizard']) + ' 00:00:00'
        fecha_end = str(data['fecha_wizard']) + ' 23:59:59'
        records_sale = self.env['sale.order'].search([('confirmation_date', '>=', fecha_init), ('confirmation_date', '<=', fecha_end)])
        met_pay = self.env['account.payment.mode'].search([('id', '>=', 1),('payment_type', '=', 'inbound')], order='id asc')

        for l in met_pay:
            lista.append(l.id)

        metodo = self.env['account.payment.mode'].browse(lista)

        docargs = {
            'doc_ids': records_sale,
            'doc_model': 'sale.order',
            'docs': self,
            'data': data,
            'metodo': metodo
        }

        return report_obj.render('b92_ventas.report_ventas_b92', docargs)