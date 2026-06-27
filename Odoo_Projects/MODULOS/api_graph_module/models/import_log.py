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

class MetaLeadImportLog(models.Model):
    _name = 'meta.lead.import.log'
    _description = 'Historial de importación de leads Meta'
    _rec_name = 'name'

    name = fields.Char(string='Importación', required=True)
    fecha_importacion = fields.Datetime(
        string='Fecha de importación',
        default=lambda self: fields.Datetime.now()
    )
    leads_importados = fields.Integer(string='Leads importados', default=0, readonly=True)
    estado = fields.Selection([
        ('borrador', 'Borrador'),
        ('completado', 'Completado'),
        ('error', 'Error')
    ], string='Estado', default='borrador')
    mensaje = fields.Text(string='Mensaje de resultado', readonly=True)
    
    # Campo para seleccionar el token a usar
    token_importer_id = fields.Many2one(
        'meta.lead.importer',
        string='Token a usar',
        help='Selecciona el token/app que deseas usar para importar leads',
        domain=[('access_token_long', '!=', False)],
        required=True
    )

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

    def _resolve_selected_token(self):
        """
        Devuelve el token del registro seleccionado
        """
        if not self.token_importer_id:
            return None, None
            
        importer = self.token_importer_id
        now = fields.Datetime.now()
        
        # Verificar que el token no esté vencido
        if importer.fecha_expiracion and importer.fecha_expiracion < now:
            return None, None
            
        token = importer.access_token_long or importer.name
        if token:
            return token, importer.id
            
        return None, None

    def _get_all_ad_accounts(self, token):
        """
        Obtiene todos los account_id disponibles
        """
        api_version = "v23.0"
        url = f"https://graph.facebook.com/{api_version}/me/adaccounts?fields=id,name&access_token={token}"
        
        resp = self._graph_get(url)
        if resp and resp.status_code < 400:
            data = resp.json()
            _logger.info("CUENTAS DE ANUNCIOS ENCONTRADAS:\n%s", 
                        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))
            return data.get("data", [])
        return []

    def _get_ads_from_account(self, account_id, token):
        """
        Obtiene todos los ads de una cuenta específica
        """
        api_version = "v23.0"
        url = f"https://graph.facebook.com/{api_version}/{account_id}/ads?access_token={token}"
        
        all_ads = []
        resp = self._graph_get(url)
        if resp and resp.status_code < 400:
            data = resp.json()
            _logger.info("ADS ENCONTRADOS EN CUENTA %s:\n%s", account_id,
                        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))
            all_ads.extend(data.get("data", []))
            
            # Paginación si hay más ads
            next_url = data.get("paging", {}).get("next")
            while next_url:
                r2 = self._graph_get(next_url)
                if r2 is None or r2.status_code >= 400:
                    break
                d2 = r2.json()
                all_ads.extend(d2.get("data", []))
                next_url = d2.get("paging", {}).get("next")
        
        return all_ads

    def _get_lead_form_id_from_ad(self, ad_id, token):
        """
        Extrae el lead_gen_form_id de un ad específico
        """
        api_version = "v23.0"
        url = f"https://graph.facebook.com/{api_version}/{ad_id}?fields=creative{{object_story_spec{{link_data{{call_to_action{{value{{lead_gen_form_id}}}}}}}}}}&access_token={token}"
        
        resp = self._graph_get(url)
        if resp and resp.status_code < 400:
            data = resp.json()
            _logger.info("CREATIVE DATA PARA AD %s:\n%s", ad_id,
                        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))
            
            try:
                # Navegamos la estructura anidada
                creative = data.get('creative', {})
                object_story_spec = creative.get('object_story_spec', {})
                link_data = object_story_spec.get('link_data', {})
                call_to_action = link_data.get('call_to_action', {})
                value = call_to_action.get('value', {})
                lead_gen_form_id = value.get('lead_gen_form_id')
                
                if lead_gen_form_id:
                    _logger.info("ENCONTRADO lead_gen_form_id %s en AD %s", lead_gen_form_id, ad_id)
                    return lead_gen_form_id
            except Exception as e:
                _logger.warning("Error extrayendo lead_gen_form_id de AD %s: %s", ad_id, e)
        
        return None

    def _get_leads_from_form(self, form_id, token):
        """
        Obtiene leads de un formulario específico
        """
        api_version = "v23.0"
        url = f"https://graph.facebook.com/{api_version}/{form_id}/leads?fields=id,created_time,form_id,ad_id,field_data&access_token={token}"
        
        all_leads = []
        resp = self._graph_get(url)
        if resp and resp.status_code < 400:
            data = resp.json()
            _logger.info("LEADS ENCONTRADOS EN FORM %s:\n%s", form_id,
                        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default))
            all_leads.extend(data.get("data", []))
            
            # Paginación si hay más leads
            next_url = data.get("paging", {}).get("next")
            while next_url:
                r2 = self._graph_get(next_url)
                if r2 is None or r2.status_code >= 400:
                    break
                d2 = r2.json()
                all_leads.extend(d2.get("data", []))
                next_url = d2.get("paging", {}).get("next")
        
        return all_leads

    def _create_crm_lead(self, lead_data):
        """
        Crea un lead en CRM desde la data de Meta
        """
        lead_id = lead_data.get('id')
        external_id = f"meta_lead_{lead_id}"

        # Verificar si ya existe
        existing = self.env['ir.model.data'].search([
            ('module', '=', 'api_graph_module'),
            ('name', '=', external_id),
            ('model', '=', 'crm.lead')
        ], limit=1)
        if existing:
            return False  # Ya existe, no crear duplicado

        # Mapear field_data
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

        # Construir descripción
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

        # Crear el lead
        CrmLead = self.env['crm.lead']
        new_lead = CrmLead.create(lead_vals)

        # Registrar xmlid para evitar duplicados
        self.env['ir.model.data'].create({
            'module': 'api_graph_module',
            'name': external_id,
            'model': 'crm.lead',
            'res_id': new_lead.id,
        })

        return True  # Lead creado exitosamente

    def action_importar_leads(self):
        """
        Importación completa: busca en todas las cuentas, ads y formularios usando el token seleccionado
        """
        # Usar el token seleccionado en lugar del método anterior
        token, src_id = self._resolve_selected_token()
        if not token:
            mensaje_error = 'Token no válido o vencido. Selecciona un token válido o genera uno nuevo.'
            self.write({
                'estado': 'error',
                'mensaje': mensaje_error
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Token requerido'),
                    'message': _(mensaje_error),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        if src_id:
            _logger.info("Usando token desde registro ID %s seleccionado por el usuario.", src_id)

        total_created = 0
        resultados = []

        try:
            # Agregar información del token utilizado
            importer_info = f"App ID: {self.token_importer_id.app_id}" if self.token_importer_id.app_id else "App ID no disponible"
            resultados.append(f"Usando token de: {importer_info}")
            
            # 1. Obtener todas las cuentas de anuncios
            ad_accounts = self._get_all_ad_accounts(token)
            if not ad_accounts:
                msg = "No se encontraron cuentas de anuncios"
                self.write({'estado': 'error', 'mensaje': msg})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Sin cuentas'),
                        'message': _(msg),
                        'type': 'warning',
                        'sticky': False,
                    }
                }

            resultados.append(f"Encontradas {len(ad_accounts)} cuentas de anuncios")

            # 2. Para cada cuenta de anuncios
            for account in ad_accounts:
                account_id = account.get('id')
                account_name = account.get('name', 'Sin nombre')
                _logger.info("Procesando cuenta: %s (%s)", account_name, account_id)
                
                # 3. Obtener todos los ads de esta cuenta
                ads = self._get_ads_from_account(account_id, token)
                if not ads:
                    resultados.append(f"Cuenta {account_name}: Sin ads activos")
                    continue

                resultados.append(f"Cuenta {account_name}: {len(ads)} ads encontrados")
                forms_procesados = set()  # Para evitar duplicados

                # 4. Para cada ad, obtener el lead_gen_form_id
                for ad in ads:
                    ad_id = ad.get('id')
                    form_id = self._get_lead_form_id_from_ad(ad_id, token)
                    
                    if form_id and form_id not in forms_procesados:
                        forms_procesados.add(form_id)
                        
                        # 5. Obtener leads del formulario
                        leads = self._get_leads_from_form(form_id, token)
                        if leads:
                            created_count = 0
                            for lead_data in leads:
                                if self._create_crm_lead(lead_data):
                                    created_count += 1
                            
                            total_created += created_count
                            resultados.append(f"Form {form_id}: {created_count} leads nuevos de {len(leads)} totales")
                        else:
                            resultados.append(f"Form {form_id}: Sin leads")

            # Actualizar registro con resultados
            mensaje_final = "\n".join(resultados)
            if total_created > 0:
                msg = f"Importación completada: {total_created} leads creados en CRM"
                estado = 'completado'
            else:
                msg = "Importación completada: No se encontraron leads nuevos"
                estado = 'completado'

            self.write({
                'estado': estado,
                'leads_importados': total_created,
                'mensaje': mensaje_final,
                'fecha_importacion': fields.Datetime.now()
            })

        except Exception as e:
            _logger.exception("Error en importación completa: %s", e)
            msg = f"Error en importación: {str(e)}"
            self.write({
                'estado': 'error',
                'mensaje': msg
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Importación de Leads'),
                'message': msg,
                'type': 'success' if total_created > 0 else 'info',
                'sticky': False,
            }
        }
