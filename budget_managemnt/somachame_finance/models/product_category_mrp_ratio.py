import logging
from odoo import api, fields, models, _
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ProductCategoryRatio(models.Model):
    _name = "product.category.mrp.ratio"
    _description = "Ratio du taux d'avancement en fabrication"

    axis_id = fields.Many2one(
        'project.financial.axis',
        string='Axe analytique',
        required=True,
        ondelete='cascade'
    )
    
    product_category_id = fields.Many2one(
        'product.category',
        string='Catégorie produit',
        required=True
    )
    
    # Ratios pour chaque phase de production
    debitage_ratio = fields.Float(
        string='Débitage (%)',
        default=0.0,
        help="Pourcentage estimé pour la phase de débitage"
    )
    
    assemblage_ratio = fields.Float(
        string='Assemblage (%)',
        default=0.0,
        help="Pourcentage estimé pour la phase d'assemblage"
    )
    
    soudage_ratio = fields.Float(
        string='Soudage (%)',
        default=0.0,
        help="Pourcentage estimé pour la phase de soudage"
    )
    
    finition_ratio = fields.Float(
        string='Finition (%)',
        default=0.0,
        help="Pourcentage estimé pour la phase de finition"
    )
    
    peinture_ratio = fields.Float(
        string='Peinture (%)',
        default=0.0,
        help="Pourcentage estimé pour la phase de peinture"
    )
    
    total_ratio = fields.Float(
        string='Total (%)',
        compute='_compute_total_ratio',
        store=True
    )
    
    @api.depends('debitage_ratio', 'assemblage_ratio', 'soudage_ratio', 'finition_ratio', 'peinture_ratio')
    def _compute_total_ratio(self):
        for record in self:
            record.total_ratio = sum([
                record.debitage_ratio,
                record.assemblage_ratio,
                record.soudage_ratio,
                record.finition_ratio,
                record.peinture_ratio
            ])
    
    _sql_constraints = [
        ('category_uniq', 'UNIQUE(axis_id, product_category_id)',
         'Cette catégorie a déjà des ratios définis pour cet axe!'),
        ('total_ratio_check', 'CHECK(total_ratio <= 100)',
         'La somme des ratios ne peut pas dépasser 100%!'),
    ]


class ProjectFinancialAxis(models.Model):
    _inherit = "project.financial.axis"

    _sql_constraints = [
        ('project_location_uniq', 'UNIQUE(project_financial_id, location_id)', 
         'Ce emplacement est déja utilisé pour un autre axe pour le méme projet'),
    ]
    
    show_ratio_fields = fields.Boolean(
        string='Afficher les ratios',
        compute='_compute_show_ratio_fields',
        store=False
    )
    

    category_ratio_ids = fields.One2many(
        'product.category.mrp.ratio',
        'axis_id',
        string='Ratios par catégorie',
        domain="[('product_category_id', 'in', product_category_ids)]"
    )
    
    @api.depends('type')
    def _compute_show_ratio_fields(self):
        for record in self:
            record.show_ratio_fields = record.type == 'rate'

    @api.onchange('product_category_ids')
    def _onchange_product_category_ids(self):
        """Crée ou supprime les lignes de ratios lorsque les catégories changent"""
        self.ensure_one()
        if self.type == 'rate':
            existing_cat_ids = set(self.category_ratio_ids.mapped('product_category_id.id'))
            new_cat_ids = set(self.product_category_ids.ids)
            
            to_add_ids = new_cat_ids - existing_cat_ids
            to_remove_ids = existing_cat_ids - new_cat_ids
            
            if not to_add_ids and not to_remove_ids:
                return
            
            commands = []
            if to_add_ids:
                commands.extend([
                    (0, 0, {'product_category_id': cat_id})
                    for cat_id in to_add_ids
                ])
            
            if to_remove_ids:
                ratio_ids_to_remove = self.category_ratio_ids.filtered(
                    lambda r: r.product_category_id.id in to_remove_ids
                ).ids
                
                commands.extend([
                    (2, ratio_id) for ratio_id in ratio_ids_to_remove
                ])
            
            self.category_ratio_ids = commands
    
    @api.model
    def create(self, vals):
        """Override create pour initialiser les ratios"""
        axis = super(ProjectFinancialAxis, self).create(vals)
        if axis.type == 'rate' and 'product_category_ids' in vals:
            axis._onchange_product_category_ids()
        return axis
