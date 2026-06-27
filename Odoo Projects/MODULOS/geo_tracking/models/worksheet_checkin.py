from odoo import models, fields, api
from odoo.exceptions import UserError

class ProjectTaskWorksheet(models.Model):
    """Extensión de la hoja de trabajo de Field Service para check-in georreferenciado"""
    _inherit = 'project.task'
    
    # Campos para check-in georreferenciado
    checkin_latitude = fields.Float(
        string="Latitud Check-in",
        help="Latitud donde se realizó el check-in"
    )
    checkin_longitude = fields.Float(
        string="Longitud Check-in", 
        help="Longitud donde se realizó el check-in"
    )
    checkin_datetime = fields.Datetime(
        string="Fecha y Hora Check-in",
        help="Momento exacto del check-in"
    )
    checkin_distance_km = fields.Float(
        string="Distancia al Cliente (km)",
        help="Distancia calculada entre check-in y ubicación del cliente"
    )
    
    @api.depends('checkin_latitude', 'checkin_longitude')
    def _compute_has_checkin(self):
        """Computed field para saber si ya se hizo check-in"""
        for record in self:
            record.has_checkin = bool(record.checkin_latitude and record.checkin_longitude)
    
    has_checkin = fields.Boolean(
        string="Tiene Check-in",
        compute='_compute_has_checkin',
        store=True
    )
    
    def action_checkin(self):
        """Método para realizar check-in georreferenciado"""
        self.ensure_one()
        
        # Validar que sea una tarea de Field Service
        if not self.is_fsm:
            raise UserError("El check-in solo está disponible para tareas de Field Service")
            
        # Validar que no se haya hecho check-in previamente
        if self.has_checkin:
            raise UserError("Ya se ha realizado el check-in para esta tarea")
        
        # Aquí implementarías la lógica real para obtener coordenadas
        # Por ahora usamos coordenadas de ejemplo
        self.write({
            'checkin_latitude': 40.4168,  # Reemplazar con coordenadas reales
            'checkin_longitude': -3.7038,  # Reemplazar con coordenadas reales
            'checkin_datetime': fields.Datetime.now(),
            'checkin_distance_km': self._calculate_distance_to_partner(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Check-in realizado',
                'message': f'Check-in registrado correctamente para la tarea: {self.name}',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _calculate_distance_to_partner(self):
        """Calcula la distancia entre el check-in y la ubicación del cliente"""
        # Implementar cálculo real de distancia usando coordenadas del partner
        # Por ahora retorna 0.0
        return 0.0
    
    def action_reset_checkin(self):
        """Método para resetear el check-in (útil para testing)"""
        self.ensure_one()
        self.write({
            'checkin_latitude': False,
            'checkin_longitude': False,
            'checkin_datetime': False,
            'checkin_distance_km': 0.0,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Check-in reseteado',
                'message': 'Los datos de check-in han sido eliminados',
                'type': 'info',
            }
        }