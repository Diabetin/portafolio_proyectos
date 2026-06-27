from odoo import http
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)

class RandomERPController(http.Controller):

    @http.route('/randomerp_connector/save_credentials', type='json', auth='public', methods=['POST'])
    def save_credentials(self, username, password, ttl=3600):
        try:
            config = request.env['ir.config_parameter'].sudo()
            base_url = config.get_param('randomerp_connector.api_url')
            if not base_url:
                return {
                    'status': 'error',
                    'message': 'API URL no configurada. Por favor, configure la URL de la API en la configuración del módulo.'
                }
            if config.get_param('randomerp_connector.login_method') == 'userpass':
                # 1️⃣ Realizar login con usuario y contraseña
                login_url = f"{base_url}/login"
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
                payload = {
                    'username': username,
                    'password': password,
                    'ttl': ttl
                }

                response = requests.post(login_url, headers=headers, data=payload)

                if response.status_code != 200:
                    return {
                        'status': 'error',
                        'message': f'Error en login API externo: {response.text}'
                    }

                # 2️⃣ Obtener datos del login
                login_data = response.json()
                token = login_data.get('token')
                if not token:
                    return {
                        'status': 'error',
                        'message': 'No se recibió token del API externo'
                    }
                config.set_param('randomerp_connector.username', username)
                config.set_param('randomerp_connector.password', password)
                config.set_param('randomerp_connector.token', token)
            elif config.get_param('randomerp_connector.login_method') == 'token':
                token = config.get_param('randomerp_connector.token')
                config.set_param('randomerp_connector.token', token)

            # Asignar grupo al usuario
            user = request.env.user
            group = request.env.ref('randomerp_connector.group_randomerp_logged')
            if group and group.id not in user.groups_id.ids:
                user.sudo().write({'groups_id': [(4, group.id)]})

            return {
                'status': 'ok',
                'message': 'Credenciales y token guardados correctamente',
                'token': token
            }
        except Exception as e:
            _logger.exception("Error guardando credenciales y token")
            return {
                'status': 'error',
                'message': str(e)
            }
        
    @http.route('/randomerp_connector/session_active', type='json', auth='user')
    def session_active(self):
        # Esto solo devuelve si la sesión de módulo está activa
        session_flag = request.env['ir.config_parameter'].sudo().get_param('randomerp_connector.session_active')
        if session_flag == 'true':
            return {'status': 'ok'}
        return {'status': 'no_session'}

    @http.route('/randomerp_connector/set_session', type='json', auth='user', methods=['POST'])
    def set_session(self):
        # Se llama después de login exitoso
        request.env['ir.config_parameter'].sudo().set_param('randomerp_connector.session_active', 'true')
        return {'status': 'ok'}
    
    @http.route('/randomerp_connector/importar_productos_rpc', type='json', auth='user', methods=['POST'])
    def importar_productos_rpc(self, incluir_ocultos=False):
        try:
            picking_model = request.env['stock.picking.type'].sudo()
            result = picking_model.importar_productos_desde_api(incluir_ocultos=incluir_ocultos)
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    
    @http.route('/randomerp_connector/importar_precios_rpc', type='json', auth='user', methods=['POST'])
    def importar_precios_rpc(self):
        try:
            picking_model = request.env['stock.picking.type'].sudo()
            result = picking_model.importar_precios_desde_api()
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        
    @http.route('/randomerp_connector/logout', type='http', auth='user', methods=['GET'])
    def logout(self, **kwargs):
        request.env['ir.config_parameter'].sudo().set_param('randomerp_connector.session_active', 'false')
        request.env.user.sudo().write({'groups_id': [(3, request.env.ref('randomerp_connector.group_randomerp_logged').id)]})
        return request.redirect('/')
    
    @http.route('/randomerp_connector/get_config_params', type='json', auth='user')
    def get_config_params(self):
        return {
            'randomerp_login_method': request.env['ir.config_parameter'].sudo().get_param('randomerp_connector.login_method', 'userpass')
        }
