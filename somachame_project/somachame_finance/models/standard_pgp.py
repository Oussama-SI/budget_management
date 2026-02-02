from datetime import datetime
from odoo import models, api, fields

class ProjectFinancialProgress(models.Model):
    _inherit = 'project.financial.progress'
    
    def _create_standard_axes(self):
        """Crée les axes standards pour ce projet"""
        self.ensure_one()
        
        # Vérifier si des axes existent déjà
        if self.axis_ids:
            return False
        
        last_day = datetime(fields.date.today().year, 12, 31).date()

        standard_axes = [
            # DS1: Etudes et Methodes
            {
                'name': "Études d'execution",
                'category_id': self._get_or_create_category('DS1', 'Etudes et Methodes', 1),
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 10
            },
            {
                'name': 'Méthodes et préparation',
                'category_id': self._get_or_create_category('DS1', 'Etudes et Methodes', 1),
                'type': 'manual', 
                'cost_type': 'analytic',
                'sequence': 20
            },
            # DS2: Appro
            {
                'name': 'Toles et profilés',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'type': 'stock',
                'cost_type': 'mrp',
                'sequence': 30
            },
            {
                'name': 'Couverture et Bardage',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 40
            },
            {
                'name': 'Planchers',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 50
            },
            {
                'name': 'Boulonnerie et Accessoires',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 60
            },
            {
                'name': 'Tuyauterie',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 70
            },
            {
                'name': 'Peinture',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 80
            },
            
            # DS3: Fabrication
            {
                'name': 'MO Fab',
                'category_id': self._get_or_create_category('DS3', 'Fabrication', 3),
                'type': 'rate',
                'cost_type': 'analytic',
                'sequence': 100
            },
            {
                'name': 'MO Peinture',
                'category_id': self._get_or_create_category('DS3', 'Fabrication', 3),
                'type': 'rate',
                'cost_type': 'analytic',
                'sequence': 110
            },
            
            # DS4: Montage
            {
                'name': 'MO Pose',
                'category_id': self._get_or_create_category('DS4', 'Montage', 4),
                'type': 'manual',
                'cost_type': 'analytic',
                'sequence': 120
            },
            {
                'name': 'Transport',
                'category_id': self._get_or_create_category('DS4', 'Montage', 4),
                'type': 'move',
                'cost_type': 'invoice',
                'sequence': 130
            },
            {
                'name': 'Manutention',
                'category_id': self._get_or_create_category('DS4', 'Montage', 4),
                'type': 'move',
                'cost_type': 'invoice',
                'sequence': 140
            },
            
            # DS5: Préstations
            {
                'name': 'Bureau de contrôle',
                'category_id': self._get_or_create_category('DS5', 'Préstations', 5),
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 150
            },
            {
                'name': 'Galvanisation',
                'category_id': self._get_or_create_category('DS5', 'Préstations', 5),
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 160
            },
            {
                'name': 'Autres Sous traitance',
                'category_id': self._get_or_create_category('DS5', 'Préstations', 5),
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 170
            },
        ]
        
        # Créer les axes
        Axis = self.env['project.financial.axis']
        AxisBudgetLine = self.env['project.financial.axis.budget.line']
        AxisLine = self.env['project.financial.axis.line']
        
        for axis_data in standard_axes:
            axis = Axis.create({
                'name': axis_data['name'],
                'project_financial_id': self.id,
                'category_id': axis_data['category_id'],
                'type': axis_data['type'],
                'cost_type': axis_data['cost_type'],
                'sequence': axis_data['sequence'],
                # 'color': axis_data['category_id'].color if axis_data['category_id'] else 0,
            })
            axis_id = axis.id
            date = self.date_from or last_day
            
            AxisBudgetLine.create({
                'axis_id': axis_id,
                'date': date,
                'planned_budget': 0.0,
            })
            # AxisLine.create({
            #     'axis_id': axis_id,
            #     'date': date,
            #     'acquise_value': 0.0,
            # })
        
        return True
    
    def _get_or_create_category(self, code, name, color):
        """Récupère ou crée une catégorie"""
        Category = self.env['project.financial.axis.category']
        
        # Chercher la catégorie par nom ou code
        category = Category.search(['|', ('name', '=', name), ('code', '=', code)], limit=1)
        
        if not category:
            # Créer la catégorie si elle n'existe pas
            category = Category.create({
                'name': name,
                'code': code,
                'color': color,
                'active': True
            })
        
        return category.id
    
    @api.model
    def create(self, vals):
        """Override create pour générer automatiquement la structure"""
        record = super().create(vals)

        if record.create_axis:
            record._create_standard_axes()
        
        return record