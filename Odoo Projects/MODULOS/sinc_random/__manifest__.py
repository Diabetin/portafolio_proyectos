# -*- coding: utf-8 -*-
{
    'name': 'Conector RANDOM',
    'version': '1.0',
    'summary': 'Importa productos y pedidos desde ERP RANDOM',
    'description': """
        Este módulo permite importar productos y pedidos de venta desde una API externa y crear registros de productos en Odoo.
    """,
    'category': 'Inventory',
    'author': 'Sellside SPA',
    'license':'LGPL-3',
    'website': 'https://www.sellside.cl',
    'depends': ['base', 'stock', 'product', 'sale'],
    'data': [
        'views/import_product_views.xml',
        'views/import_price_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}