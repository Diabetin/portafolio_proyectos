# -*- coding: utf-8 -*-
import secrets
import requests
import logging
from datetime import datetime, timedelta, timezone
from werkzeug.utils import redirect as wk_redirect
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

FB_API_VERSION = "v20.0"

def _abs_redirect_uri():
    base = request.httprequest.url_root.rstrip("/")
    return f"{base}/meta_leads_oauth/callback"

class MetaLeadsOAuthController(http.Controller):
    
    @http.route("/meta_leads_oauth/start", type="http", auth="user", csrf=False)
    def oauth_start(self, importer_id=None, **kw):
        if not importer_id:
            return request.make_response("Missing importer_id", status=400)
            
        # Obtener credenciales del registro
        importer = request.env["meta.lead.importer"].browse(int(importer_id))
        if not importer.exists():
            return request.make_response("Invalid importer_id", status=400)
        
        if not importer.app_id or not importer.app_secret:
            return request.make_response(
                "<html><body><h3>Error</h3>"
                "<p>App ID y App Secret son requeridos. Configúralos en el formulario antes de obtener el token.</p>"
                "<p><a href='javascript:window.close();'>Cerrar ventana</a></p></body></html>",
                headers=[("Content-Type", "text/html")]
            )

        # Guardar registro objetivo y credenciales en sesión
        request.session["meta_importer_id"] = int(importer_id)
        request.session["meta_app_id"] = importer.app_id
        request.session["meta_app_secret"] = importer.app_secret
        
        # CSRF state
        state = secrets.token_urlsafe(16)
        request.session["meta_oauth_state"] = state
        
        # Redirección absoluta al diálogo de Facebook
        redirect_uri = _abs_redirect_uri()
        scope = "public_profile,email,leads_retrieval"
        auth_url = (
            f"https://www.facebook.com/{FB_API_VERSION}/dialog/oauth"
            f"?client_id={importer.app_id}"
            f"&redirect_uri={requests.utils.quote(redirect_uri, safe='')}"
            f"&state={state}"
            f"&response_type=code"
            f"&scope={scope}"
        )
        _logger.info("OAuth redirect to (Facebook): %s", auth_url)
        return wk_redirect(auth_url, code=302)

    @http.route("/meta_leads_oauth/callback", type="http", auth="user", csrf=False)
    def oauth_callback(self, **kw):
        # Validación de state
        state_expected = request.session.get("meta_oauth_state")
        if not state_expected or kw.get("state") != state_expected:
            return request.make_response("Invalid state", status=400)

        # Obtener credenciales de la sesión
        app_id = request.session.get("meta_app_id")
        app_secret = request.session.get("meta_app_secret")
        
        if not app_id or not app_secret:
            return request.make_response("Missing app credentials in session", status=400)

        # Código devuelto por FB
        code = kw.get("code")
        if not code:
            return request.make_response("Missing code", status=400)

        redirect_uri = _abs_redirect_uri()
        try:
            # 1) code -> access_token corto (web login)
            token_url = f"https://graph.facebook.com/{FB_API_VERSION}/oauth/access_token"
            params = {
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            }
            r = requests.get(token_url, params=params, timeout=30)
            if r.status_code >= 400:
                return request.make_response(f"Token exchange error: {r.text}", status=400)
            
            short_data = r.json()
            short_token = short_data.get("access_token")
            short_expires = short_data.get("expires_in")
            _logger.info("TOKEN CORTO OBTENIDO: %s (expira en %s s)", short_token, short_expires)

            # 2) corto -> access_token largo (~60 días)
            extend_url = f"https://graph.facebook.com/{FB_API_VERSION}/oauth/access_token"
            extend_params = {
                "grant_type": "fb_exchange_token",
                "client_id": app_id,
                "client_secret": app_secret,
                "fb_exchange_token": short_token,
            }
            r2 = requests.get(extend_url, params=extend_params, timeout=30)
            if r2.status_code >= 400:
                _logger.warning("No se pudo obtener token largo: %s", r2.text)
                return request.make_response("No se pudo generar token largo", status=400)

            long_data = r2.json()
            long_token = long_data.get("access_token")
            long_expires = long_data.get("expires_in")
            _logger.info("TOKEN LARGO OBTENIDO (~60 días): %s (expires_in=%s s)", long_token, long_expires)

            # 3) Calcular fecha de expiración
            fecha_exp = None
            if long_expires:
                fecha_exp = datetime.utcnow() + timedelta(seconds=int(long_expires))
            else:
                # Fallback: consultar /debug_token
                dbg_url = f"https://graph.facebook.com/{FB_API_VERSION}/debug_token"
                dbg_params = {
                    "input_token": long_token,
                    "access_token": f"{app_id}|{app_secret}",  # App Token
                }
                r3 = requests.get(dbg_url, params=dbg_params, timeout=30)
                if r3.status_code < 400:
                    d = r3.json().get("data", {})
                    exp_epoch = d.get("expires_at") or d.get("data_access_expires_at")
                    if exp_epoch:
                        fecha_exp = datetime.fromtimestamp(int(exp_epoch), tz=timezone.utc).replace(tzinfo=None)
                    _logger.info("DEBUG_TOKEN expires_at=%s data_access_expires_at=%s",
                                 d.get("expires_at"), d.get("data_access_expires_at"))

            # 4) Guardar en el registro
            importer_id = request.session.get("meta_importer_id")
            if importer_id:
                importer = request.env["meta.lead.importer"].browse(int(importer_id))
                if importer.exists():
                    vals = {
                        "name": long_token,
                        "access_token_long": long_token
                    }
                    if fecha_exp:
                        vals["fecha_expiracion"] = fecha_exp
                    importer.sudo().write(vals)
                    _logger.info("Token largo guardado en ID %s; fecha_expiracion=%s", importer_id, fecha_exp)

            # 5) Limpiar sesión
            request.session.pop("meta_app_id", None)
            request.session.pop("meta_app_secret", None)
            request.session.pop("meta_oauth_state", None)
            request.session.pop("meta_importer_id", None)

            # 6) Respuesta HTML
            return request.make_response(
                "<html><body><h3>Token largo generado</h3>"
                "<p>Se guardó el token como Nombre y la Fecha de expiración en el registro.</p>"
                "<p>Puedes cerrar esta ventana.</p></body></html>",
                headers=[("Content-Type", "text/html")],
            )

        except Exception as e:
            _logger.exception("Error en callback OAuth: %s", e)
            return request.make_response(f"Error: {str(e)}", status=500)
