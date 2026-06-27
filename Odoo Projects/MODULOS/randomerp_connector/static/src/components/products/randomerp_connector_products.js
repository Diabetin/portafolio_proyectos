import { Component, useState } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class RandomERP_connector_products extends Component {
    static template = 'randomerp_connector.randomerp_connector_products';

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            incluir_ocultos: false
        });
    }

    async importar() {
        try {
            const result = await rpc('/randomerp_connector/importar_productos_rpc', {
                incluir_ocultos: this.state.incluir_ocultos
            });

            if (result.status === 'ok') {
                const message = `Productos importados correctamente` +
                                `\nNuevos: ${result.creados}\n` +
                                `\nActualizados: ${result.actualizados}\n` +
                                `\nPrecios actualizados: ${result.precios_actualizados || 0}`;

                this.notification.add(message, { type: 'success', title: 'Importación exitosa' });
            } else {
                this.notification.add(result.message || "Error al importar productos", { type: 'danger', title: 'Error' });
            }
        } catch (error) {
            console.error("Error al importar productos:", error);
            this.notification.add("Error al importar productos: " + error.message, { type: 'danger', title: 'Error' });
        }
    }
}

registry.category("actions").add("randomerp_connector_products", RandomERP_connector_products);
