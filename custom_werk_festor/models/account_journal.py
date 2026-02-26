from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    purchase_draft_count = fields.Integer(
        compute='_compute_purchase_draft',
    )
    purchase_draft_amount = fields.Monetary(
        compute='_compute_purchase_draft',
        currency_field='currency_id',
    )

    @api.depends('type')
    def _compute_purchase_draft(self):
        for journal in self:
            if journal.type == 'purchase':
                moves = self.env['account.move'].search([
                    ('move_type', '=', 'in_invoice'),
                    ('state', '=', 'draft'),
                    ('journal_id', '=', journal.id),
                ])
                journal.purchase_draft_count = len(moves)
                journal.purchase_draft_amount = sum(moves.mapped('amount_total'))
            else:
                journal.purchase_draft_count = 0
                journal.purchase_draft_amount = 0

    def open_purchase_draft_bills(self):
        action = self.open_action()
        action.pop('domain', None)
        ctx = dict(action.get('context', {}))
        ctx['search_default_unposted'] = 1
        ctx['search_default_vendor_bills_only'] = 1
        ctx['default_move_type'] = 'in_invoice'
        action['context'] = ctx
        return action
