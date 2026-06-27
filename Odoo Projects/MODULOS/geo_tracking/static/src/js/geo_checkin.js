/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
import { browser } from "@web/core/browser/browser";

// Función para obtener la IP pública del usuario
async function getPublicIpAddress() {
    try {
        const response = await browser.fetch('https://api.ipify.org?format=json');
        if (!response.ok) {
            throw new Error('Failed to fetch IP from ipify.org');
        }
        const data = await response.json();
        return data.ip;
    } catch (error) {
        console.error("Error getting public IP:", error);
        return null; // Retornar null si falla
    }
}

// Función de acción cliente para el check-in
async function getGeolocationClientAction(env, action) {
    const { task_id } = action.params || {};
    const orm = env.services.orm;
    const notification = env.services.notification;

    if (!task_id) {
        notification.add(_t("Error: No se encontró el ID de la tarea."), { type: 'danger', sticky: true });
        return;
    }

    notification.add(_t("Obteniendo su ubicación actual..."), { type: 'info', sticky: false });

    const publicIp = await getPublicIpAddress();
    if (!publicIp) {
        notification.add(_t("No se pudo obtener tu dirección IP. Verifica tu conexión a internet."), { type: 'danger', sticky: true });
        return;
    }

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const { latitude, longitude, accuracy } = position.coords;
                console.log("Ubicación obtenida:", { latitude, longitude, accuracy });

                try {
                    const result = await orm.call(
                        'project.task',
                        'get_location',
                        [task_id, {
                            latitude,
                            longitude,
                            accuracy,
                            ip: publicIp,
                            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                        }]
                    );
                    
                    // Imprimir todos los datos de la IP en la consola
                    if (result.ip_data) {
                        console.log("Datos completos de la IP:", result.ip_data);
                    }

                    handleServerResponse(result, notification, env.services.action);

                } catch (error) {
                    handleRpcError(error, notification);
                }
            },
            (error) => {
                handleGeolocationError(error, notification);
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    } else {
        notification.add(_t("Tu navegador no soporta la geolocalización."), { type: 'danger', sticky: true });
    }
}

// Función para manejar la respuesta del servidor
function handleServerResponse(result, notification, actionService) {
    if (result.type === 'ir.actions.client' && result.tag === 'display_notification') {
        const params = result.params || {};
        notification.add(params.message || _t("Error al registrar la ubicación"), {
            title: params.title || _t("Error"),
            type: params.type || 'danger',
            sticky: params.sticky !== undefined ? params.sticky : true,
        });
    } else {
        notification.add(result.message || _t("Ubicación registrada con éxito"), {
            type: 'success',
        });
        actionService.doAction({ type: 'ir.actions.act_window_close' }).then(() => {
            browser.location.reload();
        });
    }
}

// Función para manejar errores de RPC
function handleRpcError(error, notification) {
    const errorMessage = error.message?.data?.message || _t("Error al procesar la solicitud.");
    console.error("Error RPC:", error);
    notification.add(errorMessage, { type: 'danger', sticky: true });
}

// Función para manejar errores de geolocalización
function handleGeolocationError(error, notification) {
    let errorMessage;
    switch (error.code) {
        case error.PERMISSION_DENIED:
            errorMessage = _t("Permiso de geolocalización denegado.");
            break;
        case error.POSITION_UNAVAILABLE:
            errorMessage = _t("Información de ubicación no disponible.");
            break;
        case error.TIMEOUT:
            errorMessage = _t("Tiempo de espera agotado para obtener la ubicación.");
            break;
        default:
            errorMessage = _t("Error desconocido de geolocalización.");
            break;
    }
    console.error("Error de geolocalización:", error);
    notification.add(errorMessage, { type: 'danger', sticky: true });
}

// Registrar la acción en el registro de Odoo
registry.category('actions').add('get_geolocation_from_browser', getGeolocationClientAction, { force: true });