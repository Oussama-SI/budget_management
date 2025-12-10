# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"


    def _get_matching_axis_for_line(self):
        """
        Trouve l'axe financier correspondant à cette ligne analytique
        Uniquement pour les lignes de COÛT (amount <= 0)
        """
        self.ensure_one()
        
        if not self.account_id:
            return self.env['project.financial.axis']
        
        domain = [
            ('project_financial_id.analytic_account_id', '=', self.account_id.id)
        ]
        
        if self.product_id and self.product_id.product_tmpl_id.categ_id:
            domain.append(('product_category_ids', 'parent_of', self.product_id.product_tmpl_id.categ_id.id))
        else:
            domain.append(('product_category_ids', '=', False))
        
        if self.employee_id and self.employee_id.department_id:
            domain.append(('employee_department_ids', '=', self.employee_id.department_id.id))
        else:
            domain.append(('employee_department_ids', '=', False))
        
        # Type d'axe
        # if self.manufacturing_order_id:
        #     domain.append(('type', '=', 'mrp'))
        # elif self.stock_move_id:
        #     domain.append(('type', '=', 'inventaire'))
        # elif self.task_id:
        #     domain.append(('type', '=', 'intern'))
        # else:
        #     domain.append(('type', '=', 'manual'))
        
        return self.env['project.financial.axis'].search(domain)
    
    
    def _update_axis_line_for_date(self, axis, date):
        """
        Met à jour ou crée la ligne d'axe pour une date donnée
        Calcule le earned_value total pour cette date et cet axe
        """
        AxisLine = self.env['project.financial.axis.line']
        
        # Chercher la ligne existante
        axis_line = AxisLine.search([
            ('axis_id', '=', axis.id),
            ('date', '=', date)
        ], limit=1)
        
        total_earned_value = 0.0
        total_actual_cost = 0.0
        
        # Chercher TOUTES les lignes analytiques qui correspondent
        domain = [
            ('account_id', '=', self.account_id.id),  # Même compte analytique
            ('date', '=', date),                      # Même date
            ('amount', '<=', 0),                      # Uniquement les coûts
        ]
        
        # IMPORTANT: On recherche toutes les lignes, pas seulement celle en cours
        all_analytic_lines = self.search(domain)
        
        for analytic_line in all_analytic_lines:
            matching_axes = analytic_line._get_matching_axis_for_line()
            if axis in matching_axes:
                total_earned_value += analytic_line.unit_amount
                total_actual_cost += abs(analytic_line.amount)
        
        # Créer ou mettre à jour la ligne d'axe
        if total_earned_value > 0 or axis_line:
            if axis_line:
                axis_line.write({
                    'earned_value': total_earned_value,
                    'actual_cost': total_actual_cost
                })
            else:
                axis_line = AxisLine.create({
                    'axis_id': axis.id,
                    'date': date,
                    'earned_value': total_earned_value,
                    'actual_cost': total_actual_cost,
                    # 'progress': 0.0,
                })
        
        return axis_line

    def _cleanup_empty_axis_lines(self, axis_id, date):
        """
        Supprime les lignes d'axe qui n'ont plus de lignes analytiques
        """
        AxisLine = self.env['project.financial.axis.line']
        
        # Vérifier si la ligne d'axe existe encore
        axis_line = AxisLine.search([
            ('axis_id', '=', axis_id),
            ('date', '=', date)
        ], limit=1)
        
        if axis_line:
            # Vérifier s'il y a encore des lignes analytiques pour cette date
            analytic_lines = self.search([
                ('account_id', '=', self.account_id.id),
                ('date', '=', date),
                ('amount', '<=', 0),
            ])
            
            # Filtrer celles qui correspondent à l'axe
            has_matching_lines = False
            for line in analytic_lines:
                matching_axes = line._get_matching_axis_for_line()
                if axis_line.axis_id in matching_axes:
                    has_matching_lines = True
                    break
            
            if not has_matching_lines:
                # Supprimer la ligne d'axe vide
                axis_line.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Surcharge de la création
        """
        # Créer les lignes analytiques d'abord
        analytic_lines = super(AccountAnalyticLine, self).create(vals_list)
        
        # Traiter chaque ligne créée
        for line in analytic_lines:
            try:
                # Uniquement pour les lignes de coût
                if line.amount and line.amount > 0:
                    continue
                
                # Trouver les axes correspondants
                matching_axes = line._get_matching_axis_for_line()
                
                for axis in matching_axes:
                    # Mettre à jour la ligne d'axe pour cette date
                    line._update_axis_line_for_date(axis, line.date)
                    
            except Exception as e:
                continue
        
        return analytic_lines

    def write(self, vals):
        """
        Surcharge de l'écriture
        """
        # Stocker les anciennes valeurs avant modification
        old_values = {}
        for line in self:
            old_values[line.id] = {
                'date': line.date,
                'account_id': line.account_id.id,
                'product_id': line.product_id.id if line.product_id else False,
                'employee_id': line.employee_id.id if line.employee_id else False,
                'unit_amount': line.unit_amount,
                'amount': line.amount,
            }
        
        # Appliquer les modifications
        result = super(AccountAnalyticLine, self).write(vals)
        
        # Identifier les champs qui affectent le matching
        affecting_fields = ['date', 'account_id', 'product_id', 'employee_id', 
                          'unit_amount', 'amount']
        
        if any(field in vals for field in affecting_fields):
            for line in self:
                try:
                    old_data = old_values.get(line.id, {})
                    
                    # Nettoyer l'ancienne date si la date a changé
                    if 'date' in vals and old_data.get('date') != line.date:
                        # Trouver les anciens axes correspondants
                        old_matching_axes = line._get_matching_axis_for_line()
                        for axis in old_matching_axes:
                            line._cleanup_empty_axis_lines(axis.id, old_data['date'])
                    
                    # Mettre à jour pour la nouvelle configuration
                    # Uniquement pour les lignes de coût
                    if line.amount and line.amount > 0:
                        # Si c'est devenu un revenu, nettoyer l'ancienne ligne
                        if old_data.get('amount', 0) <= 0:
                            matching_axes = line._get_matching_axis_for_line()
                            for axis in matching_axes:
                                line._cleanup_empty_axis_lines(axis.id, line.date)
                        continue
                    
                    # Trouver les nouveaux axes correspondants
                    matching_axes = line._get_matching_axis_for_line()
                    
                    for axis in matching_axes:
                        # Mettre à jour la ligne d'axe
                        line._update_axis_line_for_date(axis, line.date)
                        
                except Exception as e:
                    continue
        
        return result

    def unlink(self):
        """
        Surcharge de la suppression
        """
        # Stocker les informations avant suppression
        to_cleanup = []
        for line in self:
            # Uniquement pour les lignes de coût
            if line.amount and line.amount > 0:
                continue
            
            matching_axes = line._get_matching_axis_for_line()
            for axis in matching_axes:
                to_cleanup.append({
                    'axis_id': axis.id,
                    'date': line.date,
                    'account_id': line.account_id.id if line.account_id else False,
                })
        
        # Supprimer les lignes
        result = super(AccountAnalyticLine, self).unlink()
        
        # Nettoyer les lignes d'axe vides
        for cleanup_data in to_cleanup:
            if not cleanup_data['account_id']:
                continue
                
            try:
                # Vérifier s'il reste des lignes analytiques pour cette combinaison
                remaining_lines = self.search([
                    ('account_id', '=', cleanup_data['account_id']),
                    ('date', '=', cleanup_data['date']),
                    ('amount', '<=', 0),
                ], limit=1)
                
                if not remaining_lines:
                    # Chercher la ligne d'axe
                    axis_line = self.env['project.financial.axis.line'].search([
                        ('axis_id', '=', cleanup_data['axis_id']),
                        ('date', '=', cleanup_data['date'])
                    ], limit=1)
                    
                    if axis_line:
                        axis_line.unlink()
                        
            except Exception as e:
                continue
        
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
                matching_axes = line._get_matching_axis_for_line()
                for axis in matching_axes:
                    line._update_axis_line_for_date(axis, line.date)
            except Exception as e:
                continue
        
        return True