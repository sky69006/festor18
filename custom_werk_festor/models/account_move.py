from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    df_analytic_account = fields.Many2one('account.analytic.account', 'Kostenplaats')

    def write(self, values):
        new_values = values.copy()

        if 'df_analytic_account' in new_values:
            analytic_id = new_values.get('df_analytic_account')

            if analytic_id:
                new_values['analytic_distribution'] = {
                    str(analytic_id): 100.0
                }
            else:
                # Clear distribution if analytic is removed
                new_values['analytic_distribution'] = {}

        return super().write(new_values)

    @api.model_create_multi
    def create(self, values_list):
        new_values_list = []

        for values in values_list:
            new_values = values.copy()
            analytic_id = new_values.get('df_analytic_account')

            if analytic_id:
                new_values['analytic_distribution'] = {
                    str(analytic_id): 100.0
                }

            new_values_list.append(new_values)

        return super().create(new_values_list)

