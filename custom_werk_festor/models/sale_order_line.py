from odoo import models, fields, api
import re

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _create_sale_order_lines_from_rental(self, rental_order):
        sale_order_lines = []
        for rental_line in rental_order.order_line:
            sale_order_line_vals = {
                'product_id': rental_line.product_id.id,
                'product_uom_qty': rental_line.product_uom_qty,
                'price_unit': rental_line.price_unit,
                'order_id': rental_order.sale_order_id.id,
                # You can adjust the name here to remove the rental period information
                'name': rental_line.product_id.name,  # This is where you modify it
            }
            sale_order_lines.append((0, 0, sale_order_line_vals))

        return sale_order_lines

    def _update_rental_order_line_description(self):
        # Override to prevent Odoo from injecting date text
        return

    def _compute_name(self):
        super()._compute_name()
        pattern = r'\n\d{2}-\d{2}-\d{4} .*'
        for line in self:
            if line.name:
                line.name = re.sub(pattern, '', line.name)

