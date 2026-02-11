import logging
from odoo import models, api, fields
from collections import defaultdict

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
    
    def _sync_all_project_invoices_old(self, cleanup=False):
        """
        Synchronise TOUTES les factures du projet avec les axes financiers
        """
        if not self.project_id:
            return False
        
        # Récupérer toutes les factures du projet
        all_invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('project_id', '=', self.project_id.id)
        ])
        
        # Récupérer le projet financier
        financial_progress = self.env['project.financial.progress'].search([
            ('project_id', '=', self.project_id.id)
        ], limit=1)
        
        if not financial_progress:
            _logger.warning(f"Aucun projet financier trouvé pour le projet {self.project_id.name}")
            return False
        
        # Récupérer tous les axes de type invoice
        invoice_axes = financial_progress.axis_ids.filtered(
            lambda a: a.cost_type == 'invoice'
        )
        
        # Pour chaque axe, calculer le total de TOUTES les factures
        for axis in invoice_axes:
            # Dictionnaire pour stocker les totaux par date
            totals_by_date = {}
            
            if not cleanup:
                # Parcourir toutes les factures du projet
                for invoice in all_invoices:
                    invoice_date = invoice.invoice_date or invoice.date
                    date_str = invoice_date.strftime('%Y-%m-%d') if invoice_date else fields.Date.today().strftime('%Y-%m-%d')
                    
                    # Initialiser le total pour cette date si nécessaire
                    if date_str not in totals_by_date:
                        totals_by_date[date_str] = 0.0
                    
                    # Ajouter les montants des lignes qui correspondent à l'axe
                    for line in invoice.line_ids:
                        if line._is_valid_for_axis_sync() and line._matches_axis(axis):
                            totals_by_date[date_str] += abs(line.price_total)
            
            # Mettre à jour les lignes d'axe pour chaque date
            for date_str, total in totals_by_date.items():
                # Rechercher ou créer la ligne d'axe
                AxisLine = self.env['project.financial.axis.line']
                axis_line = AxisLine.search([
                    ('axis_id', '=', axis.id),
                    ('date', '=', date_str),
                ], limit=1)
                
                if axis_line:
                    if cleanup:
                        # Si cleanup, soustraire la valeur
                        new_value = max(0, axis_line.actual_cost - total)
                        axis_line.write({'actual_cost': new_value})
                        _logger.info(f"Axe {axis.name}: nettoyage {total} → {new_value}")
                    else:
                        # Sinon, remplacer par le nouveau total
                        axis_line.write({'actual_cost': total})
                        _logger.info(f"Axe {axis.name}: mise à jour {total}")
                else:
                    if not cleanup and total > 0:
                        # Créer une nouvelle ligne si pas de cleanup et total > 0
                        AxisLine.create({
                            'axis_id': axis.id,
                            'date': date_str,
                            'actual_cost': total,
                        })
                        _logger.info(f"Axe {axis.name}: création ligne {total} à {date_str}")
        
        _logger.info(f"Toutes les factures du projet {self.project_id.name} synchronisées avec axes")
        return True
    
    def _sync_invoice_to_axes(self):
        """Synchronise une facture avec ses axes"""
        if not self.project_id or self.move_type != 'in_invoice' or self.state != 'posted':
            return False
        
        _logger.info(f"Synchronisation facture {self.name} avec axes")
        
        # Regrouper les totaux par axe et par date
        axis_totals = defaultdict(lambda: defaultdict(float))
        
        # Date de la facture
        invoice_date = self.invoice_date or self.date
        date_str = invoice_date.strftime('%Y-%m-%d') if invoice_date else fields.Date.today().strftime('%Y-%m-%d')
        
        # Parcourir les lignes de la facture
        for line in self.line_ids:
            if not line._is_valid_for_axis_sync():
                continue
            
            axes = line._get_financial_axes()
            for axis in axes:
                axis_totals[axis.id][date_str] += abs(line.price_total)
        
        # Mettre à jour les lignes d'axe
        AxisLine = self.env['project.financial.axis.line']
        
        for axis_id, date_values in axis_totals.items():
            axis = self.env['project.financial.axis'].browse(axis_id)
            
            for date_str, total in date_values.items():
                # Calculer le nouveau total pour cet axe et cette date
                lines_same_date = self.env['account.move.line'].search([
                    ('move_id.move_type', '=', 'in_invoice'),
                    ('parent_state', '=', 'posted'),
                    ('move_id.project_id', '=', self.project_id.id),
                    '|',
                    ('invoice_date', '=', invoice_date),
                    ('date', '=', invoice_date),
                    ('display_type', '=', 'product'),
                ])
                
                total_for_date = 0.0
                for l in lines_same_date:
                    if l._matches_axis(axis):
                        total_for_date += abs(l.price_total)
                
                # Mettre à jour la ligne d'axe
                axis_line = AxisLine.search([
                    ('axis_id', '=', axis_id),
                    ('date', '=', date_str),
                ], limit=1)
                
                if axis_line:
                    axis_line.write({'actual_cost': total_for_date})
                    _logger.info(f"Axe {axis.name}: coût mis à jour {total_for_date}")
                elif total_for_date > 0:
                    AxisLine.create({
                        'axis_id': axis_id,
                        'date': date_str,
                        'actual_cost': total_for_date,
                    })
                    _logger.info(f"Axe {axis.name}: nouvelle ligne {total_for_date}")
        
        return True
    
    def _sync_all_project_invoices(self, cleanup=False):
        """
        Synchronise TOUTES les factures du projet avec les axes financiers
        Version optimisée avec regroupement
        """
        if not self.project_id:
            return False
        
        _logger.info(f"Synchronisation complète factures projet {self.project_id.name}")
        
        # Récupérer le projet financier
        financial_progress = self.env['project.financial.progress'].search([
            ('project_id', '=', self.project_id.id)
        ], limit=1)
        
        if not financial_progress:
            _logger.warning(f"Aucun projet financier trouvé pour le projet {self.project_id.name}")
            return False
        
        # Récupérer tous les axes de type invoice
        invoice_axes = financial_progress.axis_ids.filtered(
            lambda a: a.cost_type == 'invoice'
        )
        
        # Récupérer toutes les factures
        all_invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('project_id', '=', self.project_id.id)
        ])
        
        # Regrouper les totaux par axe et par date
        axis_totals = defaultdict(lambda: defaultdict(float))
        
        # Phase 1: Calculer les totaux
        for invoice in all_invoices:
            invoice_date = invoice.invoice_date or invoice.date
            date_str = invoice_date.strftime('%Y-%m-%d') if invoice_date else fields.Date.today().strftime('%Y-%m-%d')
            
            for line in invoice.line_ids:
                if not line._is_valid_for_axis_sync():
                    continue
                
                for axis in invoice_axes:
                    if line._matches_axis(axis):
                        axis_totals[axis.id][date_str] += abs(line.price_total)
        
        # Phase 2: Mettre à jour les lignes d'axe
        AxisLine = self.env['project.financial.axis.line']
        
        for axis_id, date_values in axis_totals.items():
            axis = self.env['project.financial.axis'].browse(axis_id)
            
            # Supprimer les anciennes lignes pour cet axe
            if not cleanup:
                old_lines = AxisLine.search([('axis_id', '=', axis_id)])
                old_lines.unlink()
            
            # Créer les nouvelles lignes
            for date_str, total in date_values.items():
                if total > 0:
                    AxisLine.create({
                        'axis_id': axis_id,
                        'date': date_str,
                        'actual_cost': total,
                    })
                    _logger.info(f"Axe {axis.name}: ligne {date_str} = {total}")
        
        _logger.info(f"Synchronisation terminée: {len(all_invoices)} factures, {len(invoice_axes)} axes")
        return True

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
