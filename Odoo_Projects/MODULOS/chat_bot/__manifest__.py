# -*- coding: utf-8 -*-
{
    'name': 'Bot Chat IA para Discuss',
    'version': '1.0.0',
    'category': 'Discuss',
    'summary': 'Canal de chat con integración de IA Gemini',
    'description': "Modulo IA",
    'author': 'Alex',
    'depends': ['base', 'mail','project'],
    'data': [
        'security/ir.model.access.csv',
        'views/channel_views.xml',
        'data/bot_chat_channel_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
