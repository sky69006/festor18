from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    df_analytic_account = fields.Many2one('account.analytic.account', 'Kostenplaats')

    def _sanitize_analytic_distribution(self, distribution):
        """Remove invalid keys (like 'False') from analytic_distribution."""
        if not distribution or not isinstance(distribution, dict):
            return distribution
        sanitized = {}
        for key, value in distribution.items():
            try:
                # Validate that all parts of a composite key are valid integers
                for part in str(key).split(","):
                    int(part)
                sanitized[key] = value
            except (ValueError, TypeError):
                continue
        return sanitized

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

        if 'analytic_distribution' in new_values:
            new_values['analytic_distribution'] = self._sanitize_analytic_distribution(
                new_values['analytic_distribution']
            )

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

            if 'analytic_distribution' in new_values:
                new_values['analytic_distribution'] = self._sanitize_analytic_distribution(
                    new_values['analytic_distribution']
                )

            new_values_list.append(new_values)

        return super().create(new_values_list)

    def _prepare_analytic_lines(self):
        """Sanitize analytic_distribution before creating analytic lines to
        prevent ValueError on invalid keys like 'False' in existing data."""
        for line in self:
            if line.analytic_distribution:
                sanitized = line._sanitize_analytic_distribution(line.analytic_distribution)
                if sanitized != line.analytic_distribution:
                    line.analytic_distribution = sanitized
        return super()._prepare_analytic_lines()

