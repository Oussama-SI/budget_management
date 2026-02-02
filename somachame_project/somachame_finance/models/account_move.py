import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def action_post(self):
        """
        Surcharge de l'action de validation
        """
        result = super().action_post()
        
        # Après validation, synchroniser toutes les lignes
        for move in self:
            if move.move_type == 'in_invoice' and move.project_id:
                for line in move.line_ids:
                    if line._is_valid_for_axis_sync():
                        axis =  line._get_financial_axes()
                        if axis:
                            line._update_axis_line_total(axis)
                        else:
                            line.returning_exception('comptabilisation')
        
        return result
    
    def button_draft(self):
        """
        Surcharge de l'action de remise à brouillon
        """
        # Avant remise à brouillon, nettoyer les axes pour les factures validées
        for move in self:
            if move.move_type == 'in_invoice' and move.project_id and move.state == 'posted':
                _logger.info(f"Facture {move.id}: Passage à brouillon -> NETTOYAGE")
                for line in move.line_ids:
                    if line._is_valid_for_axis_sync():
                        axis = line._get_financial_axes()
                        if axis:
                            line._cleanup_old_axis(
                                axis, 
                                move.invoice_date or line.date,
                                abs(line.price_total)
                            )
                        else:
                            line.returning_exception('met en brouillans')
        
        result = super().button_draft()
        return result

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _is_valid_for_axis_sync(self):
        """Vérifie si la ligne est valide pour synchronisation"""
        return (
            self.move_id and
            self.move_id.move_type == 'in_invoice' and 
            self.move_id.project_id and
            self.display_type == 'product' and
            self.product_id
        )

    def _matches_axis(self, axis):
        """Vérifie si la ligne correspond à un axe"""
        if not axis.product_category_ids:
            return False
        
        if not self.product_id or not self.product_id.categ_id:
            return False
        
        product_categ = self.product_id.categ_id
        if product_categ in axis.product_category_ids:
            return True
        
        current = product_categ
        while current.parent_id:
            if current.parent_id in axis.product_category_ids:
                return True
            current = current.parent_id
        
        return False

    def _get_financial_axes(self):
        """Récupère les axes financiers correspondants"""
        axis = self.env['project.financial.axis']

        axes = self.env['project.financial.axis'].search([
            ('project_financial_id.project_id', '=', self.move_id.project_id.id),
            ('cost_type', '=', 'invoice')
        ])
        if axes:
            axis = axes.filtered(lambda a: self._matches_axis(a))
        return axis

    def _update_axis_line_total(self, axis):
        """Met à jour le total d'un axe"""
        AxisLine = self.env['project.financial.axis.line']
        
        date = self.invoice_date or self.date
        
        total = 0.0
        lines = self.env['account.move.line'].search([
            ('move_id.move_type', '=', 'in_invoice'),
            ('parent_state', '=', 'posted'),
            ('move_id.project_id', '=', axis.project_financial_id.project_id.id),
            ('invoice_date', '=', date),
            ('product_id', '!=', False),
            ('display_type', '=', 'product'),
        ])
        
        for line in lines:
            if line._matches_axis(axis):
                total += abs(line.price_total)
        
        axis_line = AxisLine.search([
            ('axis_id', '=', axis.id),
            ('date', '=', date)
        ], limit=1)
        
        if axis_line:
            axis_line.write({'actual_cost': total})
            _logger.info(f"we update the axis {axis_line.axis_id.name} with cost : {total}")
        elif not axis_line and total > 0:
            AxisLine.create({
                'axis_id': axis.id,
                'date': date,
                'actual_cost': total,
            })
            _logger.info(f"we create axis line for : {AxisLine.axis_id.name} with cost : {total}")

    def _cleanup_old_axis(self, axis, date, price):
        """Soustrait un montant d'un axe existant"""
        AxisLine = self.env['project.financial.axis.line']
        
        axis_line = AxisLine.search([
            ('axis_id', '=', axis.id),
            ('date', '=', date),
        ], limit=1)
        
        if axis_line and axis_line.actual_cost >= abs(price):
            remain = axis_line.actual_cost - abs(price)
            axis_line.write({'actual_cost': remain})
            _logger.info(f"we clean the axis : {axis_line.axis_id.name} with price {remain + abs(price)} to {remain}")

    # ===== CRUD METHODS =====

    @api.model_create_multi
    def create(self, vals_list):
        """Création avec synchronisation"""
        lines = super().create(vals_list)
        for line in lines:
            if line.parent_state == 'posted' and line._is_valid_for_axis_sync():
                for axis in line._get_financial_axes():
                    line._update_axis_line_total(axis)
        return lines

    # def write(self, vals):
    #     """Écriture avec synchronisation - LOGIQUE CORRECTE"""
    #     old_data = {}
    #     for line in self:
    #         if line._is_valid_for_axis_sync() and line.parent_state == 'posted':
    #             axis = line._get_financial_axes()
    #             if axis:
    #                 old_data[line.id] = {
    #                     'axes': axis,
    #                     'date': line.invoice_date or line.date,
    #                     'price': abs(line.price_total),
    #                 }
    #                 _logger.info(f"We got old value : {axis}")
        
    #     result = super().write(vals)
    #     _logger.info(f"updating : {vals} \n with result : {result}")
        
    #     for line in self:    
    #         old_info = old_data.get(line.id)
            
    #         if old_info:
    #             for axis in old_info['axes']:
    #                 line._cleanup_old_axis(axis, old_info['date'], old_info['price'])
    #                 _logger.info(f"we clean the axis with values : {old_info}")
            
    #         if not line._is_valid_for_axis_sync():
    #             continue

    #         if line.parent_state == 'posted':
    #             for axis in line._get_financial_axes():
    #                 line._update_axis_line_total(axis)
        
    #     return result
        

    def unlink(self):
        """Suppression avec nettoyage"""
        to_clean = []
        for line in self:
            if line._is_valid_for_axis_sync() and line.parent_state == 'posted':
                axes = line._get_financial_axes()
                if axes:
                    to_clean.append({
                        'axes': axes,
                        'date': line.invoice_date or line.date,
                        'price': line.price_total,
                    })
        
        result = super().unlink()
        
        for data in to_clean:
            for axis in data['axes']:
                self._cleanup_old_axis(axis, data['date'], data['price'])
        
        return result
    
    def returning_exception(self, type):
        for line in self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': (f'Facture Fournissuer : Erreur de synchronisation pour : {line.move_id.project_id.name}'),
                    'message': (
                    f'Une erreur est survenue lors de {type} des ligne de cette facture associé,\n avec les axes analytique'),
                    'type': 'danger',
                    'sticky': False,
                }
            }
