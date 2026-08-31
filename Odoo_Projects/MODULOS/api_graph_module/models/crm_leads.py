# -*- coding: utf-8 -*-
import logging
import json
import time
import requests
from datetime import datetime, date
from odoo import models, fields, _

_logger = logging.getLogger(__name__)

def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray)):
        try:
            return o.decode('utf-8')
        except Exception:
            return str(o)
    return str(o)

class MetaLeadImporter(models.Model):
    _name = "meta.lead.importer"
    _description = "Importador Simple de Leads Meta"
    _rec_name = "name"

    name = fields.Char("Nombre (Token de acceso largo)", readonly=True)
    access_token_long = fields.Text("Token Largo", readonly=True)
    fecha_expiracion = fields.Datetime("Fecha de expiración", readonly=True)
    
    # Nuevos campos para credenciales dinámicas
    app_id = fields.Char("App ID de Meta", required=True, help="Identificador de la aplicación de Meta")
    app_secret = fields.Char("App Secret de Meta", required=True, help="Clave secreta de la aplicación de Meta")

    def _graph_get(self, url, params=None, max_retries=3):
        attempt = 0
        last_resp = None
        while True:
            try:
                resp = requests.get(url, params=params, timeout=30)
                last_resp = resp
                if resp.status_code < 400:
                    return resp
                try:
                    err = resp.json().get('error', {})
                except Exception:
                    err = {}
                code = err.get('code')
                subcode = err.get('error_subcode')
                message = err.get('message', resp.text)
                _logger.warning("Graph error HTTP=%s code=%s subcode=%s msg=%s",
                                resp.status_code, code, subcode, message)
                if code == 190 or code in (10, 200, 2500, 298, 100):
                    break
                if attempt < max_retries:
                    sleep_s = 2 ** attempt
                    time.sleep(sleep_s)
                    attempt += 1
                    continue
                break
            except requests.exceptions.RequestException as e:
                _logger.exception("Graph RequestException: %s", e)
                if attempt < max_retries:
                    sleep_s = 2 ** attempt
                    time.sleep(sleep_s)
                    attempt += 1
                    continue
                raise
        return last_resp

    def _resolve_active_token(self):
        """
        Devuelve el token largo más reciente y válido:
        1) Preferir el del registro actual si existe y no está vencido.
        2) Si no, buscar en todo el modelo por fecha_expiracion desc (o write_date desc si no hay fecha).
        """
        now = fields.Datetime.now()
        token = (self.access_token_long or self.name) if self else None
        if token and (not self.fecha_expiracion or self.fecha_expiracion >= now):
            return token, self.id
        rec = self.sudo().search(
            [('access_token_long', '!=', False)],
            order='fecha_expiracion desc, write_date desc',
            limit=1
        )
        if rec:
            tok = rec.access_token_long or rec.name
            if tok and (not rec.fecha_expiracion or rec.fecha_expiracion >= now):
                return tok, rec.id
        return None, None

    def action_obtener_token(self):
        # Validación de credenciales antes de proceder
        if not self.app_id or not self.app_secret:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Credenciales requeridas'),
                    'message': _('Debe ingresar App ID y App Secret antes de obtener el token.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        oauth_url = f"{base_url}/meta_leads_oauth/start?importer_id={self.id}"
        return {'type': 'ir.actions.act_url', 'url': oauth_url, 'target': 'new'}

    def action_importar_leads(self):
        """
        Usa el token largo vigente y consulta /{form_id}/leads (v23.0),
        siguiendo paging.next hasta agotar resultados.
        """
        token, src_id = self._resolve_active_token()
        if not token:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Token requerido'),
                    'message': _('No hay token largo vigente. Genera un token en "Obtener Token".'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        if src_id and self.id != src_id:
            _logger.info("Usando token desde registro ID %s por ser el más reciente disponible.", src_id)
    
        # FORM_ID del formulario que contiene las respuestas
        form_id = "3147296205436793"
        api_version = "v23.0"
    
        # Endpoint del formulario con fields útiles (incluye ad_id y field_data)
        url = (
            f"https://graph.facebook.com/{api_version}/{form_id}/leads"
            f"?fields=id,created_time,form_id,ad_id,field_data"
            f"&access_token={token}"
        )
    
        leads_all, created_count = [], 0
        try:
            resp = self._graph_get(url, params=None)
            if resp and resp.status_code < 400:
                data = resp.json()
                _logger.info("RESPUESTA COMPLETA META API:\n%s",
                             json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))
                leads_all.extend(data.get("data", []))
    
                # Paginación con paging.next
                next_url = data.get("paging", {}).get("next")
                while next_url:
                    r2 = self._graph_get(next_url, params=None)
                    if r2 is None or r2.status_code >= 400:
                        break
                    d2 = r2.json()
                    _logger.info("RESPUESTA PÁGINA ADICIONAL:\n%s",
                                 json.dumps(d2, indent=2, ensure_ascii=False, default=_json_default))
                    leads_all.extend(d2.get("data", []))
                    next_url = d2.get("paging", {}).get("next")
    
                CrmLead = self.env['crm.lead']
                for lead_data in leads_all:
                    lead_id = lead_data.get('id')
                    external_id = f"meta_lead_{lead_id}"
    
                    existing = self.env['ir.model.data'].search([
                        ('module', '=', 'api_graph_module'),
                        ('name', '=', external_id),
                        ('model', '=', 'crm.lead')
                    ], limit=1)
                    if existing:
                        continue
    
                    # Mapear field_data con reglas:
                    # - full_name -> contact_name
                    # - company_name -> partner_name
                    # - email* -> email_from
                    # - phone* -> phone
                    # - resto -> a descripción
                    field_data = lead_data.get('field_data', [])
                    lead_info = {}
                    extras = []
                    partner_name = None
    
                    for field in field_data:
                        key = field.get('name') or ''
                        key_l = key.lower()
                        vals = field.get('values') or []
                        val_list = vals if isinstance(vals, list) else [vals]
                        primary = val_list if val_list else ''
    
                        if key_l == 'full_name':
                            lead_info['contact_name'] = primary
                        elif key_l == 'company_name':
                            partner_name = primary
                        elif 'email' in key_l:
                            lead_info['email_from'] = primary
                        elif 'phone' in key_l:
                            lead_info['phone'] = primary
                        else:
                            extras.append(f"{key}: {', '.join([str(v) for v in val_list])}")
    
                    # Construir descripción con metadatos y extras
                    desc_lines = [
                        "Importado desde Meta Lead Ads",
                        f"Form ID: {lead_data.get('form_id', '')}",
                        f"Ad ID: {lead_data.get('ad_id', '')}",
                        f"Creado: {lead_data.get('created_time', '')}",
                    ]
                    if extras:
                        desc_lines.append("Respuestas:")
                        desc_lines.extend(extras)
    
                    lead_vals = {
                        'name': f"Lead Meta {lead_id}",
                        'contact_name': lead_info.get('contact_name', 'Sin nombre'),
                        'email_from': lead_info.get('email_from'),
                        'phone': lead_info.get('phone'),
                        'partner_name': partner_name,
                        'description': "\n".join(desc_lines),
                    }
    
                    new_lead = CrmLead.create(lead_vals)
    
                    # Registrar xmlid para no duplicar
                    self.env['ir.model.data'].create({
                        'module': 'api_graph_module',
                        'name': external_id,
                        'model': 'crm.lead',
                        'res_id': new_lead.id,
                    })
                    created_count += 1
    
                msg = _("Importación completada: %s leads creados en CRM") % created_count
            else:
                msg = _("Error al obtener leads de Meta")
        except Exception as e:
            _logger.exception("Error en importación: %s", e)
            msg = _("Error en importación: %s") % str(e)
    
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Importación de Leads'),
                'message': msg,
                'type': 'success' if created_count > 0 else 'warning',
                'sticky': False,
            }
        }
