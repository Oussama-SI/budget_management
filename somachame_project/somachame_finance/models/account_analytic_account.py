# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"


    def get_matching_axis_for_line(self):
        """
        Trouve l'axe financier correspondant à cette ligne analytique
        Uniquement pour les lignes de COÛT du feuille de temps
        """
        self.ensure_one()
        
        if not self.account_id:
            return self.env['project.financial.axis']
        
        domain = [
            ('project_financial_id.account_id', '=', self.account_id.id),
            ('cost_type', '=', 'analytic')
        ]
        axes = self.env['project.financial.axis'].search(domain)
        matching_axes = axes.filtered(lambda a: self.employee_id in a.employee_ids)

        return matching_axes
    
    def _calculate_amount_for_axis_date(self, axis, date):
        total = 0.0
        lines = self.search([
                ('account_id', '=', axis.project_financial_id.account_id.id),
                ('employee_id', 'in', axis.employee_ids.ids),
                ('date', '=', date),
                ('product_id', '=', False),
                ('amount', '<', 0),
        ])
            
        for line in lines:
            total += abs(line.amount)
        _logger.info(f"total est : {total}")
        return total
    
    def update_axis_line_for_date(self, axis, date):
        """
        Met à jour ou crée la ligne d'axe pour une date donnée
        Calcule le coùt total pour cette date et cet axe
        """
        AxisLine = self.env['project.financial.axis.line']
        axis_line = AxisLine.search([
            ('axis_id', '=', axis.id),
            ('date', '=', date)
        ], limit=1)

        abs_amount = self._calculate_amount_for_axis_date(axis, date)
        _logger.info(f"amount: {abs_amount}")
        
        if axis_line:
                # new = axis_line.actual_cost + abs_amount
                axis_line.write({'actual_cost': abs_amount})
                _logger.info(f"axis {axis_line} updated")
        else:
            axis_line = AxisLine.create({
                    'axis_id': axis.id,
                    'date': date,
                    'actual_cost': abs_amount,
                    # 'progress': 0.0,
            })
            _logger.info(f"axis {axis_line} created")
        
        return axis_line

    def _cleanup_empty_axis_lines(self, axis_id, date, amount):
        """
        Supprime les lignes d'axe qui n'ont plus de lignes analytiques
        """
        AxisLine = self.env['project.financial.axis.line']
        
        # Vérifier si la ligne d'axe existe encore
        axis_line = AxisLine.search([
            ('axis_id', '=', axis_id),
            ('date', '=', date),
            ('actual_cost', '>=', amount),
        ], limit=1)
        
        if axis_line:
            remains = axis_line.actual_cost - abs(amount)
            _logger.info(f"to remise :  {remains}")
            axis_line.write({'actual_cost': remains})     

    @api.model_create_multi
    def create(self, vals_list):

        analytic_lines = super(AccountAnalyticLine, self).create(vals_list)
        
        for line in analytic_lines:
            if line.product_id or line.amount >= 0:
                continue
            try:
                matching_axis = line.get_matching_axis_for_line()
                _logger.info(f"matching_axes : {matching_axis}")
                if matching_axis:
                    axis_line =  line.update_axis_line_for_date(matching_axis, line.date)
                    _logger.info(f"Ligne axe mise à jour/créée: {axis_line.id if axis_line else 'Erreur'}")
                else:
                    _logger.warning(f"Aucun axe trouvé pour la ligne {line.id}")
                    
            except Exception as e:
                self.returning_exception("améleoration")
        
        return analytic_lines

    def write(self, vals):
        """
        Surcharge de WRITE
        """
        old_values = {}
        for line in self:
            if line.product_id:
                continue
            old_matching_axe = line.get_matching_axis_for_line()
            if not old_matching_axe:
                continue
            old_values[line.id] = {
                    'axis_id': old_matching_axe.id,
                    'date': line.date,
                    'account_id': line.account_id.id,
                    'employee_id': line.employee_id.id if line.employee_id else False,
                    # 'unit_amount': line.unit_amount,
                    'amount': line.amount,
            }
        
        result = super(AccountAnalyticLine, self).write(vals)
        
        affecting_fields = ['date', 'account_id', 'employee_id', 
                          'unit_amount', 'amount']
        
        if any(field in vals for field in affecting_fields) and 'product_id' not in vals:
            for line in self:
                try:
                    old_data = old_values.get(line.id, {}) or None
                    
                    # Nettoyer l'ancienne date si la date a changé
                    if old_data and (('date' in vals and old_data.get('date') != line.date) \
                        or ('employee_id' in vals and line.employee_id.id != old_data.get('employee_id')) \
                            or ('account_id' in vals and line.account_id.id != old_data.get('account_id'))):
                        line._cleanup_empty_axis_lines(old_data['axis_id'], old_data['date'], old_data['amount'])
                                      
                    matching_axe = line.get_matching_axis_for_line()
                    if matching_axe:
                        line.update_axis_line_for_date(matching_axe, line.date)
                        
                except Exception as e:
                    self.returning_exception("modéfication")
        
        return result

    def unlink(self):
        """
        Surcharge de la suppression
        """
        # Stocker les informations avant suppression
        to_cleanup = []
        for line in self:
            if line.product_id or line.amount >= 0:
                continue
            
            matching_axis = line.get_matching_axis_for_line()
            if not matching_axis:
                _logger.info(f"there is no matching for {line}")
                continue
            
            to_cleanup.append({
                    'axis_id': matching_axis.id,
                    'date': line.date,
                    'account_id': line.account_id.id,
                    'employee_id': line.employee_id.id,
                    'amount': line.amount
            })
        
        result = super(AccountAnalyticLine, self).unlink()
        if to_cleanup:
            for data in to_cleanup:
                try:
                    self._cleanup_empty_axis_lines(data['axis_id'], data['date'], data['amount'])
                    _logger.info(f"cleaning for {data['axis_id']}")                        
                except Exception as e:
                    self.returning_exception("démuniation")
            
        return result

    def _recompute_all_axis_lines(self):
        """
        Méthode utilitaire pour tout recalculer
        """
        
        # Nettoyer toutes les lignes d'axe existantes
        self.env['project.financial.axis.line'].search([]).unlink()
        
        # Récupérer toutes les lignes analytiques de coût
        cost_lines = self.search([('amount', '<=', 0)])
                
        # Recréer les lignes d'axe
        for line in cost_lines:
            try:
                matching_axis = line.get_matching_axis_for_line()
                line.update_axis_line_for_date(matching_axis, line.date)
            except Exception as e:
                self.returning_exception("recalcule")
        
        return True
    
    def returning_exception(self, type):
        for line in self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': (f'FT : Erreur de synchronisation : {line.project_id.name}'),
                    'message': (
                    f'Une erreur est survenue lors de la {type} des ligne de ce Axe'
                    ),
                    'type': 'danger',
                    'sticky': False,
                }
            }