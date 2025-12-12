from odoo import models, fields, api
from datetime import timedelta

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    start_datetime = fields.Datetime("Start Time")
    end_datetime = fields.Datetime("End Time")

    @api.depends("start_datetime", "end_datetime")
    def _compute_unit_amount_from_datetime(self):
        """
        Compute time spent (unit_amount in HOURS)
        based on start and end datetime.
        """
        for line in self:
            if line.start_datetime and line.end_datetime:
                delta = line.end_datetime - line.start_datetime
                # convert delta to hours
                hours = delta.total_seconds() / 3600
                line.unit_amount = hours
            # else: user may enter manually or stays 0

    @api.onchange("start_datetime", "end_datetime")
    def _onchange_compute_time(self):
        """Realtime UI update when user changes start or end."""
        for line in self:
            if line.start_datetime and line.end_datetime:
                delta = line.end_datetime - line.start_datetime
                line.unit_amount = delta.total_seconds() / 3600
