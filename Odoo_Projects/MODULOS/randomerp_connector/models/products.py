from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    x_studio_family = fields.Char(string="Familia")
    x_studio_subfamily = fields.Char(string="Sub-Familia")
    x_studio_stock = fields.Char(string="Stock")
    x_studio_bodega = fields.Char(string="Bodega")
