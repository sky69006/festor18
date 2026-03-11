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
        """Check if all rental products are available for the rental period."""
        self.ensure_one()

        if not self.rental_start_date or not self.rental_return_date:
            raise UserError("Stel eerst de eventdatum in voordat je de beschikbaarheid controleert.")

        product_results = []
        rental_start = self.rental_start_date
        rental_end = self.rental_return_date

        # Timeline window: 2 weeks before and after the rental period
        window_start = rental_start - timedelta(days=14)
        window_end = rental_end + timedelta(days=14)

        for line in self.order_line:
            product = line.product_id
            if not product or not product.rent_ok:
                continue

            qty_needed = line.product_uom_qty
            if qty_needed <= 0:
                continue

            # Get ALL rental lines for this product in the wider timeline window
            nearby_lines = self.env['sale.order.line'].search([
                ('order_id', '!=', self.id),
                ('order_id.state', 'in', ['sale', 'done']),
                ('product_id', '=', product.id),
                ('product_uom_qty', '>', 0),
                ('start_date', '<', window_end),
                ('return_date', '>', window_start),
            ])

            # Filter to only those that overlap with our rental period
            qty_reserved = 0.0
            conflicting = []
            for cl in nearby_lines:
                if cl.start_date < rental_end and cl.return_date > rental_start:
                    qty_reserved += cl.product_uom_qty
                    conflicting.append({
                        'order': cl.order_id.name,
                        'partner': cl.order_id.partner_id.display_name or '',
                        'qty': cl.product_uom_qty,
                        'start': cl.order_id.df_startDatum,
                        'end': cl.order_id.df_eindDatum,
                    })

            qty_on_hand = product.qty_available
            available = qty_on_hand - qty_reserved

            # Collect timeline events from all nearby lines
            timeline_events = []
            for cl in nearby_lines:
                timeline_events.append({
                    'start': cl.start_date,
                    'end': cl.return_date,
                    'qty': cl.product_uom_qty,
                    'order': cl.order_id.name,
                })

            product_results.append({
                'name': product.display_name,
                'needed': qty_needed,
                'on_hand': qty_on_hand,
                'reserved': qty_reserved,
                'available': available,
                'ok': available >= qty_needed,
                'conflicting': conflicting,
                'timeline_events': timeline_events,
                'window_start': window_start,
                'window_end': window_end,
                'rental_start': rental_start,
                'rental_end': rental_end,
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

    def _build_timeline_svg(self, p):
        """Build an SVG timeline chart showing virtual stock over time."""
        w = 560  # chart width
        h = 100  # chart height
        margin_left = 40
        margin_right = 10
        margin_top = 10
        margin_bottom = 30
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        window_start = p['window_start']
        window_end = p['window_end']
        total_seconds = (window_end - window_start).total_seconds() or 1

        def x_pos(dt):
            return margin_left + ((dt - window_start).total_seconds() / total_seconds) * chart_w

        # Build step function of available stock over time
        # Collect all time boundaries
        events = []
        for ev in p['timeline_events']:
            events.append((ev['start'], -ev['qty']))   # stock goes down
            events.append((ev['end'], +ev['qty']))      # stock comes back

        events.sort(key=lambda e: e[0])

        # Build the step points
        stock = p['on_hand']
        points = [(window_start, stock)]
        for dt, delta in events:
            # Add point at current level just before the change
            points.append((dt, stock))
            stock += delta
            points.append((dt, stock))
        points.append((window_end, stock))

        # Calculate y scale
        max_qty = max(p['on_hand'], p['needed'] + 1, 1)
        min_stock = min(pt[1] for pt in points)
        if min_stock < 0:
            y_min = min_stock - 1
        else:
            y_min = 0
        y_max = max_qty + 1

        def y_pos(qty):
            if y_max == y_min:
                return margin_top + chart_h / 2
            return margin_top + chart_h - ((qty - y_min) / (y_max - y_min)) * chart_h

        # Start building SVG
        svg = f'<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="font-family:sans-serif;">'

        # Background
        svg += f'<rect x="{margin_left}" y="{margin_top}" width="{chart_w}" height="{chart_h}" fill="#f8f9fa" stroke="#dee2e6" stroke-width="1"/>'

        # Highlight current rental period
        rx1 = x_pos(p['rental_start'])
        rx2 = x_pos(p['rental_end'])
        svg += f'<rect x="{rx1:.1f}" y="{margin_top}" width="{max(rx2 - rx1, 2):.1f}" height="{chart_h}" fill="#fff3cd" opacity="0.6"/>'

        # "Needed" quantity line (dashed red/green)
        needed_y = y_pos(p['needed'])
        needed_color = '#28a745' if p['ok'] else '#dc3545'
        svg += f'<line x1="{margin_left}" y1="{needed_y:.1f}" x2="{margin_left + chart_w}" y2="{needed_y:.1f}" stroke="{needed_color}" stroke-width="1" stroke-dasharray="4,3" opacity="0.7"/>'
        svg += f'<text x="{margin_left - 4}" y="{needed_y + 3:.1f}" text-anchor="end" font-size="9" fill="{needed_color}">{p["needed"]:.0f}</text>'

        # Zero line if needed
        if y_min < 0:
            zero_y = y_pos(0)
            svg += f'<line x1="{margin_left}" y1="{zero_y:.1f}" x2="{margin_left + chart_w}" y2="{zero_y:.1f}" stroke="#aaa" stroke-width="0.5" stroke-dasharray="2,2"/>'

        # Stock line - build polyline with fill
        # Area fill under the line
        area_points = []
        for dt, qty in points:
            px = x_pos(dt)
            py = y_pos(qty)
            area_points.append(f'{px:.1f},{py:.1f}')

        # Close the area to the bottom
        baseline_y = y_pos(max(y_min, 0))
        area_path = (
            f'M {x_pos(points[0][0]):.1f},{baseline_y:.1f} '
            + ' L '.join(f'{x_pos(dt):.1f},{y_pos(qty):.1f}' for dt, qty in points)
            + f' L {x_pos(points[-1][0]):.1f},{baseline_y:.1f} Z'
        )

        # Color the area: green above needed, red below
        svg += f'<path d="{area_path}" fill="#71b5e0" opacity="0.25"/>'

        # Stock step line
        line_points = ' '.join(f'{x_pos(dt):.1f},{y_pos(qty):.1f}' for dt, qty in points)
        svg += f'<polyline points="{line_points}" fill="none" stroke="#4c8dba" stroke-width="2"/>'

        # Red zone where stock < needed within the rental period
        # Find the stock level at the rental period
        for i in range(len(points) - 1):
            dt1, qty1 = points[i]
            dt2, qty2 = points[i + 1]
            # Only draw red if in or near the rental period and below needed
            seg_start = max(dt1, p['rental_start'])
            seg_end = min(dt2, p['rental_end'])
            if seg_start < seg_end and qty1 < p['needed']:
                sx1 = x_pos(seg_start)
                sx2 = x_pos(seg_end)
                sy = y_pos(qty1)
                sn = y_pos(p['needed'])
                svg += f'<rect x="{sx1:.1f}" y="{min(sy, sn):.1f}" width="{max(sx2 - sx1, 1):.1f}" height="{abs(sn - sy):.1f}" fill="#dc3545" opacity="0.2"/>'

        # On-hand line
        onhand_y = y_pos(p['on_hand'])
        svg += f'<line x1="{margin_left}" y1="{onhand_y:.1f}" x2="{margin_left + chart_w}" y2="{onhand_y:.1f}" stroke="#888" stroke-width="0.5" stroke-dasharray="2,2"/>'
        svg += f'<text x="{margin_left - 4}" y="{onhand_y + 3:.1f}" text-anchor="end" font-size="9" fill="#888">{p["on_hand"]:.0f}</text>'

        # Rental period markers
        svg += f'<line x1="{rx1:.1f}" y1="{margin_top}" x2="{rx1:.1f}" y2="{margin_top + chart_h}" stroke="#e67e00" stroke-width="1.5" stroke-dasharray="3,2"/>'
        svg += f'<line x1="{rx2:.1f}" y1="{margin_top}" x2="{rx2:.1f}" y2="{margin_top + chart_h}" stroke="#e67e00" stroke-width="1.5" stroke-dasharray="3,2"/>'

        # X-axis date labels
        num_labels = 5
        for i in range(num_labels + 1):
            frac = i / num_labels
            dt = window_start + timedelta(seconds=total_seconds * frac)
            px = margin_left + frac * chart_w
            label = dt.strftime('%d/%m')
            svg += f'<text x="{px:.1f}" y="{h - 4}" text-anchor="middle" font-size="9" fill="#888">{label}</text>'
            svg += f'<line x1="{px:.1f}" y1="{margin_top + chart_h}" x2="{px:.1f}" y2="{margin_top + chart_h + 3}" stroke="#aaa" stroke-width="0.5"/>'

        # Y-axis: 0 label
        svg += f'<text x="{margin_left - 4}" y="{y_pos(0) + 3:.1f}" text-anchor="end" font-size="9" fill="#aaa">0</text>'

        svg += '</svg>'
        return svg

    def _build_availability_html(self, product_results):
        if not product_results:
            return '<div style="text-align:center; padding:20px; color:#888;">Geen verhuurproducten gevonden op deze order.</div>'

        all_ok = all(p['ok'] for p in product_results)
        problems = [p for p in product_results if not p['ok']]

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

            # SVG timeline chart
            timeline_svg = self._build_timeline_svg(p)

            # Legend
            legend = (
                '<div style="display:flex; gap:16px; font-size:11px; color:#888; margin-top:4px; flex-wrap:wrap;">'
                '<span><span style="display:inline-block;width:12px;height:12px;background:#fff3cd;border:1px solid #e67e00;vertical-align:middle;margin-right:3px;"></span>Verhuurperiode</span>'
                '<span><span style="display:inline-block;width:12px;height:2px;background:#4c8dba;vertical-align:middle;margin-right:3px;"></span>Beschikbare voorraad</span>'
                f'<span><span style="display:inline-block;width:12px;height:1px;border-top:2px dashed {status_color};vertical-align:middle;margin-right:3px;"></span>Nodig ({p["needed"]:.0f})</span>'
                '<span><span style="display:inline-block;width:12px;height:1px;border-top:1px dashed #888;vertical-align:middle;margin-right:3px;"></span>Voorraad ({on_hand})</span>'
                '</div>'
            ).format(on_hand=f'{p["on_hand"]:.0f}')

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
                f'{timeline_svg}'
                f'{legend}'
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
            