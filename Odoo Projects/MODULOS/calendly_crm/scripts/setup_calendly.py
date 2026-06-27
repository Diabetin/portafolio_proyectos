#!/usr/bin/env python3
"""
Script para configurar automáticamente tu token de Calendly
"""

import requests
import json

class CalendlyConfig:
    def __init__(self):
        # Tu token ya proporcionado
        self.access_token = "eyJraWQiOiIxY2UxZTEzNjE3ZGNmNzY2YjNjZWJjY2Y4ZGM1YmFmYThhNjVlNjg0MDIzZjdjMzJiZTgzNDliMjM4MDEzNWI0IiwidHlwIjoiUEFUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJodHRwczovL2F1dGguY2FsZW5kbHkuY29tIiwiaWF0IjoxNzU4MDQ3NTg5LCJqdGkiOiIxYzg4MTEyNy05OWQ1LTQyY2EtYTcwMC0yMDljZDZiOTJmMjciLCJ1c2VyX3V1aWQiOiI3MTI1N2ExZS01MzAyLTQ4MTAtODU2My04NTVkN2JmZWU0MTYifQ.VLC2q7SAr-KqQw-pIMURUPYGxjyNdaU08_tHOVQuZ8r_vA4L-wOTeEBlj19HFcQDFifgtOBfduJL9cDH-45QKg"
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def test_connection(self):
        """Probar conexión con API de Calendly"""
        print("🔍 Probando conexión con Calendly API...")
        
        try:
            response = requests.get(
                'https://api.calendly.com/users/me',
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print("✅ Conexión exitosa!")
                print(f"Usuario: {user_data['resource']['name']}")
                print(f"Email: {user_data['resource']['email']}")
                print(f"Organization: {user_data['resource']['current_organization']}")
                return user_data
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {str(e)}")
            return None
    
    def get_organization_info(self, user_data):
        """Obtener información de la organización"""
        org_uri = user_data['resource']['current_organization']
        
        print(f"\n📋 Obteniendo información de la organización...")
        
        try:
            response = requests.get(
                org_uri,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                org_data = response.json()
                print("✅ Información de organización obtenida!")
                print(f"Nombre: {org_data['resource']['name']}")
                print(f"URI: {org_data['resource']['uri']}")
                return org_data
            else:
                print(f"❌ Error obteniendo organización: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {str(e)}")
            return None
    
    def list_event_types(self, user_data):
        """Listar tipos de eventos disponibles"""
        user_uri = user_data['resource']['uri']
        
        print(f"\n📅 Obteniendo tipos de eventos...")
        
        try:
            response = requests.get(
                'https://api.calendly.com/event_types',
                headers=self.headers,
                params={'user': user_uri},
                timeout=10
            )
            
            if response.status_code == 200:
                events_data = response.json()
                print("✅ Tipos de eventos obtenidos!")
                
                for event in events_data['collection']:
                    print(f"- {event['name']} ({event['duration']} min)")
                    print(f"  URL: {event['scheduling_url']}")
                    print(f"  Slug: {event['slug']}")
                    print()
                
                return events_data
            else:
                print(f"❌ Error obteniendo eventos: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {str(e)}")
            return None
    
    def create_webhook(self, org_uri, webhook_url):
        """Crear webhook subscription"""
        print(f"\n🔗 Creando webhook para: {webhook_url}")
        
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
                headers=self.headers,
                json=webhook_data,
                timeout=10
            )
            
            if response.status_code == 201:
                webhook_info = response.json()
                print("✅ Webhook creado exitosamente!")
                print(f"ID: {webhook_info['resource']['uri']}")
                print(f"Estado: {webhook_info['resource']['state']}")
                print(f"URL: {webhook_info['resource']['callback_url']}")
                return webhook_info
            else:
                print(f"❌ Error creando webhook: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ Excepción: {str(e)}")
            return None
    
    def generate_odoo_config(self, user_data, org_data):
        """Generar configuración para Odoo"""
        print("\n🔧 CONFIGURACIÓN PARA ODOO:")
        print("=" * 50)
        
        config_xml = f"""
<record id="calendly_access_token" model="ir.config_parameter">
    <field name="key">calendly.access.token</field>
    <field name="value">{self.access_token}</field>
</record>

<record id="calendly_organization_uri" model="ir.config_parameter">
    <field name="key">calendly.organization.uri</field>
    <field name="value">{org_data['resource']['uri']}</field>
</record>

<record id="calendly_user_uri" model="ir.config_parameter">
    <field name="key">calendly.user.uri</field>
    <field name="value">{user_data['resource']['uri']}</field>
</record>
        """
        
        print(config_xml)
        
        # También generar comando para consola Odoo
        print("\n🐍 COMANDOS PARA CONSOLA DE ODOO:")
        print("=" * 50)
        
        console_commands = f"""
# Configurar parámetros en consola de Odoo
env['ir.config_parameter'].set_param('calendly.access.token', '{self.access_token}')
env['ir.config_parameter'].set_param('calendly.organization.uri', '{org_data['resource']['uri']}')
env['ir.config_parameter'].set_param('calendly.user.uri', '{user_data['resource']['uri']}')
env['ir.config_parameter'].set_param('calendly.sync.enabled', 'True')

# Probar conexión
api_service = env['calendly.api']
user_info = api_service.get_user_info()
print("Conexión exitosa:", user_info is not None)
        """
        
        print(console_commands)
    
    def run_full_setup(self):
        """Ejecutar configuración completa"""
        print("🚀 CONFIGURACIÓN COMPLETA DE CALENDLY")
        print("=" * 50)
        
        # 1. Probar conexión
        user_data = self.test_connection()
        if not user_data:
            return False
        
        # 2. Obtener información de organización
        org_data = self.get_organization_info(user_data)
        if not org_data:
            return False
        
        # 3. Listar tipos de eventos
        events_data = self.list_event_types(user_data)
        
        # 4. Generar configuración para Odoo
        self.generate_odoo_config(user_data, org_data)
        
        # 5. Preguntar por webhook
        webhook_url = input("\n¿Deseas crear un webhook? Ingresa la URL (Enter para saltar): ").strip()
        if webhook_url:
            self.create_webhook(org_data['resource']['uri'], webhook_url)
        
        print("\n✅ ¡CONFIGURACIÓN COMPLETADA!")
        print("\nPróximos pasos:")
        print("1. Copia la configuración XML a tu archivo data/calendly_config.xml")
        print("2. O ejecuta los comandos en la consola de Odoo")
        print("3. Reinicia el servidor Odoo")
        print("4. Prueba la integración")
        
        return True

# Ejecutar configuración
if __name__ == "__main__":
    config = CalendlyConfig()
    config.run_full_setup()
