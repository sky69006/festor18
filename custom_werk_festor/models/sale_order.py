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

        product_results = []

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

            qty_on_hand = product.qty_available
            available = qty_on_hand - qty_reserved

            product_results.append({
                'name': product.display_name,
                'needed': qty_needed,
                'on_hand': qty_on_hand,
                'reserved': qty_reserved,
                'available': available,
                'ok': available >= qty_needed,
                'conflicting': conflicting,
            })

        message = self._build_availability_html(product_results)

        wizard = self.env['rental.availability.wizard'].create({
            'result_html': message,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Beschikbaarheid verhuurproducten',
            'res_model': 'rental.availability.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _build_availability_html(self, product_results):
        if not product_results:
            return '<div style="text-align:center; padding:20px; color:#888;">Geen verhuurproducten gevonden op deze order.</div>'

        all_ok = all(p['ok'] for p in product_results)
        problems = [p for p in product_results if not p['ok']]

        # Header with summary
        if all_ok:
            header = (
                '<div style="background:#d4edda; border:1px solid #c3e6cb; border-radius:8px; '
                'padding:16px; margin-bottom:16px; text-align:center;">'
                '<span style="font-size:28px;">&#10004;</span><br/>'
                '<b style="font-size:16px; color:#155724;">Alle verhuurproducten zijn beschikbaar!</b>'
                '</div>'
            )
        else:
            header = (
                '<div style="background:#f8d7da; border:1px solid #f5c6cb; border-radius:8px; '
                'padding:16px; margin-bottom:16px; text-align:center;">'
                '<span style="font-size:28px;">&#9888;</span><br/>'
                f'<b style="font-size:16px; color:#721c24;">{len(problems)} product(en) niet volledig beschikbaar</b>'
                '</div>'
            )

        rows = ''
        for p in product_results:
            # Bar chart: show proportions
            total = max(p['on_hand'], p['needed'], 1)
            reserved_pct = min(p['reserved'] / total * 100, 100)
            needed_pct = min(p['needed'] / total * 100, 100)

            if p['ok']:
                status_color = '#28a745'
                status_icon = '&#10004;'
                status_text = 'Beschikbaar'
                row_bg = '#f0fff0'
            else:
                shortage = p['needed'] - p['available']
                status_color = '#dc3545'
                status_icon = '&#10008;'
                status_text = f'Tekort: {shortage:.0f}'
                row_bg = '#fff5f5'

            # Build conflict details
            conflict_html = ''
            if p['conflicting']:
                conflict_rows = ''
                for c in p['conflicting']:
                    period = ''
                    if c['start'] and c['end']:
                        period = f"{c['start'].strftime('%d/%m/%Y')} - {c['end'].strftime('%d/%m/%Y')}"
                    conflict_rows += (
                        f'<tr><td style="padding:2px 8px; color:#666;">{c["order"]}</td>'
                        f'<td style="padding:2px 8px; color:#666;">{c["partner"]}</td>'
                        f'<td style="padding:2px 8px; color:#666; text-align:right;">{c["qty"]:.0f}</td>'
                        f'<td style="padding:2px 8px; color:#666;">{period}</td></tr>'
                    )
                conflict_html = (
                    '<div style="margin-top:6px;">'
                    '<table style="width:100%; font-size:12px;">'
                    '<tr style="color:#999;"><td style="padding:2px 8px;">Order</td>'
                    '<td style="padding:2px 8px;">Klant</td>'
                    '<td style="padding:2px 8px; text-align:right;">Aantal</td>'
                    '<td style="padding:2px 8px;">Periode</td></tr>'
                    f'{conflict_rows}</table></div>'
                )

            # Visual bar
            bar_html = (
                '<div style="background:#e9ecef; border-radius:4px; height:20px; width:100%; position:relative; overflow:hidden;">'
                f'<div style="background:#ffc107; height:100%; width:{reserved_pct:.0f}%; position:absolute; left:0; top:0;" title="Gereserveerd: {p["reserved"]:.0f}"></div>'
                f'<div style="background:transparent; border-right:3px solid {status_color}; height:100%; width:{needed_pct:.0f}%; position:absolute; left:0; top:0;" title="Nodig: {p["needed"]:.0f}"></div>'
                '</div>'
                '<div style="display:flex; justify-content:space-between; font-size:11px; color:#888; margin-top:2px;">'
                f'<span>&#9632; Gereserveerd: {p["reserved"]:.0f}</span>'
                f'<span>Voorraad: {p["on_hand"]:.0f}</span>'
                '</div>'
            )

            rows += (
                f'<div style="background:{row_bg}; border:1px solid #dee2e6; border-radius:6px; padding:12px; margin-bottom:8px;">'
                '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
                f'<b style="font-size:14px;">{p["name"]}</b>'
                f'<span style="color:{status_color}; font-weight:bold;">{status_icon} {status_text}</span>'
                '</div>'
                '<div style="display:flex; gap:20px; margin-bottom:6px; font-size:13px;">'
                f'<span>Nodig: <b>{p["needed"]:.0f}</b></span>'
                f'<span>Voorraad: <b>{p["on_hand"]:.0f}</b></span>'
                f'<span>Gereserveerd: <b>{p["reserved"]:.0f}</b></span>'
                f'<span>Beschikbaar: <b style="color:{status_color};">{p["available"]:.0f}</b></span>'
                '</div>'
                f'{bar_html}'
                f'{conflict_html}'
                '</div>'
            )

        return header + rows

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
            