from odoo import models, fields

class CrmLead(models.Model):
    _inherit = "crm.lead"

    x_studio_renta = fields.Char(string="Renta")
    x_studio_ahorro = fields.Char(string="Capacidad de ahorro")
    x_studio_situacion = fields.Char(string="Situación financiera")