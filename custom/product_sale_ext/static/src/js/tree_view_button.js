odoo.define('product_count.tree_view_button', function (require){
"use strict";
    var ListView = require('web.ListView');
    var Model = require('web.DataModel');
    ListView.include({
        render_buttons: function() {
            this._super.apply(this, arguments)
            if (this.$buttons) {
                var btn = this.$buttons.find('.sync_button')
                btn.on('click', this.proxy('do_sync'))
            }
       },
        do_sync: function() {
            new Model('stock.picking.control')
                .call('my_function', [[]])
        }
    });
});