# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    
    # ==================== IMPORTACIÓN DE PRODUCTOS ====================
    @api.model
    def importar_productos_desde_api(self):
        """
        Importa productos desde dos APIs externas:
        1. Endpoint de productos: datos básicos y familia
        2. Endpoint de stock/detalle: stock, bodega y código de producto
        """
        try:
            _logger.info("Iniciando importación de productos desde dos endpoints...")
            
            # Obtener datos de ambos endpoints
            productos_data = self._obtener_datos_productos()
            stock_data = self._obtener_datos_stock_detalle()
            
            if not productos_data and not stock_data:
                raise UserError("No se encontraron productos para importar en ningún endpoint")
            
            resultados = self._procesar_productos_combinados(productos_data, stock_data)
            _logger.info(
                "Importación completada: %d creados, %d actualizados",
                resultados['creados'],
                resultados['actualizados']
            )
            
            return self._mostrar_notificacion_exito(
                resultados['creados'],
                resultados['actualizados']
            )
            
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

    def _obtener_datos_productos(self):
        """Obtiene datos del endpoint de productos (familia y subfamilia)"""
        try:
            api_url = "http://seguimiento.random.cl:51034/productos"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...',
                'Content-Type': 'application/json'
            }
            
            _logger.info("🔗 Consultando endpoint de productos...")
            response = requests.get(api_url, headers=headers, timeout=60)
            
            if response.status_code != 200:
                _logger.warning(f"Error en endpoint de productos: Código {response.status_code}")
                return []
            
            try:
                data = response.json()
                productos_data = self._extraer_datos_productos(data)
                _logger.info(f"✅ Obtenidos {len(productos_data or [])} productos del endpoint de productos")
                return productos_data or []
            except ValueError:
                _logger.warning("Respuesta del endpoint de productos no es JSON válido")
                return []
                
        except Exception as e:
            _logger.warning(f"Error al obtener datos de productos: {str(e)}")
            return []

    def _obtener_datos_stock_detalle(self):
        """Obtiene datos del endpoint de stock/detalle (KOPR, DISP1, KOBO)"""
        try:
            api_url = "http://seguimiento.random.cl:51034/stock/detalle?fields=KOPR,DISP1,KOBO"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpZ...',
                'Content-Type': 'application/json'
            }
            
            _logger.info("🔗 Consultando endpoint de stock/detalle...")
            response = requests.get(api_url, headers=headers, timeout=60)
            
            if response.status_code != 200:
                _logger.warning(f"Error en endpoint de stock/detalle: Código {response.status_code}")
                return []
            
            try:
                data = response.json()
                stock_data = self._extraer_datos_stock_detalle(data)
                _logger.info(f"✅ Obtenidos {len(stock_data or [])} registros del endpoint de stock/detalle")
                return stock_data or []
            except ValueError:
                _logger.warning("Respuesta del endpoint de stock/detalle no es JSON válido")
                return []
                
        except Exception as e:
            _logger.warning(f"Error al obtener datos de stock/detalle: {str(e)}")
            return []

    def _extraer_datos_productos(self, data):
        """Extrae lista de productos de la respuesta API de productos"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            posibles_claves = ['productos', 'data', 'items', 'results', 'records']
            for clave in posibles_claves:
                if clave in data and isinstance(data[clave], list):
                    return data[clave]
            if 'KOPR' in data and 'NOKOPR' in data:
                return [data]
        return []

    def _extraer_datos_stock_detalle(self, data):
        """Extrae lista de datos de stock del endpoint stock/detalle"""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            posibles_claves = ['data', 'items', 'results', 'records', 'stock']
            for clave in posibles_claves:
                if clave in data and isinstance(data[clave], list):
                    return data[clave]
            if 'KOPR' in data:
                return [data]
        return []

    def _procesar_productos_combinados(self, productos_data, stock_data):
        """Procesa productos combinando datos de ambos endpoints"""
        ProductProduct = self.env['product.product']
        creados = 0
        actualizados = 0
        
        # Crear diccionario de productos para búsqueda rápida de familia
        productos_dict = {}
        for item in productos_data:
            if isinstance(item, dict) and item.get('KOPR'):
                productos_dict[item['KOPR']] = item
        
        # Procesar datos de stock/detalle como fuente principal
        for item in stock_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('KOPR')
            disp1 = item.get('DISP1', 0.0)
            kobo = item.get('KOBO', '')
            
            if not kopr:
                _logger.debug(f"Registro sin código de producto: {item}")
                continue
            
            # Buscar datos adicionales del endpoint de productos
            producto_info = productos_dict.get(kopr, {})
            fmpr = producto_info.get('FMPR', '')
            poivpr = producto_info.get('POIVPR', 0.0)
            
            try:
                # Usar KOPR como nombre del producto
                nombre_producto = kopr
                
                producto_existente = ProductProduct.search([('default_code', '=', kopr)], limit=1)
                if not producto_existente:
                    self._crear_producto_combinado(kopr, nombre_producto, poivpr, fmpr, disp1, kobo)
                    creados += 1
                else:
                    self._actualizar_producto_combinado(producto_existente, nombre_producto, poivpr, fmpr, disp1, kobo)
                    actualizados += 1
                    
            except Exception as e:
                _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                continue
        
        # Procesar productos del endpoint de productos que no estén en stock/detalle
        for item in productos_data:
            if not isinstance(item, dict):
                continue
                
            kopr = item.get('KOPR')
            nokopr = item.get('NOKOPR')
            poivpr = item.get('POIVPR', 0.0)
            fmpr = item.get('FMPR')
            
            if not kopr or not nokopr:
                continue
            
            # Verificar si ya fue procesado desde stock/detalle
            ya_procesado = any(s.get('KOPR') == kopr for s in stock_data if isinstance(s, dict))
            if ya_procesado:
                continue
                
            try:
                producto_existente = ProductProduct.search([('default_code', '=', kopr)], limit=1)
                if not producto_existente:
                    self._crear_producto_combinado(kopr, nokopr, poivpr, fmpr, 0.0, '')
                    creados += 1
                else:
                    self._actualizar_producto_combinado(producto_existente, nokopr, poivpr, fmpr, 0.0, '')
                    actualizados += 1
                    
            except Exception as e:
                _logger.error(f"Error procesando producto {kopr}: {str(e)}")
                continue
        
        self.env.cr.commit()
        return {'creados': creados, 'actualizados': actualizados}

    def _crear_producto_combinado(self, codigo, nombre, precio, familia, stock, bodega):
        """Crea producto con datos combinados de ambos endpoints"""
        vals = {
            'name': nombre,
            'list_price': float(precio) if precio else 0.0,
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': True,
            'default_code': codigo,
            'x_studio_family': familia or '',
            'x_studio_stock': float(stock) if stock else 0.0,
            'x_studio_bodega': str(bodega) if bodega else '',
        }
        
        try:
            self.env['product.product'].create(vals)
            _logger.info(f"✅ Producto creado: {codigo} - {nombre} (Stock: {stock}, Bodega: {bodega})")
        except Exception as e:
            _logger.error(f"Error al crear producto {codigo}: {str(e)}")
            raise

    def _actualizar_producto_combinado(self, producto, nombre, precio, familia, stock, bodega):
        """Actualiza producto con datos combinados de ambos endpoints"""
        vals = {
            'name': nombre,
            'x_studio_family': familia or '',
        }
        
        # Solo actualizar precio si viene del endpoint de productos
        if precio and precio > 0:
            vals['list_price'] = float(precio)
        
        # Actualizar stock y bodega solo si vienen del endpoint de stock/detalle
        if stock is not None:
            vals['x_studio_stock'] = float(stock)
        if bodega is not None:
            vals['x_studio_bodega'] = str(bodega)
        
        try:
            producto.write(vals)
            _logger.info(f"♻️ Producto actualizado: {producto.default_code} (Stock: {stock}, Bodega: {bodega})")
        except Exception as e:
            _logger.error(f"Error al actualizar producto {producto.default_code}: {str(e)}")
            raise

    # ==================== IMPORTACIÓN DE PRECIOS ====================
    @api.model
    def importar_precios_desde_api(self):
        """Importa precios y stock físico desde API externa (manejo de decimales y negativos)"""
        try:
            api_url = "http://seguimiento.random.cl:51034/web32/precios/pidelistaprecio"
            headers = {
                'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                'Content-Type': 'application/json'
            }

            _logger.info("🔗 Consultando API de precios y stock...")
            response = requests.get(api_url, headers=headers, timeout=60)
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
            productos_stock = {}

            for item in productos_api:
                if not isinstance(item, dict):
                    continue
                barcode = item.get('kopr')
                unidades = item.get('unidades', [])

                precio_bruto = 0.0
                stock_fisico = 0.0

                if unidades and isinstance(unidades, list) and len(unidades) > 0:
                    first_unit = unidades[0]
                    prunbruto_list = first_unit.get('prunbruto', [])
                    if prunbruto_list and isinstance(prunbruto_list, list) and len(prunbruto_list) > 0:
                        precio_bruto = prunbruto_list[0].get('f', 0.0)

                    # Obtener stockfisico con tolerancia a decimales y negativos
                    sf = first_unit.get('stockfisico', 0)
                    try:
                        stock_fisico = float(sf)
                    except (TypeError, ValueError):
                        stock_fisico = 0.0

                if barcode:
                    productos_precio[barcode] = precio_bruto
                    productos_stock[barcode] = stock_fisico

                _logger.debug(f"Producto {barcode}: precio_bruto={precio_bruto}, stock_fisico={stock_fisico}")

            # Buscar productos por default_code en lugar de barcode
            codigos_api = list(productos_precio.keys())
            productos_odoo = self.env['product.product'].search([('default_code', 'in', codigos_api)])
            
            precios_actualizados = 0
            stocks_actualizados = 0

            for producto in productos_odoo:
                nuevo_precio = productos_precio.get(producto.default_code, 0.0)
                nuevo_stock = productos_stock.get(producto.default_code, 0.0)

                if nuevo_precio > 0:
                    producto.list_price = nuevo_precio
                    precios_actualizados += 1

                # Actualizar stock siempre (independiente del precio)
                producto.product_tmpl_id.write({
                    'x_studio_stock': nuevo_stock,
                })
                stocks_actualizados += 1

                _logger.info(
                    f"✅ Producto {producto.default_code} actualizado con "
                    f"list_price={nuevo_precio} y stock={nuevo_stock}"
                )

            # Mensaje de notificación
            message = (
                f"Precios actualizados: {precios_actualizados}\n"
                f"Stock actualizado: {stocks_actualizados}"
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '🔔 Importación de precios y stock',
                    'message': message,
                    'sticky': True,
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'}
                }
            }

        except requests.exceptions.RequestException as e:
            _logger.error(f"🌐 Error de conexión con la API: {str(e)}")
            raise UserError(f"Error al conectar con la API: {str(e)}")
        except Exception as e:
            _logger.error(f"❌ Error inesperado: {str(e)}")
            raise UserError(f"Error inesperado: {str(e)}")

    # ==================== MÉTODOS COMPARTIDOS ====================
    def _mostrar_notificacion_exito(self, creados, actualizados):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✅ Importación completada',
                'message': (
                    f'Productos nuevos: {creados}\n'
                    f'Productos actualizados: {actualizados}'
                ),
                'sticky': True,
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window_close'
                },
            }
        }
