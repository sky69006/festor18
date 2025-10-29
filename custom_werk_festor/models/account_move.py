from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    df_analytic_account = fields.Many2one('account.analytic.account', 'Kostenplaats')

    def write(self, values):
        newValues = values
        if 'df_analytic_account' in values:
            newValues['analytic_distribution'] = {str(values['df_analytic_account']):100}

        result = super(AccountMoveLine, self).write(newValues)

    @api.model_create_multi
    def create(self, valuesList):
        #print(valuesList)
        newValuesList = []
        for values in valuesList:
            #print(values)
            newValues = values
            if 'df_analytic_account' in values:
                newValues['analytic_distribution'] = {str(values['df_analytic_account']): 100}
            #print(newValues)
            newValuesList.append(newValues)
        #print(newValuesList)
        res = super(AccountMoveLine, self).create(newValuesList)

class AccountMove(models.Model):
    _inherit = 'account.move'

    edi_show_force_cancel_button = fields.Boolean()
    show_update_fpos = fields.Boolean()

    def button_force_cancel(self):
        print('hi')

    def action_update_fpos_values(self):
        print('hi')