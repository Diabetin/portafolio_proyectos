from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = "crm.lead"
    
    # Campos específicos de Calendly
    x_studio_calendly_id_reunion = fields.Char(string="ID de la reunión en Calendly")
    x_studio_calendly_link_reunion = fields.Char(string="Link siguiente reunión")
    x_studio_calendly_evento_utilizado = fields.Char(string="Evento de calendly utilizado")
    x_studio_calendly_ip = fields.Char(string="IP")
    x_studio_calendly_fecha_siguiente = fields.Datetime(string="Fecha siguiente reunión")
    x_studio_calendly_fecha_ultima = fields.Datetime(string="Fecha última reunión")
    x_studio_calendly_fecha_ajustada = fields.Datetime(string="Fecha siguiente reunión ajustada")
    x_studio_calendly_fecha_agendada = fields.Datetime(string="Fecha en la que se agendó la siguiente reunión")
    x_studio_calendly_fecha_asignacion_llamado = fields.Datetime(string="Fecha asignación para llamado")
    x_studio_calendly_fecha_perdido = fields.Datetime(string="Fecha Perdido")
    x_studio_calendly_ejecutivo_llamaton = fields.Char(string="Ejecutivo llamatón")
    x_studio_calendly_nombre_apellido = fields.Char(string="Nombre y Apellido")
    x_studio_calendly_capacidad_inversion = fields.Char(string="Capacidad de inversión estimada en millones")
    
    # Campos de control de sincronización
    x_studio_calendly_last_sync = fields.Datetime(string="Última sincronización")
    x_studio_calendly_sync_status = fields.Selection([
        ('synced', 'Sincronizado'),
        ('pending', 'Pendiente'),
        ('error', 'Error'),
        ('manual', 'Manual')
    ], string="Estado de sincronización", default='manual')
    
    # Campos comunes entre ambos CSVs (Datos Lead)
    x_studio_lead_apellido = fields.Char(string="Apellido")
    x_studio_lead_calificacion_fluent = fields.Selection([
        ('tengo_cuenta_corriente_y_no_estoy_en_dicom', 'Tengo cuenta corriente y no estoy en DICOM'),
        ('no_tengo_cuenta_corriente', 'No tengo cuenta corriente'),
        ('estoy_en_dicom', 'Estoy en DICOM'),
        ('otros', 'Otros')
    ], string="Calificación Fluent Forms")
    x_studio_lead_capacidad_ahorro = fields.Selection([
        ('menos_100000', 'Menos de $100.000'),
        ('100001_200000', '$100.001 - $200.000'),
        ('200001_300000', '$200.001 - $300.000'),
        ('300001_400000', '$300.001 - $400.000'),
        ('mas_400001', 'Más de $400.001')
    ], string="Capacidad de ahorro mensual opciones")
    x_studio_lead_fecha_creado = fields.Datetime(string="Fecha de creación lead")
    x_studio_lead_ejecutiva_promesa = fields.Char(string="Ejecutiva de Promesa")
    x_studio_lead_ejecutivo_asignado = fields.Char(string="Ejecutivo Asignado")
    x_studio_lead_ejecutivos_ventas = fields.Char(string="Ejecutivos de Ventas")
    x_studio_lead_fecha_asignacion_ejecutivo = fields.Datetime(string="Fecha asignación ejecutivo para llamar")
    x_studio_lead_fecha_asignacion_call_sc = fields.Datetime(string="Fecha Asignación Call SC")
    x_studio_lead_nombre_ejecutivo_asignado = fields.Char(string="Nombre y Apellido Ejecutivo Asignado")
    x_studio_lead_perdido = fields.Selection([
        ('si', 'Sí'),
        ('no', 'No')
    ], string="Perdido", default='no')
    x_studio_lead_record_id = fields.Char(string="Record ID")
    x_studio_lead_socio_comercial = fields.Char(string="Socio Comercial Asignado")
    x_studio_lead_socios_comerciales = fields.Char(string="Socios comerciales")
    x_studio_lead_status = fields.Selection([
        ('registro', 'Registro'),
        ('reunion_agendada', 'Reunión agendada'),
        ('contactado', 'Contactado'),
        ('no_contactado', 'No contactado'),
        ('calificado', 'Calificado'),
        ('no_calificado', 'No calificado'),
        ('vendido', 'Vendido'),
        ('perdido', 'Perdido')
    ], string="Status Lead")
    x_studio_lead_sueldo_liquido = fields.Selection([
        ('menos_600000', 'Menos de $600.000'),
        ('600001_1000000', '$600.001 - $1.000.000'),
        ('1000001_1400000', '$1.000.001 - $1.400.000'),
        ('1400001_1800000', '$1.400.001 - $1.800.000'),
        ('1800001_2500000', '$1.800.001 - $2.500.000'),
        ('mas_2500001', 'Más de $2.500.001')
    ], string="Sueldo líquido opciones")
    x_studio_lead_team = fields.Char(string="Team")
    x_studio_lead_team_leader = fields.Char(string="Team Leader")
    x_studio_lead_team_leader_llamados = fields.Char(string="Team Leader Asignado Llamados")
    x_studio_lead_utm_campaign = fields.Char(string="UTM Campaign")
    x_studio_lead_utm_medium = fields.Char(string="UTM Medium")
    x_studio_lead_utm_source = fields.Char(string="UTM Source")
    x_studio_lead_utm_term = fields.Char(string="UTM Term")
    x_studio_lead_ultima_modificacion_status = fields.Datetime(string="Última Modificación de Status")
    x_studio_lead_ultima_modificacion_reunion = fields.Datetime(string="Última modificación siguiente reunión")
    
    # Campos adicionales específicos del CSV Meta/Form Native
    x_studio_lead_reagendar = fields.Char(string="Reagendar (Encuesta Post Reunión)")
    x_studio_lead_mes_ingreso = fields.Selection([
        ('january', 'Enero'),
        ('february', 'Febrero'),
        ('march', 'Marzo'),
        ('april', 'Abril'),
        ('may', 'Mayo'),
        ('june', 'Junio'),
        ('july', 'Julio'),
        ('august', 'Agosto'),
        ('september', 'Septiembre'),
        ('october', 'Octubre'),
        ('november', 'Noviembre'),
        ('december', 'Diciembre')
    ], string="Mes de ingreso del Lead")
    
    # CAMPOS ADICIONALES SOLICITADOS
    x_studio_renta = fields.Char(string="Renta")
    x_studio_ahorro = fields.Char(string="Capacidad de ahorro")
    x_studio_situacion = fields.Char(string="Situación financiera")
    
    @api.model
    def update_from_calendly_webhook(self, webhook_data):
        """Actualizar lead desde datos del webhook de Calendly"""
        try:
            payload = webhook_data.get('payload', {})
            event_type = webhook_data.get('event')
            
            # Buscar lead por email
            email = payload.get('email')
            if not email:
                _logger.warning('Webhook de Calendly sin email')
                return False
            
            lead = self.search([('email_from', '=', email)], limit=1)
            
            if event_type == 'invitee.created':
                return self._handle_invitee_created(lead, payload)
            elif event_type == 'invitee.canceled':
                return self._handle_invitee_canceled(lead, payload)
            
        except Exception as e:
            _logger.error(f'Error actualizando lead desde Calendly: {str(e)}')
            return False
    
    def _handle_invitee_created(self, lead, payload):
        """Manejar creación/agendamiento de invitado"""
        scheduled_event = payload.get('scheduled_event', {})
        
        # Crear lead si no existe
        if not lead:
            lead = self.create({
                'name': f'Agendamiento Calendly - {payload.get("name", "Sin nombre")}',
                'email_from': payload.get('email'),
                'partner_name': payload.get('name'),
                'phone': payload.get('phone', ''),
            })
        
        # Actualizar campos de Calendly
        update_vals = {
            'x_studio_calendly_id_reunion': payload.get('uuid'),
            'x_studio_calendly_evento_utilizado': scheduled_event.get('name'),
            'x_studio_calendly_fecha_siguiente': scheduled_event.get('start_time'),
            'x_studio_calendly_fecha_agendada': payload.get('created_at'),
            'x_studio_calendly_nombre_apellido': payload.get('name'),
            'x_studio_calendly_last_sync': fields.Datetime.now(),
            'x_studio_calendly_sync_status': 'synced',
            
            # Actualizar campos comunes de datos lead
            'x_studio_lead_status': 'reunion_agendada',
            'x_studio_lead_fecha_creado': payload.get('created_at'),
            'x_studio_lead_ultima_modificacion_status': fields.Datetime.now(),
        }
        
        # Extraer link de la reunión
        location = scheduled_event.get('location', {})
        if location and location.get('join_url'):
            update_vals['x_studio_calendly_link_reunion'] = location.get('join_url')
        
        lead.write(update_vals)
        
        _logger.info(f'Lead actualizado desde Calendly: {lead.name}')
        return lead
    
    def _handle_invitee_canceled(self, lead, payload):
        """Manejar cancelación de reunión"""
        if not lead:
            return False
        
        lead.write({
            'x_studio_calendly_fecha_perdido': payload.get('canceled_at'),
            'x_studio_calendly_sync_status': 'synced',
            'x_studio_calendly_last_sync': fields.Datetime.now(),
            'x_studio_lead_status': 'perdido',
            'x_studio_lead_perdido': 'si',
            'x_studio_lead_ultima_modificacion_status': fields.Datetime.now(),
        })
        
        # Agregar nota de cancelación
        lead.message_post(
            body=f"Reunión de Calendly cancelada el {payload.get('canceled_at')}",
            message_type='comment'
        )
        
        return lead
