# -*- coding: utf-8 -*-
{
    'name': 'Website AP SSCL Landing',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['website', 'crm', 'web'],  # Make sure 'website' is in dependencies
    'data': [
        #'views/crm_campos.xml',
        'views/template_landing.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_ap_sscl/static/src/js/landing_form.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}