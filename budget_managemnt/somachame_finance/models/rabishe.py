from odoo import models, api

class Rabishe():

    def _get_matching_axis_for_line(self):
        """
        Trouve l'axe financier correspondant à cette ligne analytique
        Uniquement pour les lignes de COÛT (amount <= 0)
        """
        self.ensure_one()
        
        if not self.account_id:
            return self.env['project.financial.axis']
        
        # Chercher les axes liés à ce compte analytique
        axes = self.env['project.financial.axis'].search([
            ('project_financial_id.analytic_account_id', '=', self.account_id.id)
        ])
        
        if not axes:
            return self.env['project.financial.axis']
        
        matching_axes = self.env['project.financial.axis']
        
        for axis in axes:
            # Vérifier si cette ligne correspond aux critères de l'axe
            
            # 1. Vérifier les catégories de produits (avec hiérarchie)
            if axis.product_category_ids:
                if not self.product_id:
                    continue
                
                # Récupérer toutes les catégories parentes du produit
                product_categories = self._get_all_parent_categories(self.product_id.product_tmpl_id.categ_id)
                
                # Vérifier si une catégorie correspond
                category_match = False
                for axis_category in axis.product_category_ids:
                    if axis_category in product_categories:
                        category_match = True
                        break
                
                if not category_match:
                    continue
            
            # 2. Vérifier les départements (avec hiérarchie si nécessaire)
            if axis.employee_department_ids and self.employee_id:
                if not self.employee_id.department_id:
                    continue
                
                # Pour vérifier la hiérarchie des départements si nécessaire:
                # (À adapter si vous avez une hiérarchie)
                if self.employee_id.department_id not in axis.employee_department_ids:
                    continue
            
            # Si on arrive ici, l'axe correspond
            matching_axes += axis
        
        # Normalement, on devrait avoir au plus un axe correspondant
        # Si plusieurs, prendre le premier
        return matching_axes


    def _update_axis_line_for_date(self, axis, date):
        """
        Met à jour ou crée la ligne d'axe pour une date donnée
        """
        AxisLine = self.env['project.financial.axis.line']
        
        # Chercher la ligne existante pour cette date
        domain = [
            ('axis_id', '=', axis.id),
            ('date', '=', date)
        ]
        
        axis_line = AxisLine.search(domain, limit=1)
        
        if not axis_line:
            # Créer une nouvelle ligne
            axis_line = AxisLine.create({
                'axis_id': axis.id,
                'date': date,
                'progress': 0.0,
                'actual_cost': 0.0,
            })

        linked_analytic_lines = self.search([
            ('account_id', '=', self.account_id.id),
            ('date', '=', date),
            ('amount', '<=', 0),  # Uniquement les coûts
            ('id', '!=', self.id)  # Exclure la ligne courante si en cours de création
        ])
        
        # Ajouter les critères de matching de l'axe
        filtered_lines = self.env['account.analytic.line']
        for line in linked_analytic_lines:
            matching_axes = line._get_matching_axis_for_line()
            if axis in matching_axes:
                filtered_lines += line
        
        # Calculer le total
        total_earned_value = sum(filtered_lines.mapped('unit_amount'))
        
        # Mettre à jour la ligne d'axe
        axis_line.write({
            'earned_value': total_earned_value,
        })
        
        return axis_line
    
    @api.depends('product_category_ids', 'employee_department_ids')
    def get_analytic_domain(self, analytic):
        domain = [('account_id', '=', analytic.id),
                  ('amount', '<', 0)]
        if self.product_category_ids:
            domain.append(('product_id.categ_id', 'in', self.product_category_ids.ids))
        if self.employee_department_ids:
            domain.append(('employee_id.department_id', 'in', self.employee_department_ids.ids))

        return domain
