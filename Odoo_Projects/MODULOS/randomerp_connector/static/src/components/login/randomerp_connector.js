/** @odoo-module **/
import { Component, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

export class RandomERPConnector extends Component {
    static template = "randomerp_connector.RandomERPConnector";

    async setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.username = useRef("username");
        this.password = useRef("password");

        // Estado
        this.state = useState({ 
            loading: true,
            loginMethod: 'userpass', // valor por defecto
        });

        // Traer el login method desde los parámetros de sistema
        try {
            const params = await rpc("/randomerp_connector/get_config_params");
            if (params.randomerp_login_method) {
                this.state.loginMethod = params.randomerp_login_method;
            }

            const result = await rpc("/randomerp_connector/session_active");
            if (result.status === "ok") {
                this.action.doAction("randomerp_connector_home");
            }
        } catch (e) {
            console.error("Error verificando sesión o parámetros:", e);
        } finally {
            this.state.loading = false;
        }
    }

    async login() {
        const username = this.username.el?.value?.trim();
        const password = this.password.el?.value?.trim();

        if (!username || !password) {
            this.notification.add(
                "Por favor ingrese usuario y contraseña",
                { type: "warning", title: "Campos requeridos" }
            );
            return;
        }

        this.state.loading = true;
        try {
            const result = await rpc("/randomerp_connector/save_credentials", { username, password });
            if (result.status === "ok") {
                this.notification.add(result.message || "Credenciales guardadas correctamente", {
                    type: "success", title: "Login exitoso"
                });
                await rpc("/randomerp_connector/set_session", {});
                this.action.doAction("randomerp_connector_home");
                window.location.reload(); // Recargar para aplicar cambios
            } else {
                this.notification.add(result.message || "Error en el login", {
                    type: "danger", title: "Error de autenticación"
                });
            }
        } catch (error) {
            console.error("Error guardando credenciales:", error);
            this.notification.add(
                "No se pudo guardar la información. Verifique su conexión e intente nuevamente.",
                { type: "danger", title: "Error de conexión" }
            );
        } finally {
            this.state.loading = false;
        }
    }
}

registry.category("actions").add("RandomERPConnector", RandomERPConnector);
