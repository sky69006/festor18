from odoo import models

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_journal_dashboard_data(self):
        data = super()._get_journal_dashboard_data()

        for journal in self:
            if journal.type == 'purchase':
                domain = [
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'draft'),
                    ('journal_id', '=', journal.id),
                ]

                moves = self.env['account.move'].search(domain)

                data[journal.id].update({
                    'number_draft': len(moves),
                    'sum_draft': sum(moves.mapped('amount_total')),
                })

        return data