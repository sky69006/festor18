from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    #translated_product_name = fields.Text()