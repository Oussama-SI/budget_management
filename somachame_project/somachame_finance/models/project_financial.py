import logging
from odoo import api, fields, models, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


# project.financial is the same domain as project.projct 1.1
class ProjectFinancialProgress(models.Model):
    _name = "project.financial.progress"
    _description = "Analyse Financière du Projet"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    
    @api.model
    def _get_default_currency(self):
        return self.env.company.currency_id
    

    active = fields.Boolean(default=True, export_string_translation=False)
    name = fields.Char("Désignation", compute='_compute_name', state={'done': [('readonly', True)]})
    code = fields.Char('Code du Projet', compute='_get_project_data')
    description = fields.Html(help="Vous pouvez metre une ou plusieurs piéces jointes ou text")
    project_id = fields.Many2one('project.project', string="Projet", copy=False, ondelete='cascade')
    account_id = fields.Many2one('account.analytic.account', string="Compte Analytique", 
                                 related="project_id.account_id", store=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user,  
                              tracking=True, store=True)
    date_from = fields.Date("Date de début", compute='_get_project_data', state={'done': [('readonly', True)]}, tracking=True)
    date_to = fields.Date('Date de fin', compute='_get_project_data', state={'done': [('readonly', True)]}, tracking=True)
    state = fields.Selection([
        ('draft', 'brouillon'),
        ('cancel', 'Annulé'),
        ('budgeted', 'Budgétisé'),
        ('in_progress', 'En cours'),
        ('confirm', 'Terminé'),
        ], 'Status', default='draft', index=True, compute="_compute_state_automatically", store=True, copy=False, tracking=True)
    axis_ids = fields.One2many('project.financial.axis', 'project_financial_id', 'Axes analytiques',
        state={'done': [('readonly', True)]}, copy=True)
    currency_id = fields.Many2one('res.currency', string='Devise',  default=_get_default_currency, required=True)
    create_axis = fields.Boolean(string="Axes automatique")
    total_budget = fields.Monetary(string="Budget Total", compute='_compute_total_budget', store=True)
    project_earned_amount = fields.Monetary(string="Valeur Acquise", 
        compute='_compute_financial_metrics',
        store=True,
        help="Valeur du travail réalisé VA"
    )
    is_axis_budget = fields.Boolean("Axe Budget définie", default=False)
    project_planned_amount = fields.Monetary(string="Valeur Planifiée", 
        compute='_compute_financial_metrics',
        store=True,
        help="Valeur de travail planifié VP"
    )
    project_cost = fields.Monetary(string="Coût Réel", 
        compute='_compute_financial_metrics',
        store=True,
        help="Coût réel engagé CR"
    )
    cost_performance_index = fields.Float(string="IPC",
                                          compute='_compute_financial_metrics',
                                          digits=(3, 2), help="VA / CR")
    delay_performance_index = fields.Float(string="IPD", 
                                           compute='_compute_financial_metrics',
                                           digits=(3, 2), help="VA / VP")
    rec_performance_index = fields.Float(string="IPR",
                                         compute="_compute_index",
                                         digits=(3,2), help="IPR = FU / FP")
    marge_sale = fields.Monetary(
          compute='_compute_index',
          string="Marge sur vente")
    cost_variance = fields.Monetary(
        string="Écart Coût",
        compute='_compute_financial_metrics',
        # store=True,
        help="EC = VA - CR"
    )
    delay_variance = fields.Monetary(
        string="Ecart de Délais",
        compute='_compute_financial_metrics',
        # store=True,
        help="ED = VA - VP")
    completion_rate = fields.Float(
        string="Taux Achèvement",
        # compute='_compute_financial_metrics',
        # store=True,
        digits=(12, 2), help="(VA / Budget Total) * 100")
    performance_state = fields.Selection(
        [('good', 'Bon'), ('warning', 'À surveiller')],
        string='Performance State',
        compute='_compute_performance_state',
        store=True)
    
    axis_count = fields.Integer(string="Nombre d'Axes", compute='_compute_axis_count', store=False)
    
    def _compute_axis_count(self):
        for project in self:
            project.axis_count = self.env['project.financial.axis'].search_count([
                ('project_financial_id', '=', project.id)
            ])
    
    @api.depends('project_id', 'project_id.code')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.code}-PGP[{rec.project_id.name}]" if rec.code \
            else f"PDG[{rec.project_id.name}]"

    @api.depends('project_id', 'project_id.date', 'project_id.code')
    def _get_project_data(self):
        today = fields.Date.today()
        for rec in self:
            rec.code = rec.project_id.code or False
            rec.date_from = rec.project_id.date_start or False
            rec.date_to = rec.project_id.date or False
            if rec.date_to and rec.date_to <= today:
                self.state = 'confirm'
    
    @api.depends('cost_performance_index')
    def _compute_performance_state(self):
        for rec in self:
            rec.performance_state = 'good' if rec.cost_performance_index >= 1 else 'warning'
    
    @api.depends('project_id', 'axis_ids', 'project_earned_amount', 'project_cost', 'project_planned_amount')
    def _compute_index(self):
        move = self.env['account.move']
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
        ]
        for project in self:
            domain += [('project_id', '=', project.project_id.id)]
            if project.axis_ids:
                # project.delay_performance_index = sum(self.env['project.financial.axis.line']) / len(project.axis_ids)
                # project.cost_performance_index = sum(axis.cost_performance_index for axis in project.axis_ids) / len(project.axis_ids)
                move_ids = move.search(domain)
                sale_amount = sum(id.amount_untaxed for id in move_ids)
                analytic_amount = sum(axis.cost for axis in project.axis_ids) or project.project_cost
                project.marge_sale = sale_amount - analytic_amount or 0.0
            else:
                project.marge_sale = project.delay_performance_index = project.cost_performance_index = 0.0

            if project.account_id: #and self.user_has_groups('analytic.group_analytic_accounting')
                get_move_ids = move.search(domain + [('payment_state', '=', 'paid')])
                #amount_paid = sum(get_move_ids.mapped('amount_total_signed'))
                amount_paid = sum(move.amount_total_signad for move in get_move_ids)
                out_move_ids = move.search(domain + [('payment_state', 'in', ('not_paid', 'partial'))])
                #amount_unpaid = sum(out_move_ids.mapped('amount_residual_signed'))
                amount_unpaid = sum(move.amount_residual_signad for move in out_move_ids)
                diff = amount_paid - amount_unpaid
                project.rec_performance_index = diff / amount_paid \
                    if amount_paid != 0.0 \
                    else 0.0
            else:
                project.rec_performance_index = 0.0
    """paid = 0.0
                unpaid = 0.0
                get_move_ids = move.search(domain + [('payment_state', '=', 'paid')])
                #amount_paid = sum(get_move_ids.mapped('amount_total_signed'))
                for move in get_move_ids:
                    paid += move.amount_total_signad
                out_move_ids = move.search(domain + [('payment_state', 'in', ('not_paid', 'partial'))])
                #amount_unpaid = sum(out_move_ids.mapped('amount_residual_signed'))
                for move in out_move_ids:
                    unpaid += move.amount_residual_signad
                diff = paid - unpaid
                project.performance_index = diff / paid \
                    if paid != 0.0 \
                    else 0.0"""
    
    @api.depends('is_axis_budget', 'axis_ids', 'total_budget')
    def _compute_financial_metrics(self):
        """
        Calcule les métriques financières
        """
        for record in self:  # Utiliser 'record' au lieu de 'axis'
            try:
                # Récupérer toutes les lignes d'axes pour ce projet
                axis_lines = self.env['project.financial.axis.line'].search([
                    ('project_financial_id', '=', record.id)
                ])
                
                # Calculer VA et CR
                record.project_earned_amount = sum(axis_lines.mapped('earned_amount')) or 0.0
                record.project_cost = sum(axis_lines.mapped('actual_cost')) or 0.0
                
                # Calculer VP selon le type d'axe
                if record.is_axis_budget:
                    # Si c'est un axe budget, utiliser les lignes de budget
                    budget_lines = self.env['project.financial.axis.budget.line'].search([
                        ('project_financial_id', '=', record.id)
                    ])
                    record.project_planned_amount = sum(budget_lines.mapped('planned_budget')) or 0.0
                else:
                    # Sinon, utiliser le budget total
                    record.project_planned_amount = record.total_budget or 0.0
                
                # Calculer IPC (CPI) avec protection contre division par zéro
                if record.project_cost and float(record.project_cost) != 0:
                    record.cost_performance_index = float(record.project_earned_amount) / float(record.project_cost)
                else:
                    record.cost_performance_index = 0.0
                
                # Calculer IPD (SPI) avec protection contre division par zéro
                if record.project_planned_amount and float(record.project_planned_amount) != 0:
                    record.delay_performance_index = float(record.project_earned_amount) / float(record.project_planned_amount)
                else:
                    record.delay_performance_index = 0.0
                
                # Calculer les écarts
                record.cost_variance = float(record.project_earned_amount) - float(record.project_cost)
                record.delay_variance = float(record.project_earned_amount) - float(record.project_planned_amount)
                
            except (ZeroDivisionError, TypeError, ValueError) as e:
                # En cas d'erreur, mettre toutes les valeurs à 0
                record.project_earned_amount = 0.0
                record.project_planned_amount = 0.0
                record.project_cost = 0.0
                record.cost_performance_index = 0.0
                record.delay_performance_index = 0.0
                record.cost_variance = 0.0
                record.delay_variance = 0.0
        
    # @api.depends('is_axis_budget')
    # def _compute_financial_metrics(self):
    #     """
    #     Calcule les métriques financières basées sur le dernier cumul mensuel
    #     ou les données directes si pas de cumul disponible
    #     """
    #     # MonthlyCumulative = self.env['project.financial.axis.monthly.cumulative']
        
    #     for axis in self:
            
    #         # last_cumul = MonthlyCumulative.search([
    #         #     ('axis_id', '=', axis.id)
    #         # ], order='month_date desc', limit=1)
            
    #         # if last_cumul:
    #         #     # Utiliser les valeurs cumulées du dernier mois
    #         #     axis.project_earned_amount = last_cumul.cumulative_earned_amount
    #         #     axis.project_planned_amount = last_cumul.cumulative_planned_budget
    #         #     axis.project_cost = last_cumul.cumulative_actual_cost
    #         #     axis.last_monthly_cumulative_id = last_cumul.id
    #         #     axis.last_update_date = last_cumul.month_date
                
    #         #     # Indices de performance
    #         #     axis.cost_performance_index = last_cumul.cost_performance_index
    #         #     axis.schedule_performance_index = last_cumul.schedule_performance_index
                
    #         #     # Écarts
    #         #     axis.cost_variance = last_cumul.cost_variance
    #         #     axis.schedule_variance = last_cumul.schedule_variance
    #         axis_lines = self.env['project.financial.axis.line'].search([
    #                 ('project_financial_id', '=', axis.id)
    #         ])
                
    #         axis.project_earned_amount = sum(axis_lines.mapped('earned_amount'))
    #         axis.project_cost = sum(axis_lines.mapped('actual_cost'))
                
    #         # Calculer les indices manuellement
    #         if axis.project_cost != 0:
    #             axis.cost_performance_index = axis.project_earned_amount / axis.project_cost
    #         else:
    #             axis.cost_performance_index = 0.0
            
    #         if axis.is_axis_budget:
    #             budget_lines = self.env['project.financial.axis.budget.line'].search([
    #                 ('project_financial_id', '=', axis.id)
    #             ])
    #             axis.project_planned_amount = sum(budget_lines.mapped('planned_budget')) or axis.total_budget
                
    #             # Pas de dernier cumul
    #             # axis.last_monthly_cumulative_id = False
    #             # axis.last_update_date = False
                
                    
    #             if axis.project_planned_amount != 0:
    #                 axis.delay_performance_index = axis.project_earned_amount / axis.project_planned_amount
    #             else:
    #                 axis.delay_performance_index = 0.0
                
    #             # Calculer les écarts
    #             axis.cost_variance = axis.project_earned_amount - axis.project_cost or 0.0
    #             axis.delay_variance = axis.project_earned_amount - axis.project_planned_amount or 0.0
    
    def recompute_all_axis_lines(self):
        """
        Méthode utilitaire pour tout recalculer
        """
        
        # Nettoyer toutes les lignes d'axe existantes
        self.env['project.financial.axis.line'].search([
            ('axis_id', 'in', self.axis_ids.ids),
            ]).unlink()
        
        # Récupérer toutes les lignes analytiques de coût
        cost_lines = self.env['account.analytic.line'].search([
                                    ('account_id', '=', self.account_id.id),
                                ])
                
        # Recréer les lignes d'axe
        for line in cost_lines:
            try:
                matching_axes = line.get_matching_axis_for_line()
                for axis in matching_axes:
                    line.update_axis_line_for_date(axis, line.date)
            except Exception as e:
                raise UserError(f"{e}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Axis lines have been recomputed successfully for {len(self)} axis(s).',
                'sticky': False,
            }
        }


    @api.depends('axis_ids.planned_budget')
    def _compute_total_budget(self):
        for record in self:
            record.total_budget = sum(record.axis_ids.mapped('planned_budget'))


    # @api.constrains('date_from', 'date_to')
    # def _check_dates(self):
    #     for record in self:
    #         if record.date_from and record.date_to and record.date_from > record.date_to:
    #             raise ValidationError("La date de début doit être anférieure à la date de fin.")

    @api.model
    def _cron_update_state_on_date_fin(self):
        """Scheduled action to update state when date_to is reached"""
        today = fields.Date.today()
        records = self.search([
            ('date_to', '<=', today),
            ('state', '=', 'in_progress')
        ])
        if not records:
            return True

        for record in records:
            record.write({'state': 'confirm'})
            for axis in record.axis_ids:
                axis.write({'active': False})

        _logger.info(f"Updated {len(records)} financial progress records to 'confirm' state")
        return True

    @api.depends('axis_ids.planned_budget', 'axis_ids.monetary_planned_budget',
                 'axis_ids.line_ids.actual_cost',
                 'axis_ids.line_ids.earned_amount',
                 'axis_ids.line_ids.earned_value')
    def _compute_state_automatically(self):
        """Calcule l'état automatiquement basé sur toutes les règles"""
        today = fields.Date.today()
        
        for record in self:
            if record.state == 'cancel':
                continue
            # if record.date_to and record.date_to <= today:
            #     record.state = 'confirm'
            #     record.actual_end_date = today
            #     continue
                        
            all_axes_have_budget = False
            if record.axis_ids:
                all_axes_have_budget = all(
                    axis.planned_budget and axis.planned_budget > 0 
                    for axis in record.axis_ids
                )
            
            has_financial_activity = False
            if record.axis_ids:
                domain = [
                    ('axis_id', 'in', record.axis_ids.ids),
                    '|', ('actual_cost', '>', 0),
                    '|', ('earned_amount', '>', 0),
                    ('earned_value', '>', 0)
                ]
                axis_lines = self.env['project.financial.axis.line'].search(domain, limit=1)
                has_financial_activity = bool(axis_lines)
            
            current_state = record.state
            
            if current_state == 'draft' and all_axes_have_budget:
                record.state = 'budgeted'
                
            elif current_state in ['draft', 'budgeted'] and has_financial_activity:
                record.state = 'in_progress'
                
            elif current_state == 'in_progress' and not has_financial_activity:
                record.state = 'budgeted'
    
    def action_open_project_axes(self, *args, **kwargs):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Axes Financiers',
            'res_model': 'project.financial.axis',
            'view_mode': 'list,form',
            'views': [(self.env.ref('somachame_finance.view_project_financial_axis_list').id, 'list'),
                      (self.env.ref('somachame_finance.view_project_financial_axis_form').id, 'form')],
            'domain': [('project_financial_id', '=', self.id)],
            'context': {
                'default_project_financial_id': self.id,
                'my_axes': True,
            },
            'target': 'current',
        }
    
    def action_open_axes_progress(self):
        """Ouvre l'analyse temporelle des axes (GRID/PIVOT sur les LIGNES)"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Valeur Acquise - {self.name}',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'grid,pivot,cohort,form',
            'views': [
                (self.env.ref('somachame_finance.view_project_financial_axis_line_progress_grid').id, 'grid'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_pivot').id, 'pivot'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_cohort').id, 'cohort'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_grid_form').id, 'form')
            ],
            'domain': [('project_financial_id', '=', self.id)],
            'context': {
                'default_project_financial_id': self.id,
                'field_budget': True,
                'field_cost': True,
                'grid_range': 'month',
                'search_default_group_by_axis': 1,
            },
            'target': 'current',
        }
    
    def action_open_axes_cost(self):
        """Ouvre l'analyse temporelle des axes (GRID/PIVOT sur les LIGNES)"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Coût Réel - {self.name}',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'grid,form',
            'views': [
                (self.env.ref('somachame_finance.view_project_financial_axis_line_cost_grid').id, 'grid'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_grid_form').id, 'form'),
            ],
            'domain': [('project_financial_id', '=', self.id)],
            'context': {
                'default_project_financial_id': self.id,
                'field_budget': True,
                'field_ipd': True,
                'grid_range': 'month',
                'search_default_group_by_axis': 1,
            },
            'target': 'current',
        }
    
    def action_open_budget_grid(self):
        """Ouvre le grid view des budgets planifiés"""
        self.ensure_one()
        
        return {
            'name': f'Budget Planifié - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'project.financial.axis.budget.line',
            'view_mode': 'grid,form',
            'views': [
                (self.env.ref('somachame_finance.view_project_financial_axis_budget_line_grid').id, 'grid'),
                (self.env.ref('somachame_finance.view_project_financial_axis_budget_line_grid_form').id, 'form')
            ],
            'domain': [('axis_id.project_financial_id', '=', self.id)],
            'context': {
                'default_project_financial_id': self.id,
                # 'search_default_group_by_axis': 1,
                # 'field_ipd': True,
                # 'field_cost': True,
                # 'grid_range': 'month',  # Par défaut afficher par mois
            },
            'target': 'current',
        }
    
    def action_import_all_financial_data(self):
        """
        Action pour importer TOUTES les données financières depuis l'interface
        """
        self.ensure_one()
        
        try:
            importer = self.env['project.financial.data.importer']
            result = importer.import_financial_data(self.id)
            
            # Notification de succès
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import terminé'),
                    'message': result['message'],
                    'type': 'success',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'project.financial.axis.line',
                        'view_mode': 'tree,graph',
                        'name': _('Lignes importées'),
                        'domain': [('id', 'in', result['acquise_line_ids'] + result['cost_line_ids'])],
                        'context': {'group_by': 'date:month'},
                    }
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Erreur lors de l\'import'),
                    'message': _('Une erreur est survenue: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def action_view_imported_lines(self):
        """Voir toutes les lignes importées"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Données financières importées'),
            'res_model': 'project.financial.axis.line',
            'view_mode': 'list',
            'domain': [('project_financial_id', '=', self.id)],
            'context': {
                'default_project_financial_id': self.id,
                'search_default_group_by_month': 1,
                'search_default_group_by_axis': 1,
                'graph_mode': 'line',
                'graph_measure': 'acquise_value',
            },
            # 'views': [
            #     (False, 'list'),
            #     (False, 'pivot'),
            #     (False, 'graph'),
            #     (False, 'form'),
            # ],
        }
    

class ProjectFinancialAxis(models.Model):
    _name = "project.financial.axis"
    _order = "sequence, id"
    _description = "Axe Analytique"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('project_location_uniq', 'UNIQUE(project_financial_id, location_id)', 
         'Ce emplacement est déja utilisé pour un autre axe pour le méme projet'),
    ]
    
    def _get_picking_type_domain(self):
        domain = []
        domain.append(('warehouse_id.project_id', '=', self.project_financial_id.project_id.id))
        return domain or False

    active = fields.Boolean(string="Active", default=True, help="Désactiver pour masquer l'axe")
    name = fields.Char('Axe analytique', required=True, translate=True)
    complete_name = fields.Char("Désignation", index="trigram", compute="_add_project_name")
    sequence = fields.Integer(default=1, export_string_translation=False)
    project_financial_id = fields.Many2one('project.financial.progress', 'Projet', ondelete='cascade', index=True, required=True)
    category_id = fields.Many2one('project.financial.axis.category', string="Catégorie", ondelete='set null')
    line_ids = fields.One2many('project.financial.axis.line','axis_id',
        string="Historique de Progression")
    axis_budget_id = fields.Many2one("project.financial.axis.budget", ondelete='cascade')
    description = fields.Html(help="")
    color = fields.Integer(string='Couleur', help="Couleur pour les tags")
    type = fields.Selection([
            ('manual', 'Saisie Manuelle'),
            ('stock', 'Livraison Fournisseur'),
            ('move', 'Livraison Chantier'),
            ('rate', "Taux d'Avancement"),
        ],
        string="Source Aquise", required=True,
        default='manual',
        tracking=True,
        help="")
    cost_type = fields.Selection([
            ('invoice', 'Facture Fournisseur'),
            ('analytic', 'Feuille de temps'),
            ('mrp', 'Sortie Stock'),
        ],
        string="Source de coùt", required=True,
        default='invoice',
        tracking=True,
        help="")
    uom_id = fields.Many2one('uom.uom', "Unité")
    planned_quantity = fields.Float("Quantité prévue", default=1.0, required=True)
    budget_unit = fields.Monetary(string="Prix Unitaire")
    monetary_planned_budget = fields.Monetary(# le montant prévus exist dans la forme vue
        'Budget', required=True, default=0.0,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    planned_budget = fields.Float(string="budget sans devise", default=0.0, help="Requis pour les calcules et la synchronisation avec autres bases ")
    product_category_ids =  fields.Many2many('product.category', string="Catégorie produit")
    employee_department_ids = fields.Many2many('hr.department', string="Département")
    employee_ids = fields.Many2many('hr.employee', string="Main d'Oeuvre")
    mrp_id = fields.Many2one('mrp.workcenter', string="Phase de Fabrication")
    picking_type_id = fields.Many2one('stock.picking.type', string="Emplacement", 
                                          domain=lambda self: self._get_picking_type_domain())
    location_id = fields.Many2one('stock.location', string="Emplacement source")
    location_dest_id = fields.Many2one('stock.location', string="Emplacement reçu")
    analytic_account_id = fields.Many2one('account.analytic.account', related="project_financial_id.account_id")
    # analytic_group_id = fields.Many2one('account.analytic.group', 'Analytic Group', related='analytic_account_id.group_id', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    cost = fields.Monetary("Coùt totale")
    progress = fields.Float(string="Avancement %",
                            group_operator="avg",
                            #  compute='_compute_progress', 
                            digits=(12, 2), store=True)
    performance_index = fields.Float(
        string="Indice Performance",
        # compute='_compute_performance_index',
        digits=(12, 3)
    )

    @api.model
    def create(self, vals):

        if 'planned_budget' in vals and 'monetary_planned_budget' not in vals:
            vals['monetary_planned_budget'] = vals['planned_budget']
        elif 'monetary_planned_budget' in vals and 'planned_budget' not in vals:
            vals['planned_budget'] = vals['monetary_planned_budget']
        
        axis = super().create(vals)
        budget = self.env['project.financial.axis.budget'].create({'axis_id': axis.id})
        axis.write({'axis_budget_id': budget.id})

        return axis
    
    @api.model
    def write(self, vals):

        if 'planned_budget' in vals and 'monetary_planned_budget' not in vals:
            vals['monetary_planned_budget'] = vals['planned_budget']
        elif 'monetary_planned_budget' in vals and 'planned_budget' not in vals:
            vals['planned_budget'] = vals['monetary_planned_budget']
        
        if (self.project_financial_id.is_axis_budget == False and 
            'monetary_planned_budget' in vals and vals.get('monetary_planned_budget') > 0):
            self.project_financial_id.is_axis_budget = True
        return super().write(vals)       

    
    @api.constrains('employee_ids' ,'product_category_ids', 'project_financial_id')
    def _unique_categories_per_project(self):
        for record in self:
            if record.project_financial_id and record.product_category_ids:
                all_categories = self.env['project.financial.axis'].search([
                    ('project_financial_id', '=', record.project_financial_id.id),
                    ('id', '!=', record.id)
                ]).mapped('product_category_ids')
                
                duplicates = record.product_category_ids & all_categories
                if duplicates:
                    duplicate_names = ', '.join(duplicates.mapped('name'))
                    raise ValidationError(
                        f"Catégories : {duplicate_names}.\nDéjà utilisées dans ce PGP pour un autre Axe"
                    )

    @api.constrains('product_category_ids', 'employee_ids', 'project_financial_id')
    def _unique_categories_per_project(self):
        for record in self:
            if record.product_category_ids:
                self.env.cr.execute("""
                    SELECT DISTINCT pc.name, axis.name
                    FROM product_category_project_financial_axis_rel rel
                    JOIN project_financial_axis axis ON axis.id = rel.project_financial_axis_id
                    JOIN product_category pc ON pc.id = rel.product_category_id
                    WHERE axis.project_financial_id = %s
                    AND axis.id != %s
                    AND pc.id IN %s
                """, (record.project_financial_id.id, record.id, 
                    tuple(record.product_category_ids.ids)))
                
                for cat_name, axis_name in self.env.cr.fetchall():
                    raise ValidationError(_(
                        "La catégorie '%(category)s' est déjà utilisée dans l'axe '%(axis)s'",
                        category=cat_name,
                        axis=axis_name
                    ))
            
            if record.employee_ids:
                self.env.cr.execute("""
                    SELECT DISTINCT emp.name, axis.name
                    FROM hr_employee_project_financial_axis_rel erel
                    JOIN project_financial_axis axis ON axis.id = erel.project_financial_axis_id
                    JOIN hr_employee emp ON emp.id = erel.hr_employee_id
                    WHERE axis.project_financial_id = %s
                    AND axis.id != %s
                    AND emp.id IN %s
                """, (record.project_financial_id.id, record.id, 
                    tuple(record.employee_ids.ids)))
                
                for emp_name, axis_name in self.env.cr.fetchall():
                    raise ValidationError(_(
                        "La main d'oeuvre '%(employee)s' est déjà utilisé dans l'axe '%(axis)s'",
                        employee=emp_name,
                        axis=axis_name
                    ))
    
    @api.onchange('budget_unit', 'planned_quantity')
    def _compute_budget_unit(self):
        for axis in self:
            axis.monetary_planned_budget = axis.planned_quantity * axis.budget_unit \
                                        if axis.budget_unit != 0.0 else 0.0

    
    @api.depends("name", "project_financial_id.project_id")
    def _add_project_name(self):
        # for record in self:
        #     project = record.budget_analytic_id.project_id.name
        #     record.complete_name = f"{project}\{record.name}" if record.name else None
        for record in self:
            if record.project_financial_id and record.name:
                project_code = record.project_financial_id.project_id.code
                record.complete_name = f"{project_code}-PGP/{record.name}"
            else:
                record.complete_name = record.name or ""

    @api.depends('product_category_ids', 'employee_department_ids')
    def get_analytic_domain(self, analytic_id):
        domain = [('account_id', '=', analytic_id),
                  ('amount', '<', 0)]
        if self.product_category_ids:
            # all_category_ids = self._get_all_child_category_ids()
            # domain.append(('product_id.categ_id', 'in', all_category_ids))
            domain.append(('product_id.product_tmpl_id.categ_id', 'child_of', self.product_category_ids.ids))
        if self.employee_department_ids:
            domain.append(('employee_id.department_id', 'in', self.employee_department_ids.ids))

        return domain

    def _get_all_child_category_ids(self):
        """
        Récupère tous les IDs des catégories enfants (et les catégories sélectionnées elles-mêmes)
        """
        all_category_ids = set()
        
        for category in self.product_category_ids:
            all_category_ids.add(category.id)
            
            # Récupérer toutes les sous-catégories via la recherche hiérarchique
            child_categories = self.env['product.category'].search([
                ('id', 'child_of', category.id)
            ])
            all_category_ids.update(child_categories.ids)
        
        return list(all_category_ids)


    @api.depends('analytic_account_id')
    def _compute_analytic_cost(self):
        for axis in self:
            total = 0.0
            if not axis.analytic_account_id:
                axis.analytic_cost = 0.0
                continue

            domain = axis.get_analytic_domain(axis.analytic_account_id)
            lines = self.env['account.analytic.line'].search(domain)
            axis.cost = sum(lines.mapped('amount')) * -1


    def action_open_analytic_history(self):
        """Ouvre les écritures analytiques filtrées par compte + catégories produits + départements."""
        self.ensure_one()

        if not self.analytic_account_id:
            raise UserError("Aucun compte analytique n'est défini pour cet axe.")

        domain = self.get_analytic_domain(self.analytic_account_id)
        return {
            'type': 'ir.actions.act_window',
            'name': f"Coûts Analytiques - {self.name}",
            'res_model': 'account.analytic.line',
            'view_mode': 'list',
            'domain': domain,
            'views': [
                (self.env.ref('somachame_finance.view_analytic_axis_list').id, 'list'),
            ],
            'context': {
                'default_account_id': self.analytic_account_id.id,
            },
            'target': 'current',
        }

    def returning_exception(self, type):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _(f'Erreur de synchronisation : {self.complete_name}'),
                'message': _(
                   f'Une erreur est survenue lors de la {type} des ligne de ce Axe'
                ),
                'type': 'danger',
                'sticky': False,
            }
        }

    def compute_engage(self):
        for record in self:
            purchase_lines = self.env['purchase.order.line'].search(
                [('account_analytic_id', '=', record.analytic_account_id.id),
                 ('order_id.date_order', '>=', record.project_financial_id.date_from),
                 ('order_id.date_order', '<=', record.project_financial_id.date_to)])
            # record.engage = sum(
            #     (line.price_unit * (line.product_qty - line.qty_received)) for line in
            #     purchase_lines) * (-1)
    
    def action_open_line_history(self):
        """Ouvre l'historique des lignes pour cet axe"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Historique - {self.name}',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'tree,form',
            'domain': [('axis_id', '=', self.id)],
            'context': {'default_axis_id': self.id}
        }
    
    def add_progress_entry(self):
        """Ouvre un wizard pour ajouter une entrée de progression"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ajouter une progression',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_axis_id': self.id,
                'default_date': fields.Date.today(),
            }
        }

class ProjectFinancialAxisCategory(models.Model):
    """
    Catégorie unidimensionnelle pour les axes financiers
    """
    _name = "project.financial.axis.category"
    _description = "Déboursé Sec"
    _order = "code, id"
    _tec_name = "display_name"

    display_name = fields.Char("Déboursé Séc", compute="_get_display_name")
    name = fields.Char(string="Nom du DS", required=True, translate=True,
        help="Nom de la catégorie (ex: 'Main d\'œuvre', 'Matériel', 'Sous-traitance')")
    code = fields.Char(string="Code", size=10, required=True,
        help="Code court unique (ex: 'MO', 'MAT', 'ST')")
    description = fields.Text(string="Description", help="Description détaillée de la catégorie")
    color = fields.Integer(string="Couleur", help="Couleur pour l'affichage dans les graphiques")
    active = fields.Boolean(string="Active", default=True, help="Désactiver pour masquer la catégorie")
    # type = fields.Selection(
    #     selection=[
    #         ('labor', 'Main d\'œuvre'),
    #         ('material', 'Matériel'),
    #         ('equipment', 'Équipement'),
    #         ('subcontracting', 'Sous-traitance'),
    #         ('travel', 'Déplacements'),
    #         ('overhead', 'Frais généraux'),
    #         ('other', 'Autre'),
    #     ],
    #     string="Type de Catégorie",
    #     default='other',
    #     required=True
    # )
    
    # Critères de matching avec les lignes analytiques
    # product_category_ids = fields.Many2many(
    #     'product.category',
    #     string="Catégories de Produits",
    #     help="Si défini, seules les lignes analytiques avec ces catégories seront associées"
    # )
    
    # account_ids = fields.Many2many(
    #     'account.account',
    #     string="Comptes Comptables",
    #     domain=[('deprecated', '=', False)],
    #     help="Comptes comptables associés à cette catégorie"
    # )
    
    # department_ids = fields.Many2many(
    #     'hr.department',
    #     string="Départements",
    #     help="Départements associés à cette catégorie"
    # )
    axis_ids = fields.One2many('project.financial.axis', 'category_id', string="Axes de cette Catégorie")
    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Le code de la catégorie doit être unique !'),
        ('name_uniq', 'UNIQUE(name)', 'Le nom de la catégorie doit être unique !'),
    ]
    
    def _get_display_name(self):
        """Affiche le code et le nom"""
        for category in self:
            name = f"{category.code} : {category.name}"
            category.display_name = name
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """Recherche par code ou nom"""
        if args is None:
            args = []
        domain = args + ['|', ('code', operator, name), ('name', operator, name)]
        return self._search(domain, limit=limit, access_rights_uid=name_get_uid)
    
    def matches_analytic_line(self, analytic_line):
        """
        Vérifie si une ligne analytique correspond à cette catégorie
        Basé sur les critères définis (catégories produits, départements, etc.)
        """
        self.ensure_one()
        
        # Vérifier les catégories de produits
        if self.product_category_ids:
            if not analytic_line.product_id:
                return False
            
            # Vérifier hiérarchie des catégories
            all_categories = analytic_line.product_id.categ_id
            current = analytic_line.product_id.categ_id
            while current.parent_id:
                all_categories += current.parent_id
                current = current.parent_id
            
            if not (self.product_category_ids & all_categories):
                return False
        
        if self.department_ids and analytic_line.employee_id:
            if analytic_line.employee_id.department_id not in self.department_ids:
                return False
        
        if self.account_ids and analytic_line.general_account_id:
            if analytic_line.general_account_id not in self.account_ids:
                return False
        
        return True
    
    def get_matching_categories_for_line(self, analytic_line):
        """
        Retourne toutes les catégories qui correspondent à une ligne analytique
        """
        categories = self.env['project.financial.axis.category']
        
        for category in self.search([]):
            if category.matches_analytic_line(analytic_line):
                categories += category
        
        return categories
    
    def action_view_axes(self):
        """Voir tous les axes de cette catégorie"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Axes - {self.name}',
            'res_model': 'project.financial.axis',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }

class ProjectFinancialAxisBudget(models.Model):
    _name = "project.financial.axis.budget"
    _description = "Suivi Budget pour l'affiche Temporel des Budget"

    name = fields.Char(string="Budget", compute='_compute_name', store=True, readonly=True) 
    axis_id = fields.Many2one('project.financial.axis', string="Axe", required=True, ondelete='cascade')
    budget = fields.Float(related='axis_id.planned_budget', string="Valeur planifiée", store=True)

    @api.depends('budget')
    def _compute_name(self):
        for budget in self:
            if budget.budget and budget.axis_id:
                # Formater le montant avec séparateurs de milliers
                formatted_amount = "{:,.0f}".format(budget.budget).replace(",", " ")
                budget.name = f"{formatted_amount} DH"
            else:
                budget.name = "0,00 DH"

class ProjectFinancialAxisBudgetLine(models.Model):
    _name = "project.financial.axis.budget.line"
    _description = "Ligne des budgets monsuelles des Axes"
    _order = "date desc"

    axis_id = fields.Many2one('project.financial.axis', string="Axe Parent",
                              required=True, ondelete='cascade')
    project_financial_id = fields.Many2one('project.financial.progress', string="Projet Financier",
                                           related='axis_id.project_financial_id', store=True, 
                                           readonly=True, ondelete='cascade')
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    axis_budget_id = fields.Many2one(related="axis_id.axis_budget_id", store=True)
    planned_budget = fields.Float(string="Budget périodique", default=0.0)

    @api.model
    def create(self, vals):

        line = super().create(vals)
        if line.planned_budget > 0:
            project = self.env['project.financial.progress'].search([('id', '=', line.project_financial_id.id)], limit=1)
            project.write({'is_axis_budget': True})

        return line

class ProjectFinancialAxisLine(models.Model):
    _name = "project.financial.axis.line"
    _description = "Ligne de Suivi Temporel des Axes"
    _order = "date desc"

    @api.model
    def _get_default_axis(self):
        """Retourne un axe par défaut basé sur le contexte"""
        context = self.env.context
        if context.get('default_project_financial_id'):
            # Chercher un axe existant pour ce projet
            axis = self.env['project.financial.axis'].search([
                ('project_financial_id', '=', context['default_project_financial_id'])
            ], limit=1)
            if axis:
                return axis.id
        if context.get('default_axis_id'):
            return context.get('default_axis_id').id
        
        return True

    _sql_constraints = [
        ('axis_date_uniq', 'UNIQUE(axis_id, date)', 
         'Une date déja utilisé pour une autre ligne'),
    ]

    axis_id = fields.Many2one('project.financial.axis', string="Axe Parent",
                              required=True, ondelete='cascade',
                              default=lambda self: self._get_default_axis())  
    project_financial_id = fields.Many2one(
        'project.financial.progress',  # Pas project.project !
        string="Projet Financier",
        related='axis_id.project_financial_id',  # Related, pas store=True direct
        store=True,  # Optionnel - si vous voulez pouvoir rechercher dessus
        readonly=True,
        ondelete='cascade'  # IMPORTANT : cascade
    )  
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    description = fields.Text(string="Description", help="Description de la ligne")
    progress = fields.Float(string="Avancement %", digits=(12, 2), help="Avancement à cette date précise")
    axis_planned_quantity = fields.Float(related="axis_id.planned_quantity", store=True)
    actual_cost = fields.Monetary(string="Coût Réel", currency_field='currency_id', digits=(12, 6), group_operator="sum", default=0.0)
    # axis_budget_id = fields.Many2one(related="axis_id.axis_budget_id", store=True)
    # planned_budget = fields.Float(string="Budget périodique", default=0.0)
    earned_value = fields.Float(string="Quantité Acquise", default=0.0, digits=(12, 6))
    earned_amount = fields.Monetary(string="Valeur Acquise", 
        compute='_compute_earned_amount',
        store=True,
        currency_field='currency_id',
        help="Valeur du travail réalisé (VA)",
    )
    currency_id = fields.Many2one('res.currency', related='axis_id.currency_id', store=True)
    acquise_value = fields.Float(string="% Valeur Acquie", 
                                 compute='_compute_acquise', inverse='_inverse_acquise', store=True,
                                  digits=(3, 6), help="VA / VP")
    
    grid_cost = fields.Float(
        string="Coût Réel (Grid)",
        compute='_compute_grid_cost',
        inverse='_inverse_grid_cost',
        store=True
    )

    @api.depends('actual_cost')
    def _compute_grid_cost(self):
        for record in self:
            record.grid_cost = record.actual_cost

    def _inverse_grid_cost(self):
        for record in self:
            record.actual_cost = record.grid_cost
    # cost_performance_index = fields.Float(string="Indicateur de Coùt", store=True,# compute='_compute_cost',
    #                                       digits=(3, 6), help="VA / CR")
    # delay_performance_index = fields.Float(string="Indicteur de Délais", store=True, group_operator="avg",
    #                                     # compute='_compute_delay',
    #                                       digits=(3, 6), help="VA / VP")
    
    # grid_cost = fields.Float(
    #     string="Coût Réel (Grid)",
    #     compute='_compute_grid_cost',
    #     inverse='_inverse_grid_cost',
    #     store=True
    # )

    # @api.depends('actual_cost')
    # def _compute_grid_cost(self):
    #     for record in self:
    #         record.grid_cost = record.actual_cost

    def write(self, vals):
        """
        Surcharge de write pour protéger earned_value selon le type d'axe
        """
        # if 'earned_value' in vals:
        #     for line in self:
        #         axis = line.axis_id
        #         if axis and axis.type != 'manual':
        #             old_value = line.earned_value
        #             new_value = vals['earned_value']
        #             if old_value != new_value:
        #                 raise UserError(_(
        #                     "❌ Modification interdite\n\n"
        #                     "Le champ Valeur Aquise ne peut pas être modifié "
        #                     "manuellement pour les axes de type '%(type)s'.\n\n"
        #                     "Cette valeur est automatiquement calculée "))
        
        return super(ProjectFinancialAxisLine, self).write(vals)


    # @api.depends('axis_id.project_financial_id')
    # def _compute_project_financial(self):
    #     for line in self:
    #         line.project_financial_id = line.axis_id.project_financial_id.id \
    #             if line.axis_id.project_financial_id else False
    
    @api.depends('axis_id.budget_unit', 'earned_value')
    def _compute_earned_amount(self):
        for line in self:
            line.earned_amount = line.earned_value * line.axis_id.budget_unit

    @api.depends('date', 'axis_planned_quantity', 'earned_value')
    def _compute_acquise(self):
        for line in self:
            line.acquise_value = line.earned_value / line.axis_planned_quantity \
                if line.axis_planned_quantity != 0 else 0.0
                # return line._get_performance(
                #     'acquise_value', 'earned_value', line.axis_id, 
                #     line.date, line.axis_planned_quantity)
    
    def _inverse_acquise(self):
        for record in self:
            if record.acquise_value in round(0,1):
                record.earned_value = record.acquise_value * record.axis_planned_quantity
            else:
                raise UserError(_(
                            "❌ Modification interdite\n\n"
                            "Le champ Valeur Aquise ne peut pas prendre "
                            "une valeur dépase la valeur planifier.\n\n"
                            "Cette valeur est automatiquement calculée "))

    # @api.depends('date', 'actual_cost', 'earned_amount')
    def _compute_cost(self):
        for line in self:
            if line.earned_amount != 0:
                return line._get_performance(
                    'cost_performance_index', 'actual_cost', line.axis_id, 
                    line.date, 0.0, True)
    
    # @api.depends('date', 'axis_id.planned_budget', 'earned_amount')
    def _compute_delay(self):
        for line in self:
            if line.axis_id.planned_budget != 0:
                return line._get_performance(
                    'delay_performance_index', 'earned_amount', line.axis_id, 
                    line.date, line.axis_id.planned_budget)
    
    def _get_performance(self, field, src_field, axis, date, value, is_cost=False):
            lines = self.env['project.financial.axis.line']
            line_month = date.month
            line_year = date.year
            start_date = fields.Date.to_date(f'{line_year}-{line_month:02d}-01')
            index = 0
            
            domain = [
                ('axis_id', '=', axis.id),
                ('date', '>=', start_date),
                ('date', '<=', fields.Date.end_of(date, 'month')),
            ]
            month_lines = lines.search(domain)            
            monthly_value = sum(month_lines.mapped(src_field))
            if is_cost:
                monthly_earned_amount = sum(month_lines.mapped('earned_amount'))
                index = monthly_earned_amount / monthly_value if monthly_value != 0.0 else 0.0
            else:
                index = monthly_value / value
            
            debut = lines.search([('axis_id', '=', axis.id),
                ('date', '=', start_date)], limit=1)
            if debut:
                debut.write({field: index})
            else:
                lines.create({
                    'date': date,
                    'axis_id': axis.id,
                    field: index,
                })

    # def _compute_performance(self):
    #     for line in self:
    #         line.cost_performance_index = line.earned_amount / line.actual_cost if line.actual_cost != 0 else 0.0
    #         if line.axis_id.planned_budget != 0:
    #             line.acquise_value = line.earned_value / line.axis_planned_quantity
    #             line.delay_performance_index = line.earned_amount / line.axis_id.planned_budget
    #         else:
    #             line.delay_performance_index = 0.0
    
    # project_id = fields.Many2one("project.project", required=True, index=True)
    # date = fields.Date(required=True, index=True)

    # kpi_type = fields.Selection([
    #     ("planned_budget", "Planned Budget"),
    #     ("delay_performance_index", "Delay Performance Index (DPI)"),
    #     ("cost_performance_index", "Cost Performance Index (CPI)"),
    # ], string="KPI Type", required=True, index=True)

    # value = fields.Float(string="Value", required=True)
    def _sync_kpi_lines(self):
        KPI = self.env["project.financial.axis.kpi"].sudo()
        for line in self:
            vals_map = {
                "planned_budget": line.planned_budget or 0.0,
                "delay_performance_index": line.delay_performance_index or 0.0,
                "cost_performance_index": line.cost_performance_index or 0.0,
            }
            for kpi_type, value in vals_map.items():
                kpi = KPI.search([("axis_line_id", "=", line.id), ("kpi_type", "=", kpi_type)], limit=1)
                vals = {"axis_line_id": line.id, "kpi_type": kpi_type, "value": value}
                if kpi:
                    kpi.write(vals)
                else:
                    KPI.create(vals)

