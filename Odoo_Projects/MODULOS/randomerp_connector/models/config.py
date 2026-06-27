from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    randomerp_login_method = fields.Selection(
        selection=[
            ('token', "Token"),
            ('userpass', "Usuario/Contraseña"),
        ],
        string="Login",
        config_parameter='randomerp_connector.login_method',
        default='userpass'
    )

    randomerp_token = fields.Char(
        string="Token",
        config_parameter='randomerp_connector.token'
    )

    randomerp_api_url = fields.Char(
        string="API URL",
        config_parameter='randomerp_connector.api_url',
    )
