
from odoo import models, fields, api


class CustomReportInvoiceWithPayment(models.AbstractModel):
    _name = 'report.custom_invoice_report.invoice_report_customisation'
    _description = 'Account report with payment lines'
    _inherit = 'report.account.report_invoice_with_payments'

    # @api.model
    # def _get_report_values(self, docids, data=None):
    #     rslt = super()._get_report_values(docids, data)
    #     return rslt