from odoo import models, fields, api, _
from odoo.exceptions import UserError

class WorksheetTemplateCheckin(models.Model):
    _inherit = 'worksheet.template'

    task_id = fields.Many2one('project.task', string="Tarea")

    # Campos Check-in relacionados (solo lectura desde la tarea)
    checkin_latitude = fields.Float(
        related='task_id.checkin_latitude',
        readonly=True,
        string="Latitud Check-in"
    )
    checkin_longitude = fields.Float(
        related='task_id.checkin_longitude',
        readonly=True,
        string="Longitud Check-in"
    )
    checkin_datetime = fields.Datetime(
        related='task_id.checkin_datetime',
        readonly=True,
        string="Fecha Check-in"
    )
    checkin_distance_km = fields.Float(
        related='task_id.checkin_distance_km',
        readonly=True,
        string="Distancia al Cliente (km)"
    )

    # Campos Check-out relacionados (solo lectura desde la tarea)
    checkout_latitude = fields.Float(
        related='task_id.checkout_latitude',
        readonly=True,
        string="Latitud Check-out"
    )
    checkout_longitude = fields.Float(
        related='task_id.checkout_longitude',
        readonly=True,
        string="Longitud Check-out"
    )
    checkout_datetime = fields.Datetime(
        related='task_id.checkout_datetime',
        readonly=True,
        string="Fecha Check-out"
    )
    checkout_distance_km = fields.Float(
        related='task_id.checkout_distance_km',
        readonly=True,
        string="Distancia Check-out (km)"
    )

    # Campos relacionados del cliente
    partner_latitude = fields.Float(
        related='task_id.partner_latitude',
        readonly=True,
        string="Latitud Cliente"
    )
    partner_longitude = fields.Float(
        related='task_id.partner_longitude',
        readonly=True,
        string="Longitud Cliente"
    )

    # Estado del check-in/out
    checkin_status = fields.Selection(
        related='task_id.checkin_status',
        readonly=True,
        string="Estado Check-in/out"
    )

    def action_checkin(self):
        """Acción para realizar check-in desde worksheet"""
        for record in self:
            if not record.task_id:
                raise UserError(_("No hay tarea asignada para hacer check-in."))
            
            if record.task_id.checkin_datetime:
                raise UserError(_("Ya se ha realizado el check-in para esta tarea."))
            
            # Llamar al método de la tarea para obtener la ubicación
            return record.task_id.get_location_button()

    def get_checkin_summary(self):
        """Retorna un resumen del estado de check-in"""
        self.ensure_one()
        
        if not self.task_id:
            return "No hay tarea asignada"
        
        task = self.task_id
        
        if task.checkin_status == 'none':
            return "Sin check-in"
        elif task.checkin_status == 'checked_in':
            return f"Check-in realizado - Distancia: {task.checkin_distance_km:.3f} km"
        elif task.checkin_status == 'checked_out':
            return f"Check-in completado - Distancia: {task.checkin_distance_km:.3f} km"
        
        return "Estado desconocido"