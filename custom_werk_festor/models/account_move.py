from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    df_analytic_account = fields.Many2one('account.analytic.account', 'Kostenplaats')

    def write(self, values):
        newValues = values.copy()  # IMPORTANT
        if 'df_analytic_account' in newValues:
            newValues['analytic_distribution'] = {
                str(newValues['df_analytic_account']): 100
            }

        return super(AccountMoveLine, self).write(newValues)  # IMPORTANT RETURN

    @api.model_create_multi
    def create(self, valuesList):
        newValuesList = []
        for values in valuesList:
            newValues = values.copy()  # IMPORTANT
            if 'df_analytic_account' in newValues:
                newValues['analytic_distribution'] = {
                    str(newValues['df_analytic_account']): 100
                }
            newValuesList.append(newValues)

        return super(AccountMoveLine, self).create(newValuesList)  # IMPORTANT RETURN
