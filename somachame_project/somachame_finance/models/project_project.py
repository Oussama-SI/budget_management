from odoo import api, models, fields

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    @api.model
    def create(self, vals):
        """Créer automatiquement l'analyse financière quand un projet est créé"""
        project = super().create(vals)
        
        # Créer automatiquement l'analyse financière
        self.env['project.financial.progress'].create({
            'project_id': project.id,
            'user_id': project.user_id.id or False,
            'currency_id': self.env.company.currency_id.id or 109,
            'state': 'draft',
            'create_axis': True,
            'active': True,
        })
        
        return project
    
    def action_create_financial_analysis(self):
        """Bouton pour créer manuellement l'analyse financière"""
        self.ensure_one()
        
        # Vérifier si une analyse existe déjà
        existing = self.env['project.financial.progress'].search([
            ('project_id', '=', self.id)
        ], limit=1)
        
        if existing:
            financial_id = existing.id
        else:
            # Si n'existe pas, créer nouvelle analyse
            new_progress = self.env['project.financial.progress'].create({
                'project_id': self.id,
                'state': 'draft'
            })
            new_progress._create_standard_axes()
            financial_id = new_progress.id
        
        # Ouvrir l'analyse financière
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analyse Financière',
            'res_model': 'project.financial.progress',
            'res_id': financial_id,
            'view_mode': 'form',
            'target': 'current'
        }