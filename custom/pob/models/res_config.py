from odoo import api, fields, models, _
from odoo.tools.translate import _
from odoo import SUPERUSER_ID

class PobConfigSettings(models.Model):
    _name = 'pob.config.settings'
    _inherit = 'res.config.settings'
    
    @api.model
    def _install_modules(self, modules):
        """Install the requested modules.
            return the next action to execute

          modules is a list of tuples
            (mod_name, browse_record | None)
        """
        response = super(PobConfigSettings, self)._install_modules(modules)
        if response:
            if response.has_key('tag') == True:
                pob_modules = ''
                if response['tag'] == 'apps':
                    for module in response['params']['modules']:
                        if module.startswith('pob_extension'):
                            pob_modules = pob_modules+ "<h3>&#149; ' %s ' </h3><br />"%(module)
                    if pob_modules:
                        message="<h2>Following POB Extensions are not found on your odoo -</h2><br /><br />"
                        message=message+pob_modules
                        message=message+'<br /><br />Raise a Ticket at <a href="http://webkul.com/ticket/open.php" target="_blank">Click me</a>'
                        partial_id = self.env['pob.message'].create({'text':message})
                        return {
                                    'name':_("Message"),
                                    'view_mode': 'form',
                                    'view_id': False,
                                    'view_type': 'form',
                                    'res_model': 'pob.message',
                                    'res_id': partial_id.id,
                                    'type': 'ir.actions.act_window',
                                    'nodestroy': True,
                                    'target': 'new',
                                    'domain': '[]',
                                    'context': self._context
            
                                }
            else : return None                    
        return response




# _columns = {
    module_pob_extension_stock = fields.Boolean("Real-Time Stock Synchronization")
    module_pob_extension_multilang = fields.Boolean("Multi-Language Synchronization")

    pob_delivery_product = fields.Many2one('product.product',"Delivery Product",
        help="""Service type product used for Delivery purposes.""")
    pob_discount_product = fields.Many2one('product.product',"Discount Product",
        help="""Service type product used for Discount purposes.""")
    
# }
    @api.multi
    def set_default_fields(self):
        ir_values = self.env['ir.values']
        # config = self.browse(self.ids[0])
        ir_values.sudo().set_default('product.product', 'pob_delivery_product',
            self.pob_delivery_product and self.pob_delivery_product.id or False,True)
        ir_values.sudo().set_default('product.product', 'pob_discount_product',
            self.pob_discount_product and self.pob_discount_product.id or False,True)
        return True
    
    @api.multi
    def get_default_fields(self, fields):
        values = {}
        ir_values = self.env['ir.values']
        # config = self.browse(self.ids[0])
        pob_delivery_product = ir_values.sudo().get_default('product.product', 'pob_delivery_product')
        pob_discount_product = ir_values.sudo().get_default('product.product', 'pob_discount_product')
        return {'pob_discount_product':pob_discount_product,'pob_delivery_product':pob_delivery_product}
