/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

class MapslyFrameView extends Component {
  setup() {
    const params = this.props.action?.params || {};
    const base = params.base_url || "http://localhost:5173/";
    const pid = params.project_id;

    const url = pid ? `${base}?project_id=${encodeURIComponent(pid)}` : base;
    this.state = useState({ url });
  }
}

MapslyFrameView.template = "mapsly_connector.MapslyFrameView";

registry.category("actions").add("mapsly_frame", MapslyFrameView);