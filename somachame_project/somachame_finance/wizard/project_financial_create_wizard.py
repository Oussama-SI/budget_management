from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import random
from datetime import date

class ProjectFinancialCreateWizard(models.TransientModel):
    _name = 'project.financial.create.wizard'
    _description = 'Assistant de création de projet financier'
        
    project_id = fields.Many2one(
        'project.project',
        string="Projet lié",
        domain="[('account_id', '!=', False)]",
        required=True,
        help="Projet Odoo auquel lier le suivi financier"
    )
    
    user_id = fields.Many2one(
        'res.users',
        string="Responsable",
        default=lambda self: self.env.user,
        required=True
    )
    
    date_start = fields.Date(
        string="Date de début",
        related="project_id.date_start",
    )
    
    date_end = fields.Date(
        string="Date de fin prévue",
        related="project_id.date"
    )
    
    description = fields.Text(string="Description")
    
    # Étape 2: Options d'import
    import_standard_axes = fields.Boolean(
        string="Importer les axes standards",
        default=True,
        help="Importer les axes budgétaires prédéfinis"
    )
    
    import_sample_data = fields.Boolean(
        string="Importer des données d'exemple",
        default=False,
        help="Importer des données d'avancement et de coûts d'exemple"
    )
    
    import_year = fields.Integer(
        string="Année d'import",
        default=fields.Date.today().year,
        help="Année pour les données importées"
    )

    total_budget = fields.Float(
        string="Budget total estimé",
        # compute='_compute_total_budget',
        # store=False,
        help="Budget total calculé à partir des axes standards"
    )
    
    # @api.constrains('date_start', 'date_end')
    # def _check_dates(self):
    #     """Vérifie la cohérence des dates"""
    #     for wizard in self:
    #         if wizard.date_end and wizard.date_start > wizard.date_end:
    #             raise ValidationError(
    #                 _("La date de fin doit être postérieure à la date de début.")
    #             )
    
        
    # def _import_sample_data(self, financial_project):
    #     """Importe des données d'exemple (acquise_value et coûts)"""
    #     # Utiliser la fonction d'import existante si disponible
    #     if hasattr(self.env['project.financial.data.importer'], 'import_financial_data'):
    #         importer = self.env['project.financial.data.importer']
    #         return importer.import_financial_data(financial_project.id, self.import_year)
    #     return {}
    
    
    def action_create_financial_project(self):
        """Crée le projet financier avec toutes les options"""
        self.ensure_one()
        progress = self.env['project.financial.progress']

        if progress.search([('project_id', '=', self.project_id.id)]):
            raise UserError('')
        
        financial_vals = {
            'project_id': self.project_id.id,
            'user_id': self.user_id.id,
            'description': self.description,
            'currency_id': self.env.company.currency_id.id,
            'create_axis': self.import_standard_axes,
            'active': True,
        }
        
        financial_project = progress.create(financial_vals)        
        return {
            'type': 'ir.actions.act_window',
            'name': financial_project.name,
            'res_model': 'project.financial.progress',
            'res_id': financial_project.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }