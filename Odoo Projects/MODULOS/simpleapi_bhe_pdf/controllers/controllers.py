# -*- coding: utf-8 -*-
import base64
from odoo import http
from odoo.http import request

class SimpleApiBhePdfController(http.Controller):

    @http.route('/simpleapi_bhe/pdf/view/<int:rec_id>', type='http', auth='user')
    def view_pdf(self, rec_id, **kwargs):
        rec = request.env['simpleapi.bhe.pdf'].browse(rec_id)
        if not rec.exists() or not rec.pdf_file:
            return request.not_found()
        content = base64.b64decode(rec.pdf_file)
        fname = rec.pdf_filename or f"bhe_{rec_id}.pdf"
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'inline; filename="{fname}"'),
                ('X-Frame-Options', 'SAMEORIGIN'),
                # ('Content-Security-Policy', "frame-ancestors 'self'"),
            ]
        )
