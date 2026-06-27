# -*- coding: utf-8 -*-
# from odoo import http


# class ChatBot(http.Controller):
#     @http.route('/chat_bot/chat_bot', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/chat_bot/chat_bot/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('chat_bot.listing', {
#             'root': '/chat_bot/chat_bot',
#             'objects': http.request.env['chat_bot.chat_bot'].search([]),
#         })

#     @http.route('/chat_bot/chat_bot/objects/<model("chat_bot.chat_bot"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('chat_bot.object', {
#             'object': obj
#         })

