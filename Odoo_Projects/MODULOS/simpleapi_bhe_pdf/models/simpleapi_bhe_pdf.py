# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .rate_limit import SimpleAPIRateLimiter
import json as _json

_logger = logging.getLogger(__name__)

def _mask_key(key: str, show_start: int = 6, show_end: int = 4) -> str:
    if not key:
        return ''
    s = str(key)
    if len(s) <= show_start + show_end:
        return '*' * len(s)
    return f"{s[:show_start]}{'*'*6}{s[-show_end:]}"

def _hash_sha256(text: str) -> str:
    """Genera hash SHA-256 de un texto para logging seguro"""
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# 1 req/s con backoff y respeto de Retry-After
_LIMITER = SimpleAPIRateLimiter(min_interval_sec=1.0, max_retries=5, base_delay=1.0, factor=2.0, max_delay=30.0)

class SimpleApiBhePdf(models.Model):
    _name = 'simpleapi.bhe.pdf'
    _description = 'SimpleAPI BHE PDF (SII)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Descripción', default='Consulta PDF BHE', readonly=True)
    folio = fields.Integer('Folio', required=True)
    anio = fields.Integer('Año', required=True, default=fields.Date.today().year)
    rut_usuario = fields.Char('RUT Usuario', required=True, help='Formato 12345678-9')
    password_sii = fields.Char('Password SII', required=True)
    pdf_file = fields.Binary('PDF', attachment=True, readonly=True)
    pdf_filename = fields.Char('Nombre de archivo', readonly=True)
    last_status = fields.Char('Último estado', readonly=True)
    pdf_iframe_html = fields.Html('Visor PDF', compute='_compute_pdf_iframe_html',
                                  sanitize=False, readonly=True)

    @api.depends('pdf_file', 'pdf_filename')
    def _compute_pdf_iframe_html(self):
        for rec in self:
            if rec.pdf_file and rec.id:
                src = f"/simpleapi_bhe/pdf/view/{rec.id}"
                rec.pdf_iframe_html = (
                    f'<iframe src="{src}" '
                    f'style="width:100%; height:800px; border:1px solid #ccc;"></iframe>'
                )
            else:
                rec.pdf_iframe_html = '<div class="text-muted">No hay PDF descargado aún.</div>'

    @api.model
    def _get_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('simpleapi_bhe_pdf.api_key', '4648-N330-6392-2590-9354')
        base_url = icp.get_param('simpleapi_bhe_pdf.base_url', 'https://servicios.simpleapi.cl/api')
        timeout = int(icp.get_param('simpleapi_bhe_pdf.timeout', 30))
        _logger.info(f"[BHE-PDF] Config base_url={base_url} api_key={_mask_key(api_key)} timeout={timeout}")
        if not api_key:
            raise UserError(_('Falta configurar la API Key en Ajustes'))
        return {'api_key': api_key, 'base_url': base_url, 'timeout': timeout}

    def _http_preview(self, resp):
        preview = ''
        if getattr(resp, 'text', None):
            preview = (resp.text or '')[:300]
        if not preview and getattr(resp, 'content', None):
            try:
                preview = resp.content[:300].decode('utf-8', errors='ignore')
            except Exception:
                preview = str(resp.content[:120])
        if not preview:
            preview = resp.reason or 'Sin cuerpo de respuesta'
        return preview

    def action_fetch_pdf(self):
        """
        GET con body JSON (autenticación requerida por el endpoint):
          - GET /bhe/pdf/emitidas/{folio}/{anio}
          - Body: {"RutUsuario": "...", "PasswordSII": "..."}
          - Content-Type: application/json; charset=UTF-8
        """
        for rec in self:
            if rec.folio <= 0 or rec.anio <= 2000:
                raise UserError(_('Folio/Año inválidos'))
            if not rec.rut_usuario or not rec.password_sii:
                raise UserError(_('Debe indicar RutUsuario y PasswordSII'))

            cfg = rec._get_config()
            url = f"{cfg['base_url'].rstrip('/')}/bhe/pdf/emitidas/{rec.folio}/{rec.anio}"
            
            # Payload real (sin cifrar) para envío al endpoint
            payload = {"RutUsuario": rec.rut_usuario, "PasswordSII": rec.password_sii}
            body_bytes = _json.dumps(payload).encode('utf-8')

            # GET con body JSON explícito
            headers = {
                'Authorization': cfg['api_key'],
                'Accept': 'application/pdf',
                'Content-Type': 'application/json; charset=UTF-8',
                'User-Agent': 'odoo-18-simpleapi-bhe-pdf'
            }

            # Log con credenciales cifradas SHA-256 para seguridad
            rut_hash = _hash_sha256(rec.rut_usuario)
            password_hash = _hash_sha256(rec.password_sii)
            _logger.info(f"[BHE-PDF] GET(body) {url} CT={headers['Content-Type']} body={{'RutUsuario':'{rut_hash}','PasswordSII':'{password_hash}'}}")

            try:
                resp = _LIMITER.request(
                    "GET", url,
                    headers=headers,
                    data=body_bytes,           # body JSON en GET (sin cifrar)
                    timeout=cfg['timeout'],
                    allow_redirects=False,     # evitar cambios de método/cuerpo implícitos
                )
            except Exception as e:
                rec.last_status = f"Conexión fallida: {e}"
                raise UserError(_('Conexión fallida contra SimpleAPI: %s') % e)

            # Redirecciones: reemitir GET con el MISMO body/headers
            if getattr(resp, 'is_redirect', False) or getattr(resp, 'is_permanent_redirect', False):
                loc = resp.headers.get('Location')
                code = resp.status_code
                _logger.info(f"[BHE-PDF] Redirect {code} -> {loc}")
                if not loc:
                    rec.last_status = f"Redirección sin Location (HTTP {code})"
                    raise UserError(_('Redirección sin destino'))
                resp = _LIMITER.request(
                    "GET", loc,
                    headers=headers,
                    data=body_bytes,
                    timeout=cfg['timeout'],
                    allow_redirects=False,
                )

            ctype = resp.headers.get('Content-Type', '')
            size = len(resp.content) if resp.content else 0
            _logger.info(f"[BHE-PDF] status={resp.status_code} reason={resp.reason} ctype={ctype} len={size}")

            # 405: el recurso no admite GET -> informar Allow
            if resp.status_code == 405:
                allow = resp.headers.get('Allow', '')
                rec.last_status = f"405 Method Not Allowed. Allow={allow or 'N/D'}"
                raise UserError(_('Método HTTP no permitido para esta ruta. Revise Allow: %s') % (allow or 'N/D'))

            # 415: probar CT sin charset
            if resp.status_code == 415:
                headers_no_cs = dict(headers)
                headers_no_cs['Content-Type'] = 'application/json'
                _logger.info("[BHE-PDF] 415 -> reintento GET(body) con Content-Type: application/json")
                resp = _LIMITER.request(
                    "GET", url,
                    headers=headers_no_cs,
                    data=body_bytes,
                    timeout=cfg['timeout'],
                    allow_redirects=False,
                )
                ctype = resp.headers.get('Content-Type', '')
                if resp.status_code == 415:
                    rec.last_status = "415 Unsupported Media Type en GET con body JSON"
                    raise UserError(_('El servidor rechazó el tipo de medio (415) aun con JSON'))

            if resp.status_code not in (200, 202):
                preview = self._http_preview(resp)
                rec.last_status = f"HTTP {resp.status_code} ({ctype}): {preview}"
                raise UserError(_('Error HTTP %s: %s') % (resp.status_code, preview))

            # Validación estricta del PDF
            if 'pdf' not in ctype and not (resp.content and resp.content[:4] == b'%PDF'):
                preview = self._http_preview(resp)
                rec.last_status = f"No es PDF ({ctype}): {preview}"
                raise UserError(_('La respuesta no parece un PDF'))

            # Guardar y notificar
            fname = f"bhe_{rec.folio}_{rec.anio}.pdf"
            rec.pdf_file = base64.b64encode(resp.content)
            rec.pdf_filename = fname
            rec.last_status = "PDF descargado correctamente"
            rec.message_post(body=f"PDF almacenado: {fname}", message_type='notification')
#hola