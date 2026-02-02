from datetime import datetime, date
import random
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProjectFinancialDataImporter(models.Model):
    _name = 'project.financial.data.importer'
    _description = 'Importateur des données financières'
    
    def import_financial_data(self, project_financial_id, year=2024):
        """
        Importe TOUTES les données financières : acquise_value et coûts réels
        """
        # 1. DONNÉES DES ACQUISE_VALUE (pourcentages d'avancement)
        acquise_data = [
            {
                'axis_name': "Études d'execution",
                'monthly_acquise': {'Jan': 0.40, 'Mar': 0.55}
            },
            {
                'axis_name': 'Méthodes et préparation',
                'monthly_acquise': {'Fev': 0.10, 'Mar': 0.10, 'Avr': 0.25, 'Mai': 0.25, 'Jui': 0.00}
            },
            {
                'axis_name': 'Toles et profilés',
                'monthly_acquise': {'Mar': 0.10, 'Jun': 0.33, 'Mai': 0.10, 'Jui': 0.20}
            },
            {
                'axis_name': 'Tole striee',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'goujon',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00}
            },
            {
                'axis_name': 'Boulonnerie et Accessoires',
                'monthly_acquise': {'Fev': 0.10, 'Mar': 0.30, 'Avr': 0.30, 'Mai': 0.25, 'Jui': 0.00}
            },
            {
                'axis_name': 'Couverture et Bardage',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.10, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Caillebotis',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Marche caillebotis',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Convoyeur cover',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00}
            },
            {
                'axis_name': 'Translucide',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00}
            },
            {
                'axis_name': 'Garde corps',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Autres…',
                'monthly_acquise': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00}
            },
            {
                'axis_name': 'MO Fab',
                'monthly_acquise': {'Fev': 0.10, 'Mar': 0.15, 'Avr': 0.20}
            },
            {
                'axis_name': 'MO Peinture',
                'monthly_acquise': {'Fev': 0.10, 'Mar': 0.15, 'Avr': 0.20}
            },
            {
                'axis_name': 'MO Pose',
                'monthly_acquise': {'Mar': 0.10, 'Mai': 0.15, 'Jui': 0.15}
            },
            {
                'axis_name': 'Transport et Manutention',
                'monthly_acquise': {'Mar': 0.10, 'Mai': 0.20, 'Jui': 0.20}
            },
            {
                'axis_name': 'Bureau de contrôle',
                'monthly_acquise': {'Mai': 0.50}
            },
        ]
        
        # 2. DONNÉES DES COÛTS RÉELS
        actual_cost_data = [
            {
                'axis_name': 'Méthodes et préparation',
                'cost_type': 'timesheet',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Toles et profilés',
                'cost_type': 'stock',
                'monthly_costs': {
                    'Fev': 5715814.95, 'Mar': 4348466.66, 'Avr': 860675.80,
                    'Mai': 179990.40, 'Jui': 321584.20, 'Juil': 5097.89
                }
            },
            {
                'axis_name': 'Tole striee',
                'cost_type': 'stock',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'goujon',
                'cost_type': 'stock',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Boulonnerie et Accessoires',
                'cost_type': 'invoice',
                'monthly_costs': {
                    'Fev': 146576.60, 'Mar': 111118.80, 'Avr': 9735.55,
                    'Mai': 25722.25, 'Jui': 0.00
                }
            },
            {
                'axis_name': 'Couverture et Bardage',
                'cost_type': 'stock',
                'monthly_costs': {
                    'Fev': 273734.00, 'Mar': 0.00, 'Avr': 270206.00,
                    'Mai': 3528.00, 'Jui': 0.00
                }
            },
            {
                'axis_name': 'Caillebotis',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Marche caillebotis',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Convoyeur cover',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Translucide',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Garde corps',
                'cost_type': 'stock',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Autres…',
                'cost_type': 'invoice',
                'monthly_costs': {
                    'Fev': 13400.00, 'Mar': 170.00, 'Avr': 0.00,
                    'Mai': 0.00, 'Jui': 13230.00
                }
            },
            {
                'axis_name': 'MO Fab',
                'cost_type': 'timesheet',
                'monthly_costs': {
                    'Fev': 159660.00, 'Mar': 22020.00, 'Avr': 85980.00,
                    'Mai': 51660.00, 'Jui': 0.00
                }
            },
            {
                'axis_name': 'MO Peinture',
                'cost_type': 'timesheet',
                'monthly_costs': {
                    'Fev': 25740.00, 'Mar': 0.00, 'Avr': 22020.00,
                    'Mai': 3720.00, 'Jui': 0.00
                }
            },
            {
                'axis_name': 'Autres',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'MO Pose',
                'cost_type': 'timesheet',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 32970.00, 'Mai': 0.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Transport et Manutention',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 27100.00, 'Mai': 24000.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Bureau de contrôle',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 4000.00, 'Jui': 0.00}
            },
            {
                'axis_name': 'Autres Sous traitance',
                'cost_type': 'invoice',
                'monthly_costs': {'Fev': 0.00, 'Mar': 0.00, 'Avr': 0.00, 'Mai': 0.00, 'Jui': 0.00}
            },
        ]
        
        # Mapping des mois
        month_mapping = {
            'Fev': 2, 'Mar': 3, 'Avr': 4, 'Mai': 5, 'Jui': 6,
            'Juil': 7, 'Août': 8, 'Sept': 9, 'Oct': 10, 'Nov': 11, 'Déc': 12
        }
        
        # Vérifier que le projet existe
        project = self.env['project.financial.progress'].browse(project_financial_id)
        if not project.exists():
            raise UserError(_("Projet financier non trouvé"))
        
        # Récupérer tous les axes du projet
        axes = self.env['project.financial.axis'].search([
            ('project_financial_id', '=', project_financial_id)
        ])
        
        if not axes:
            raise UserError(_("Aucun axe trouvé pour ce projet. Importez d'abord les axes budgétaires."))
        
        # Créer un mapping nom_axe → objet_axe
        axis_dict = {axis.name: axis for axis in axes}
        
        acquise_lines_created = []
        cost_lines_created = []
        
        # ==================== IMPORT DES ACQUISE_VALUE ====================
        print("=== Import des acquise_value ===")
        for data in acquise_data:
            axis_name = data['axis_name']
            axis = axis_dict.get(axis_name)
            
            if not axis:
                print(f"Axe non trouvé pour acquise_value: {axis_name}")
                continue
            
            # Pour chaque mois avec pourcentage
            for month_name, acquise_value in data['monthly_acquise'].items():
                if acquise_value > 0:  # Ne créer que si > 0
                    month_number = month_mapping.get(month_name)
                    if month_number:
                        # Générer une date aléatoire dans le mois (entre le 1er et le 28)
                        random_day = random.randint(1, 28)
                        line_date = date(year, month_number, random_day)
                        
                        # Vérifier si une ligne existe déjà pour ce mois
                        existing_line = self.env['project.financial.axis.line'].search([
                            ('axis_id', '=', axis.id),
                            ('date', '=', line_date)
                        ], limit=1)
                        
                        if existing_line:
                            # Mettre à jour la ligne existante
                            existing_line.write({
                                'acquise_value': acquise_value,
                                'progress': acquise_value * 100,
                                'description': f"Avancement {month_name} {year}: {acquise_value*100:.0f}%",
                            })
                            acquise_lines_created.append(existing_line.id)
                        else:
                            # Créer une nouvelle ligne
                            line_vals = {
                                'axis_id': axis.id,
                                'date': line_date,
                                'acquise_value': acquise_value,
                                'progress': acquise_value * 100,
                                'description': f"Avancement {month_name} {year}: {acquise_value*100:.0f}%",
                                'actual_cost': 0.0,  # Sera mis à jour après
                            }
                            
                            new_line = self.env['project.financial.axis.line'].create(line_vals)
                            acquise_lines_created.append(new_line.id)
        
        # ==================== IMPORT DES COÛTS RÉELS ====================
        print("=== Import des coûts réels ===")
        for data in actual_cost_data:
            axis_name = data['axis_name']
            axis = axis_dict.get(axis_name)
            
            if not axis:
                print(f"Axe non trouvé pour coût: {axis_name}")
                continue
            
            cost_type = data['cost_type']
            
            # Pour chaque mois avec coût
            for month_name, cost_amount in data['monthly_costs'].items():
                if cost_amount > 0:  # Ne créer que si > 0
                    month_number = month_mapping.get(month_name)
                    if month_number:
                        # Générer une date aléatoire dans le mois (différente de celle des acquise_value)
                        random_day = random.randint(1, 28)
                        # S'assurer que ce n'est pas le même jour que pour acquise_value
                        while True:
                            line_date = date(year, month_number, random_day)
                            # Vérifier si cette date existe déjà pour cet axe
                            existing_for_date = self.env['project.financial.axis.line'].search([
                                ('axis_id', '=', axis.id),
                                ('date', '=', line_date)
                            ], limit=1)
                            if not existing_for_date:
                                break
                            random_day = (random_day % 28) + 1
                        
                        # Vérifier si une ligne existe déjà pour ce mois
                        existing_line = self.env['project.financial.axis.line'].search([
                            ('axis_id', '=', axis.id),
                            ('date', '=', line_date)
                        ], limit=1)
                        
                        if existing_line:
                            # Mettre à jour le coût sur la ligne existante
                            existing_line.write({
                                'actual_cost': cost_amount,
                                'description': f"{existing_line.description or ''} | Coût {cost_type} {month_name}: {cost_amount:,.2f} DH"
                            })
                            cost_lines_created.append(existing_line.id)
                        else:
                            # Créer une nouvelle ligne pour le coût
                            line_vals = {
                                'axis_id': axis.id,
                                'date': line_date,
                                'actual_cost': cost_amount,
                                'acquise_value': 0.0,  # Pas d'avancement, seulement coût
                                'progress': 0.0,
                                'description': f"Coût {cost_type} {month_name} {year}: {cost_amount:,.2f} DH",
                            }
                            
                            new_line = self.env['project.financial.axis.line'].create(line_vals)
                            cost_lines_created.append(new_line.id)
        
        # ==================== RECALCUL AUTOMATIQUE ====================
        print("=== Recalcul des indicateurs ===")
        
        # Recalculer earned_value à partir de acquise_value
        if acquise_lines_created:
            lines_to_recompute = self.env['project.financial.axis.line'].browse(
                list(set(acquise_lines_created))  # Éviter les doublons
            )
            for line in lines_to_recompute:
                if line.acquise_value > 0 and line.axis_planned_quantity:
                    line.earned_value = line.acquise_value * line.axis_planned_quantity
        
        # Recalculer les indicateurs du projet
        project._compute_financial_metrics()
        
        # Mettre à jour les cumuls mensuels si existent
        if hasattr(self.env['project.financial.progress'], '_trigger_cumulative_recomputation'):
            project._trigger_cumulative_recomputation()
        
        return {
            'message': _(
                "Import terminé avec succès!\n"
                "• Lignes d'avancement créées/mises à jour: %(acquise_count)d\n"
                "• Lignes de coût créées/mises à jour: %(cost_count)d"
            ) % {
                'acquise_count': len(set(acquise_lines_created)),
                'cost_count': len(set(cost_lines_created))
            },
            'acquise_line_ids': list(set(acquise_lines_created)),
            'cost_line_ids': list(set(cost_lines_created)),
        }