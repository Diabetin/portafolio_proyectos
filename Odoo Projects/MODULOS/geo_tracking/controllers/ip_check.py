from odoo import http
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)

class IPCheckController(http.Controller):

    def _get_ip_info(self, user_ip):
        """Obtiene la información de la IP usando ip-api.com"""
        try:
            api_url = f"http://ip-api.com/json/{user_ip}?fields=status,message,country,countryCode,regionName,city,timezone,isp,org,as,proxy,hosting,mobile,query"
            response = requests.get(api_url, timeout=8)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'fail':
                raise Exception(f"IP-API error: {data.get('message')}")

            return {
                'provider': 'ip-api.com',
                'ip': data.get('query'),
                'country': data.get('country'),
                'region': data.get('regionName'),
                'city': data.get('city'),
                'timezone': data.get('timezone'),
                'isp': data.get('isp'),
                'org': data.get('org'),
                'proxy': data.get('proxy', False),
                'hosting': data.get('hosting', False),
                'mobile': data.get('mobile', False),
                'success': True
            }
        except Exception as e:
            _logger.error(f"❌ IP-API.com falló: {str(e)}")
            return {
                'success': False,
                'proxy': False,
                'error': str(e)
            }

    @http.route('/check/ipdetective', type='json', auth="user", methods=['POST'])
    def check_ip_endpoint(self, **post):
        user_ip = post.get('client_ip')

        if not user_ip:
            if hasattr(request, 'httprequest'):
                user_ip = request.httprequest.environ.get('HTTP_X_FORWARDED_FOR')
                if user_ip and ',' in user_ip:
                    user_ip = user_ip.split(',')[0].strip()
                if not user_ip:
                    user_ip = request.httprequest.environ.get('HTTP_X_REAL_IP')
                if not user_ip:
                    user_ip = request.httprequest.remote_addr

        if not user_ip or user_ip == "unknown":
            _logger.warning("❗ No se pudo detectar la IP del usuario.")
            return {'success': False, 'error': 'No se pudo detectar la IP'}

        ip_info = self._get_ip_info(user_ip)

        return {
            'success': ip_info.get('success'),
            'ip': user_ip,
            'proxy_detectado': ip_info.get('proxy', False),
            'ip_data': ip_info
        }