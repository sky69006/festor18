from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_journal_dashboard_data(self):
        data = super()._get_journal_dashboard_data()

        if self.type == 'purchase':
            domain = [
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'draft'),
                ('journal_id', '=', self.id),
            ]
            moves = self.env['account.move'].search(domain)
            data['number_draft'] = len(moves)
            data['sum_draft'] = self.env['account.move']._format_value(
                sum(moves.mapped('amount_total')),
                self.currency_id,
            )

        return data