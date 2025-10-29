from odoo import models, fields, api
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_koelcel_stock(self, nProductId, nAantal):
        nQ = 0.0
        aantalOpStockQ = self.env['stock.quant'].search([('location_id','=',60),('product_id','=',nProductId)])

        #print(aantalOpStockQ)

        if aantalOpStockQ:
            nQ = aantalOpStockQ.quantity

        #print(nQ)

        if nQ > nAantal:
            nQ = nAantal

        #print(nQ)

        return nQ


    def get_stock_koelcel(self):
        print('Getting stock koelcel')
        for record in self:
            for r in self.env['stock.quant'].search([('location_id.name','=','Koelcel')]):
                print(r)
                currentMl = self.env['stock.move'].search([('picking_id','=',record.id),('product_id','=',r.product_id.id)])
                sQ = r.inventory_quantity_auto_apply
                if currentMl:
                    currentMl.write({'product_uom_qty':sQ, 'quantity':sQ})
                else:
                    self.env['stock.move'].create({'location_id':r.location_id.id, 'location_dest_id':5, 'name':r.product_id.name, 'picking_id':record.id, 'product_id':r.product_id.id, 'product_uom_qty':sQ, 'quantity':sQ})

    def po_aanmaken_voor_dropship_rental(self):
        for record in self:
            #_logger.info('Destination: ' + record.location_dest_id.name)
            #if record.location_dest_id.name not in ['Rental', 'Verhuur']:
            #    raise  UserError("Dit is enkel maar mogelijk voor rental pickings")

            if not record.sale_id.partner_id:
                raise UserError("Geen saleorder met klant gevonden voor deze picking")

            poProducts = []
            for m in record.move_ids:
                print(m)
                if m.product_uom_qty > m.quantity:
                    poProducts.append(m)

            noSellerProducts = []
            for p in poProducts:
                seller = p.product_id.seller_ids[:1]
                if not seller:
                    noSellerProducts.append(p.product_id.display_name)

            if noSellerProducts != []:
                raise UserError("Geen leverancier voor: " + str(noSellerProducts))

            poOrderProducts = {}
            correctMoveLines = []
            for p in poProducts:
                seller = p.product_id.seller_ids[:1]
                if seller not in poOrderProducts.keys():
                    poOrderProducts[seller.partner_id.id] = [{'quantity':p.product_uom_qty - p.quantity, 'product_id':p.product_id.id}]
                else:
                    poOrderProducts[seller.partner_id.id].append({'quantity': p.product_uom_qty - p.quantity, 'product_id': p.product_id.id})

                correctMoveLines.append({'moveLineId':p.id, 'newQuantity':p.quantity})

            print(poOrderProducts)
            print(correctMoveLines)

            for k,v in poOrderProducts.items():
                po = self.env['purchase.order'].create({
                    'partner_id': k,
                    'picking_type_id': 35,
                    'dest_address_id': record.sale_id.partner_id.id,
                    'picking_ids': [record.id]
                })

                print(po)

                prodSoLine = {}

                for ol in record.sale_id.order_line:
                    prodSoLine[ol.product_id.id] = ol.id

                print(prodSoLine)

                for p in v:
                    poline = self.env['purchase.order.line'].create({
                        'product_qty': p['quantity'],
                        'product_uom_qty': p['quantity'],
                        'product_id': p['product_id'],
                        'order_id': po.id,
                        'sale_order_id': record.sale_id.id
                    })

                    if p['product_id'] in prodSoLine.keys():
                        poline['sale_line_id'] = prodSoLine[p['product_id']]

                    print(poline)

            for c in correctMoveLines:
                ml = self.env['stock.move'].search([('id','=',c['moveLineId'])])
                print(ml)

                ml.write({'product_uom_qty': c['newQuantity']})

            action = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Purchase order',
                    'message': str(len(poOrderProducts)) + ' po(s) aangemaakt',
                    'sticky': False,  # True/False will display for few seconds if false
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            return action




