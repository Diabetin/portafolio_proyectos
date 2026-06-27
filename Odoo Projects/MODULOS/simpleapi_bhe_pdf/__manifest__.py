# -*- coding: utf-8 -*-
{
    'name': 'SimpleAPI BHE PDF',
    'version': '18.0.1.0',
    'summary': 'Visor y descarga de PDFs de Boletas de Honorarios (SII) vía SimpleAPI',
    'category': 'Tools',
    'author': 'Tu Empresa',
    'license': 'LGPL-3',
    'depends': ['base','mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/simpleapi_bhe_pdf_views.xml',
        'views/res_config_settings.xml',
    ],
    'application': True,
    'installable': True,
}
