# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api
from odoo.tools.translate import html_translate

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    x_studio_verberg_prijs = fields.Boolean(string='VerbergP', help="If set to true, the quantity will not display in report.")

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    account_line_unit_price_visibility = fields.Boolean(string='Account line unit price visibility checkbox', help="If set to true, the invoice line will not display in report and portal.")
    
    #account_line_unit_price_visibility = fields.Boolean(string='Account line unit price visibility checkbox', #help="If set to true, the invoice line will not display in report and portal.", #compute='_find_saleline_cb', store=True)
    
    #@api.model_create_multi
    #def create(self, vals_list):
        #result = super().create(vals_list)
        #_logger.info(str(result.sale_line_ids))
        #for sol in result.sale_line_ids:
        #    _logger.info('Verberg prijs ' + str(sol.id) + ': ' + str(sol.x_studio_verberg_prijs))
        #for r in result:
        #    r.account_line_unit_price_visibility = r.sale_line_cb
        #_logger.info('Result: ' + str(result))
        #return result
    
    sale_line_cb = fields.Boolean('VerbergP', compute='_find_saleline_cb', inverse="_manual_saleline_cb")
    
    def _manual_saleline_cb(self):
        pass
    
    @api.depends('sale_line_ids')
    def _find_saleline_cb(self):
        for record in self:
            record.sale_line_cb = False
            for sl in record.sale_line_ids:
                record.sale_line_cb = sl.x_studio_verberg_prijs