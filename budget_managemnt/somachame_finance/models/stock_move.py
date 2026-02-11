import logging
from odoo import models, api, fields, _
from odoo.exceptions import UserError
from collections import defaultdict

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _sync_production_axes(self):
        """Synchro des mouvements de production"""
        # 1. Synchro des composants (mouvements entrants)
        for move in self.move_raw_ids:
            if move._is_valid_for_axis_sync():
                axes = move._get_financial_axes()
                for axis in axes:
                    try:
                        move._update_axis_line_cost(axis)
                    except Exception as e:
                        _logger.error(f"Erreur synchro composant {move.id}: {str(e)}")
        
        # 2. Synchro du produit fini (mouvement sortant) pour taux d'avancement
        for move in self.move_finished_ids:
            if move._is_valid_for_axis_sync():
                axes = move._get_financial_axes()
                for axis in axes:
                    try:
                        if axis.type == 'rate':
                            move._update_axis_line_for_rate(axis, self)
                        else:
                            move._update_axis_line_cost(axis)
                    except Exception as e:
                        _logger.error(f"Erreur synchro produit fini {move.id}: {str(e)}")
    
    def _get_product_cost_for_axis(self):
        """
        Version simplifiée - utilise directement price_unit d'Odoo
        """
        if not self.product_id or self.product_qty <= 0:
            return 0.0
        
        # price_unit est déjà calculé par Odoo selon la méthode de coût
        cost_per_unit = abs(self.price_unit) if self.price_unit else 0.0
        
        # Sécurité si price_unit = 0
        if cost_per_unit == 0:
            cost_per_unit = self.product_id.standard_price
        
        return self.product_qty * cost_per_unit

    def _calculate_earned_value_for_axis(self, axis):
        """
        Calcule la valeur acquise selon l'unité de l'axe
        """
        if not self.product_id or self.product_qty <= 0:
            return 0.0
        
        # Récupérer l'UoM de l'axe
        axis_uom = axis.uom_id
        if not axis_uom:
            return self.product_qty
        
        UOM_UNIT = 1      # Unité
        UOM_KG = 12       # Kilogramme
        UOM_M2 = 9        # Mètre carré
        UOM_M = 5      # Mètre
        UOM_CM = 4        # Centimètre
        
        axis_uom_id = axis_uom.id
        
        if axis_uom_id == UOM_UNIT:
            return self.product_qty
        
        elif axis_uom_id == UOM_KG:
            if self.product_id.weight:
                return self.product_qty * self.product_id.weight
            else:
                raise UserError(_(
                    "Produit %s n'a pas de poids défini pour l'axe %s (kg)",
                    self.product_id.name, axis.name
                ))
        
        elif axis_uom_id in [UOM_M, UOM_CM]:
            # En mètres ou cm → utiliser la longueur
            if hasattr(self.product_id, 'product_length') and self.product_id.product_length:
                length = self.product_id.product_length
                
                if axis_uom_id == UOM_M:
                    return self.product_qty * length
                else:  # CM
                    return self.product_qty * (length * 100)
            else:
                raise UserError(_(
                    "Produit %s n'a pas de longueur définie pour l'axe %s",
                    self.product_id.name, axis.name
                ))
        
        elif axis_uom_id == UOM_M2:
            # En m² → utiliser largeur × longueur
            if hasattr(self.product_id, 'product_length') and self.product_id.volume:
                # hasattr(self.product_id, 'product_width') and self.product_id.product_width):
                
                # area = self.product_id.product_length * self.product_id.product_width
                return self.product_qty * self.product_id.volume
            else:
                raise UserError(_(
                    "Produit %s n'a pas de dimensions complètes pour l'axe %s (m²)",
                    self.product_id.name, axis.name
                ))
        
        else:
            # Autre unité non gérée
            raise UserError(_(
                "Unité %s non gérée pour l'axe %s",
                axis_uom.name, axis.name
            ))


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
            # self.raw_material_production_id.type_operation == 'debitage' and ####################################################
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
            if self.raw_material_production_id.type_operation == 'debitage':
                account_id = self.analytic_account_id.id
                axes = self.env['project.financial.axis'].search([
                    ('project_financial_id.account_id', '=', account_id),
                    ('cost_type', '=', 'mrp')  # Sortie de stock
                ])
                
                if axes:
                    _logger.info(f"_get_financial_axes trouve : {axes} pour mrp")
                    axes += axes.filtered(lambda a: self._matches_axis(a))
            
            if self.raw_material_production_id.type_operation:
                account_id = self.analytic_account_id.id
                axes = self.env['project.financial.axis'].search([
                    ('project_financial_id.account_id', '=', account_id),
                    ('cost_type', '=', 'rate')  # Taux d'avancement
                ])
                
                if axes:
                    _logger.info(f"_get_financial_axes trouve : {axes} pour mrp")
                    axes += axes.filtered(lambda a: self._matches_axis(a))
        
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
            _logger.info(f"produit {self.product_id.name} a pas de categorie")
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

    def _update_axis_line_total(self, axis):
        """Met à jour le total d'un axe"""
        AxisLine = self.env['project.financial.axis.line']
        date = self._get_move_date_for_axis()
        total = 0.0
        domain = self._get_axis_calculation_domain(axis)
        axis_line = AxisLine.search([('axis_id', '=', axis.id), ('date', '=', date)], limit=1)
        moves = self.env['stock.move'].search(domain).filtred(
            lambda move: date == move.__get_move_date_for_axis()
            )
        
        _logger.info(f"Calcul axe {axis.complete_name} - {len(moves)} mouvements trouvés")
        
        for move in moves:
            if move._matches_axis(axis):
                #.product_qty
                total += move._calculate_earned_value_for_axis(axis)

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
        
        cost = self._get_product_cost_for_axis()
        # self.product_qty * self.product_id.standard_price
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
                new_value = axis_line.actual_cost - abs(price)
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
                        'product_qty': move._calculate_earned_value_for_axis(axes),
                        # .product_qty,
                        'price': move._get_product_cost_for_axis(),
                        # .product_id.standard_price,
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
