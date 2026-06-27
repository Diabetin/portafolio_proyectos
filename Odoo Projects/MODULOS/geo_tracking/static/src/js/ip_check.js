/** @odoo-module **/

import { whenReady } from "@odoo/owl";

// Función para mostrar notificaciones
function showNotification(type, title, message) {
    const typeClasses = {
        'success': 'alert-success',
        'warning': 'alert-warning',
        'error': 'alert-danger',
        'info': 'alert-info'
    };

    const icons = {
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'error': 'fa-times-circle',
        'info': 'fa-info-circle'
    };

    const notification = document.createElement('div');
    notification.className = `alert ${typeClasses[type]} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        animation: slideIn 0.5s ease-out;
    `;

    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fa ${icons[type]} me-2"></i>
            <div class="flex-grow-1">
                <strong>${title}</strong>
                ${message ? `<br><small>${message}</small>` : ''}
            </div>
            <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.5s ease-in';
            setTimeout(() => notification.remove(), 500);
        }
    }, 8000);
}

// Inyectar CSS de animaciones
if (!document.getElementById('security-notifications-css')) {
    const style = document.createElement('style');
    style.id = 'security-notifications-css';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Función principal
async function verificarConexion() {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    console.log("🚀 Iniciando verificación de seguridad IP con timezone:", timezone);

    let clientIp = null;
    try {
        const ipResponse = await fetch('https://api.ipify.org?format=json');
        const ipData = await ipResponse.json();
        clientIp = ipData.ip;
        console.log("IP pública obtenida:", clientIp);
    } catch (ipError) {
        console.warn("No se pudo obtener la IP pública:", ipError);
    }

    try {
        const response = await fetch('/check/ipdetective', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ timezone, client_ip: clientIp }),
        });

        if (!response.ok) throw new Error(`HTTP error ${response.status}`);

        const json = await response.json();
        const data = json.result || {};

        // 🔧 Desempaquetar flags si vienen anidados
        if (data.flags) {
            data.vpn = data.flags.vpn_detectado;
            data.proxy = data.flags.proxy_detectado;
            data.datacenter = data.flags.datacenter_detectado;
            data.timezone_mismatch = data.flags.timezone_mismatch;
        }

        console.log("📡 Respuesta completa del servidor:", data);

        if (!data || typeof data !== 'object') {
            console.warn("⚠️ Respuesta inválida del servidor:", data);
            return;
        }

        if (data.error) {
            console.warn("❌ Error en verificación IP:", data.error);
            if (data.status === 'critical_error') {
                showNotification('error', '🚨 Error crítico de verificación', data.error);
            }
            return;
        }

        if (data.status === 'local_ip') {
            console.log("🏠 IP local detectada:", data.message);
            return;
        }

        const hasSecurityIssues = data.vpn || data.proxy || data.datacenter || data.timezone_mismatch;

        console.log("🔍 Análisis de seguridad completo:", {
            provider: data.provider,
            ip: data.ip,
            country: data.country,
            region: data.region,
            city: data.city,
            isp: data.isp,
            vpn: data.vpn,
            proxy: data.proxy,
            datacenter: data.datacenter,
            mobile: data.mobile,
            timezone_mismatch: data.timezone_mismatch,
            geo_timezone: data.geo_timezone,
            browser_timezone: data.browser_timezone
        });

        if (hasSecurityIssues) {
            let riskLevel = 'warning';
            let riskCount = 0;
            if (data.vpn) riskCount++;
            if (data.proxy) riskCount++;
            if (data.datacenter) riskCount++;
            if (data.timezone_mismatch) riskCount++;
            if (riskCount >= 2) riskLevel = 'danger';

            let issues = [];
            if (data.vpn) issues.push('🔒 VPN');
            if (data.proxy) issues.push('🛡️ Proxy');
            if (data.datacenter) issues.push('🏢 Datacenter');
            if (data.timezone_mismatch) issues.push('🌍 Zona horaria');

            const notification = document.createElement('div');
            notification.className = `alert alert-${riskLevel} alert-dismissible fade show position-fixed`;
            notification.style.cssText = `
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 450px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.4);
                border-left: 5px solid ${riskLevel === 'danger' ? '#dc3545' : '#ffc107'};
                animation: slideIn 0.5s ease-out;
            `;

            const icon = riskLevel === 'danger' ? '🚨' : '⚠️';
            const title = riskLevel === 'danger' ? 'Conexión de alto riesgo' : 'Conexión sospechosa detectada';

            notification.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="me-3 mt-1">
                        <i class="fa fa-shield-alt text-${riskLevel}" style="font-size: 1.2em;"></i>
                    </div>
                    <div class="flex-grow-1">
                        <strong>${icon} ${title}</strong><br>
                        <small class="text-muted">Detectado: ${issues.join(', ')}</small><br>
                        <small class="text-muted">📍 ${data.country || 'País desconocido'} • ${data.city || 'Ciudad desconocida'}</small><br>
                        <small class="text-muted">🌐 ${data.ip} • ${data.isp || 'ISP desconocido'}</small><br>
                        <small class="text-muted mt-1 d-block">🔗 Fuente: ${data.provider || 'API múltiple'}</small>
                    </div>
                    <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            `;

            document.body.appendChild(notification);

            setTimeout(() => {
                if (notification.parentNode) {
                    notification.style.animation = 'slideOut 0.5s ease-in';
                    setTimeout(() => notification.remove(), 500);
                }
            }, 15000);

            console.warn("🔒 CONEXIÓN SOSPECHOSA DETECTADA:", {
                riskLevel: riskLevel,
                ip: data.ip,
                location: `${data.city}, ${data.region}, ${data.country}`,
                issues: issues,
                details: {
                    vpn: data.vpn,
                    proxy: data.proxy,
                    datacenter: data.datacenter,
                    timezone_mismatch: data.timezone_mismatch,
                    geo_tz: data.geo_timezone,
                    browser_tz: data.browser_timezone,
                    isp: data.isp,
                    provider: data.provider
                }
            });

            window.dispatchEvent(new CustomEvent('suspiciousConnection', {
                detail: { riskLevel, data, issues }
            }));

        } else {
            console.log("✅ CONEXIÓN SEGURA VERIFICADA:", {
                ip: data.ip,
                location: `${data.city}, ${data.region}, ${data.country}`,
                isp: data.isp,
                mobile: data.mobile,
                geo_timezone: data.geo_timezone,
                browser_timezone: data.browser_timezone,
                provider: data.provider
            });

            if (window.location.hash.includes('debug') || localStorage.getItem('show_security_ok')) {
                showNotification('success', '✅ Conexión verificada',
                    `IP segura desde ${data.country} (${data.provider})`);
            }
        }

    } catch (error) {
        console.error("💥 Error completo verificando IP:", error);

        if (error.message) {
            if (error.message.includes("Extra data")) {
                console.error("🔧 Error de formato JSON del servidor.");
            } else if (error.message.includes("Unexpected token")) {
                console.error("🔧 Respuesta del servidor no es JSON válido.");
            } else if (error.message.includes("404")) {
                console.error("🔧 Endpoint /check/ipdetective no encontrado.");
            } else if (error.message.includes("500")) {
                console.error("🔧 Error interno del servidor.");
            } else {
                console.error("🔧 Error general:", error.message);
            }
        }

        if (!error.message?.includes("404")) {
            showNotification('error', '🚨 Error de verificación',
                'No se pudo verificar la seguridad de la conexión');
        }
    }
}

whenReady(verificarConexion);