import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from collections import defaultdict

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _is_valid_for_axis_sync(self):
        """Vérifie si le mouvement est valide pour synchronisation"""
        # Condition 1: Mouvements liés à un transfert
        picking_valid = (
            self.picking_id and
            self.picking_id._is_picking_valid_for_axis_sync() and
            self.product_qty > 0
        )
        
        # Condition 2: Mouvements liés à une production MRP (composants)
        production_component_valid = (
            self.raw_material_production_id and
            self.raw_material_production_id.state == 'done' and
            self.state == 'done' and
            self.raw_material_production_id.type_operation == 'debutage' and ####################################################
            self.product_qty > 0 and
            self.location_dest_id and
            self.location_dest_id.usage == 'production'
        )
        
        # Condition 3: Mouvements liés à une production MRP (produits finis)
        # production_finished_valid = (
        #     self.production_id and
        #     self.production_id.state == 'done' and
        #     self.state == 'done' and
        #     self.type_operation == 'debutage' and #####################################################
        #     self.product_qty > 0 and
        #     self.location_id and
        #     self.location_id.usage == 'production' and
        #     self.product_id == self.production_id.product_id
        # )
        
        # Condition 4: Mouvements de déconstruction (composants retournés)
        unbuild_component_valid = (
            self.unbuild_id and
            self.state == 'done' and
            self.product_qty > 0 and
            self.location_dest_id and
            self.location_dest_id.usage == 'internal'
        )
        
        # unbuild_product_valid = (
        #     self.consume_unbuild_id and
        #     self.state == 'done' and
        #     self.product_qty > 0 and
        #     self.location_id and
        #     self.location_id.usage == 'internal' and
        #     self.product_id == self.consume_unbuild_id.product_id
        # )
        _logger.info(f"en touve : {picking_valid or production_component_valid or unbuild_component_valid}")
        return (picking_valid or production_component_valid or 
                unbuild_component_valid # or production_finished_valid or
                # unbuild_product_valid
                )

    def _get_move_date_for_axis(self):
        """Retourne la date pour l'axe financier"""
        if self.picking_id:
            _logger.info(f"return picking date")
            return self.picking_id.scheduled_date.date()
        elif self.raw_material_production_id:
            _logger.info(f"return mrp date")
            return self.raw_material_production_id.date_finished.date()
        # elif self.production_id:
        #     return self.production_id.date_finished.date()
        elif self.unbuild_id:
            _logger.info(f"return unbuild date")
            return self.unbuild_id.create_date.date()
        # elif self.consume_unbuild_id:
        #     return self.consume_unbuild_id.create_date.date()
        elif self.date:
            return self.date.date()
        else:
            return fields.Date.today()

    # anused
    # def _get_project_from_production(self, production):
    #     """Récupère le projet lié à une production"""
    #     if production.origin:
    #         sale_order = self.env['sale.order'].search([
    #             ('name', '=', production.origin)
    #         ], limit=1)
    #         if sale_order and sale_order.project_id:
    #             return sale_order.project_id
        
    #     if production.picking_ids:
    #         for picking in production.picking_ids:
    #             if picking.project_id:
    #                 return picking.project_id
        
    #     if hasattr(production.product_id, 'default_project_id') and production.product_id.default_project_id:
    #         return production.product_id.default_project_id
        
    #     return None

    def _get_financial_axes(self, loc='dest'):
        """Récupère les axes financiers correspondants"""
        axes = self.env['project.financial.axis']
        
        # 1. Pour les transferts
        if self.picking_id and self.picking_id.project_id:
            location = self.picking_id.location_dest_id.id if loc == 'dest' else self.picking_id.location_id.id
            
            axes = self.env['project.financial.axis'].search([
                ('project_financial_id.project_id', '=', self.picking_id.project_id.id),
                ('location_dest_id', '=', location), 
                ('type', 'in', ['move', 'stock'])
            ])
            
            if axes:
                _logger.info(f"_get_financial_axes trouve : {axes} pour picking")
                return axes.filtered(lambda a: self._matches_axis(a))
        
        elif self.raw_material_production_id:
            # production = self.raw_material_production_id
            # project_id = self._get_project_from_production(production)
            # project_id = self.raw_material_production_id.project_id.id
            # if not project_id:
            #     _logger.warning(f"Aucun projet trouvé pour production {production.name}")
            #     return axes
            
            location_id = self.location_dest_id.id
            account_id = self.analytic_account_id.id
            
            axes = self.env['project.financial.axis'].search([
                ('project_financial_id.account_id', '=', account_id),
                # ('location_dest_id', '=', location_id),
                ('cost_type', '=', 'mrp')  # Sortie de stock
            ])
            
            if axes:
                _logger.info(f"_get_financial_axes trouve : {axes} pour mrp")
                return axes.filtered(lambda a: self._matches_axis(a))
        
        # elif self.production_id:
        #     production = self.production_id
        #     # project_id = self._get_project_from_production(production)
        #     project_id = self.production_id.project_id.id
            
        #     if not project_id:
        #         return axes
            
        #     # Emplacement source (production)
        #     location_id = self.location_id.id
            
        #     axes = self.env['project.financial.axis'].search([
        #         ('project_financial_id.project_id', '=', project_id.id),
        #         ('location_id', '=', location_id),
        #         # ('type', '=', 'move'),
        #         ('cost_type', '=', 'stock ')  # Entrée en stock
        #     ])
            
        #     if axes:
        #         return axes.filtered(lambda a: self._matches_axis(a))
        
        # elif self.unbuild_id:
        #     unbuild = self.unbuild_id
        #     mo = unbuild.mo_id.project_id.id
            
        #     if not mo:
        #         return axes
            
        #     # project_id = self._get_project_from_production(mo)
        #     project_id = self.mo_id.project_id
        #     if not project_id:
        #         return axes
            
        #     # Emplacement destination (stock)
        #     location_id = self.location_dest_id.id
            
        #     axes = self.env['project.financial.axis'].search([
        #         ('project_financial_id.project_id', '=', project_id.id),
        #         ('location_id', '=', location_id),
        #         ('type', '=', 'move'),
        #     ])
            
        #     if axes:
        #         return axes.filtered(lambda a: self._matches_axis(a))
        
        # # 5. Pour les déconstructions - produit déconstruit (sortie stock)
        # elif self.consume_unbuild_id:
        #     unbuild = self.consume_unbuild_id
        #     mo = unbuild.mo_id
            
        #     if not mo:
        #         return axes
            
        #     # project_id = self._get_project_from_production(mo)
        #     # project_id = mo.project_id.id
        #     # if not project_id:
        #     #     return axes
            
        #     # Emplacement source (stock)
        #     location_id = self.location_id.id
        #     account_id = self.analytic_account_id.id
            
        #     axes = self.env['project.financial.axis'].search([
        #         ('project_financial_id.account_id', '=', account_id),
        #         ('location_id', '=', location_id),
        #         ('cost_type', '=', 'mrp')  # Sortie de stock
        #     ])
            
        #     if axes:
        #         return axes.filtered(lambda a: self._matches_axis(a))
        
        return axes

    def _matches_axis(self, axis):
        """Vérifie si le mouvement correspond à un axe"""
        if not axis.product_category_ids:
            _logger.info(f"axe avec categorie vide")
            return False
        
        if not self.product_id.categ_id:
            _logger.info(f"produit a pas de categorie")
            return False
        
        product_categ = self.product_id.categ_id
        if product_categ in axis.product_category_ids:
            return True
        
        current = product_categ
        while current.parent_id:
            if current.parent_id in axis.product_category_ids:
                return True
            current = current.parent_id
        
        _logger.debug(f"Aucun match d'axe pour catégorie {product_categ.name}")
        return False

    def _update_axis_line_total(self, axis):
        """Met à jour le total d'un axe"""
        AxisLine = self.env['project.financial.axis.line']
        date = self._get_move_date_for_axis()
        total = 0.0
        domain = self._get_axis_calculation_domain(axis)
        axis_line = AxisLine.search([('axis_id', '=', axis.id), ('date', '=', date)], limit=1)
        moves = self.env['stock.move'].search(domain)
        
        _logger.info(f"Calcul axe {axis.complete_name} - {len(moves)} mouvements trouvés")
        
        for move in moves:
            if move._matches_axis(axis):
                total += move.product_qty

        _logger.info(f"Total calculé: {total} pour axe {axis.complete_name} à date {date}") 
        if axis_line:
                axis_line.write({'earned_value': total})
                _logger.info(f"Mise à jour ligne axe {axis.name} avec: {total}")
        elif total > 0:
            AxisLine.create({
                'axis_id': axis.id,
                'date': date,
                'earned_value':total,
            })
            _logger.info(f"Création ligne axe {axis.name}: {total}")

    def _update_axis_line_cost(self, axis):
        """Met à jour le total d'un axe"""
        AxisLine = self.env['project.financial.axis.line']
        date = self._get_move_date_for_axis()
        cost = 0.0
        axis_line = AxisLine.search([('axis_id', '=', axis.id),('date', '=', date)], limit=1)
        domain = self._get_axis_calculation_domain(axis)
        moves = self.env['stock.move'].search(domain)
        
        _logger.info(f"Calcul axe {axis.complete_name} - {len(moves)} mouvements trouvés")
        
        cost = self.product_qty * self.product_id.standard_price
        _logger.info(f"le coùt est : {cost}")
        if axis_line:
            old = axis_line.actual_cost
            axis_line.write({'actual_cost': old + cost})
            _logger.info(f"Mise à jour ligne axe {axis.name} avec: {old} + {cost}")
        elif cost > 0:
            AxisLine.create({
                'axis_id': axis.id,
                'date': date,
                'actual_cost': cost,
            })
            _logger.info(f"Création ligne axe {axis.name}: {cost}")

    # def _update_value(self, env, axis, field, value, date, create=False):
    #     if create and value > 0:
    #         Axis = env.create({
    #             'axis_id': axis.id,
    #             'date': date,
    #             field: value,
    #         })
    #         _logger.info(f"Création ligne axe {Axis.name}: {value}")
    #     elif axis:
    #         axis.write({field: value})
    #         _logger.info(f"Mise à jour ligne axe {axis.name}: {value}")

    def _get_axis_calculation_domain(self, axis):
        """Retourne le domaine pour calculer le total d'un axe"""
        domain = [
            ('state', '=', 'done'),
            ('product_qty', '>', 0),
        ]
        
        # Ajouter les conditions basées sur le type de mouvement
        if self.picking_id:
            domain.extend([
                ('picking_id.project_id', '=', axis.project_financial_id.project_id.id),
                ('picking_id.state', '=', 'done'),
                ('picking_id.location_dest_id', '=', self.picking_id.location_dest_id.id),
            ])
        elif self.raw_material_production_id:
            # Pour les composants de production
            domain.extend([
                ('raw_material_production_id', '!=', False),
                ('location_dest_id', '=', self.location_dest_id.id),
            ])
        # elif self.production_id:
        #     # Pour les produits finis
        #     domain.extend([
        #         ('production_id', '!=', False),
        #         ('location_id', '=', self.location_id.id),
        #     ])
        elif self.unbuild_id:
            # Pour les composants de déconstruction
            domain.extend([
                ('unbuild_id', '!=', False),
                ('location_dest_id', '=', self.location_dest_id.id),
            ])
        # elif self.consume_unbuild_id:
        #     # Pour les produits déconstruits
        #     domain.extend([
        #         ('consume_unbuild_id', '!=', False),
        #         ('location_id', '=', self.location_id.id),
        #     ])
        
        return domain

    def _cleanup_old_axis(self, axis, date, value, price):
        """Soustrait une valeur d'un axe existant"""
        new_value = -1
        AxisLine = self.env['project.financial.axis.line']
        
        axis_line = AxisLine.search([
            ('axis_id', '=', axis.id),
            ('date', '=', date),
        ], limit=1)
        
        if axis_line:
            if self.picking_id:
                new_value = axis_line.earned_value - abs(value)
                _logger.info(f"the new value for picking : {new_value} instead of {axis_line.earned_value}")
                field = 'earned_value'
            else:
                new_value = axis_line.actual_cost - (abs(value) * price)
                _logger.info(f"the new cost for mrp : {new_value} instead of {axis_line.actual_cost}")
                field = 'actual_cost'

            if new_value >= 0:
                axis_line.write({field: new_value})
                _logger.info(f"Nettoyage axe {axis.name}: {axis_line.earned_value} | {axis_line.actual_cost} DH → {new_value}")
            else:
                # Si la valeur devient négative, on met à 0
                axis_line.write({field: new_value})
                _logger.warning(f"Axe {axis.name}: valeur négative après nettoyage, mis à 0")
        else:
            _logger.info(f"Aucune ligne d'axe trouvée pour nettoyage: {axis.complete_name} à {date}")

    # ===== CRUD METHODS =====

    @api.model_create_multi
    def create(self, vals_list):
        """Création avec synchronisation"""
        moves = super().create(vals_list)
        for move in moves:
            if move.state == 'done' and move._is_valid_for_axis_sync():
                axes = move._get_financial_axes()
                for axis in axes:
                    try:
                        move._update_axis_line_total(axis) if move.picking_id else move._update_axis_line_cost(axis)
                    except Exception as e:
                        _logger.error(f"Erreur synchro création mouvement {move.id}: {str(e)}")
        return moves

    # def write(self, vals):
    #     """Écriture avec synchronisation"""
    #     # Sauvegarder les anciennes données avant modification
    #     old_data = {}
    #     fields_to_check = {'product_id', 'product_qty', 'state', 'picking_id', 
    #                       'raw_material_production_id', 'production_id',
    #                       'unbuild_id', 'consume_unbuild_id'}
        
    #     if any(field in vals for field in fields_to_check):
    #         for move in self:
    #             if move._is_valid_for_axis_sync() and move.state == 'done':
    #                 axes = move._get_financial_axes()
    #                 if axes:
    #                     old_data[move.id] = {
    #                         'axes': axes,
    #                         'date': move._get_move_date_for_axis(),
    #                         'product_qty': move.product_qty,
    #                     }
        
    #     result = super().write(vals)
        
    #     # Si changement important, resynchroniser
    #     if any(field in vals for field in fields_to_check):
    #         # Nettoyer anciens états
    #         for move_id, old_info in old_data.items():
    #             move = self.browse(move_id)
    #             if move.exists():
    #                 for axis in old_info['axes']:
    #                     move._cleanup_old_axis(axis, old_info['date'], old_info['product_qty'])
            
    #         # Mettre à jour nouveaux états
    #         for move in self:
    #             if move._is_valid_for_axis_sync() and move.state == 'done':
    #                 axes = move._get_financial_axes()
    #                 for axis in axes:
    #                     try:
    #                         move._update_axis_line_total(axis)
    #                     except Exception as e:
    #                         _logger.error(f"Erreur synchro écriture mouvement {move.id}: {str(e)}")
        
    #     return result

    def unlink(self):
        """Suppression avec nettoyage"""
        to_clean = []
        for move in self:
            if move._is_valid_for_axis_sync() and move.state == 'done':
                axes = move._get_financial_axes()
                if axes:
                    to_clean.append({
                        'axes': axes,
                        'date': move._get_move_date_for_axis(),
                        'product_qty': move.product_qty,
                        'price': move.product_id.standard_price,
                    })
        
        result = super().unlink()
        
        # Nettoyer après suppression
        for data in to_clean:
            for axis in data['axes']:
                self._cleanup_old_axis(axis, data['date'], data['product_qty'], data['price'])
        
        return result

    # ===== MÉTHODES UTILITAIRES =====

    def action_resync_all_axes(self):
        """Recalcule tous les axes pour les mouvements"""
        _logger.info("=== Début resynchronisation complète des axes ===")
        
        # Trouver tous les mouvements valides
        domain = [
            ('state', '=', 'done'),
            ('product_qty', '>', 0),
        ]
        
        # Différents types de mouvements
        movement_types = [
            ('picking_id', '!=', False),
            ('raw_material_production_id', '!=', False),
            ('production_id', '!=', False),
            ('unbuild_id', '!=', False),
            ('consume_unbuild_id', '!=', False),
        ]
        
        or_domains = []
        for field, operator, value in movement_types:
            or_domains.append([(field, operator, value)])
        
        if or_domains:
            domain.append('|' * (len(or_domains) - 1))
            for sub_domain in or_domains:
                domain.extend(sub_domain)
        
        moves = self.search(domain)
        _logger.info(f"{len(moves)} mouvements à resynchroniser")
        
        # Traiter par lots
        batch_size = 100
        for i in range(0, len(moves), batch_size):
            batch = moves[i:i + batch_size]
            for move in batch:
                if move._is_valid_for_axis_sync():
                    axes = move._get_financial_axes()
                    for axis in axes:
                        try:
                            move._update_axis_line_total(axis)
                        except Exception as e:
                            _logger.error(f"Erreur resynchro mouvement {move.id}: {str(e)}")
            
            _logger.info(f"Traité lot {i//batch_size + 1}/{(len(moves)+batch_size-1)//batch_size}")
        
        _logger.info("=== Fin resynchronisation ===")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Resynchronisation terminée'),
                'message': _('%s mouvements resynchronisés avec les axes') % len(moves),
                'type': 'success',
                'sticky': False,
            }
        }

    def returning_exception(self, type):
        """Gestion des exceptions"""
        error_message = _(
            'Une erreur est survenue lors de %(type)s du mouvement %(move_name)s\n'
            'avec les axes analytiques',
            type=type,
            move_name=self.display_name or self.id
        )
        
        _logger.error(error_message)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Erreur de synchronisation'),
                'message': error_message,
                'type': 'danger',
                'sticky': False,
            }
        }

    # ===== MÉTHODES DE DEBUG =====

    def debug_axis_info(self):
        """Méthode de debug pour afficher les infos d'axe"""
        info = []
        info.append(f"=== DEBUG Mouvement {self.id} ===")
        info.append(f"Produit: {self.product_id.display_name}")
        info.append(f"Quantité: {self.product_qty}")
        info.append(f"État: {self.state}")
        info.append(f"Date: {self._get_move_date_for_axis()}")
        
        if self.picking_id:
            info.append(f"Transfert: {self.picking_id.name}")
            info.append(f"Projet: {self.picking_id.project_id.name if self.picking_id.project_id else 'Aucun'}")
        elif self.raw_material_production_id:
            info.append(f"Production composant: {self.raw_material_production_id.name}")
        elif self.production_id:
            info.append(f"Production produit fini: {self.production_id.name}")
        elif self.unbuild_id:
            info.append(f"Déconstruction composant: {self.unbuild_id.name}")
        elif self.consume_unbuild_id:
            info.append(f"Déconstruction produit: {self.consume_unbuild_id.name}")
        
        info.append(f"Valide pour synchro: {self._is_valid_for_axis_sync()}")
        
        axes = self._get_financial_axes()
        if axes:
            info.append(f"Axes trouvés ({len(axes)}):")
            for axis in axes:
                info.append(f"  - {axis.complete_name} (type: {axis.cost_type})")
        else:
            info.append("Aucun axe trouvé")
        
        return "\n".join(info)


# class StockMove(models.Model):
#     _inherit = 'stock.move'

#     def _is_valid_for_axis_sync(self):
#         """Vérifie si le mouvement est valide pour synchronisation"""
#         return (
#             self.picking_id and
#             self.picking_id._is_valid_for_axis_sync() and
#             # self.state == 'done' and
#             # self.product_id and
#             # self.product_id.type == 'product' and
#             self.product_qty > 0
#         )

#     def _get_move_date_for_axis(self):
#         return self.picking_id.scheduled_date.date()

#     def _matches_axis(self, axis):
#         """Vérifie si le mouvement correspond à un axe"""
#         if not axis.product_category_ids:
#             return False
        
#         if not self.product_id or not self.product_id.categ_id:
#             return False
        
#         product_categ = self.product_id.categ_id
#         if product_categ in axis.product_category_ids:
#             return True
        
#         # Vérifier les catégories parentes
#         current = product_categ
#         while current.parent_id:
#             if current.parent_id in axis.product_category_ids:
#                 return True
#             current = current.parent_id
#         _logger.info(f"No matching axes : False")
#         return False

#     def _get_financial_axes(self, loc='dest'):
#         """Récupère les axes financiers correspondants"""

#         location = self.picking_id.location_dest_id.id if loc == 'dest' else self.picking_id.location_id.id
        
#         axes = self.env['project.financial.axis'].search([
#             ('project_financial_id.project_id', '=', self.picking_id.project_id.id),
#             ('location_id', '=', location), 
#             ('type', '=', 'move')
#         ])
        
#         if axes:
#             return axes.filtered(lambda a: self._matches_axis(a))
#         return self.env['project.financial.axis']

#     # def _calculate_move_value(self):
#     #     """Calcule la valeur du mouvement"""
#     #     # Utiliser le prix standard ou un prix spécifique
#     #     return self.product_qty_done * self.product_id.standard_price

#     def _update_axis_line_total(self, axis):
#         """Met à jour le total d'un axe"""
#         AxisLine = self.env['project.financial.axis.line']
#         date = self._get_move_date_for_axis()

#         total = 0.0
#         moves = self.env['stock.move'].search([
#             ('picking_id.project_id', '=', axis.project_financial_id.project_id.id),
#             ('picking_id.state', '=', 'done'),
#             ('picking_id.location_dest_id', '=', self.picking_id.location_dest_id.id),
#             ('picking_id.scheduled_date', '=', self.picking_id.scheduled_date),
#             ('product_id', '!=', False),
#             ('product_qty', '>', 0),
#         ])
#         _logger.info(f"------------- THe move are : {moves}")
#         for move in moves:
#             if move._matches_axis(axis):
#                 total += move.product_qty
        
#         axis_line = AxisLine.search([
#             ('axis_id', '=', axis.id),
#             ('date', '=', date)
#         ], limit=1)
#         _logger.info(f"-------------- The Total's : {total}")
#         if axis_line:
#             axis_line.write({'earned_value': total})
#             _logger.info(f"---------- Mise à jour de l'axe {axis.name} avec coût : {total}")
#         elif not axis_line and total > 0:
#             AxisLine.create({
#                 'axis_id': axis.id,
#                 'date': date,
#                 'earned_value': total,
#             })
#             _logger.info(f"--------- Création ligne axe pour : {axis.name} avec coût : {total}")

#     def _cleanup_old_axis(self, axis, date, value):
#         """Soustrait une valeur d'un axe existant"""
#         AxisLine = self.env['project.financial.axis.line']
        
#         axis_line = AxisLine.search([
#             ('axis_id', '=', axis.id),
#             ('date', '=', date),
#         ], limit=1)
        
#         if axis_line and axis_line.earned_value >= abs(value):
#             remain = axis_line.earned_value - abs(value)
#             axis_line.write({'earned_value': remain})
#             _logger.info(f"Nettoyage axe : {axis.name} de {axis_line.actual_cost + abs(value)} à {remain}")

#         _logger.info(f"there is no value for : {axis.complete_name if axis_line else None}")

#     # ===== CRUD METHODS =====

#     @api.model_create_multi
#     def create(self, vals_list):
#         """Création avec synchronisation"""
#         moves = super().create(vals_list)
#         for move in moves:
#             if move.picking_id.state == 'done' and move._is_valid_for_axis_sync():
#                 for axis in move._get_financial_axes():
#                     move._update_axis_line_total(axis)
#         return moves

#     # def write(self, vals):
#     #     """Écriture avec synchronisation"""
#     #     old_data = {}
        
#     #     # Sauvegarder les anciennes données avant modification
#     #     for move in self:
#     #         if move._is_valid_for_axis_sync() and move.state == 'done':
#     #             axes = move._get_financial_axes()
#     #             if axes:
#     #                 old_data[move.id] = {
#     #                     'axes': axes,
#     #                     'date': move.picking_id.scheduled_date,
#     #                     'value': move._calculate_move_value(),
#     #                 }
#     #                 _logger.info(f"Données anciennes sauvegardées : {axes}")
        
#     #     result = super().write(vals)
        
#     #     # Traiter les modifications
#     #     for move in self:
#     #         old_info = old_data.get(move.id)
            
#     #         # Nettoyer les anciennes valeurs si nécessaire
#     #         if old_info:
#     #             for axis in old_info['axes']:
#     #                 move._cleanup_old_axis(axis, old_info['date'], old_info['value'])
#     #                 _logger.info(f"Nettoyage axe avec valeurs : {old_info}")
            
#     #         # Mettre à jour avec nouvelles valeurs si valide
#     #         if move._is_valid_for_axis_sync() and move.state == 'done':
#     #             for axis in move._get_financial_axes():
#     #                 move._update_axis_line_total(axis)
        
#     #     return result

#     def unlink(self):
#         """Suppression avec nettoyage"""
#         to_clean = []
#         for move in self:
#             if move._is_valid_for_axis_sync() and move.state == 'done':
#                 axes = move._get_financial_axes()
#                 if axes:
#                     to_clean.append({
#                         'axes': axes,
#                         'date': move._get_move_date_for_axis(),
#                         'value': move.product_qtyh,
#                     })
        
#         result = super().unlink()
        
#         # Nettoyer après suppression
#         for data in to_clean:
#             for axis in data['axes']:
#                 self._cleanup_old_axis(axis, data['date'], data['value'])
        
#         return result
    
#     def returning_exception(self, type):
#         """Gestion des exceptions"""
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Transfert Chantier : Erreur de synchronisation'),
#                 'message': _(
#                     f'Une erreur est survenue lors de {type} du transfert {self.picking_id.name}\n'
#                     f'avec les axes analytique'
#                 ),
#                 'type': 'danger',
#                 'sticky': False,
#             }
#         }

#     # Méthode utilitaire pour forcer la resynchronisation
#     def action_resync_axis(self):
#         """Force la resynchronisation avec les axes"""
#         for move in self:
#             if move._is_valid_for_axis_sync():
#                 for axis in move._get_financial_axes():
#                     move._update_axis_line_total(axis)
        
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Resynchronisation effectuée'),
#                 'message': _('La synchronisation avec les axes a été recalculée'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }

# class StockMoveLine(models.Model):
    # _inherit = 'stock.move.line'
 
    # def _is_valid_for_stock_axis(self):        
    #     return {
    #         self.move_id or self.move_id.state != 'done' and
    #         self.picking_code != 'incoming' and
    #         self.move_id.project_id.account_id
    #     }
    
    # def _get_analytic_account(self):
    #     """Retourne le compte analytique associé"""
    #     return self.move_id.project_id.account_id or False
    
    # def _get_stock_axes(self, analytic_account):
    #     """Retourne les axes de type 'stock' pour un compte analytique"""
    #     if not analytic_account:
    #         return self.env['project.financial.axis']
        
    #     return self.env['project.financial.axis'].search([
    #         ('project_financial_id.account_id', '=', analytic_account.id),
    #         ('cost_type', '=', 'stock')
    #     ])
    
    # def _matches_axis_criteria(self, axis):
    #     """Vérifie si cette ligne correspond aux critères d'un axe"""
    #     if axis.product_category_ids:
    #         return False
        
    #     if not self.product_id or not self.product_id.categ_id:
    #         return False
        
    #     product_categ = self.product_id.categ_id
        
    #     if product_categ in axis.product_category_ids:
    #         return True
        
    #     current = product_categ
    #     while current.parent_id:
    #         if current.parent_id in axis.product_category_ids:
    #             return True
    #         current = current.parent_id
        
    #     return False
    
    # def _get_stock_date(self):
    #     """Retourne la date à utiliser pour les axes"""
    #     return self.move_id.date or self.move_id.scheduled_date or self.date
    
    # def _get_valuation_price(self):
    #     if self.product_id.standard_price:
    #         return self.product_id.standard_price
    #     elif self.product_id.product_tmpl_id.standard_price:
    #         return self.product_id.product_tmpl_id.standard_price
    #     else:
    #         return 0.0
    
    # def _calculate_earned_value(self):
    #     """Calcule la valeur gagnée pour cette ligne"""
    #     return self.product_qty
    
    # # ===========================================================================
    # # MÉTHODE PRINCIPALE DE SYNCHRONISATION
    # # ===========================================================================
    
    # def _sync_with_stock_axes(self):
    #     """
    #     Synchronise cette ligne avec les axes de type 'stock'
    #     Met à jour le earned_value des axes
    #     """
    #     if not self._is_valid_for_stock_axis():
    #         return False
        
    #     analytic_account = self._get_analytic_account()
    #     axes = self._get_stock_axes(analytic_account)
        
    #     if not axes:
    #         return False
        
    #     stock_date = self._get_stock_date()
    #     earned_value = self.quntity
        
    #     for axis in axes:
    #         if self._matches_axis_criteria(axis):
    #             self._update_axis_earned_value(axis, stock_date, earned_value)
        
    #     return True
    
    # def _update_axis_earned_value(self, axis, date, additional_value=0.0):
    #     """
    #     Met à jour le earned_value d'un axe
    #     Si additional_value = 0, recalcule depuis zéro
    #     """
    #     AxisLine = self.env['project.financial.axis.line']
        
    #     # Chercher la ligne existante
    #     axis_line = AxisLine.search([
    #         ('axis_id', '=', axis.id),
    #         ('date', '=', date)
    #     ], limit=1)
        
    #     if additional_value > 0:
    #         # Ajout simple (pour création)
    #         if axis_line:
    #             new = axis_line.earned_value + additional_value
    #             axis_line.write({'earned_value': new})
    #         else:
    #             AxisLine.create({
    #                 'axis_id': axis.id,
    #                 'date': date,
    #                 'earned_value': additional_value,
    #             })
    #     else:
    #         # Recalcul complet (pour modification/suppression)
    #         total_value = self._compute_total_earned_value(axis, date)
            
    #         if axis_line:
    #             axis_line.earned_value = total_value
    #             if total_value == 0:
    #                 axis_line.unlink()
    #         elif total_value > 0:
    #             AxisLine.create({
    #                 'axis_id': axis.id,
    #                 'date': date,
    #                 'earned_value': total_value,
    #             })
    
    # def _compute_total_earned_value(self, axis, date):
    #     """
    #     Calcule le earned_value total pour un axe à une date
    #     """
    #     total = 0.0
        
    #     lines = self.search([
    #         ('move_id.state', '=', 'done'),
    #         ('picking_code', 'in', ['outgoing', 'internal', 'mrp_operation']),
    #     ])
        
    #     for line in lines:
    #         analytic_account = line._get_analytic_account()
    #         if not analytic_account or analytic_account.id != axis.project_financial_id.account_id.id:
    #             continue
            
    #         line_date = line._get_stock_date()
    #         if line_date != date:
    #             continue
            
    #         if line._matches_axis_criteria(axis):
    #             total += line.product_qty
        
    #     return total
    
    # # ===========================================================================
    # # SURCHARGES DES MÉTHODES STANDARD
    # # ===========================================================================
    
    # @api.model_create_multi
    # def create(self, vals_list):
    #     """
    #     Création avec synchronisation
    #     """
    #     lines = super().create(vals_list)
        
    #     # Synchroniser uniquement les lignes de mouvements terminés
    #     for line in lines:
    #         if line.move_id and line.move_id.state == 'done':
    #             try:
    #                 line._sync_with_stock_axes()
    #             except Exception:
    #                 self.returning_exception("améleoration")
        
    #     return lines
    
    # def write(self, vals):
    #     """
    #     Écriture avec synchronisation
    #     """
    #     # Vérifier si des champs importants sont modifiés
    #     important_fields = {
    #         'product_qty', 'product_id', 'move_id', 'state',
    #         'analytic_account_id', 'picking_id'
    #     }
        
    #     # Stocker les anciens états pour le nettoyage
    #     old_data = {}
    #     if any(field in vals for field in important_fields):
    #         for line in self:
    #             if line.move_id and line.move_id.state == 'done':
    #                 analytic_account = line._get_analytic_account()
    #                 if analytic_account:
    #                     old_data[line.id] = {
    #                         'date': line._get_stock_date(),
    #                         'account_id': analytic_account.id,
    #                         'product_id': line.product_id.id,
    #                     }
        
    #     result = super().write(vals)
        
    #     # Si changement important, resynchroniser
    #     if any(field in vals for field in important_fields):
    #         # Traiter les lignes terminées
    #         done_lines = self.filtered(lambda l: l.move_id and l.move_id.state == 'done')
            
    #         for line in done_lines:
    #             try:
    #                 # Nettoyer ancien état si nécessaire
    #                 old_info = old_data.get(line.id)
    #                 if old_info:
    #                     old_date = old_info['date']
    #                     old_account_id = old_info['account_id']
    #                     old_product_id = old_info['product_id']
                        
    #                     new_date = line._get_stock_date()
    #                     new_account = line._get_analytic_account()
    #                     new_product_id = line.product_id.id
                        
    #                     # Si changement de date, compte ou produit, nettoyer ancien
    #                     if (old_date != new_date or 
    #                         old_account_id != (new_account.id if new_account else None) or
    #                         old_product_id != new_product_id):
                            
    #                         # Recalculer ancien axe
    #                         self._recalculate_axis_for_old_state(old_account_id, old_date, old_product_id)
                    
    #                 # Synchroniser nouvel état
    #                 line._sync_with_stock_axes()
                    
    #             except Exception:
    #                 self.returning_exception("modification")
        
    #     return result
    
    # def unlink(self):
    #     """
    #     Suppression avec nettoyage
    #     """
    #     # Identifier les combinaisons (axe, date) affectées
    #     axes_to_recalculate = defaultdict(set)
        
    #     for line in self:
    #         if line.move_id and line.move_id.state == 'done':
    #             analytic_account = line._get_analytic_account()
    #             if not analytic_account:
    #                 continue
                
    #             axes = self._get_stock_axes(analytic_account)
    #             stock_date = line._get_stock_date()
                
    #             for axis in axes:
    #                 if line._matches_axis_criteria(axis):
    #                     key = (axis.id, stock_date)
    #                     axes_to_recalculate[key] = {
    #                         'axis_id': axis.id,
    #                         'date': stock_date,
    #                         'account_id': analytic_account.id,
    #                     }
        
    #     result = super().unlink()
        
    #     for data in axes_to_recalculate.values():
    #         try:
    #             axis = self.env['project.financial.axis'].browse(data['axis_id'], data['date'])
    #             if axis.exists():
    #                 # Recalculer depuis zéro
    #                 self._update_axis_earned_value(axis, data['date'], 0.0)
    #         except Exception:
    #             self.returning_exception( "démination")
        
    #     return result
    
    # # ===========================================================================
    # # MÉTHODES AUXILIAIRES
    # # ===========================================================================
    
    # def _recalculate_axis_for_old_state(self, account_id, date, product_id):
    #     """
    #     Recalcule les axes pour un ancien état
    #     """
    #     axes = self.env['project.financial.axis'].search([
    #         ('project_financial_id.account_id', '=', account_id),
    #         ('cost_type', '=', 'stock')
    #     ])
        
    #     for axis in axes:
    #         # Vérifier si le produit correspondait à cet axe
    #         product = self.env['product.product'].browse(product_id)
    #         if product and product.categ_id:
    #             product_categ = product.categ_id
    #             match = False
    #             for axis_categ in axis.product_category_ids:
    #                 if (product_categ == axis_categ or 
    #                     product_categ.parent_of(axis_categ) or 
    #                     axis_categ.parent_of(product_categ)):
    #                     match = True
    #                     break
                
    #             if match:
    #                 self._update_axis_earned_value(axis, date, 0.0)
    
    # # ===========================================================================
    # # ACTION MANUELLE POUR RECALCUL COMPLET
    # # ===========================================================================
    
    # def action_recompute_all_stock_values(self):
    #     """
    #     Recalcule tous les earned_value pour les axes stock
    #     """
    #     # Nettoyer les earned_value existants
    #     axis_lines = self.env['project.financial.axis.line'].search([
    #         ('axis_id.cost_type', '=', 'stock')
    #     ])
    #     axis_lines.earned_value = 0.0
        
    #     # Trouver toutes les lignes de mouvements terminés
    #     done_lines = self.search([
    #         ('move_id.state', '=', 'done'),
    #         ('picking_code', 'in', ['outgoing', 'internal', 'mrp_operation']),
    #     ])
        
    #     # Traiter par lots pour optimisation
    #     batch_size = 500
    #     for i in range(0, len(done_lines), batch_size):
    #         batch = done_lines[i:i + batch_size]
            
    #         # Grouper par compte analytique et date
    #         updates_by_account_date = defaultdict(lambda: defaultdict(list))
            
    #         for line in batch:
    #             analytic_account = line._get_analytic_account()
    #             if not analytic_account:
    #                 continue
                
    #             date = line._get_stock_date()
    #             key = (analytic_account.id, date)
    #             updates_by_account_date[key]['lines'].append(line.id)
    #             updates_by_account_date[key]['account_id'] = analytic_account.id
    #             updates_by_account_date[key]['date'] = date
            
    #         # Traiter chaque groupe
    #         for (account_id, date), data in updates_by_account_date.items():
    #             lines = self.browse(data['lines'])
    #             axes = self._get_stock_axes(self.env['account.analytic.account'].browse(account_id))
                
    #             for axis in axes:
    #                 # Calculer le total pour cet axe
    #                 total = 0.0
    #                 for line in lines:
    #                     if line._matches_axis_criteria(axis):
    #                         total += line.product_qty
                    
    #                 # Mettre à jour l'axe
    #                 if total > 0:
    #                     self._update_axis_earned_value(axis, date, total)
        
    #     # Supprimer les lignes vides
    #     empty_lines = self.env['project.financial.axis.line'].search([
    #         ('axis_id.cost_type', '=', 'stock'),
    #         ('earned_value', '=', 0),
    #     ])
    #     empty_lines.unlink()
        
    #     return True
    
    # def returning_exception(self, type):
    #     for line in self:
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': (f'LF : Erreur de synchronisation : {line.name}'),
    #                 'message': (
    #                 f'Une erreur est survenue lors de la {type} des ligne de ce Axe'
    #                 ),
    #                 'type': 'danger',
    #                 'sticky': False,
    #             }
    #         }