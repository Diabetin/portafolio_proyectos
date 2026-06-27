# -*- coding: utf-8 -*-
{
    'name': 'Boletas de Honorarios SimpleAPI',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localization',
    'summary': 'Integración con SimpleAPI para emisión automática de boletas de honorarios',
    'description': """
        Módulo para la creación y autodescarga de boletas de honorarios
        mediante integración con SimpleAPI Chile.
        
        Características:
        - Emisión automática de boletas de honorarios
        - Descarga automática de PDF
        - Integración directa con SII Chile
        - Gestión de estados y seguimiento
    """,
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'contacts', 'mail','web'],
    'data': [
        'views/boleta_honorarios_views.xml',
        'views/res_config_settings_view.xml',
        #'data/ir_cron_data.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            #'boleta_honorarios_simpleapi/static/src/js/preview_iframe.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
