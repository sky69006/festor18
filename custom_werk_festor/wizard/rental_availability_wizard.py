from odoo import models, fields


class RentalAvailabilityWizard(models.TransientModel):
    _name = 'rental.availability.wizard'
    _description = 'Rental Availability Check Result'

    result_html = fields.Html("Resultaat", readonly=True)
