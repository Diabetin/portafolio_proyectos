{
    'name': 'Geo Tracking',
    'summary': 'Registro de check-in y check-out georreferenciado para vendedores en visitas a clientes',
    'description': """
Este módulo permite a los vendedores registrar un check-in georreferenciado directamente desde su dispositivo móvil o navegador 
al visitar a un cliente. La ubicación capturada se almacena junto a la tarea a realizar, permitiendo verificar que 
la visita se realizó en el lugar correcto. Ideal para equipos de ventas en terreno.

Funcionalidades:
- Check-in y Check-out desde formulario de tareas
- Check-in y Check-out desde vista de mapa
""",
    'author': 'Sellside SPA*',
    'website': 'https://www.sellside.cl',
    'category': 'Services/Field Service',
    'version': '0.2',
    'license': 'LGPL-3',
    'depends': [
        'base', 'project', 'industry_fsm', 'web', 'web_map', 'industry_fsm_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/geo_checkin_view.xml',
        #'views/worksheet_checkin_template.xml',
        #'views/worksheet_checkin_view.xml', 
        'views/geo_checkout_view.xml',
        #'views/worksheet_checkout_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'web_map/static/src/map_view/map_renderer.js',
            'geo_tracking/static/src/js/geo_checkin.js',
            'geo_tracking/static/src/js/geo_checkout.js',
            'geo_tracking/static/src/js/ip_check.js',
            'geo_tracking/static/src/map_view/map_renderer.js',
            'geo_tracking/static/src/map_view/map_renderer.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}