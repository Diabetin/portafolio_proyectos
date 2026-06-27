# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, http
from odoo.exceptions import UserError
import logging
import requests
import json
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class GeoCheckoutTask(models.Model):
    _inherit = 'project.task'

    # Campos Check-out
    checkout_latitude = fields.Float(string="Latitud Check-out", digits=(16, 6), help="Latitud registrada durante el check-out del usuario.")
    checkout_longitude = fields.Float(string="Longitud Check-out", digits=(16, 6), help="Longitud registrada durante el check-out del usuario.")
    checkout_datetime = fields.Datetime(string="Fecha Check-out", help="Fecha y hora en que se realizó el check-out.")
    checkout_distance_km = fields.Float(string="Distancia Check-out (km)", digits=(8, 2), help="Distancia en kilómetros entre la ubicación del check-out y la ubicación del cliente.")

    # Campos calculados para duración de la visita
    visit_duration = fields.Float(
        string="Duración de Visita (horas)",
        digits=(8, 2),
        compute="_compute_visit_duration",
        store=True,
        help="Tiempo transcurrido entre check-in y check-out en horas."
    )
    visit_duration_formatted = fields.Char(
        string="Duración Formateada",
        compute="_compute_visit_duration_formatted",
        help="Duración de la visita en formato HH:MM"
    )

    # Campos de seguridad del check-out
    checkout_ip = fields.Char(string="IP Check-out", help="Dirección IP desde la que se realizó el check-out")
    checkout_security_flags = fields.Text(string="Banderas Seguridad Check-out", help="Información de seguridad detectada durante el check-out")
    checkout_blocked = fields.Boolean(string="Check-out Bloqueado", default=False, help="Indica si el check-out fue bloqueado por razones de seguridad")
    checkout_block_reason = fields.Text(string="Razón Bloqueo Check-out", help="Motivo por el cual se bloqueó el check-out")

    @api.depends('checkin_datetime', 'checkout_datetime')
    def _compute_visit_duration(self):
        """Calcula la duración de la visita en horas"""
        for record in self:
            if record.checkin_datetime and record.checkout_datetime:
                delta = record.checkout_datetime - record.checkin_datetime
                record.visit_duration = delta.total_seconds() / 3600.0  # Convertir a horas
            else:
                record.visit_duration = 0.0

    @api.depends('visit_duration')
    def _compute_visit_duration_formatted(self):
        """Calcula la duración formateada en HH:MM"""
        for record in self:
            if record.visit_duration > 0:
                hours = int(record.visit_duration)
                minutes = int((record.visit_duration - hours) * 60)
                record.visit_duration_formatted = f"{hours:02d}:{minutes:02d}"
            else:
                record.visit_duration_formatted = "00:00"

    def _get_ip_info(self, user_ip):
        """Obtiene la información de la IP usando ip-api.com"""
        try:
            api_url = f"http://ip-api.com/json/{user_ip}?fields=status,message,country,countryCode,regionName,city,timezone,isp,org,as,proxy,hosting,mobile,query"
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'fail':
                raise Exception(f"IP-API error: {data.get('message')}")

            _logger.info(f"IP Info for {user_ip}: {json.dumps(data, indent=2)}")

            return {
                'success': True,
                'proxy': data.get('proxy', False),
                'ip_data': data
            }
        except Exception as e:
            _logger.error(f"❌ IP-API.com falló: {str(e)}")
            return {
                'success': False,
                'proxy': False,
                'error': str(e)
            }

    def get_checkout_location_button(self):
        """Inicia el proceso de check-out con geolocalización"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("No hay un cliente asociado a esta tarea. Por favor, asocia un cliente primero."))

        if not self.checkin_datetime:
            raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))

        if self.checkout_datetime:
            raise UserError(_("Ya se ha realizado el check-out para esta tarea."))

        provider = self.env['base.geocoder']._get_provider().tech_name
        _logger.info("Geolocalización realizada por el proveedor: %s", provider)
        self.partner_id.geo_localize()

        if not (self.partner_id.partner_latitude and self.partner_id.partner_longitude):
            raise UserError(_("El cliente no tiene coordenadas geográficas. Primero actualiza las coordenadas del cliente."))

        _logger.info("Botón 'Registrar Check-out' presionado para la tarea %s.", self.name)

        return {
            'type': 'ir.actions.client',
            'tag': 'get_geolocation_from_browser_checkout',
            'params': {
                'task_id': self.id,
            },
        }

    @api.model
    def get_checkout_location(self, task_id, location_data):
        """Procesa los datos de ubicación y realiza la validación de seguridad para el check-out."""
        _logger.info("=== INICIANDO CHECK-OUT PARA TAREA %s ===", task_id)

        task = self.browse(task_id)
        if not task.exists():
            raise UserError(_("Tarea no encontrada."))

        if not task.checkin_datetime:
            raise UserError(_("No se puede hacer check-out sin haber hecho check-in primero."))

        if task.checkout_datetime:
            raise UserError(_("Ya se ha realizado el check-out para esta tarea."))

        user_ip = location_data.get('ip')
        ip_info = {}

        if user_ip:
            ip_info = task._get_ip_info(user_ip)
            task.write({
                'checkout_ip': user_ip,
                'checkout_security_flags': json.dumps(ip_info.get('ip_data'), indent=2)
            })

            if ip_info.get('proxy'):
                block_reason = "Check-out bloqueado por conexión sospechosa: Proxy detectado"
                task.write({
                    'checkout_blocked': True,
                    'checkout_block_reason': block_reason
                })
                _logger.warning(f"🚫 {block_reason} - Usuario: {self.env.user.name}, Tarea: {task.name}, IP: {user_ip}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Proxy Detectado'),
                        'message': _("No se puede realizar el check-out porque se ha detectado el uso de un proxy. Por favor, desactive cualquier proxy o VPN e intente de nuevo."),
                        'type': 'danger',
                        'sticky': True,
                        'ip_data': ip_info.get('ip_data')
                    }
                }
        else:
            _logger.warning("No se pudo obtener la IP del cliente. El check-out continuará sin validación de seguridad.")
            task.write({
                'checkout_ip': 'unknown',
                'checkout_security_flags': "IP del cliente no disponible.",
            })

        latitude = location_data.get('latitude')
        longitude = location_data.get('longitude')
        accuracy = location_data.get("accuracy")
        distance_km = 0.0

        if not latitude or not longitude:
            raise UserError(_("No se pudo obtener la ubicación del dispositivo. Asegúrate de que los servicios de ubicación estén activados."))

        if accuracy and accuracy > 200:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("La precisión de la ubicación es demasiado baja (%.3f m). Intenta nuevamente.") % accuracy,
                    'type': 'danger',
                    'sticky': True
                }
            }

        partner = task.partner_id
        if partner and partner.partner_latitude and partner.partner_longitude:
            client_lat = partner.partner_latitude
            client_lon = partner.partner_longitude
            distance_km = task._haversine(client_lat, client_lon, latitude, longitude)

            if distance_km > 0.30:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("Estás fuera del rango permitido, a %.3f km del cliente.") % distance_km,
                        'type': 'danger',
                        'sticky': True,
                    }
                }

        checkout_time = fields.Datetime.now()
        task.write({
            'checkout_latitude': latitude,
            'checkout_longitude': longitude,
            'checkout_datetime': checkout_time,
            'checkout_distance_km': distance_km,
            'checkin_status': 'checked_out',
            'checkout_blocked': False,
        })

        _logger.info("✅ Check-out exitoso para la tarea %s. Duración de visita: %s", task.name, task.visit_duration_formatted)

        return {
            'distance_km': f"{distance_km:.3f}",
            'duration': task.visit_duration_formatted,
            'message': _("Check-out realizado con éxito. Duración: %s, Distancia: %.3f km.") % (task.visit_duration_formatted, distance_km),
            'ip_data': ip_info.get('ip_data')
        }

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Fórmula de Haversine para calcular distancia entre 2 coordenadas en km."""
        R = 6371.0
        lat1, lon1 = radians(float(lat1)), radians(float(lon1))
        lat2, lon2 = radians(float(lat2)), radians(float(lon2))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * asin(sqrt(a))
        return R * c