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
        
        today = fields.date.today()
        
        last_day = datetime(today.year, 12, 31).date()
        year_before = datetime(today.year - 1, 12, 31).date()
        year_after = datetime(today.year + 1, 12, 31).date()

        # 32694
        standard_axes = [
            # DS1: Etudes et Methodes
            {
                'name': "Études d'execution",
                'category_id': self._get_or_create_category('DS1', 'Etudes et Methodes', 1),
                'uom_id': 32694,
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 10,
                'product_category_ids': [87],
                'employee_ids': []
            },
            {
                'name': 'Méthodes et préparation',
                'category_id': self._get_or_create_category('DS1', 'Etudes et Methodes', 1),
                'uom_id': 32694,
                'type': 'manual', 
                'cost_type': 'analytic',
                'sequence': 20,
                'product_category_ids': [],
                'employee_ids': [12, 9, 13, 15, 11, 8]
            },
            
            # DS2: Appro
            {
                'name': 'Toles et profilés',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'uom_id': 12,
                'type': 'stock',
                'cost_type': 'mrp',
                'sequence': 30,
                'product_category_ids': [67, 69],
                'employee_ids': []
            },
            {
                'name': 'Couverture et Bardage',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'uom_id': 9,
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 40,
                'product_category_ids': [88],
                'employee_ids': []
            },
            {
                'name': 'Planchers',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'uom_id': 9,
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 50,
                'product_category_ids': [68],
                'employee_ids': []
            },
            {
                'name': 'Boulonnerie et Accessoires',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'uom_id': 12,
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 60,
                'product_category_ids': [86, 74],
                'employee_ids': []
            },
            {
                'name': 'Tuyauterie',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'uom_id': 5,
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 70,
                'product_category_ids': [89],
                'employee_ids': []
            },
            {
                'name': 'Peinture',
                'category_id': self._get_or_create_category('DS2', 'Appro', 2),
                'uom_id': 12,
                'type': 'stock',
                'cost_type': 'invoice',
                'sequence': 80,
                'product_category_ids': [76],
                'employee_ids': []
            },
            
            # DS3: Fabrication
            {
                'name': 'MO Fab',
                'category_id': self._get_or_create_category('DS3', 'Fabrication', 3),
                'uom_id': 269960,
                'type': 'rate',
                'cost_type': 'analytic',
                'sequence': 100,
                'product_category_ids': [],
                'employee_ids': [3, 2, 5, 4]
            },
            {
                'name': 'MO Peinture',
                'category_id': self._get_or_create_category('DS3', 'Fabrication', 3),
                'uom_id': 269960,
                'type': 'rate',
                'cost_type': 'analytic',
                'sequence': 110,
                'product_category_ids': [],
                'employee_ids': [6]
            },
            
            # DS4: Montage
            {
                'name': 'MO Pose',
                'category_id': self._get_or_create_category('DS4', 'Montage', 4),
                'uom_id': 269960,
                'type': 'manual',
                'cost_type': 'analytic',
                'sequence': 120,
                'product_category_ids': [],
                'employee_ids': [7]
            },
            {
                'name': 'Transport',
                'category_id': self._get_or_create_category('DS4', 'Montage', 4),
                'uom_id': 1,
                'type': 'move',
                'cost_type': 'invoice',
                'sequence': 130,
                'product_category_ids': [90],
                'employee_ids': []
            },
            {
                'name': 'Manutention',
                'category_id': self._get_or_create_category('DS4', 'Montage', 4),
                'uom_id': 1,
                'type': 'move',
                'cost_type': 'invoice',
                'sequence': 140,
                'product_category_ids': [91],
                'employee_ids': []
            },
            
            # DS5: Préstations
            {
                'name': 'Bureau de contrôle',
                'category_id': self._get_or_create_category('DS5', 'Préstations', 5),
                'uom_id': 32694,
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 150,
                'product_category_ids': [77],
                'employee_ids': []
            },
            {
                'name': 'Galvanisation',
                'category_id': self._get_or_create_category('DS5', 'Préstations', 5),
                'uom_id': 12,
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 160,
                'product_category_ids': [92],
                'employee_ids': []
            },
            {
                'name': 'Autres Sous traitance',
                'category_id': self._get_or_create_category('DS5', 'Préstations', 5),
                'uom_id': 32694,
                'type': 'manual',
                'cost_type': 'invoice',
                'sequence': 170,
                'product_category_ids': [93],
                'employee_ids': []
            },
        ]
        
        Axis = self.env['project.financial.axis']
        AxisBudgetLine = self.env['project.financial.axis.budget.line']
        AxisLine = self.env['project.financial.axis.line']
        
        for axis_data in standard_axes:
            axis_vals = {
                'name': axis_data['name'],
                'project_financial_id': self.id,
                'category_id': axis_data['category_id'],
                'uom_id': axis_data['uom_id'],
                'type': axis_data['type'],
                'cost_type': axis_data['cost_type'],
                'sequence': axis_data['sequence'],
            }
            
            if axis_data.get('product_category_ids'):
                axis_vals['product_category_ids'] = [(6, 0, axis_data['product_category_ids'])]
            if axis_data.get('employee_ids'):
                axis_vals['employee_ids'] = [(6, 0, axis_data['employee_ids'])]
            
            axis = Axis.create(axis_vals)

            axis_id = axis.id
            # date = self.date_from or last_day
            
            AxisBudgetLine.create({
                'axis_id': axis_id,
                'date': last_day,
                'planned_budget': 0.0,
            })
            AxisBudgetLine.create({
                'axis_id': axis_id,
                'date': year_before,
                'planned_budget': 0.0,
            })
            AxisBudgetLine.create({
                'axis_id': axis_id,
                'date': year_after,
                'planned_budget': 0.0,
            })

            AxisLine.create({
                 'axis_id': axis_id,
                 'date': last_day,
                 'acquise_value': 0.0,
                 'actual_cost':0.0,
                 'is_default': True,
            })
            AxisLine.create({
                 'axis_id': axis_id,
                 'date': year_before,
                 'acquise_value': 0.0,
                 'actual_cost':0.0,
                 'is_default': True,
            })
            AxisLine.create({
                 'axis_id': axis_id,
                 'date': year_after,
                 'acquise_value': 0.0,
                 'actual_cost':0.0,
                 'is_default': True,
            })
        
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