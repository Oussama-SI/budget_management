/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { xml } from "@odoo/owl";

class FinancialAxisKpiDashboard extends Component {
    static template = xml/* xml */`
        <div class="o_fin_axis_kpi_dashboard p-3">
            <div class="d-flex flex-wrap gap-3">

                <div class="card shadow-sm" style="min-width:260px; border-radius:16px;">
                    <div class="card-body">
                        <div class="text-muted">Planned Budget</div>
                        <div class="h3 m-0"><t t-esc="state.planned_budget_display"/></div>
                    </div>
                </div>

                <div class="card shadow-sm" style="min-width:260px; border-radius:16px;">
                    <div class="card-body">
                        <div class="text-muted">Delay Performance Index (DPI)</div>
                        <div class="h3 m-0"><t t-esc="state.dpi_display"/></div>
                    </div>
                </div>

                <div class="card shadow-sm" style="min-width:260px; border-radius:16px;">
                    <div class="card-body">
                        <div class="text-muted">Cost Performance Index (CPI)</div>
                        <div class="h3 m-0"><t t-esc="state.cpi_display"/></div>
                    </div>
                </div>

            </div>

            <div class="mt-3 text-muted" t-if="state.note">
                <t t-esc="state.note"/>
            </div>
        </div>
    `;

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            planned_budget_display: "-",
            dpi_display: "-",
            cpi_display: "-",
            note: "",
        });

        onWillStart(async () => {
            await this._loadKpis();
        });
    }

    _fmtNumber(val, digits = 3) {
        if (val === null || val === undefined || val === false) return "-";
        const n = Number(val);
        if (Number.isNaN(n)) return String(val);
        return n.toFixed(digits);
    }

    _fmtMoney(val, digits = 2) {
        if (val === null || val === undefined || val === false) return "-";
        const n = Number(val);
        if (Number.isNaN(n)) return String(val);
        return `${n.toFixed(digits)} DH`;
    }

    async _loadKpis() {
        // Dernière ligne (id desc). Adapte domain si tu veux par projet.
        const recs = await this.orm.searchRead(
            "project_financial_axis_line",
            [],
            ["planned_budget", "delay_perforance_index", "cost_perforance_index"],
            { limit: 1, order: "id desc" }
        );

        if (!recs.length) {
            this.state.note = "Aucune donnée trouvée dans project_financial_axis_line.";
            return;
        }

        const r = recs[0];
        this.state.planned_budget_display = this._fmtMoney(r.planned_budget, 2);
        this.state.dpi_display = this._fmtNumber(r.delay_perforance_index, 3);
        this.state.cpi_display = this._fmtNumber(r.cost_perforance_index, 3);
    }
}

registry.category("actions").add(
    "somachame_finance.fin_axis_kpi_dashboard",
    FinancialAxisKpiDashboard
);
