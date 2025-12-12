from odoo import models, api

class Project(models.Model):
    _inherit = "project.project"

    @api.model
    def create(self, vals):
        project = super().create(vals)

        # Only apply if the project is linked to a sale order
        sale_order = project.sale_order_id
        if sale_order:
            client = sale_order.partner_id.name or ""
            so_name = sale_order.name or ""

            project.name = f"{client} - {so_name}"

        return project