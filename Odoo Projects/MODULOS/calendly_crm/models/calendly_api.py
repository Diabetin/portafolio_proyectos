from odoo import models, api
import requests
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class CalendlyAPI(models.AbstractModel):
    _name = 'calendly.api'
    _description = 'Servicio API de Calendly'
    
    @api.model
    def _get_headers(self):
        """Obtener headers para API de Calendly"""
        token = self.env['ir.config_parameter'].sudo().get_param('calendly.access.token')
        if not token:
            raise UserError('Token de Calendly no configurado')
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    @api.model
    def _get_organization_uri(self):
        """Obtener URI de la organización"""
        org_uri = self.env['ir.config_parameter'].sudo().get_param('calendly.organization.uri')
        if not org_uri:
            # Si no está configurado, obtenerlo automáticamente
            user_info = self.get_user_info()
            if user_info and 'resource' in user_info:
                org_uri = user_info['resource']['current_organization']
                # Guardarlo para uso futuro
                self.env['ir.config_parameter'].sudo().set_param('calendly.organization.uri', org_uri)
                return org_uri
            else:
                raise UserError('No se pudo obtener URI de organización de Calendly')
        return org_uri
    
    @api.model
    def get_user_info(self):
        """Obtener información del usuario actual"""
        headers = self._get_headers()
        
        try:
            response = requests.get(
                'https://api.calendly.com/users/me',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f'Error obteniendo usuario: {response.status_code} - {response.text}')
                return None
                
        except Exception as e:
            _logger.error(f'Excepción en get_user_info: {str(e)}')
            return None
    
    @api.model
    def create_webhook_subscription(self, webhook_url=None):
        """Crear suscripción de webhook"""
        headers = self._get_headers()
        org_uri = self._get_organization_uri()
        
        if not webhook_url:
            webhook_url = self.env['ir.config_parameter'].sudo().get_param('calendly.webhook.url')
            if not webhook_url:
                raise UserError('URL de webhook no configurada')
        
        webhook_data = {
            "url": webhook_url,
            "events": [
                "invitee.created",
                "invitee.canceled"
            ],
            "organization": org_uri,
            "scope": "organization"
        }
        
        try:
            response = requests.post(
                'https://api.calendly.com/webhook_subscriptions',
                headers=headers,
                json=webhook_data,
                timeout=10
            )
            
            if response.status_code == 201:
                webhook_info = response.json()
                _logger.info(f'Webhook creado exitosamente: {webhook_info["resource"]["uri"]}')
                return webhook_info
            else:
                _logger.error(f'Error creando webhook: {response.status_code} - {response.text}')
                return None
                
        except Exception as e:
            _logger.error(f'Excepción creando webhook: {str(e)}')
            return None
    
    @api.model
    def list_webhook_subscriptions(self):
        """Listar webhooks existentes"""
        headers = self._get_headers()
        org_uri = self._get_organization_uri()
        
        params = {
            'organization': org_uri,
            'scope': 'organization'
        }
        
        try:
            response = requests.get(
                'https://api.calendly.com/webhook_subscriptions',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f'Error listando webhooks: {response.status_code}')
                return None
                
        except Exception as e:
            _logger.error(f'Excepción listando webhooks: {str(e)}')
            return None
    
    @api.model
    def test_connection(self):
        """Probar conexión con Calendly"""
        user_info = self.get_user_info()
        if user_info and 'resource' in user_info:
            return {
                'status': 'success',
                'user_name': user_info['resource']['name'],
                'user_email': user_info['resource']['email'],
                'organization': user_info['resource']['current_organization']
            }
        else:
            return {
                'status': 'error',
                'message': 'No se pudo conectar con Calendly'
            }
