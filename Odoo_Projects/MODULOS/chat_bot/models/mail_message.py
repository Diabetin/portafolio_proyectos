# -*- coding: utf-8 -*-
import os
import re
import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    uuid = fields.Char(string='UUID')
    show_uuid = fields.Boolean(compute='_compute_show_uuid', store=True)

    @api.depends('uuid')
    def _compute_show_uuid(self):
        for record in self:
            record.show_uuid = bool(record.uuid)

class MailMessage(models.Model):
    _inherit = 'mail.message'

    bot_response = fields.Text(string='Respuesta del Bot')

    @api.model_create_multi
    def create(self, vals_list):
        if self._context.get('bot_response_creation'):
            return super(MailMessage, self).create(vals_list)

        records = super(MailMessage, self).create(vals_list)
        for record in records:
            if record.model == 'discuss.channel' and record.message_type == 'comment':
                channel = self.env['discuss.channel'].browse(record.res_id)
                if channel.uuid == 'bot_chat_ia':
                    prompt = record.body
                    tipo = self._detectar_pregunta_de_datos(prompt)
                    if tipo:
                        respuesta = self._consultar_dato(tipo, prompt)
                    else:
                        respuesta = self._ask_google(prompt) or "Lo siento, no entendí la pregunta. ¿Podrías reformularla?"

                    self.with_context(bot_response_creation=True).create([{
                        'model': 'discuss.channel',
                        'res_id': channel.id,
                        'message_type': 'comment',
                        'body': respuesta,
                        'author_id': self._get_bot_author_id(),
                    }])
        return records

    def _get_bot_author_id(self):
        bot_partner = self.env['res.partner'].sudo().search([('name', '=', 'Bot Google')], limit=1)
        if not bot_partner:
            bot_partner = self.env['res.partner'].sudo().create({
                'name': 'Bot Google',
                'is_company': False,
            })
        return bot_partner.id

    def _detectar_pregunta_de_datos(self, mensaje):
        mensaje = mensaje.lower()
        if "tareas pendientes" in mensaje or "actividades pendientes" in mensaje:
            return "tareas_pendientes"
        elif "detalles de la tarea" in mensaje or "descripción de la tarea" in mensaje or "información de la tarea" in mensaje:
            return "descripcion_tarea"
        return None

    def _consultar_dato(self, tipo_pregunta, mensaje):
        if tipo_pregunta == "tareas_pendientes":
            tareas_pendientes = self.env['project.task'].search_count([
                ('stage_id.name', 'ilike', 'pendiente')
            ])
            return f"📌 Hay {tareas_pendientes} tareas pendientes en el sistema."

        elif tipo_pregunta == "descripcion_tarea":
            match_id = re.search(r"tarea\s+(\d+)", mensaje.lower())
            tarea = None

            if match_id:
                tarea_id = int(match_id.group(1))
                tarea = self.env['project.task'].search([('id', '=', tarea_id)], limit=1)
            else:
                partes = mensaje.lower().split("tarea")
                if len(partes) > 1:
                    nombre_tarea = partes[1].strip()
                    tarea = self.env['project.task'].search([('name', 'ilike', nombre_tarea)], limit=1)

            if tarea:
                estado = dict(tarea._fields['state'].selection).get(tarea.state, tarea.state)
                fecha_creacion = tarea.create_date.strftime("%d-%m-%Y") if tarea.create_date else "Sin fecha"
                fecha_actualizacion = tarea.write_date.strftime("%d-%m-%Y") if tarea.write_date else "Sin fecha"
                prioridad = dict(tarea._fields['priority'].selection).get(tarea.priority, tarea.priority)
                asignados = ", ".join(tarea.user_ids.mapped('name')) or "Sin asignar"
                vencimiento = tarea.date_deadline.strftime("%d-%m-%Y") if tarea.date_deadline else "Sin fecha"
                proyecto = tarea.project_id.name or "Sin proyecto"

                return (
                    f"📋 **{tarea.name}** (ID {tarea.id})\n"
                    f"- Estado: {estado}\n"
                    f"- Creación: {fecha_creacion}\n"
                    f"- Actualización: {fecha_actualizacion}\n"
                    f"- Prioridad: {prioridad}\n"
                    f"- Asignado a: {asignados}\n"
                    f"- Vencimiento: {vencimiento}\n"
                    f"- Proyecto: {proyecto}\n"
                    f"- Descripción: {tarea.description or 'Sin descripción'}"
                )
            else:
                return "No encontré ninguna tarea que coincida con ese nombre o ID."

        return "No pude procesar tu consulta."

    def _ask_google(self, prompt):
        api_key = os.getenv('')
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get('candidates') and data['candidates'][0].get('content') and \
                    data['candidates'][0]['content'].get('parts') and \
                    data['candidates'][0]['content']['parts'][0].get('text'):
                    return data['candidates'][0]['content']['parts'][0]['text']
                else:
                    _logger.warning(f"Respuesta de Gemini inesperada o vacía: {res.text}")
                    return "[Google API Error]: Respuesta vacía o inesperada del modelo Gemini."
            return f"[Google API Error] Status: {res.status_code} - Body: {res.text}"
        except Exception as e:
            return f"[Google Exception] {str(e)}"
