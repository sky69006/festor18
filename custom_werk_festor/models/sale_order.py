from odoo import models, fields, api
import logging
from datetime import date, datetime
from datetime import datetime, timedelta

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Resource(models.Model):
    _inherit = 'resource.resource'

    df_sale_order_id = fields.Integer("Sale order id voor planning Festor")


class PlanningSlot(models.Model):
    _inherit = 'planning.slot'
    df_saleorder_id = fields.Integer("Sale order id voor planning Festor")

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'
    df_saleorder_id = fields.Integer("Sale order id voor planning Festor")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    df_startDatum = fields.Datetime("Van/tot event")
    df_eindDatum = fields.Datetime("Einde event")

    df_datum_event_rapport = fields.Char("Datum event rapport", compute="_datum_rapport")

    df_archived_old_leads = fields.Boolean("Oude leads gearchiveerd", default=False)

    x_studio_aantal_personen = fields.Integer("Aantal personen")

    def action_verify_rental_availability(self):
        """Check if all rental products are available for the event period."""
        self.ensure_one()

        if not self.rental_start_date or not self.rental_return_date:
            raise UserError("Stel eerst de eventdatum in voordat je de beschikbaarheid controleert.")

        problems = []

        for line in self.order_line:
            product = line.product_id
            if not product or not product.rent_ok:
                continue

            qty_needed = line.product_uom_qty
            if qty_needed <= 0:
                continue

            # Find all OTHER confirmed/done sale orders with overlapping rental periods
            overlapping_orders = self.env['sale.order'].search([
                ('id', '!=', self.id),
                ('state', 'in', ['sale', 'done']),
                ('rental_start_date', '<', self.rental_return_date),
                ('rental_return_date', '>', self.rental_start_date),
            ])

            # Sum quantities reserved by overlapping orders for this product
            qty_reserved = 0.0
            conflicting = []
            for other_order in overlapping_orders:
                for other_line in other_order.order_line:
                    if other_line.product_id == product and other_line.product_uom_qty > 0:
                        qty_reserved += other_line.product_uom_qty
                        conflicting.append({
                            'order': other_order.name,
                            'partner': other_order.partner_id.display_name or '',
                            'qty': other_line.product_uom_qty,
                            'start': other_order.df_startDatum,
                            'end': other_order.df_eindDatum,
                        })

            # Get total on-hand stock
            qty_on_hand = product.qty_available

            available = qty_on_hand - qty_reserved
            if available < qty_needed:
                detail_lines = []
                for c in conflicting:
                    period = ''
                    if c['start'] and c['end']:
                        period = f" ({c['start'].strftime('%d/%m/%Y')} - {c['end'].strftime('%d/%m/%Y')})"
                    detail_lines.append(
                        f"  - {c['order']} / {c['partner']}: {c['qty']:.0f} stuks{period}"
                    )

                problems.append(
                    f"<b>{product.display_name}</b>: {qty_needed:.0f} nodig, "
                    f"{qty_on_hand:.0f} op voorraad, {qty_reserved:.0f} al gereserveerd "
                    f"→ <b>{available:.0f} beschikbaar</b> (tekort: {qty_needed - available:.0f})\n"
                    + "\n".join(detail_lines)
                )

        if problems:
            message = "<br/><br/>".join(problems)
        else:
            message = "Alle verhuurproducten zijn beschikbaar voor deze periode!"

        return {
            'type': 'ir.actions.act_window',
            'name': 'Beschikbaarheid verhuurproducten',
            'res_model': 'ir.ui.view',
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'readonly'},
            'context': {
                'default_name': message,
            },
        } if False else {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Beschikbaarheid verhuurproducten',
                'message': message,
                'type': 'danger' if problems else 'success',
                'sticky': True,
            },
        }

    def df_analyze(self):
        for record in self:
            for ol in record.order_line:
                print(ol.read())

        self._split_order_lines_before_picking()

    def action_confirm(self):
        for order in self:
            order._split_order_lines_before_picking()

        # Proceed with the standard confirmation (which creates the picking)
        return super(SaleOrder, self).action_confirm()

    def _split_order_lines_before_picking(self):
        for order in self:
            prodsToOrder = []
            for ol in order.order_line:
                if ol.virtual_available_at_date < ol.product_uom_qty:
                    prodsToOrder.append({'olId':ol.id, 'productId':ol.product_id.id, 'qOrdered':ol.product_uom_qty, 'qAvailable':ol.virtual_available_at_date, 'product':ol.product_id})

            print(prodsToOrder)

            #rent ok added
            warnings = []
            for p in prodsToOrder:
                if p['product'].rent_ok == True:
                    seller = p['product'].seller_ids[:1]

                    print(seller.read())

                    if not seller:
                        warnings.append(p['product'].display_name)

            if warnings != []:
                raise UserError("Geen leverancier voor: " + str(warnings))

    def _datum_rapport(self):
        for record in self:
            if record.df_startDatum != False and record.df_eindDatum != False:
                verschil = record.df_eindDatum.date() - record.df_startDatum.date()
                if verschil.days <= 1:
                    record.df_datum_event_rapport = record.df_startDatum.strftime("%d/%m/%Y")
                else:
                    record.df_datum_event_rapport = record.df_startDatum.strftime("%d/%m/%Y") + ' tot ' + record.df_eindDatum.strftime("%d/%m/%Y")
            elif record.x_studio_datum_event != False:
                record.df_datum_event_rapport = record.x_studio_datum_event.strftime("%d/%m/%Y")
            else:
                record.df_datum_event_rapport = ''

    def write(self, values):
        print('Saving... ' + str(values))
        result = super(SaleOrder, self).write(values)
        if self.state == 'cancel':
            calendarId = self.env['calendar.event'].search([('df_saleorder_id', '=', self.id)])
            if calendarId.id != False:
                calendarId.unlink()
        else:
            print('updating')

            self.createUpdateEvent()

        return result

    def unlink(self):
        if self.id != False:
            calendarId = self.env['calendar.event'].search([('df_saleorder_id', '=', self.id)])
            if calendarId.id != False:
                calendarId.unlink()
        return super(SaleOrder, self).unlink()

    def createUpdateEvent(self):
        self.ensure_one()

        if not self.df_startDatum or not self.df_eindDatum:
            return

        if self.env.uid == 14:
            return

        calendar = self.env['calendar.event'].search([('df_saleorder_id', '=', self.id)], limit=1)

        suffix = ' [Offerte]' if self.state in ['sent', 'draft'] else ''
        name = f"{self.display_name} - {self.partner_id.display_name}{suffix}"

        needs_update = not calendar or (
                calendar.start != self.df_startDatum or
                calendar.stop != self.df_eindDatum or
                calendar.name != name
        )

        if needs_update:
            event_vals = {
                'current_attendee': self.env.uid,
                'name': name,
                'start': self.df_startDatum,
                'stop': self.df_eindDatum,
                'df_saleorder_id': self.id
            }

            if calendar:
                calendar.write(event_vals)
            else:
                self.env['calendar.event'].create(event_vals)

        # Update rental dates
        rental_start = self.df_startDatum - timedelta(hours=12)
        rental_end = self.df_eindDatum + timedelta(hours=12)

        if (not self.rental_start_date or not self.rental_return_date or
                self.rental_start_date != rental_start or
                self.rental_return_date != rental_end):
            self.write({
                'rental_start_date': rental_start,
                'rental_return_date': rental_end
            })

    def archiveOldLeads(self):
        allSos = self.env['sale.order'].search([('opportunity_id', '!=', False),('state','=','sale'),('df_archived_old_leads','=',False)])

        _logger.info('Start run...')
        for a in allSos:
            _logger.info(str(a))
            
            today = date.today()
            
            datumEvent = a.x_studio_datum_event
            
            _logger.info(str(datumEvent))
            _logger.info(str(today))
            
            if datumEvent != False and today > datumEvent:
                _logger.info('Here')
                a.opportunity_id.stage_id = 9
                a.df_archived_old_leads = True
                _logger.info('Work done')
            