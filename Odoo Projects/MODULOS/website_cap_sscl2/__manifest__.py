# -*- coding: utf-8 -*-
{
    'name': 'Website CAP SSCL 2',
    'version': '1.0',
    'summary': 'Landing page para captura de leads y contactos',
    'description': """
Módulo de Website para CAP SSCL 2.
Permite mostrar una landing personalizada en Odoo Website
y registrar automáticamente leads y contactos en CRM.
""",
    'author': 'Alexander Acosta',
    'website': 'sellside.cl',
    'category': 'Website',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'crm',
        'web',
    ],
    'data': [
        'views/template_landing2.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_cap_sscl2/static/src/js/landing_form2.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

