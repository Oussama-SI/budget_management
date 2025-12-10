from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


# project.financial is the same domain as project.projct 1.1
class ProjectFinancialProgress(models.Model):
    _name = "project.financial.progress"
    _description = "Analyse Financière du Projet"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    
    @api.model
    def _get_default_currency(self):
        return self.env.company.currency_id
    

    active = fields.Boolean(default=True, export_string_translation=False)
    name = fields.Char("Désignation", required=True, states={'done': [('readonly', True)]})
    project_id = fields.Many2one('project.project', string="Projet", copy=False, ondelete='cascade')
    account_id = fields.Many2one('account.analytic.account', string="Compte Analytique", related="project_id.account_id", store=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user,  
                              tracking=True, store=True)
    date_from = fields.Date('Start Date', states={'done': [('readonly', True)]}, default=lambda self: self.project_id.date_start)
    date_to = fields.Date('End Date', states={'done': [('readonly', True)]}, default=lambda self: self.project_id.date)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'Confirmed'),
        ('validate', 'Validated'),
        ('done', 'Done')
        ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    axis_ids = fields.One2many('project.financial.axis', 'project_financial_id', 'Axes analytiques',
        states={'done': [('readonly', True)]}, copy=True)
    currency_id = fields.Many2one('res.currency', string='Devise',  default=_get_default_currency, required=True)
    total_budget = fields.Monetary(string="Budget Total", compute='_compute_total_budget', store=True)
    project_earned_amount = fields.Monetary(string="Valeur Acquise", 
        # compute='_compute_financial_metrics',
        # store=True,
        help="Valeur du travail réalisé VA"
    )
    project_planned_amount = fields.Monetary(string="Valeur Planifiée", 
        # compute='_compute_financial_metrics',
        # store=True,
        help="Valeur de travail planifié VP"
    )
    project_cost = fields.Monetary(string="Coût Réel", 
        # compute='_compute_financial_metrics',
        store=True,
        help="Coût réel engagé CR"
    )
    cost_performance_index = fields.Float(string="IPC",
                                        #    compute='_compute_index',
                                          digits=(3, 2), help="VA / CR")
    delay_performance_index = fields.Float(string="IPD", 
                                        #    compute='_compute_index',
                                          digits=(3, 2), help="VA / VP")
    rec_performance_index = fields.Float(string="IPR",
                                         compute="_compute_index",
                                         digits=(3,2), help="IPR = FU / FP")
    marge_sale = fields.Monetary(
          compute='_compute_index',
          string="Marge sur vente")
    variance = fields.Monetary(
        string="Écart Coût",
        # compute='_compute_financial_metrics',
        # store=True,
        help="EC = VA - CR"
    )
    variance_delay = fields.Monetary(
        string="Ecart de Délais",
        # compute='_compute_financial_metrics',
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
                # project.delay_performance_index = sum(axis.delay_performance_index for axis in project.axis_ids) / len(project.axis_ids)
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


    @api.depends('axis_ids.planned_budget')
    def _compute_total_budget(self):
        for record in self:
            record.total_budget = sum(record.axis_ids.mapped('planned_budget'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError("La date de début doit être anférieure à la date de fin.")

    # Actions de workflow
    def action_budget_confirm(self):
        if not self.axis_ids:
            raise UserError("Veuillez ajouter au moins un axe analytique avant de confirmer.")
        self.write({'state': 'confirm'})

    def action_budget_draft(self):
        self.write({'state': 'draft'})

    def action_budget_validate(self):
        self.write({'state': 'validate'})

    def action_budget_cancel(self):
        self.write({'state': 'cancel'})

    def action_budget_done(self):
        self.write({'state': 'done'})

    # def action_open_axes_grid(self):
    #     return {
    #         'name': "Grille des Axes",
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'project.financial.axis',
    #         'view_mode': 'list,form',
    #         'domain': [('project_financial_id', '=', self.id)],
    #         'context': {
    #             'default_project_financial_id': self.id,
    #             'grid_mode': True,
    #         }
    #     }

    def action_open_axes_grid(self):
        return {
            'name': "Grid Progress Mensuel",
            'type': 'ir.actions.act_window',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'grid,tree,form',
            'domain': [
                ('axis_id.project_financial_id', '=', self.id)
            ],
            'context': {
                'default_axis_id': self.id,
            }
        }
    
    def action_open_project_axes(self, *args, **kwargs):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Axes Financiers',
            'res_model': 'project.financial.axis',
            'view_mode': 'grid,pivot,form',
            'views': [(self.env.ref('somachame_finance.view_project_financial_axis_grid').id, 'grid'),
                      (self.env.ref('somachame_finance.view_project_financial_axis_pivot_calculated').id, 'pivot')],
            'domain': [('project_financial_id', '=', self.id)],
            'target': 'current',
        }
    
    def action_open_axes_progress(self):
        """Ouvre l'analyse temporelle des axes (GRID/PIVOT sur les LIGNES)"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyse Temporelle des Axes',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'grid,pivot,cohort,graph',
            'views': [
                (self.env.ref('somachame_finance.view_project_financial_axis_line_progress_grid').id, 'grid'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_pivot').id, 'pivot'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_cohort').id, 'cohort'),
                (self.env.ref('somachame_finance.view_project_financial_axis_line_graph').id, 'graph')
            ],
            'domain': [('project_financial_id', '=', self.id)],
            'context': {
                'default_axis_id': False,  # Permet la création manuelle
                'grid_range': 'month',
                'search_default_group_by_axis': 1,
            },
            'target': 'current',
        }
    
    def action_open_axes_cost(self):
        """Ouvre l'analyse temporelle des axes (GRID/PIVOT sur les LIGNES)"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyse Temporelle des Axes',
            'res_model': 'project.financial.axis.line',
            'view_mode': 'grid,pivot,cohort,graph',
            'views': [
                (self.env.ref('somachame_finance.view_project_financial_axis_line_progress_grid').id, 'grid'),
            ],
            'domain': [('project_financial_id', '=', self.id)],
            'context': {
                'default_axis_id': False,  # Permet la création manuelle
                'grid_range': 'month',
                'search_default_group_by_axis': 1,
            },
            'target': 'current',
        }


class ProjectFinancialAxis(models.Model):
    _name = "project.financial.axis"
    _order = "sequence, id"
    _description = "Axe Analytique"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Axe analytique', required=True, translate=True)
    complete_name = fields.Char("Désignation", index="trigram", compute="_add_project_name")
    sequence = fields.Integer(default=1, export_string_translation=False)
    project_financial_id = fields.Many2one('project.financial.progress', 'Projet', ondelete='cascade', index=True, required=True)
    category_id = fields.Many2one('project.financial.axis.category', string="Catégorie", ondelete='set null')
    line_ids = fields.One2many(
        'project.financial.axis.line',
        'axis_id',
        string="Historique de Progression"
    )
    description = fields.Html(help="")
    color = fields.Integer(string='Couleur', help="Couleur pour les tags")
    type = fields.Selection([
            ('manual', 'Saisie manuelle'),
            ('mrp', 'Ordre de fabrication'),
            ('inventaire', 'Sortie stock'),
            ('intern', 'Forfait interne'),
        ],
        string="Cible d'Axe", required=True,
        default='manual',
        tracking=True,
        help="")
    uom_id = fields.Many2one('uom.uom', "Unité")
    product_category_ids =  fields.Many2many('product.category', string="Catégorie produit")
    employee_department_ids = fields.Many2many('hr.department', string="Département")
    mrp_id = fields.Many2one('mrp.workcenter', string="Phase de Fabrication")
    stock_id = fields.Many2one('stock.location', string="Emplacement")
    analytic_account_id = fields.Many2one('account.analytic.account', related="project_financial_id.account_id")
    # analytic_group_id = fields.Many2one('account.analytic.group', 'Analytic Group', related='analytic_account_id.group_id', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    planned_quantity = fields.Float("Quantité prévue", defaults=1.0, required=True)
    planned_budget = fields.Monetary(# le montant prévus exist dans la forme vue
        'budget', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    budget_unit = fields.Monetary(compute='_compute_budget_unit', store=True)
    cost = fields.Monetary("Coùt totale")
    progress = fields.Float(string="Avancement %",
                            group_operator="avg",
                            #  compute='_compute_progress', 
                            digits=(12, 2), store=True)
    # practical_amount = fields.Monetary(
    #     compute='_compute_practical_amount', string='Practical Amount', help="Amount really earned/spent.")
    # theoritical_amount = fields.Monetary(
    #     compute='_compute_theoritical_amount', string='Theoretical Amount',
    #     help="Amount you are supposed to have earned/spent at this date.")
    # percentage = fields.Float(
    #     compute='_compute_percentage', string='Achievement',
    #     help="Comparison between practical and theoretical amount. This measure tells you if you are below or over budget.")
    performance_index = fields.Float(
        string="Indice Performance",
        # compute='_compute_performance_index',
        digits=(12, 3)
    )

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
    
    @api.depends('planned_budget', 'planned_quantity')
    def _compute_budget_unit(self):
        for axis in self:
            axis.budget_unit = axis.planned_budget / axis.planned_quantity
    
    @api.depends("name", "project_financial_id.project_id")
    def _add_project_name(self):
        # for record in self:
        #     project = record.budget_analytic_id.project_id.name
        #     record.complete_name = f"{project}\{record.name}" if record.name else None
        for record in self:
            if record.project_financial_id and record.name:
                project_name = record.project_financial_id.name
                record.complete_name = f"{project_name}/{record.name}"
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
            axis.cost = sum(lines.mapped('amount')) * -1  # Odoo stocke les coûts en négatif


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


    def compute_engage(self):
        for record in self:
            purchase_lines = self.env['purchase.order.line'].search(
                [('account_analytic_id', '=', record.analytic_account_id.id),
                 ('order_id.date_order', '>=', record.project_financial_id.date_from),
                 ('order_id.date_order', '<=', record.project_financial_id.date_to)])
            # record.engage = sum(
            #     (line.price_unit * (line.product_qty - line.qty_received)) for line in
            #     purchase_lines) * (-1)

    # livre = fields.Float('Montant Livré', compute="compute_livre")

    # def compute_livre(self):
    #     for record in self:
    #         purchase_lines = self.env['purchase.order.line'].search(
    #             [('account_analytic_id', '=', record.analytic_account_id.id),
    #              ('order_id.date_order', '>=', record.date_from),
    #              ('order_id.date_order', '<=', record.date_to)])
    #         record.livre = sum(
    #             (line.price_unit * (line.qty_received - line.qty_invoiced)) for line in
    #             purchase_lines) * (-1)

    # restant = fields.Float('Montant resant', compute="compute_restant")

    # def compute_restant(self):
    #     if self.planned_amount < 0:
    #         self.restant = self.planned_amount - (self.livre + self.engage + self.practical_amount)
    #     else:
    #         self.restant = self.planned_amount - (self.livre + self.engage + self.practical_amount)

    """@api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # overrides the default read_group in order to compute the computed fields manually for the group
        fields_list = {'practical_amount', 'theoritical_amount', 'percentage'}
        fields = {field.split(':', 1)[0] if field.split(':', 1)[0] in fields_list else field for field in fields}
        result = super(CrossoveredBudgetLines, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                                orderby=orderby, lazy=lazy)
        if any(x in fields for x in fields_list):
            for group_line in result:

                # initialise fields to compute to 0 if they are requested
                if 'practical_amount' in fields:
                    group_line['practical_amount'] = 0
                if 'theoritical_amount' in fields:
                    group_line['theoritical_amount'] = 0
                if 'percentage' in fields:
                    group_line['percentage'] = 0
                    group_line['practical_amount'] = 0
                    group_line['theoritical_amount'] = 0

                if group_line.get('__domain'):
                    all_budget_lines_that_compose_group = self.search(group_line['__domain'])
                else:
                    all_budget_lines_that_compose_group = self.search([])
                for budget_line_of_group in all_budget_lines_that_compose_group:
                    if 'practical_amount' in fields or 'percentage' in fields:
                        group_line['practical_amount'] += budget_line_of_group.practical_amount

                    if 'theoritical_amount' in fields or 'percentage' in fields:
                        group_line['theoritical_amount'] += budget_line_of_group.theoritical_amount

                    if 'percentage' in fields:
                        if group_line['theoritical_amount']:
                            # use a weighted average
                            group_line['percentage'] = float(
                                (group_line['practical_amount'] or 0.0) / group_line['theoritical_amount']) * 100

        return result

    # def _is_above_budget(self):
    #     for line in self:
    #         if line.theoritical_amount >= 0:
    #             line.is_above_budget = line.practical_amount > line.theoritical_amount
    #         else:
    #             line.is_above_budget = line.practical_amount < line.theoritical_amount

    def _compute_line_name(self):
        #just in case someone opens the budget line in form view
        for line in self:
            computed_name = line.crossovered_budget_id.name
            if line.budget_analytic_id:
                computed_name += ' - ' + line.budget_analytic_id.name
            if line.analytic_account_id:
                computed_name += ' - ' + line.analytic_account_id.name
            line.name = computed_name

    def _compute_practical_amount(self):
        for line in self:
            acc_ids = line.budget_analytic_id.account_ids.ids
            pro_ids = line.categories_pro.id
            emp_ids = line.categories_emp.id
            eng_ids = line.categories_eng.id
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id:
                analytic_line_obj = self.env['account.analytic.line']
                domain = [('account_id', '=', line.analytic_account_id.id),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ]
                if acc_ids:
                    domain += [('general_account_id', 'in', acc_ids)]
                    if pro_ids:
                        domain += [('product_id.categ_id','=', pro_ids)]
                    if emp_ids and not analytic_line_obj.engin_id:
                        domain += [('employee_id.department_id','=', emp_ids)]
                    if eng_ids:
                        domain += [('engin_id.category_id','=', eng_ids),
                                   #('code','in', line.categories_eng.vehicle.tauxf),
                                   ]
                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

            else:
                aml_obj = self.env['account.move.line']
                domain = [('account_id', 'in',
                           line.budget_analytic_id.account_ids.ids),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to)
                          ]
                if pro_ids:
                    domain += [('product_id.categ_id', '=', pro_ids)]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)
            line.practical_amount = self.env.cr.fetchone()[0] or 0.0

    def _compute_theoritical_amount(self):
        # beware: 'today' variable is mocked in the python tests and thus, its implementation matter
        today = fields.Date.today()
        for line in self:
            if line.paid_date:
                if today <= line.paid_date:
                    theo_amt = 0.00
                else:
                    theo_amt = line.planned_amount
            else:
                line_timedelta = line.date_to - line.date_from
                elapsed_timedelta = today - line.date_from

                if elapsed_timedelta.days < 0:
                    # If the budget line has not started yet, theoretical amount should be zero
                    theo_amt = 0.00
                elif line_timedelta.days > 0 and today < line.date_to:
                    # If today is between the budget line date_from and date_to
                    theo_amt = (elapsed_timedelta.total_seconds() / line_timedelta.total_seconds()) * line.planned_amount
                else:
                    theo_amt = line.planned_amount
            line.theoritical_amount = theo_amt

    def _compute_percentage(self):
        for line in self:
            if line.theoritical_amount != 0.00:
                line.percentage = float((line.practical_amount or 0.0) / line.theoritical_amount)
            else:
                line.percentage = 0.00"""

    # @api.constrains('budget_analytic_id', 'analytic_account_id')
    # def _must_have_analytical_or_budgetary_or_both(self):
    #     if not self.analytic_account_id and not self.budget_analytic_id:
    #         raise ValidationError(
    #             _("You have to enter at least a budgetary position or analytic account on a budget line."))

    
    # def action_open_budget_entries(self):
    #     if self.analytic_account_id:
    #         # if there is an analytic account, then the analytic items are loaded
    #         action = self.env['ir.actions.act_window']._for_xml_id('analytic.account_analytic_line_action_entries')
    #         action['domain'] = [('account_id', '=', self.analytic_account_id.id),
    #                             ('date', '>=', self.date_from),
    #                             ('date', '<=', self.date_to)
    #                             ]
    #         if self.budget_analytic_id:
    #             action['domain'] += [('general_account_id', 'in', self.budget_analytic_id.account_ids.ids)]
    #     else:
    #         # otherwise the journal entries booked on the accounts of the budgetary postition are opened
    #         action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
    #         action['domain'] = [('account_id', 'in',
    #                              self.budget_analytic_id.account_ids.ids),
    #                             ('date', '>=', self.date_from),
    #                             ('date', '<=', self.date_to)
    #                             ]
    #     return action

    # @api.constrains('date_from', 'date_to')
    # def _line_dates_between_budget_dates(self):
    #     for rec in self:
    #         budget_date_from = rec.crossovered_budget_id.date_from
    #         budget_date_to = rec.crossovered_budget_id.date_to
    #         if rec.date_from:
    #             date_from = rec.date_from
    #             if date_from < budget_date_from or date_from > budget_date_to:
    #                 raise ValidationError(_('"Start Date" of the budget line should be included in the Period of the budget'))
    #         if rec.date_to:
    #             date_to = rec.date_to
    #             if date_to < budget_date_from or date_to > budget_date_to:
    #                 raise ValidationError(_('"End Date" of the budget line should be included in the Period of the budget'))

class ProjectFinancialAxisCategory(models.Model):
    """
    Catégorie unidimensionnelle pour les axes financiers
    """
    _name = "project.financial.axis.category"
    _description = "Catégorie d'Axes Financiers"
    _order = "sequence, name"
    
    name = fields.Char(string="Nom de la Catégorie", required=True, translate=True,
        help="Nom de la catégorie (ex: 'Main d\'œuvre', 'Matériel', 'Sous-traitance')")
    code = fields.Char(string="Code", size=10, required=True,
        help="Code court unique (ex: 'MO', 'MAT', 'ST')")
    sequence = fields.Integer(string="Séquence", default=10, help="Ordre d'affichage")
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
    
    def name_get(self):
        """Affiche le code et le nom"""
        result = []
        for category in self:
            name = f"[{category.code}] {category.name}"
            result.append((category.id, name))
        return result
    
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


class ProjectFinancialAxisLine(models.Model):
    _name = "project.financial.axis.line"
    _description = "Ligne de Suivi Temporel des Axes"
    _order = "date desc"

    axis_id = fields.Many2one('project.financial.axis', string="Axe Parent",
                              required=True, ondelete='cascade',
                              default=lambda self: self._get_default_axis())    
    project_financial_id = fields.Many2one('project.project', compute='_compute_project_financial', store=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    progress = fields.Float(string="Avancement %", digits=(12, 2), help="Avancement à cette date précise")
    axis_planned_quantity = fields.Float(related="axis_id.planned_quantity", store=True)
    earned_value = fields.Float(string="Quantité Acquise")
    actual_cost = fields.Monetary(string="Coût Réel", currency_field='currency_id', group_operator="sum")
    # planned_budget = fields.Monetary(string="Budget Planifié", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='axis_id.currency_id', store=True)
    earned_amount = fields.Monetary(string="Valeur Acquise", 
        # compute='_compute_financial_metrics',
        # store=True,
        currency_field='currency_id',
        help="Valeur du travail réalisé (VA)"
    )
    cost_performance_index = fields.Float(string="IPC", store=True,
                                          compute='_compute_performance',
                                          digits=(3, 5), help="VA / CR")
    delay_performance_index = fields.Float(string="IPD", store=True,
                                           group_operator="avg",
                                        compute='_compute_performance',
                                          digits=(3, 5), help="VA / VP")
    @api.depends('axis_id.project_financial_id')
    def _compute_project_financial(self):
        for line in self:
            line.project_financial_id = line.axis_id.project_financial_id.id \
                if line.axis_id.project_financial_id else False
    
    @api.depends('axis_id.budget_unit', 'earned_value')
    def _compute_earned_amount(self):
        for line in self:
            line.earned_amount = line.earned_value * line.axis_id.budget_unit

    @api.depends('actual_cost', 'axis_id.planned_quantity', 'earned_amount', 'earned_value')
    def _compute_performance(self):
        for line in self:
            line.cost_performance_index = line.earned_amount / line.actual_cost if line.actual_cost != 0 else 0.0
            if line.axis_id.planned_quantity != 0:
                line.delay_performance_index = line.earned_value / line.axis_id.planned_quantity
            else:
                line.delay_performance_index = 0.0

    @api.model
    def _get_default_axis(self):
        """Retourne un axe par défaut basé sur le contexte"""
        context = self.env.context
        # if context.get('default_project_financial_id'):
        #     # Chercher un axe existant pour ce projet
        #     axis = self.env['project.financial.axis'].search([
        #         ('project_financial_id', '=', context['default_project_financial_id'])
        #     ], limit=1)
        #     if axis:
        #         return axis.id
        if context.get('default_axis_id'):
            return context.get('default_axis_id').id
        
        return False

