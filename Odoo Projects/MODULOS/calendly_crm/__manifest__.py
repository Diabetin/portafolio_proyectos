{
    'name': 'Integración Calendly Bidireccional',
    'version': '1.0',
    'summary': 'Integración bidireccional en tiempo real con Calendly',
    'license': 'LGPL-3',
    'description': """
        Módulo completo para integración bidireccional con Calendly:
        - Recepción de webhooks en tiempo real
        - Actualización automática de campos personalizados
        - Sincronización bidireccional de datos
        - API para envío de datos a Calendly
    """,
    'author': 'Tu Empresa',
    'depends': ['crm', 'mail'],
    'data': [
        'data/calendly_config.xml',
        'views/crm_campos_calendly.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
