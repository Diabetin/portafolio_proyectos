import json
import hmac
import hashlib
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class CalendlyWebhookController(http.Controller):
    
    @http.route(
        '/calendly/webhook', type='http', auth='none', methods=['POST'], csrf=False
    )
    def receive_calendly_webhook(self):
        """Endpoint para recibir webhooks de Calendly"""
        try:
            payload = request.httprequest.get_data()
            headers = dict(request.httprequest.headers)
            
            _logger.info(f"Webhook de Calendly recibido. Headers: {headers}")
            
            if not self._validate_webhook_signature(payload, headers):
                _logger.warning("Firma de webhook inválida")
                return request.make_response("Unauthorized", 401)
            
            try:
                webhook_data = json.loads(payload.decode('utf-8'))
                _logger.info(f"Datos del webhook: {webhook_data}")
            except json.JSONDecodeError as e:
                _logger.error(f"Error decodificando JSON: {str(e)}")
                return request.make_response("Bad Request", 400)
            
            sync_enabled = request.env['ir.config_parameter'].sudo().get_param(
                'calendly.sync.enabled', 'False'
            )
            
            if sync_enabled.lower() != 'true':
                _logger.info("Sincronización de Calendly deshabilitada")
                return request.make_response("Sync Disabled", 200)
            
            result = self._process_webhook(webhook_data)
            
            if result:
                _logger.info("Webhook procesado exitosamente")
                return request.make_response("OK", 200)
            else:
                _logger.error("Error procesando webhook")
                return request.make_response("Internal Server Error", 500)
                
        except Exception as e:
            _logger.error(f"Excepción procesando webhook de Calendly: {str(e)}")
            return request.make_response("Internal Server Error", 500)
    
    def _validate_webhook_signature(self, payload, headers):
        """Validar firma del webhook para seguridad"""
        signature_header = headers.get('Calendly-Webhook-Signature')
        if not signature_header:
            _logger.warning("No se encontró header de firma")
            return False
            
        webhook_secret = request.env['ir.config_parameter'].sudo().get_param(
            'calendly.webhook.secret'
        )
        if not webhook_secret:
            _logger.warning("Webhook secret no configurado")
            return False
        
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        expected_header = f'sha256={expected_signature}'
        is_valid = hmac.compare_digest(expected_header, signature_header)
        
        if not is_valid:
            _logger.warning(f"Firma inválida. Esperada: {expected_header}, Recibida: {signature_header}")
        
        return is_valid
    
    def _process_webhook(self, webhook_data):
        """Procesar datos del webhook"""
        try:
            event_type = webhook_data.get("event")
            _logger.info(f"Procesando evento: {event_type}")
            
            Lead = request.env['crm.lead'].sudo()
            result = Lead.update_from_calendly_webhook(webhook_data)
            return result is not False
            
        except Exception as e:
            _logger.error(f"Error en _process_webhook: {str(e)}")
            return False
    
    @http.route('/calendly/test', type='http', auth='user', methods=['GET'])
    def test_calendly_connection(self):
        """Endpoint de prueba para verificar conexión con Calendly"""
        try:
            api_service = request.env['calendly.api']
            user_info = api_service.get_user_info()
            
            if user_info:
                return request.make_response(
                    json.dumps(user_info, indent=2),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                return request.make_response('Error conectando con Calendly', 500)
                
        except Exception as e:
            return request.make_response(f'Error: {str(e)}', 500)
