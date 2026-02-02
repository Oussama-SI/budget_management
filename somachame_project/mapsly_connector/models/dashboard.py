from odoo import models
from odoo.exceptions import UserError

class ProjectFinancialProgress(models.Model):
    _inherit = "project.financial.progress"

    def action_open_kpi_iframe(self):
        self.ensure_one()

        # adapt this depending on your fields:
        # if you have project_financial_id:
        if hasattr(self, "project_financial_id") and self.project_financial_id:
            pid = self.project_financial_id.id
        # else if you have project_id:
        elif hasattr(self, "project_id") and self.project_id:
            pid = self.project_id.id
        else:
            # fallback to current record id
            pid = self.id

        if not pid:
            raise UserError("Impossible de déterminer project_id.")

        return {
            "type": "ir.actions.client",
            "tag": "mapsly_frame",
            "params": {
                "base_url": "http://localhost:5173/",
                "project_id": pid,
            },
        }