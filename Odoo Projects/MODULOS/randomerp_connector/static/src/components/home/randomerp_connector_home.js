import { Component } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

export class RandomERP_connector_home extends Component {
    static template = 'randomerp_connector.randomerp_connector_home';

    async setup() {
        this.action = useService("action");
        
    }

}

registry.category("actions").add("randomerp_connector_home", RandomERP_connector_home);
