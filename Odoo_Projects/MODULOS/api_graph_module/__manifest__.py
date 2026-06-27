# -*- coding: utf-8 -*-
{
    'name': "Meta Leads Importer",
    'summary': "Importador de Leads desde Meta Graph API",
    'description': "Módulo para importar leads desde Meta Lead Ads hacia CRM",
    'author': "Tu Empresa",
    'website': "https://tu-dominio.com",
    'category': 'Marketing',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': ['base', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/import_log_views.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
}
