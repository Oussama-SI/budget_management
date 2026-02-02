from odoo import models, fields, api


class ProjectFinancialAxisKpi(models.Model):
    _name = "project.financial.axis.kpi"
    _description = "Cumuls Mensuels des Indicateurs"
    _order = "month_date desc"
    _rec_name = "display_name"

    @api.depends('axis_id', 'month_date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.axis_id.name} - {record.month_date.strftime('%B %Y')}"

    display_name = fields.Char(string="Nom",  compute='_compute_display_name',  store=True)  
    axis_id = fields.Many2one('project.financial.axis',  string="Axe", required=True,  ondelete='cascade',index=True)  
    project_financial_id = fields.Many2one('project.financial.progress', string="Projet Financier",
                                           related='axis_id.project_financial_id', store=True, index=True)  
    month_date = fields.Date(string="Mois", required=True, index=True, help="Data Monsuele")
    
    cum_planned_budget = fields.Monetary(string="VP Cumulé", currency_field='currency_id', digits=(16, 2),
                                        help="Budget planifié cumulé jusqu'à fin du mois") 
    cum_earned_amount = fields.Monetary(string="VA Cumulé", currency_field='currency_id', digits=(16, 2),
                                        help="Valeur acquise cumulée jusqu'à fin du mois")
    cum_actual_cost = fields.Monetary(string="CR Cumulé", currency_field='currency_id', digits=(16, 2),
                                      help="Coût réel cumulé jusqu'à fin du mois")
    
    monthly_planned_budget = fields.Monetary(string="VP Mensuel", currency_field='currency_id', digits=(16, 2),
                                             help="Budget planifié pour le mois uniquement")
    monthly_earned_amount = fields.Monetary(string="VA Mensuel", currency_field='currency_id', digits=(16, 2), 
                                            help="Valeur acquise pour le mois uniquement")
    monthly_actual_cost = fields.Monetary(string="CR Mensuel", currency_field='currency_id', digits=(16, 2),
                                          help="Coût réel pour le mois uniquement")
    
    cost_performance_index = fields.Float(string="IPC", digits=(16, 4), help="Indice de performance des coûts: VA cumulé / CR cumulé")
    delay_performance_index = fields.Float(string="IPD", digits=(16, 4), help="Indice de performance des délais: VA cumulé / VP cumulé")
    currency_id = fields.Many2one('res.currency', related='axis_id.currency_id', store=True)
    
    cost_variance = fields.Monetary(
        string="Écart de Coût (CV)",
        currency_field='currency_id',
        digits=(16, 2),
        compute='_compute_variances',
        store=True,
        help="CV = VA - CR (positif = sous budget, négatif = dépassement)"
    )
    
    schedule_variance = fields.Monetary(
        string="Écart de Délais (SV)",
        currency_field='currency_id',
        digits=(16, 2),
        compute='_compute_variances',
        store=True,
        help="SV = VA - VP (positif = en avance, négatif = en retard)"
    )

    @api.depends('cumulative_earned_amount', 'cumulative_actual_cost', 
                 'cumulative_planned_budget')
    def _compute_variances(self):
        """Calcule les écarts (variances)"""
        for record in self:
            # Écarts absolus
            record.cost_variance = record.cumulative_earned_amount - record.cumulative_actual_cost
            record.schedule_variance = record.cumulative_earned_amount - record.cumulative_planned_budget

    def compute_cums(self, month_date=None):
        """Calcule ou recalcule les cumuls pour un mois donné"""
        for record in self:
            if month_date:
                record.month_date = fields.Date.start_of(month_date, 'month')
            
            month_start = record.month_date
            month_end = fields.Date.end_of(month_start, 'month')
            
            # Récupérer l'axe
            axis = record.axis_id
            
            # 1. Budget planifié mensuel (depuis budget.line)
            budget_lines = self.env['project.financial.axis.budget.line'].search([
                ('axis_id', '=', axis.id),
                ('date', '>=', month_start),
                ('date', '<=', month_end)
            ])
            record.monthly_planned_budget = sum(budget_lines.mapped('planned_budget'))
            
            # 2. Valeur acquise mensuelle
            axis_lines = self.env['project.financial.axis.line'].search([
                ('axis_id', '=', axis.id),
                ('date', '>=', month_start),
                ('date', '<=', month_end)
            ])
            record.monthly_earned_amount = sum(axis_lines.mapped('earned_amount'))
            record.monthly_actual_cost = sum(axis_lines.mapped('actual_cost'))
            
            # 3. Cumul jusqu'à ce mois
            # Chercher tous les mois précédents
            previous_months = self.search([
                ('axis_id', '=', axis.id),
                ('month_date', '<', month_start)
            ], order='month_date asc')
            
            # Initialiser avec les valeurs du mois courant
            cumul_vp = record.monthly_planned_budget
            cumul_va = record.monthly_earned_amount
            cumul_cr = record.monthly_actual_cost
            
            # Ajouter les cumuls des mois précédents
            for prev_month in previous_months:
                cumul_vp += prev_month.monthly_planned_budget
                cumul_va += prev_month.monthly_earned_amount
                cumul_cr += prev_month.monthly_actual_cost
            
            record.cum_planned_budget = cumul_vp
            record.cum_earned_amount = cumul_va
            record.cum_actual_cost = cumul_cr
            
            # 4. Calcul des indices
            record.cost_performance_index = cumul_va / cumul_cr if cumul_cr != 0 else 0.0
            record.delay_performance_index = cumul_va / cumul_vp if cumul_vp != 0 else 0.0

    def compute_cumulatives(self):
        """Calcule ou recalcule les cumuls"""
        for record in self:
            if not record.axis_id or not record.month_date:
                continue
                
            month_start = record.month_date
            month_end = fields.Date.end_of(month_start, 'month')
            axis = record.axis_id
            
            # 1. Budget planifié mensuel (depuis budget.line)
            budget_lines = self.env['project.financial.axis.budget.line'].search([
                ('axis_id', '=', axis.id),
                ('date', '>=', month_start),
                ('date', '<=', month_end)
            ])
            record.monthly_planned_budget = sum(budget_lines.mapped('planned_budget'))
            
            # 2. Valeur acquise mensuelle
            axis_lines = self.env['project.financial.axis.line'].search([
                ('axis_id', '=', axis.id),
                ('date', '>=', month_start),
                ('date', '<=', month_end)
            ])
            record.monthly_earned_amount = sum(axis_lines.mapped('earned_amount'))
            record.monthly_actual_cost = sum(axis_lines.mapped('actual_cost'))
            
            # 3. Cumul jusqu'à ce mois (tous les mois précédents + mois courant)
            # Chercher tous les mois précédents ou égaux
            all_previous_months = self.search([
                ('axis_id', '=', axis.id),
                ('month_date', '<=', month_start)
            ], order='month_date asc')
            
            # Réinitialiser les cumuls
            cumul_vp = 0
            cumul_va = 0
            cumul_cr = 0
            
            # Somme de tous les mois jusqu'à celui-ci
            for month in all_previous_months:
                if month.id != record.id:  # Éviter de compter l'enregistrement actuel si pas encore calculé
                    cumul_vp += month.monthly_planned_budget
                    cumul_va += month.monthly_earned_amount
                    cumul_cr += month.monthly_actual_cost
            
            # Ajouter les valeurs du mois courant
            cumul_vp += record.monthly_planned_budget
            cumul_va += record.monthly_earned_amount
            cumul_cr += record.monthly_actual_cost
            
            # Sauvegarder les cumuls
            record.cumulative_planned_budget = cumul_vp
            record.cumulative_earned_amount = cumul_va
            record.cumulative_actual_cost = cumul_cr
            
            # 4. Calcul des indices
            record.cost_performance_index = cumul_va / cumul_cr if cumul_cr != 0 else 0.0
            record.schedule_performance_index = cumul_va / cumul_vp if cumul_vp != 0 else 0.0
    
    @api.model
    def cron_compute_monthly_cums(self):
        """Cron pour calculer automatiquement les cumuls mensuels"""
        # Récupérer tous les axes actifs
        axes = self.env['project.financial.axis'].search([('active', '=', True)])
        
        for axis in axes:
            start_date = axis.project_financial_id.date_start or fields.Date.today()
            end_date = axis.project_financial_id.date_end or fields.Date.today()
            
            current_month = fields.Date.start_of(start_date, 'month')
            end_month = fields.Date.start_of(end_date, 'month')
            
            while current_month <= end_month:
                monthly_record = self.search([
                    ('axis_id', '=', axis.id),
                    ('month_date', '=', current_month)
                ], limit=1)
                
                if not monthly_record:
                    monthly_record = self.create({
                        'axis_id': axis.id,
                        'month_date': current_month,
                    })
                
                # Calculer les cumuls
                monthly_record.compute_cumulatives()
                current_month = fields.Date.add(current_month, months=1)
    
    # AJOUTER UNE MÉTHODE POUR RÉAGIR AUX CHANGEMENTS
    def _invalidate_and_recompute(self):
        """Invalide et recalcule les cumuls quand les données sources changent"""
        # Marquer tous les cumuls de cet axe comme à recalculer
        # On pourrait utiliser un champ 'needs_recomputation'
        pass

    def recompute_all_for_axis(self, axis_id):
        """Recalcule tous les cumuls pour un axe spécifique"""
        axis = self.env['project.financial.axis'].browse(axis_id)
        if not axis.exists():
            return
        
        # Récupérer tous les cumuls pour cet axe
        monthly_records = self.search([('axis_id', '=', axis.id)])
        
        # Les recalculer dans l'ordre chronologique
        for record in monthly_records.sorted('month_date'):
            record.compute_cumulatives()
    
    # ACTION DANS L'INTERFACE
    def action_recompute(self):
        """Action pour recalculer manuellement"""
        self.ensure_one()
        self.compute_cumulatives()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recalcul terminé',
                'message': f'Les cumuls pour {self.display_name} ont été recalculés.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_recompute_all(self):
        """Recalcule tous les cumuls pour cet axe"""
        self.ensure_one()
        self.recompute_all_for_axis(self.axis_id.id)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Recalcul terminé',
                'message': f'Tous les cumuls pour {self.axis_id.name} ont été recalculés.',
                'type': 'success',
                'sticky': False,
            }
        }


# class ProjectFinancialAxisKpi(models.Model):
#     _name = "project.financial.axis.kpi"
#     _description = "KPI normalisé (Graph)"

#     axis_line_id = fields.Many2one("project.financial.axis.line", required=True, ondelete="cascade", index=True)
#     axis_id = fields.Many2one(related="axis_line_id.axis_id", store=True, index=True)
#     project_financial_id = fields.Many2one(related="axis_line_id.project_financial_id", store=True, index=True)
#     date = fields.Date(related="axis_line_id.date", store=True, index=True)

#     kpi_type = fields.Selection([
#         ("planned_budget", "Planned Budget"),
#         ("delay_performance_index", "Delay Performance Index (DPI)"),
#         ("cost_performance_index", "Cost Performance Index (CPI)"),
#     ], required=True, index=True)

#     value = fields.Float(required=True)

#     _sql_constraints = [
#         ("axis_line_kpi_uniq", "unique(axis_line_id, kpi_type)", "KPI déjà généré pour cette ligne."),
#     ]

class ProjectFinancialAxisLine(models.Model):
    _inherit = "project.financial.axis.line"
    
    def write(self, vals):
        result = super().write(vals)
        
        # Si earned_amount ou actual_cost change, déclencher le recalcul des cumuls
        if any(field in vals for field in ['earned_amount', 'actual_cost', 'date']):
            self._trigger_cumulative_recomputation()
        
        return result
    
    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._trigger_cumulative_recomputation()
        return record
    
    # def unlink(self):
    #     # Récupérer les axes concernés avant suppression
    #     axes_to_recompute = self.mapped('axis_id')
    #     result = super().unlink()
        
    #     # Déclencher le recalcul
    #     if axes_to_recompute:
    #         for axis in axes_to_recompute:
    #             self.env['project.financial.axis.monthly.cumulative'].recompute_all_for_axis(axis.id)
        
    #     return result
    
    def _trigger_cumulative_recomputation(self):
        """Déclenche le recalcul des cumuls pour les axes concernés"""
        axes = self.mapped('axis_id')
        if axes:
            for axis in axes:
                # Recalcul asynchrone mais sans queue_job
                # On pourrait utiliser un flag et un cron, mais ici on recalcule directement
                self.env['project.financial.axis.monthly.cumulative'].recompute_all_for_axis(axis.id, self.date)

class ProjectFinancialAxisBudgetLine(models.Model):
    _inherit = "project.financial.axis.budget.line"

    def write(self, vals):
        result = super().write(vals)
        
        if 'planned_budget' in vals or 'date' in vals:
            self._trigger_cumulative_recomputation()
        
        return result
    
    @api.model
    def create(self, vals_list):
        record = super().create(vals_list)
        record._trigger_cumulative_recomputation()
        return record
    
    def unlink(self):
        axes_to_recompute = self.mapped('axis_id')
        result = super().unlink()
        
        if axes_to_recompute:
            for axis in axes_to_recompute:
                self.env['project.financial.axis.monthly.cumulative'].recompute_all_for_axis(axis.id)
        
        return result
    
    def _trigger_cumulative_recomputation(self):
        """Déclenche le recalcul des cumuls pour les axes concernés"""
        axes = self.mapped('axis_id')
        if axes:
            for axis in axes:
                self.env['project.financial.axis.monthly.cumulative'].recompute_all_for_axis(axis.id, self.date)
    
    # def write(self, vals):
    #     result = super().write(vals)
        
    #     if 'planned_budget' in vals or 'date' in vals:
    #         self._trigger_cumulative_recomputation()
        
    #     return result
    
    # @api.model_create_multi
    # def create(self, vals_list):
    #     records = super().create(vals_list)
    #     records._trigger_cumulative_recomputation()
    #     return records
    
    # def _trigger_cumulative_recomputation(self):
    #     """Déclenche le recalcul des cumuls pour les axes concernés"""
    #     axes = self.mapped('axis_id')
    #     if axes:
    #         # Recalculer les cumuls pour ces axes
    #         monthly_records = self.env['project.financial.axis.kpi'].search([
    #             ('axis_id', 'in', axes.ids)
    #         ])
    #         for record in monthly_records:
    #             record.compute_cumulatives()
