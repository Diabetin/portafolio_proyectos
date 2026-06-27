from odoo import models, fields, api, _
from odoo.exceptions import UserError

class WorksheetTemplateCheckout(models.Model):
    _inherit = 'worksheet.template'
    
    # Campos de duración de visita (relacionados con la tarea)
    visit_duration = fields.Float(
        related='task_id.visit_duration',
        readonly=True,
        string="Duración de Visita (horas)"
    )
    visit_duration_formatted = fields.Char(
        related='task_id.visit_duration_formatted',
        readonly=True,
        string="Duración Formateada"
    )
    
    # Estado del check-in/out (relacionado con la tarea)
    checkin_status = fields.Selection(
        related='task_id.checkin_status',
        readonly=True,
        string="Estado Check-in/out"
    )

    def action_checkout(self):
        """Acción para realizar check-out desde worksheet"""
        for record in self:
            if not record.task_id:
                raise UserError(_("No hay tarea asignada para hacer check-out."))
            
            if not record.task_id.checkin_datetime:
                raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))
            
            if record.task_id.checkout_datetime:
                raise UserError(_("Ya se ha realizado el check-out para esta tarea."))
            
            # Llamar al método de la tarea para obtener la ubicación
            return record.task_id.get_checkout_location_button()

    def get_checkin_checkout_summary(self):
        """Retorna un resumen del estado de check-in/out"""
        self.ensure_one()
        
        if not self.task_id:
            return "No hay tarea asignada"
        
        task = self.task_id
        
        if task.checkin_status == 'none':
            return "Sin check-in"
        elif task.checkin_status == 'checked_in':
            return f"Check-in realizado - Esperando check-out"
        elif task.checkin_status == 'checked_out':
            return f"Visita completada - Duración: {task.visit_duration_formatted}"
        
        return "Estado desconocido"

    def get_checkout_summary(self):
        """Retorna un resumen específico del check-out"""
        self.ensure_one()
        
        if not self.task_id:
            return "No hay tarea asignada"
        
        task = self.task_id
        
        if task.checkin_status == 'checked_out' and task.checkout_datetime:
            return f"Check-out realizado - Distancia: {task.checkout_distance_km:.3f} km - Duración: {task.visit_duration_formatted}"
        elif task.checkin_status == 'checked_in':
            return "Check-out pendiente"
        else:
            return "Sin check-in realizado"