from odoo import http, fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WebsiteApSscl(http.Controller):
    @http.route('/landing', type='http', auth='public', website=False)
    def landing(self, **kwargs):
        return request.render('website_ap_sscl.template_landing')
    
    @http.route('/landing_form2', type='http', auth='public', website=False)
    def landing2(self, **kwargs):
        return request.render('website_cap_sscl2.template_landing2')
    
    @http.route('/custom_web_lead', type='json', auth='public', methods=['POST'], csrf=False)
    def create_lead(self, **kwargs):
        """Crea un lead y SIEMPRE crea un contacto nuevo, sin comparar email, con campos x_studio personalizados."""
        try:
            _logger.info(f"Received request with kwargs: {kwargs}")
            params = kwargs.get('params', {})
            if not params:
                params = kwargs
            _logger.info(f"Extracted params: {params}")
            
            nombre = params.get('nombre', '').strip()
            apellido = params.get('apellido', '').strip()
            telefono = params.get('telefono', '').strip()
            email = params.get('email', '').strip()
            renta = params.get('renta', '')
            ahorro = params.get('ahorro', '')
            situacion = params.get('situacion', '')
            
            _logger.info(f"Form data - nombre: '{nombre}', apellido: '{apellido}', telefono: '{telefono}', email: '{email}', renta: '{renta}', ahorro: '{ahorro}', situacion: '{situacion}'")
            
            # Validar campos requeridos
            missing_fields = []
            if not nombre:
                missing_fields.append('nombre')
            if not apellido:
                missing_fields.append('apellido')
            if not telefono:
                missing_fields.append('telefono')
            if not email:
                missing_fields.append('email')
                
            if missing_fields:
                error_msg = f'Faltan los siguientes campos: {", ".join(missing_fields)}'
                _logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Map renta values
            renta_mapping = {
                '1': 'Entre $1.000.001 - $1.400.000',
                '2': 'Entre $1.400.001 - $1.800.000',
                '3': 'Más de $1.800.001'
            }
            renta_text = renta_mapping.get(renta, 'No especificado')
            
            # Map ahorro values
            ahorro_mapping = {
                '0': 'No tengo capacidad de ahorro mensual',
                '100-200': 'Entre $100.000-$200.000',
                '200-400': 'Entre $200.001-$400.000',
                '400': 'Más de $400.001'
            }
            ahorro_text = ahorro_mapping.get(ahorro, 'No especificado')
            
            # Map situación values
            situacion_mapping = {
                'corriente-ok': 'Tengo cuenta corriente y no estoy en DICOM',
                'nocorriente': 'No tengo cuenta corriente',
                'dicom': 'Estoy en DICOM'
            }
            situacion_text = situacion_mapping.get(situacion, 'No especificado')
            
            # Crear partner siempre
            partner = None
            try:
                partner = request.env['res.partner'].sudo().create({
                    'name': f'{nombre} {apellido}',
                    'email': email,
                    'phone': telefono,
                    'is_company': False,
                })
                _logger.info(f"Created new partner: {partner.id}")
            except Exception as e:
                _logger.warning(f"Could not create partner: {str(e)}")
            
            # --- ETAPA POR PERFIL FINANCIERO ---
            Stage = request.env['crm.stage'].sudo()
            # Buscar o crear etapa 'No Calificado'
            stage_no_calificado = Stage.search([('name', '=', 'No Calificado')], limit=1)
            if not stage_no_calificado:
                stage_no_calificado = Stage.create({
                    'name': 'No Calificado',
                    'fold': True
                })
            
            # Buscar etapa 'Qualified' o 'Calificado"
            stage_qualified = Stage.search([
                '|',
                ('name', '=', 'Qualified'),
                ('name', '=', 'Calificado')
            ], limit=1)
            
            # Validar condiciones para asignar etapa (por valor de la variable, NO por texto)
            es_no_calificado = False
            if ahorro == '0' or situacion in ['dicom', 'nocorriente']:
                es_no_calificado = True
            
            # --- GENERAR RECORD ID SECUENCIAL ---
            # Buscar el último record_id usado para generar el siguiente
            last_lead = request.env['crm.lead'].sudo().search([
                ('x_studio_lead_record_id', '!=', False)
            ], order='x_studio_lead_record_id desc', limit=1)
            
            if last_lead and last_lead.x_studio_lead_record_id:
                try:
                    # Convertir a entero y sumar 1
                    next_record_id = str(int(last_lead.x_studio_lead_record_id) + 1)
                except ValueError:
                    # Si no se puede convertir a entero, empezar desde 1
                    next_record_id = "1"
            else:
                # Si no hay leads con record_id, empezar desde 1
                next_record_id = "1"
            
            # --- OBTENER MES ACTUAL ---
            current_date = fields.Datetime.now()
            month_mapping = {
                1: 'january',
                2: 'february', 
                3: 'march',
                4: 'april',
                5: 'may',
                6: 'june',
                7: 'july',
                8: 'august',
                9: 'september',
                10: 'october',
                11: 'november',
                12: 'december'
            }
            current_month = month_mapping.get(current_date.month)
            
            # Datos del lead en CRM con campos x_studio
            lead_data = {
                'name': f'{nombre} {apellido}',
                'contact_name': f'{nombre} {apellido}',
                'email_from': email,
                'phone': telefono,
                'description': 'Lead desde Landing Page',
                'x_studio_renta': renta_text,
                'x_studio_ahorro': ahorro_text,
                'x_studio_situacion': situacion_text,
                
                # --- CAMPOS NUEVOS SOLICITADOS ---
                'x_studio_lead_apellido': apellido,
                'x_studio_lead_record_id': next_record_id,
                'x_studio_lead_fecha_creado': current_date,
                'x_studio_lead_mes_ingreso': current_month,
                'x_studio_lead_status': 'no_calificado' if es_no_calificado else 'registro',
                'x_studio_lead_perdido': 'si' if es_no_calificado else False,
                'x_studio_lead_ultima_modificacion_status': current_date,
            }
            
            if partner:
                lead_data['partner_id'] = partner.id
            
            # Asignar etapa correspondiente
            if es_no_calificado and stage_no_calificado:
                lead_data['stage_id'] = stage_no_calificado.id
            elif stage_qualified:
                lead_data['stage_id'] = stage_qualified.id
            
            # Origen/canal
            try:
                source_website = request.env.ref('crm.source_website', False)
                if source_website:
                    lead_data['source_id'] = source_website.id
            except:
                pass
            
            try:
                medium_website = request.env.ref('utm.utm_medium_website', False)
                if medium_website:
                    lead_data['medium_id'] = medium_website.id
            except:
                pass
            
            lead = request.env['crm.lead'].sudo().create(lead_data)
            _logger.info(f"Lead created successfully: {lead.id} for {email}")
            
            return {'success': True, 'lead_id': lead.id, 'message': 'Lead creado correctamente'}
            
        except Exception as e:
            _logger.error(f"Error creating lead: {str(e)}", exc_info=True)
            return {'success': False, 'error': f'Error interno del servidor: {str(e)}'}
