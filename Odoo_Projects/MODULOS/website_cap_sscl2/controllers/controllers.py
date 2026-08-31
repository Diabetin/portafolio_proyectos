# -*- coding: utf-8 -*-
# from odoo import http


# class WebsiteCapSscl2(http.Controller):
#     @http.route('/website_cap_sscl2/website_cap_sscl2', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/website_cap_sscl2/website_cap_sscl2/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('website_cap_sscl2.listing', {
#             'root': '/website_cap_sscl2/website_cap_sscl2',
#             'objects': http.request.env['website_cap_sscl2.website_cap_sscl2'].search([]),
#         })

#     @http.route('/website_cap_sscl2/website_cap_sscl2/objects/<model("website_cap_sscl2.website_cap_sscl2"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('website_cap_sscl2.object', {
#             'object': obj
#         })

