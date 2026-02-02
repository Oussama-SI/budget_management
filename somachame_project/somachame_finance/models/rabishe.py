from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class axislines():
        
    # @api.model
    # def grid_update_cell(self, domain, measure_field_name, value):
    #     """
    #     Simplified version assuming monthly grids
    #     """
    #     axis_id = None
    #     date_month = None
        
    #     # Flatten and parse domain
    #     def flatten_domain(domain):
    #         """Convert nested domain to flat list of conditions"""
    #         conditions = []
    #         for item in domain:
    #             if isinstance(item, (list, tuple)) and len(item) == 3:
    #                 conditions.append(item)
    #             elif isinstance(item, (list, tuple)):
    #                 conditions.extend(flatten_domain(item))
    #         return conditions
        
    #     conditions = flatten_domain(domain)        
    #     # Extract values
    #     for field, operator, val in conditions:
    #         if field == 'axis_id' and operator == '=':
    #             axis_id = val
    #         elif field == 'date' and operator == '>=':
    #             # This is the month start (e.g., '2025-07-01')
    #             date_month = val  # We'll use this as the date
        
    #     if not axis_id or not date_month:
    #         raise UserError(f"Domaine invalide. axis_id={axis_id}, date_month={date_month}")
        
    #     # Convert value
    #     try:
    #         numeric_value = float(value) if value not in [None, False, ''] else 0.0
    #     except:
    #         numeric_value = 0.0
        
    #     # Search for record in this month
    #     # Calculate end of month for search
    #     from datetime import datetime
    #     date_obj = datetime.strptime(date_month, '%Y-%m-%d')
        
    #     # Get next month for search range
    #     if date_obj.month == 12:
    #         next_month = date_obj.replace(year=date_obj.year + 1, month=1, day=1)
    #     else:
    #         next_month = date_obj.replace(month=date_obj.month + 1, day=1)
        
    #     record = self.search([
    #         ('axis_id', '=', axis_id),
    #         ('date', '>=', date_month),
    #         ('date', '<', next_month.strftime('%Y-%m-%d'))
    #     ], limit=1)
        
    #     if record:
    #         record.write({measure_field_name: numeric_value})
    #         return record
    #     else:
    #         # Create with the first day of month
    #         vals = {
    #             'axis_id': axis_id,
    #             'date': date_month,
    #             measure_field_name: numeric_value,
    #         }
            
    #         # Initialize other fields
    #         other_fields = ['planned_budget', 'grid_cost', 'delay_performance_index']
    #         if measure_field_name in other_fields:
    #             other_fields.remove(measure_field_name)
            
    #         for field in other_fields:
    #             vals[field] = 0.0
            
    #         return self.create(vals)
    
    # @api.model
    # def grid_update_cell(self, domain, measure_field, value, column_field=None, column_value=None):
    #     """
    #     Implémentation REQUISE pour le widget grid d'Odoo 18
    #     """
    #     # Log pour débogage
    #     _logger.info(f"grid_update_cell called: {measure_field} = {value}")
    #     _logger.info(f"Domain: {domain}")
    #     _logger.info(f"Column field: {column_field}, value: {column_value}")
        
    #     try:
    #         # 1. Convertir la valeur
    #         if value in [None, False, '']:
    #             numeric_value = 0.0
    #         else:
    #             try:
    #                 numeric_value = float(value)
    #             except (ValueError, TypeError):
    #                 numeric_value = 0.0
            
    #         # 2. Construire le domaine complet
    #         full_domain = list(domain) if domain else []
            
    #         # Si column_field est fourni (cas normal du grid)
    #         if column_field and column_value:
    #             full_domain.append((column_field, '=', column_value))
            
    #         _logger.info(f"Full domain: {full_domain}")
            
    #         # 3. Chercher l'enregistrement existant
    #         record = self.search(full_domain, limit=1)
            
    #         if record:
    #             # Mettre à jour l'existant
    #             record.write({measure_field: numeric_value})
    #             result_record = record
    #         else:
    #             # Créer un nouveau
    #             vals = {measure_field: numeric_value}
                
    #             # Extraire les valeurs du domaine
    #             for cond in full_domain:
    #                 if isinstance(cond, (list, tuple)) and len(cond) == 3:
    #                     field, operator, val = cond
    #                     if operator == '=' and field in self._fields:
    #                         vals[field] = val
                
    #             # S'assurer d'avoir une date
    #             if 'date' not in vals:
    #                 vals['date'] = fields.Date.context_today(self)
                
    #             result_record = self.create(vals)
            
    #         # 4. Retourner le format attendu par le grid
    #         result_value = result_record[measure_field]
            
    #         # Pour les champs monétaires, formater
    #         if self._fields[measure_field].type == 'monetary':
    #             return {
    #                 'value': result_value,
    #                 'formatted_value': formatLang(
    #                     self.env, 
    #                     result_value, 
    #                     currency_obj=result_record.currency_id
    #                 )
    #             }
            
    #         return {'value': result_value}
            
    #     except Exception as e:
    #         _logger.error(f"Error in grid_update_cell: {str(e)}")
    #         # Retourner l'erreur au client
    #         return {
    #             'error': str(e),
    #             'value': value
    #         }

    # @api.model
    # def grid_update_cell(self, domain, measure_field, value, column_field=None, column_value=None):
    #     """
    #     DOIT retourner un dict avec 'value' comme clé principale
    #     """
    #     try:
    #         # Conversion de la valeur
    #         numeric_value = 0.0
    #         if value not in [None, False, '']:
    #             try:
    #                 numeric_value = float(value)
    #             except (ValueError, TypeError):
    #                 numeric_value = 0.0
            
    #         # Construire le domaine complet
    #         search_domain = list(domain) if domain else []
    #         if column_field and column_value:
    #             search_domain.append((column_field, '=', column_value))
            
    #         # Chercher l'enregistrement
    #         record = self.search(search_domain, limit=1)
            
    #         if record:
    #             # Mettre à jour
    #             record.write({measure_field: numeric_value})
    #         else:
    #             # Créer avec les valeurs du domaine
    #             vals = {measure_field: numeric_value}
                
    #             # Extraire axis_id et date du domaine
    #             for cond in search_domain:
    #                 if isinstance(cond, (list, tuple)) and len(cond) == 3:
    #                     field, op, val = cond
    #                     if op == '=' and field in self._fields:
    #                         vals[field] = val
                
    #             # S'assurer d'avoir les champs obligatoires
    #             if 'axis_id' not in vals:
    #                 # Essayer d'extraire du contexte
    #                 if self.env.context.get('default_axis_id'):
    #                     vals['axis_id'] = self.env.context.get('default_axis_id')
    #                 else:
    #                     raise UserError(_("Impossible de déterminer l'axe pour cette cellule"))
                
    #             if 'date' not in vals:
    #                 if column_field == 'date' and column_value:
    #                     vals['date'] = column_value
    #                 else:
    #                     vals['date'] = fields.Date.context_today(self)
                
    #             record = self.create(vals)
            
    #         # IMPORTANT: Retourner UNIQUEMENT un dict avec 'value'
    #         return {
    #             'value': record[measure_field]
    #         }
            
    #     except Exception as e:
    #         # En cas d'erreur, retourner aussi un dict
    #         return {
    #             'error': str(e),
    #             'value': value or 0.0
    #         }

    @api.model
    def adjust_grid(self, row_domain, column_field, column_value, cell_field, change):
        """
        Version simplifiée de adjust_grid
        """
        try:
            # 1. Construire le domaine de recherche
            domain = row_domain.copy() if row_domain else []
            
            if column_field and column_value:
                # Pour les dates, chercher l'enregistrement du mois
                if column_field == 'date':
                    from datetime import datetime
                    try:
                        date_val = datetime.strptime(column_value, '%Y-%m-%d').date()
                        # Premier jour du mois
                        month_start = date_val.replace(day=1)
                        # Premier jour du mois suivant
                        if month_start.month == 12:
                            next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
                        else:
                            next_month = month_start.replace(month=month_start.month + 1, day=1)
                        
                        domain.extend([
                            ('date', '>=', month_start),
                            ('date', '<', next_month)
                        ])
                    except:
                        domain.append((column_field, '=', column_value))
                else:
                    domain.append((column_field, '=', column_value))
            
            # 2. Chercher ou créer
            record = self.search(domain, limit=1)
            
            if record:
                # Mettre à jour
                current = record[cell_field] or 0
                new_value = current + change
                record.write({cell_field: new_value})
            else:
                # Créer nouveau
                vals = {cell_field: change}
                
                # Extraire axis_id
                axis_id = None
                for cond in row_domain:
                    if isinstance(cond, (list, tuple)) and len(cond) == 3:
                        field, op, val = cond
                        if field == 'axis_id' and op == '=':
                            axis_id = val
                            vals['axis_id'] = val
                            break
                
                if not axis_id:
                    axis_id = self.env.context.get('default_axis_id')
                    if axis_id:
                        vals['axis_id'] = axis_id
                
                # Date
                if column_field == 'date' and column_value:
                    vals['date'] = column_value
                else:
                    vals['date'] = fields.Date.context_today(self)
                
                record = self.create(vals)
            
            return {'value': record[cell_field]}
            
        except Exception as e:
            return {'error': str(e)} 
    
    @api.model
    def grid_update_cell(self, domain, measure_field_name, value):
        """
        Implémentation inspirée de timesheet_grid pour gérer les mises à jour mensuelles
        """
        if value == 0:  # rien à faire
            return {'value': 0}
        
        # 1. Analyser le domaine pour extraire axis_id et date
        axis_id = None
        date_value = None
        
        for subdomain in domain:
            if subdomain[0] == 'axis_id' and subdomain[1] == '=':
                axis_id = subdomain[2]
            elif subdomain[0] == 'date' and subdomain[1] == '=':
                date_value = subdomain[2]
            elif subdomain[0] == 'date' and subdomain[1] == '>=':
                # Pour les grids mensuels, on reçoit souvent '>=' avec le premier jour du mois
                date_value = subdomain[2]
        
        _logger.info(f"grid_update_cell: axis_id={axis_id}, date={date_value}, field={measure_field_name}, value={value}")
        
        # 2. Construire le domaine de recherche pour le MOIS complet
        search_domain = []
        if axis_id:
            search_domain.append(('axis_id', '=', axis_id))
        
        if date_value:
            # Convertir en objet date
            try:
                target_date = fields.Date.from_string(date_value)
                # Premier jour du mois
                month_start = target_date.replace(day=1)
                # Premier jour du mois suivant
                if month_start.month == 12:
                    next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
                else:
                    next_month = month_start.replace(month=month_start.month + 1, day=1)
                
                # Rechercher dans tout le mois
                search_domain.extend([
                    ('date', '>=', month_start),
                    ('date', '<', next_month)
                ])
            except Exception as e:
                _logger.warning(f"Erreur parsing date {date_value}: {e}")
                search_domain.append(('date', '=', date_value))
        
        _logger.info(f"Domaine de recherche: {search_domain}")
        
        # 3. Chercher les enregistrements existants pour ce mois
        existing_lines = self.search(search_domain)
        
        if len(existing_lines) > 1:
            # Plusieurs lignes existent pour ce mois - créer une nouvelle ligne
            return self._create_new_line_for_month(axis_id, date_value, measure_field_name, value)
        
        elif len(existing_lines) == 1:
            # Une seule ligne existe - la mettre à jour
            line = existing_lines[0]
            old_value = line[measure_field_name] or 0
            new_value = old_value + float(value)
            line.write({measure_field_name: new_value})
            return {'value': new_value}
        
        else:
            # Aucune ligne n'existe - créer une nouvelle ligne
            return self._create_new_line_for_month(axis_id, date_value, measure_field_name, value)
    
    def _create_new_line_for_month(self, axis_id, date_value, measure_field_name, value):
        """Crée une nouvelle ligne pour un mois"""
        vals = {
            measure_field_name: float(value),
        }
        
        if axis_id:
            vals['axis_id'] = axis_id
        
        if date_value:
            # Pour un grid mensuel, utiliser le premier jour du mois
            try:
                target_date = fields.Date.from_string(date_value)
                month_start = target_date.replace(day=1)
                vals['date'] = month_start
            except:
                vals['date'] = date_value
        else:
            vals['date'] = fields.Date.context_today(self)
        
        # Vérifier que l'axe existe
        if axis_id:
            axis = self.env['project.financial.axis'].browse(axis_id)
            if not axis.exists():
                raise UserError(_("L'axe spécifié n'existe pas"))
        
        # Créer la ligne
        new_line = self.create(vals)
        return {'value': new_line[measure_field_name]}

    @api.model
    def read_grid(self, row_fields, col_field, cell_field, domain=None, range=None, 
                  offset=0, limit=None, order=None):
        result = super().read_grid(row_fields, col_field, cell_field, domain, 
                                   range, offset, limit, order)
        
        # Récupérer les couleurs des axes
        axis_ids = []
        for row in result.get('rows', []):
            if 'axis_id' in row.get('values', {}):
                axis_data = row['values']['axis_id']
                if isinstance(axis_data, list) and len(axis_data) > 0:
                    axis_ids.append(axis_data[0])
        
        if axis_ids:
            axes = self.env['project.financial.axis'].browse(axis_ids)
            axis_color_map = {axis.id: axis.color or 0 for axis in axes}
            
            # Ajouter la couleur aux lignes
            for i, row in enumerate(result.get('rows', [])):
                axis_id = None
                if 'axis_id' in row.get('values', {}):
                    axis_data = row['values']['axis_id']
                    if isinstance(axis_data, list) and len(axis_data) > 0:
                        axis_id = axis_data[0]
                
                if axis_id and axis_id in axis_color_map:
                    row['color_index'] = axis_color_map[axis_id]
        
        return result


class Rabishe():

    """
    <!-- <button name="%(action_open_axes_list)d"
                                    type="action" 
                                    class="oe_stat_button"
                                    icon="fa-cubes"
                                    context="{'search_default_project_financial_id': active_id}">
                                <div class="o_stat_info">
                                    <span class="o_stat_text">Axes</span>
                                    <span class="o_stat_value">
                                        <field name="axis_count" widget="statinfo"/>
                                    </span>
                                </div>
                            </button> -->
    """
    def _update_axis_line_total(self, axis):
        """Met à jour le total d'un axe"""
        AxisLine = self.env['project.financial.axis.line']
        date = self._get_move_date_for_axis()
        update_vals = {}
        total = 0.0
        domain = self._get_axis_calculation_domain(axis)
        moves = self.env['stock.move'].search(domain)
        
        _logger.info(f"Calcul axe {axis.complete_name} - {len(moves)} mouvements trouvés")
        
        for move in moves:
            if move._matches_axis(axis):
                total += move.product_qty

        if self.picking_id:
            cost = self.product_qty * self.product_id.standard_price
            update_vals['actual_cost'] = cost
        else:
            update_vals['earned_value'] = total
        
        axis_line = AxisLine.search([('axis_id', '=', axis.id), ('date', '=', date)], limit=1)
        _logger.info(f"Total calculé: {total} pour axe {axis.complete_name} à date {date}") 
        if axis_line:
                axis_line.write(update_vals)
                _logger.info(f"Mise à jour ligne axe {axis.name}: {update_vals}")
        elif total > 0:
            AxisLine.create({
                'axis_id': axis.id,
                'date': date,
                **update_vals
            })
            _logger.info(f"Création ligne axe {axis.name}: {update_vals}")

            
        # if self.product_id and self.product_id.product_tmpl_id.categ_id:
        #     domain.append(('product_category_ids', 'parent_of', self.product_id.product_tmpl_id.categ_id.id))
        # else:
        #     domain.append(('product_category_ids', '=', False))
        #         if self.employee_id and self.employee_id.id != 1:
        #    domain.append(('employee_ids', 'in', [self.employee_id.id]))

    def mina(self, axis, date):
        analytic_lines = self.search([
                ('account_id', '=', self.account_id.id),
                ('employee_id', '=', self.employee_id.id)
                ('date', '=', date),
                ('amount', '<=', 0),
                ('product_id', '=', False),
            ])
        # Chercher TOUTES les lignes analytiques qui correspondent
        domain = [
            ('account_id', '=', self.account_id.id),  # Même compte analytique
            ('date', '=', date),                      # Même date
            ('amount', '<=', 0),                      # Uniquement les coûts
            ('product_id', '=', False),
        ]
        all_analytic_lines = self.search(domain)
        
        for analytic_line in all_analytic_lines:
            matching_axes = analytic_line.get_matching_axis_for_line()
            if axis in matching_axes:
                # total_earned_value += analytic_line.unit_amount
                break


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

    @api.constrains('product_category_ids', 'employee_ids', 'project_financial_id')
    def _unique_categories_per_project(self):
        for record in self.filtered(lambda r: r.employee_ids or r.product_category_ids):
            self.env.cr.execute("""
            WITH categ AS (
            SELECT DISTINCT axis.project_financial_id, pc.name
                        FROM product_category_project_financial_axis_rel rel
                        JOIN project_financial_axis axis ON axis.id = rel.project_financial_axis_id
                        JOIN product_category pc ON pc.id = rel.product_category_id
                        WHERE axis.project_financial_id = %s
                        AND pc.id IN %s),
            emp AS (	
            SELECT DISTINCT axis.project_financial_id, emp.name
                        FROM hr_employee_project_financial_axis_rel erel
                        JOIN project_financial_axis axis ON axis.id = erel.project_financial_axis_id
                        JOIN hr_employee emp ON emp.id = erel.hr_employee_id
                        WHERE axis.project_financial_id = %s
                        AND emp.id IN %s)
            SELECT c.name, e.name FROM categ c
            OUTER JOIN emp e ON e.project_financial_id = c.project_financial_id;
            """, (record.project_financial_id.id, tuple(record.product_category_ids.ids),
                  record.project_financial_id.id, tuple(record.employe_ids.ids)))
            
            duplicate_names = [row[0] for row in self.env.cr.fetchall()]
            
            if duplicate_names:
                names = ', '.join(duplicate_names)
                raise ValidationError(_(
                    "Source déjà utilisées dans ce projet : %s",
                    names
                ))