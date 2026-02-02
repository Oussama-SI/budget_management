import logging
from odoo import models, api
from collections import defaultdict

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    def button_mark_done(self):
        """
        Validation de production avec synchro axes
        """
        res = super().button_mark_done()
        
        # Synchro après validation
        for production in self:
            if production.state == 'done':
                _logger.info(f"Synchro production terminée: {production.name}")
                production._sync_production_axes()
        
        return res
    
    # def action_cancel(self):
    #     """
    #     Annulation avec nettoyage axes
    #     """
    #     # Nettoyage avant annulation
    #     for production in self:
    #         if production.state == 'done':
    #             _logger.info(f"Nettoyage avant annulation: {production.name}")
    #             production._cleanup_production_axes()
        
    #     return super().action_cancel()
    
    def _sync_production_axes(self):
        """Synchro des mouvements de production"""
        for move in self.move_raw_ids:
            if move._is_valid_for_axis_sync():
                axis = move._get_financial_axes()
                if axis:
                    move._update_axis_line_cost(axis)
    
    def _cleanup_production_axes(self):
        """Nettoyage des axes de production"""
        for move in self.move_raw_ids:
            if move._is_valid_for_axis_sync():
                axis = move._get_financial_axes()
                if axis:
                    move._cleanup_old_axis(
                        axis,
                        move._get_move_date_for_axis(),
                        move.quantity,
                        move.product_id.standard_price,
                    )

class MrpUnbuild(models.Model):
    _inherit = "mrp.unbuild"
    
    def action_unbuild(self):
        """
        Déconstruction avec synchro axes
        """
        cleanup_info = self._prepare_axes_cleanup()
        
        result = super().action_unbuild()
        
        self._cleanup_old_axes(cleanup_info)
        
        # self._sync_unbuild_axes()
        
        return result
    
    def _prepare_axes_cleanup(self):
        """Prépare les données de nettoyage des axes"""
        cleanup_info = []
        
        if self.mo_id and self.mo_id.state == 'done':
            # Calculer le ratio de déconstruction
            # total_produced = self.mo_id.product_uom_id._compute_quantity(
            #     self.mo_id.qty_produced, self.product_uom_id
            # )
            # factor = self.product_qty / total_produced if total_produced > 0 else 0
            
            # _logger.info(f"Déconstruction ratio: {factor} (qty: {self.product_qty} / produit: {total_produced})")
            
            # Mouvements de composants à nettoyer
            for move in self.mo_id.move_raw_ids.filtered(lambda m: m.state == 'done'):
                if move._is_valid_for_axis_sync():
                    axis = move._get_financial_axes()
                    if axis:
                        # quantity = move.quantity * factor
                        cleanup_info.append({
                            'axis': axis,
                            'original_move_id': move.id,
                            'date': move._get_move_date_for_axis(),
                            # 'quantity': move.product_qty,
                            'product': move.product_id.name,
                            'price': move.product_id.standard_price,
                        })
        
        return cleanup_info
    
    def _cleanup_old_axes(self, cleanup_info):
        """Nettoie les anciens axes"""
        for info in cleanup_info:
            if info['axis']:
                # Utiliser un mouvement fictif pour le nettoyage
                move = self.env['stock.move'].search([('origin_returned_move_id', '=', info.get('original_move_id'))], limit=1, order='id desc')
                move._cleanup_old_axis(
                    info['axis'],
                    info['date'],
                    move.product_qty,
                    info['price'],
                )
                _logger.info(f"Nettoyé {move} de {info['product']}: {info['price']}DH & {move.product_qty}")
                _logger.info(f"loriginal est : {info}")
    
    def _sync_unbuild_axes(self):
        """Synchro des mouvements de déconstruction"""
        # 1. Produit déconstruit (sortie)
        for move in self.consume_line_ids:
            if move.product_id == self.product_id and move._is_valid_for_axis_sync():
                axis = move._get_financial_axes()
                if axis:
                    move._update_axis_line_cost(axis)
                    _logger.info(f"Produit déconstruit synchro: {axis.complete_name}")
        
        # 2. Composants retournés (entrée)
        for move in self.produce_line_ids:
            if move._is_valid_for_axis_sync():
                axis = move._get_financial_axes('dest')
                if axis:
                    move._update_axis_line_cost(axis)
                    _logger.info(f"Composant retour synchro: {axis.complete_name}")
