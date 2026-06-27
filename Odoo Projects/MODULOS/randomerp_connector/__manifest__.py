{
    "name": "Random ERP Connector",
    "version": "1.0.0",
    "category": "Integration",
    "summary": "Conector entre Random ERP y Odoo",
    "description": """
        Permite la conexión entre Odoo y el ERP Random
    """,
    "author": "Sellside Chile",
    "website": "https://www.sellside.cl",
    "license": "AGPL-3",
    "depends": ["base", "web", "contacts", "stock", "product"],
    "data": [
        "security/security.xml",
        "views/menu_action.xml",
        "views/random_settings.xml",
        "views/products_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "randomerp_connector/static/src/components/login/randomerp_connector.js",
            "randomerp_connector/static/src/components/login/randomerp_connector.xml",
            "randomerp_connector/static/src/components/login/randomerp_connector.scss",
            "randomerp_connector/static/src/components/home/randomerp_connector_home.xml",
            "randomerp_connector/static/src/components/home/randomerp_connector_home.js",
            "randomerp_connector/static/src/components/home/randomerp_connector_home.scss",
            "randomerp_connector/static/src/components/products/randomerp_connector_products.xml",
            "randomerp_connector/static/src/components/products/randomerp_connector_products.js",
            "randomerp_connector/static/src/components/products/randomerp_connector_products.scss",
        ]
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}