from odoo import models, fields, api
import logging

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    df_koelcel_product = fields.Boolean(string='Koelcel product')
