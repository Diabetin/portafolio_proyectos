# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    
    # ==================== IMPORTACIÓN DE PRODUCTOS ====================
    @api.model
    def importar_productos_desde_api(self, incluir_ocultos=False):
        """
        Importa productos desde API externa incluyendo:
        - Datos básicos (código, nombre, precio)
        - Familia jerárquica desde FMPR → Superfamilia/Familia/Subfamilia
        """
        try:
            config = self.env['ir.config_parameter'].sudo()
            token = config.get_param('randomerp_connector.token')
            base_url = config.get_param('randomerp_connector.api_url')
            products_url = f"{base_url}/productos"
            familias_url = f"{base_url}/familias"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            _logger.info("Iniciando importación de productos desde API...")
            response = requests.get(products_url, headers=headers, timeout=60)
            if response.status_code != 200:
                error_msg = f"Error API: Código {response.status_code}"
                if response.text:
                    error_msg += f"\nRespuesta: {response.text[:200]}..."
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            try:
                data = response.json()
            except ValueError:
                _logger.error("Respuesta no es JSON válido: %s", response.text[:200])
                raise UserError("La API devolvió una respuesta no válida (no JSON)")
            
            productos_data = self._extraer_datos_productos(data)
            if not productos_data:
                _logger.warning("No se encontraron productos para importar")
                raise UserError("No se encontraron productos para importar")
            
            if not incluir_ocultos:
                        productos_data = [
                            p for p in productos_data
                            if str(p.get('ATPR', '')).strip().upper() != 'OCU'
                        ]
            _logger.info("Productos después de filtro de ocultos: %d", len(productos_data))
            
            # Cargar familias desde API
            familias_dict, familias_llave_dict = self._cargar_familias(familias_url, headers)

            # Procesar productos con ambos diccionarios
            resultados = self._procesar_productos(productos_data, familias_dict, familias_llave_dict)
            _logger.info(
                "Importación completada: %d creados, %d actualizados",
                resultados['creados'],
                resultados['actualizados']
            )

            # ================= ACTUALIZAR PRECIOS DESPUÉS =================
            precios_result = self.importar_precios_desde_api()
            _logger.info(
                "Importación de precios completada: %d productos actualizados",
                precios_result.get('actualizados', 0)
            )

            return {
                'status': 'ok',
                'creados': resultados['creados'],
                'actualizados': resultados['actualizados'],
                'precios_actualizados': precios_result.get('actualizados', 0)
            }

        except requests.exceptions.Timeout:
            _logger.error("Timeout al conectar con la API")
            raise UserError("Tiempo de espera agotado. Inténtalo de nuevo.")
        except requests.exceptions.ConnectionError:
            _logger.error("Error de conexión con la API")
            raise UserError("Error de conexión. Verifica que el servidor esté disponible.")
        except Exception as e:
            _logger.exception("Error inesperado al importar productos")
            self.env.cr.rollback()
            raise UserError(f"Error inesperado: {str(e)}")
    
    def _extraer_datos_productos(self, data):
        """Extrae lista de productos de la respuesta API"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            posibles_claves = ['productos', 'data', 'items', 'results', 'records']
            for clave in posibles_claves:
                if clave in data and isinstance(data[clave], list):
                    return data[clave]
            if 'KOPR' in data and 'NOKOPR' in data:
                return [data]
        return None

    def _cargar_familias(self, familias_url, headers):
        response = requests.get(familias_url, headers=headers, timeout=30)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            raise UserError("Error al cargar familias: respuesta no válida de la API")

        familias_list = data.get("data") if isinstance(data, dict) and "data" in data else data

        familias_dict = {}
        familias_llave_dict = {}

        for fam in familias_list:
            if isinstance(fam, str) and fam.strip():
                try:
                    fam = json.loads(fam)
                except:
                    continue
            if not isinstance(fam, dict):
                continue
            codigo = fam.get("CODIGO")
            nombre = fam.get("NOMBRE")
            nivel = fam.get("NIVEL")
            llave = fam.get("LLAVE")
            if codigo:
                familias_dict[codigo] = {"nombre": nombre, "nivel": nivel, "llave": llave, "CODIGO": codigo}
            if llave:
                familias_llave_dict[llave] = {"nombre": nombre, "nivel": nivel, "CODIGO": codigo}

        return familias_dict, familias_llave_dict


    def _procesar_productos(self, productos_data, familias_dict, familias_llave_dict):
        """Procesa cada producto incluyendo la familia (FMPR)"""
        ProductProduct = self.env['product.template']
        creados = 0
        actualizados = 0

        for item in productos_data:
            if not isinstance(item, dict):
                continue
            tipr = item.get('TIPR')
            kopr = item.get('KOPR')
            nokopr = item.get('NOKOPR')

            # Resolver jerarquía de familia usando FMPR, PFPR y HFPR
            superfamilia, familia, subfamilia = self._resolver_familia(
                item.get('FMPR'),
                item.get('PFPR'),
                item.get('HFPR'),
                familias_dict,
                familias_llave_dict
            )
            try:
                producto_existente = ProductProduct.search([('barcode', '=', kopr)], limit=1)
                if not producto_existente:
                    self._crear_producto(kopr, nokopr, 0, tipr, superfamilia, familia, subfamilia)
                    creados += 1
                else:
                    self._actualizar_producto(producto_existente, nokopr, 0, tipr, superfamilia, familia, subfamilia)
                    actualizados += 1
            except Exception as e:
                _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                continue

        self.env.cr.commit()
        return {'creados': creados, 'actualizados': actualizados}
    
    def _resolver_familia(self, fmpr, pfpr, hfpr, familias_dict, familias_llave_dict):
        superfamilia = familia = subfamilia = None

        # ================= SUPERFAMILIA =================
        if fmpr and fmpr in familias_dict:
            superfamilia = familias_dict[fmpr]["nombre"]

        # ================= FAMILIA =================
        if fmpr and pfpr:
            llave2 = f"{fmpr}/{pfpr}"
            if llave2 in familias_llave_dict:
                familia = familias_llave_dict[llave2]["nombre"]

        # ================= SUBFAMILIA =================
        if fmpr and pfpr and hfpr:
            llave3 = f"{fmpr}/{pfpr}/{hfpr}"
            if llave3 in familias_llave_dict:
                subfamilia = familias_llave_dict[llave3]["nombre"]

        # Opcional: si algo falta, marcar como "N/A"
        superfamilia = superfamilia or ""
        familia = familia or ""
        subfamilia = subfamilia or ""

        return superfamilia, familia, subfamilia


    def _crear_producto(self, codigo, nombre, precio, tipr, superfamilia=None, familia=None, subfamilia=None):
        tipo_producto = 'service' if tipr == 'SSN' else 'consu'

        categ_id = False
        if superfamilia:
            categoria = self.env['product.category'].search([('name', '=', superfamilia)], limit=1)
            if not categoria:
                categoria = self.env['product.category'].create({'name': superfamilia})
            categ_id = categoria.id

        vals = {
            'type': tipo_producto,
            'barcode': codigo,
            'name': nombre,
            'list_price': float(precio),
            'sale_ok': True,
            'purchase_ok': True,
            'default_code': codigo,
            'categ_id': categ_id or self.env.ref("product.product_category_all").id,
            'x_studio_family': familia or '',
            'x_studio_subfamily': subfamilia or '',
        }
        self.env['product.template'].create(vals)
        _logger.info(f"✅ Producto creado: {codigo} - {nombre}")

    def _actualizar_producto(self, producto, nombre, precio, tipr, superfamilia=None, familia=None, subfamilia=None):
        tipo_producto = 'service' if tipr == 'SSN' else 'consu'

        categ_id = producto.categ_id.id
        if superfamilia:
            categoria = self.env['product.category'].search([('name', '=', superfamilia)], limit=1)
            if not categoria:
                categoria = self.env['product.category'].create({'name': superfamilia})
            categ_id = categoria.id

        vals = {
            'name': nombre,
            'list_price': float(precio),
            'type': tipo_producto,
            'categ_id': categ_id,
            'x_studio_family': familia or '',
            'x_studio_subfamily': subfamilia or '',
        }
        producto.write(vals)
        _logger.info(f"♻️ Producto actualizado: {producto.barcode} | ({tipo_producto})")
    
    @api.model
    def importar_precios_desde_api(self):
        """Importa precios desde API externa (solo > 0)"""
        try:
            config = self.env['ir.config_parameter'].sudo()
            token = config.get_param('randomerp_connector.token')
            base_url = config.get_param('randomerp_connector.api_url')
            precios_url = f"{base_url}/web32/precios/pidelistaprecio"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            _logger.info("🔗 Consultando API de precios...")
            response = requests.get(precios_url, headers=headers, timeout=60)
            if response.status_code != 200:
                raise UserError(f"Error en API: Código {response.status_code}")

            try:
                precios_data = response.json()
            except ValueError:
                raise UserError("Respuesta no es JSON válido")

            if not precios_data or "datos" not in precios_data:
                raise UserError("La API no devolvió datos de productos en la clave 'datos'")

            productos_api = precios_data["datos"]
            if not isinstance(productos_api, list) or not productos_api:
                raise UserError("La clave 'datos' no contiene productos válidos")

            productos_precio = {}
            for item in productos_api:
                if not isinstance(item, dict):
                    continue
                barcode = item.get('kopr')
                unidades = item.get('unidades', [])
                precio_bruto = 0.0
                if unidades and isinstance(unidades, list):
                    first_unit = unidades[0]
                    prunbruto_list = first_unit.get('prunbruto', [])
                    if prunbruto_list and isinstance(prunbruto_list, list):
                        precio_bruto = prunbruto_list[0].get('f', 0.0)
                if barcode and precio_bruto > 0.0:
                    productos_precio[barcode] = precio_bruto

            if not productos_precio:
                raise UserError("La API no devolvió productos con códigos y precios válidos (> 0)")

            barcodes_api = list(productos_precio.keys())
            productos_odoo = self.env['product.product'].search([('barcode', 'in', barcodes_api)])
            coincidencias = len(productos_odoo)

            for producto in productos_odoo:
                nuevo_precio = productos_precio.get(producto.barcode)
                if nuevo_precio:
                    producto.list_price = nuevo_precio
                    _logger.info(f"✅ Producto {producto.barcode} actualizado con list_price={nuevo_precio}")
            return {
                'status': 'ok',
                'creados': len(productos_precio),
                'actualizados': coincidencias
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"🌐 Error de conexión con la API: {str(e)}")
            raise UserError(f"Error al conectar con la API: {str(e)}")
        except Exception as e:
            _logger.error(f"❌ Error inesperado: {str(e)}")
            raise UserError(f"Error inesperado: {str(e)}")