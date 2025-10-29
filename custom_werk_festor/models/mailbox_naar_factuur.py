from odoo import models, fields, api


class MailboxNaarAccMove(models.AbstractModel):
    _inherit = 'account.move'

class FetchMailOverride(models.AbstractModel):
    _inherit = 'fetchmail.server'

    def haalMailsOp(self):
        self._fetch_mails()
