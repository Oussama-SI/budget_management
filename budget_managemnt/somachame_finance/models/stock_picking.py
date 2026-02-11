import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    def _action_done(self):
        """
        Surcharge de l'action de validation des transferts
        """
        result = super()._action_done()
        _logger.info(f"They call me for action_done")
        # Après validation, synchroniser avec les axes
        for picking in self:
            if picking._is_picking_valid_for_axis_sync():
                _logger.info(f"The picking is valid for sync")
                if picking.return_id:
                    for move in picking.return_id.move_ids:
                        if move._is_valid_for_axis_sync():
                            returned_move = self.env['stock.move'].search([
                                ('origin_returned_move_id', '=', move.id)], order='id desc', limit=1)
                            _logger.info(f"The {move} is valid for get financial axis")

                            returned_axis = returned_move._get_financial_axes('location')
                            axis = returned_move._get_financial_axes()
                            date = move.picking_id.scheduled_date.date()

                            _logger.info(f"axis : {axis} or returned axis : {returned_axis}")
                            if returned_axis:
                                returned_move._cleanup_old_axis(
                                    returned_axis,
                                    date,
                                    returned_move._calculate_earned_value_for_axis(returned_axis),
                                    0.0,
                                )
                                _logger.info(f"data d'axe de clean est : {date}")
                            elif axis:
                                _logger.info(f"He're we cum the axis for returned : {axis.complete_name}")
                                returned_move._update_axis_line_total(axis)
                else:
                    for move in picking.move_ids:
                        if move._is_valid_for_axis_sync():
                            _logger.info(f"The {move} is valid for get financial axis")
                            axis = move._get_financial_axes()
                            if axis:
                                _logger.info(f"He're we cum the axis : {axis.complete_name}")
                                move._update_axis_line_total(axis)
                            else:
                                move.returning_exception('synchronisation')
        
        return result
    
    def action_cancel(self):
        """
        Surcharge de l'action d'annulation
        """
        _logger.info(f"They call me for action_cancel")
        # Avant annulation, nettoyer les axes pour les transferts validés
        for picking in self:
            if picking._is_valid_for_axis_sync() and picking.state == 'done':
                _logger.info(f"Transfert {picking.name}: Annulation -> NETTOYAGE")
                for move in picking.move_ids:
                    if move._is_valid_for_axis_sync():
                        _logger.info(f"The picking is valid for sync to nettoyer")                        
                        axis = move._get_financial_axes()
                        if axis:
                            _logger.info(f"He're we cum the axis to clean : {axis.comlete_name}")
                            move._cleanup_old_axis(
                                axis, 
                                move._get_move_date_for_axis(),
                                move._calculate_earned_value_for_axis(axis),
                            )
                        else:
                            move.returning_exception('annulation')
        
        result = super().action_cancel()
        return result
    
    def _is_picking_valid_for_axis_sync(self):
        """Vérifie si le transfert est valide pour synchronisation"""
        return (
            self.state == 'done' and
            self.location_id and
            self.location_dest_id and 
            self.project_id
            # 'Réception Chantier' in self.location_dest_id.name and
            # self.picking_type_code == 'incoming'
        )

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def update_prices_from_purchase_orders(self):
        """
        Update standard_price from latest confirmed purchase order prices
        """
        ProductProduct = self.env['product.product']
        
        # Search for all confirmed purchase order lines
        pol_lines = self.env['purchase.order.line'].search([
            ('order_id.state', '=', 'purchase'),
            ('product_id', '!=', False)
        ], order='order_id.date_order desc, id desc')
        
        # Dictionary to store latest price per product
        product_latest_prices = {}
        
        # Get latest price for each product
        for line in pol_lines:
            product_id = line.product_id.id
            if product_id not in product_latest_prices:
                product_latest_prices[product_id] = line.price_unit
        
        # Update product standard prices
        updated_count = 0
        for product_id, latest_price in product_latest_prices.items():
            try:
                product = ProductProduct.browse(product_id)
                if product.exists() and product.standard_price != latest_price:
                    # Update the product template's standard_price
                    product.product_tmpl_id.write({'standard_price': latest_price})
                    _logger.info(
                        f"Updated {product.default_code or product.name}: "
                        f"{product.standard_price} → {latest_price}"
                    )
                    updated_count += 1
            except Exception as e:
                _logger.error(f"Error updating product {product_id}: {e}")
        
        _logger.info(f"Price update completed: {updated_count} products updated")
        return {
            'updated_count': updated_count,
            'total_products': len(product_latest_prices)
        }
    
    def cron_update_prices_from_purchase(self):
        """Method to be called by scheduled action"""
        return self.update_prices_from_purchase_orders()
