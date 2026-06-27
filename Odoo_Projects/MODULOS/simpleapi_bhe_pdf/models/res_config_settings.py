# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    simpleapi_bhe_api_key = fields.Char(
        string='SimpleAPI Key',
        config_parameter='simpleapi_bhe_pdf.api_key',
        default='4648-N330-6392-2590-9354',
        help='API Key de SimpleAPI utilizada para autenticar las llamadas'
    )
    simpleapi_bhe_base_url = fields.Char(
        string='Base URL',
        config_parameter='simpleapi_bhe_pdf.base_url',
        default='https://servicios.simpleapi.cl/api',
        help='URL base de SimpleAPI (REST)'
    )
    simpleapi_bhe_timeout = fields.Integer(
        string='Timeout (s)',
        config_parameter='simpleapi_bhe_pdf.timeout',
        default=30,
        help='Tiempo límite para peticiones HTTP'
    )
