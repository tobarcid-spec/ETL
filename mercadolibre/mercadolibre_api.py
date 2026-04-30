"""
Script para conectar con API de MercadoLibre y generar reportes de ventas
Identifica cobros, gastos y utilidad por transacción
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MercadoLibreAPI:
    """Cliente para interactuar con la API de MercadoLibre"""
    
    # Endpoints
    BASE_URL = "https://api.mercadolibre.com"
    AUTH_URL = "https://auth.mercadolibre.com.ar/authorization"
    TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
    
    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = "http://localhost:8000", access_token: str = None):
        """
        Inicializa el cliente de MercadoLibre
        
        Args:
            client_id: ID de tu aplicación en MercadoLibre
            client_secret: Secret de tu aplicación
            redirect_uri: URI de redirección configurado en MercadoLibre
            access_token: Token de acceso directo (si ya tienes uno)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        self.seller_id = None
        self.token_expiry = None
    
    def get_auth_url(self) -> str:
        """Genera URL para obtener el código de autorización"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri
        }
        auth_url = f"{self.AUTH_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        return auth_url
    
    def set_access_token(self, access_token: str) -> bool:
        """
        Establece el access token directamente
        
        Args:
            access_token: Token de acceso obtenido via OAuth
            
        Returns:
            True si se pudo obtener el seller_id
        """
        self.access_token = access_token
        logger.info("✅ Access token establecido")
        
        # Obtener seller_id automáticamente
        try:
            user_info = self._make_request("/users/me")
            if user_info:
                self.seller_id = user_info.get('id')
                logger.info(f"✅ Seller ID obtenido: {self.seller_id}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener seller_id automáticamente: {e}")
        
        return self.access_token is not None
    
    def authenticate(self, auth_code: str) -> bool:
        """
        Obtiene el access token usando el código de autorización
        
        Args:
            auth_code: Código obtenido del flujo de autenticación
            
        Returns:
            True si la autenticación fue exitosa
        """
        try:
            payload = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.TOKEN_URL, data=payload, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.seller_id = token_data.get('user_id')
            
            # Calcular expiración del token
            expires_in = token_data.get('expires_in', 21600)  # 6 horas por defecto
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(f"✅ Autenticación exitosa. Seller ID: {self.seller_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False
    
    def _make_request(self, endpoint: str, method: str = 'GET', params: Dict = None, 
                     json_data: Dict = None, retries: int = 3) -> Optional[Dict]:
        """
        Realiza una solicitud a la API con reintentos
        
        Args:
            endpoint: Endpoint de la API
            method: Método HTTP (GET, POST, etc.)
            params: Parámetros de query
            json_data: Datos para POST/PUT
            retries: Número de reintentos
            
        Returns:
            JSON response o None si falla
        """
        if not self.access_token:
            logger.error("❌ No hay access token. Ejecuta authenticate() primero")
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        for attempt in range(retries):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=json_data, params=params, timeout=15)
                else:
                    response = requests.request(method, url, headers=headers, json=json_data, params=params, timeout=15)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Backoff exponencial
                    logger.warning(f"⚠️ Intento {attempt + 1}/{retries} falló. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Error en solicitud a {endpoint}: {e}")
                    return None
        
        return None
    
    def get_seller_info(self) -> Optional[Dict]:
        """Obtiene información del vendedor"""
        if not self.seller_id:
            logger.error("❌ Seller ID no disponible")
            return None
        
        return self._make_request(f"/users/{self.seller_id}")
    
    def get_sales(self, limit: int = 50, offset: int = 0, 
                  sort: str = 'date_desc') -> Optional[List[Dict]]:
        """
        Obtiene las ventas del vendedor
        
        Args:
            limit: Número máximo de ordenes por página
            offset: Desplazamiento para paginación
            sort: Ordenamiento (date_desc, date_asc)
            
        Returns:
            Lista de órdenes/ventas
        """
        if not self.seller_id:
            logger.error("❌ Seller ID no disponible")
            return None
        
        params = {
            'seller_id': self.seller_id,
            'limit': min(limit, 50),  # MercadoLibre tiene límite de 50
            'offset': offset,
            'sort': sort
        }
        
        response = self._make_request('/orders/search', params=params)
        
        if response and 'results' in response:
            return response['results']
        return None
    
    def get_order_details(self, order_id: int) -> Optional[Dict]:
        """Obtiene detalles de una orden específica"""
        return self._make_request(f"/orders/{order_id}")
    
    def get_all_sales(self, max_results: int = 1000) -> List[Dict]:
        """
        Obtiene todas las ventas con paginación automática
        
        Args:
            max_results: Máximo número de resultados a obtener
            
        Returns:
            Lista completa de órdenes
        """
        all_sales = []
        offset = 0
        limit = 50
        
        while len(all_sales) < max_results:
            logger.info(f"📥 Obteniendo ventas (offset: {offset})...")
            
            sales = self.get_sales(limit=limit, offset=offset)
            if not sales:
                break
            
            all_sales.extend(sales)
            offset += limit
            
            # Respetar límite de rate
            time.sleep(1)
            
            if len(sales) < limit:  # Última página
                break
        
        return all_sales[:max_results]


class SalesAnalyzer:
    """Analiza ventas y calcula costos"""
    
    def __init__(self, ml_api: MercadoLibreAPI):
        self.ml_api = ml_api
        self.sales_data = []
    
    def fetch_and_analyze_sales(self, max_results: int = 1000) -> pd.DataFrame:
        """
        Obtiene todas las ventas y las analiza
        
        Args:
            max_results: Número máximo de ventas a procesar
            
        Returns:
            DataFrame con análisis de ventas
        """
        logger.info("📊 Iniciando análisis de ventas...")
        
        # Obtener todas las ventas
        sales = self.ml_api.get_all_sales(max_results)
        
        if not sales:
            logger.warning("⚠️ No se encontraron ventas")
            return pd.DataFrame()
        
        logger.info(f"📈 Procesando {len(sales)} ventas...")
        
        analyzed_sales = []
        for idx, sale in enumerate(sales, 1):
            if idx % 10 == 0:
                logger.info(f"   Procesadas {idx}/{len(sales)} ventas...")
            
            analysis = self._analyze_single_sale(sale)
            if analysis:
                analyzed_sales.append(analysis)
            
            # Rate limiting
            if idx % 5 == 0:
                time.sleep(0.5)
        
        df = pd.DataFrame(analyzed_sales)
        self.sales_data = df
        
        logger.info(f"✅ Análisis completado: {len(df)} ventas procesadas")
        return df
    
    def _analyze_single_sale(self, sale: Dict) -> Optional[Dict]:
        """
        Analiza una venta individual y calcula cobros/gastos
        
        Args:
            sale: Datos de la venta
            
        Returns:
            Diccionario con análisis
        """
        try:
            order_id = sale.get('id')
            
            # Obtener detalles completos si es necesario
            details = self.ml_api.get_order_details(order_id)
            if not details:
                return None
            
            # Extrae información
            order_data = {
                'ORDEN_ID': order_id,
                'FECHA': datetime.fromisoformat(sale.get('date_created', '').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M'),
                'ESTADO': sale.get('status', 'unknown'),
                'BUYER': sale.get('buyer', {}).get('id', 'N/A'),
                'NÚMERO_ARTÍCULOS': len(details.get('order_items', [])),
            }
            
            # Calcula totales
            total_precio = 0
            total_cantidad = 0
            items_info = []
            
            for item in details.get('order_items', []):
                price = item.get('unit_price', 0) * item.get('quantity', 0)
                total_precio += price
                total_cantidad += item.get('quantity', 0)
                items_info.append({
                    'titulo': item.get('item', {}).get('title', 'Sin título')[:50],
                    'cantidad': item.get('quantity', 0),
                    'precio_unitario': item.get('unit_price', 0),
                    'subtotal': price
                })
            
            order_data['MONTO_BRUTO'] = total_precio
            order_data['CANTIDAD_ITEMS'] = total_cantidad
            order_data['ITEMS'] = ' | '.join([f"{i['titulo']} (x{i['cantidad']})" for i in items_info])
            
            # Cálculo detallado de costos
            shipping_cost = details.get('shipping', {}).get('cost', 0) or 0
            comisión_ml = total_precio * 0.075  # 7.5% comisión típica (varía por categoría)
            
            order_data['COSTO_ENVÍO'] = shipping_cost
            order_data['COMISIÓN_ML'] = round(comisión_ml, 2)
            order_data['OTROS_GASTOS'] = 0  # Campo para gastos adicionales
            order_data['TOTAL_GASTOS'] = round(shipping_cost + comisión_ml, 2)
            
            # Cobro neto
            order_data['COBRO_NETO'] = round(total_precio - order_data['TOTAL_GASTOS'], 2)
            
            # Margen
            if total_precio > 0:
                order_data['MARGEN_%'] = round((order_data['COBRO_NETO'] / total_precio) * 100, 2)
            else:
                order_data['MARGEN_%'] = 0
            
            # Información de pago
            payment_method = details.get('payments', [{}])[0]
            order_data['MÉTODO_PAGO'] = payment_method.get('payment_type_id', 'unknown')
            order_data['FECHA_PAGO'] = datetime.fromisoformat(
                payment_method.get('date_last_modified', '').replace('Z', '+00:00')
            ).strftime('%Y-%m-%d') if payment_method.get('date_last_modified') else 'N/A'
            
            return order_data
            
        except Exception as e:
            logger.error(f"❌ Error analizando orden {sale.get('id', 'unknown')}: {e}")
            return None
    
    def export_to_excel(self, filename: str = None, include_summary: bool = True) -> str:
        """
        Exporta el análisis a un archivo Excel
        
        Args:
            filename: Nombre del archivo (default: sales_FECHAHORA.xlsx)
            include_summary: Si incluye resumen estadístico
            
        Returns:
            Ruta del archivo creado
        """
        if self.sales_data.empty:
            logger.error("❌ No hay datos de ventas para exportar")
            return ""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Ventas_MercadoLibre_{timestamp}.xlsx"
        
        filepath = Path(filename)
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Hoja 1: Datos detallados
                self.sales_data.to_excel(writer, sheet_name='Ventas Detalladas', index=False)
                
                # Hoja 2: Resumen estadístico
                if include_summary:
                    summary_df = self._generate_summary()
                    summary_df.to_excel(writer, sheet_name='Resumen', index=True)
                
                # Formatear Excel
                workbook = writer.book
                
                # Ajustar ancho de columnas
                for sheet in workbook.sheetnames:
                    worksheet = writer.sheets[sheet]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"✅ Excel exportado: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Error exportando a Excel: {e}")
            return ""
    
    def export_to_csv(self, filename: str = None) -> str:
        """
        Exporta el análisis a un archivo CSV
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            Ruta del archivo creado
        """
        if self.sales_data.empty:
            logger.error("❌ No hay datos de ventas para exportar")
            return ""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Ventas_MercadoLibre_{timestamp}.csv"
        
        try:
            self.sales_data.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"✅ CSV exportado: {filename}")
            return filename
        except Exception as e:
            logger.error(f"❌ Error exportando a CSV: {e}")
            return ""
    
    def _generate_summary(self) -> pd.DataFrame:
        """Genera resumen estadístico de las ventas"""
        if self.sales_data.empty:
            return pd.DataFrame()
        
        summary = {
            'Total Ordenes': len(self.sales_data),
            'Monto Bruto Total': self.sales_data['MONTO_BRUTO'].sum(),
            'Total Gastos': self.sales_data['TOTAL_GASTOS'].sum(),
            'Total Cobro Neto': self.sales_data['COBRO_NETO'].sum(),
            'Margen Promedio %': self.sales_data['MARGEN_%'].mean(),
            'Costo Envío Total': self.sales_data['COSTO_ENVÍO'].sum(),
            'Comisión ML Total': self.sales_data['COMISIÓN_ML'].sum(),
            'Precio Promedio': self.sales_data['MONTO_BRUTO'].mean(),
            'Cantidad Total Items': self.sales_data['CANTIDAD_ITEMS'].sum(),
        }
        
        return pd.DataFrame(summary, index=[0]).T.rename(columns={0: 'Valor'})


def main():
    """Función principal"""
    
    # ==================== CARGAR CONFIGURACIÓN ====================
    try:
        token_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'ml_token.json')
        with open(token_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        ACCESS_TOKEN = config.get('access_token')
        SELLER_ID = config.get('user_id')
        
        logger.info(f"✅ Configuración cargada desde {token_file}")
        
    except FileNotFoundError:
        logger.error(f"❌ No se encontró {token_file}")
        print("⚠️  Por favor ejecuta primero get_ml_token.py para generar el token")
        return
    except Exception as e:
        logger.error(f"❌ Error leyendo {token_file}: {e}")
        return
    
    # ==================== INICIO ====================
    
    print("\n" + "="*60)
    print("🔗 MercadoLibre Sales Analyzer".center(60))
    print("="*60 + "\n")
    
    # Inicializar API con el access token
    ml_api = MercadoLibreAPI(access_token=ACCESS_TOKEN)
    ml_api.access_token = ACCESS_TOKEN
    ml_api.seller_id = SELLER_ID
    
    logger.info(f"✅ Access token establecido. Seller ID: {SELLER_ID}")
    
    # Obtener info del vendedor
    seller_info = ml_api.get_seller_info()
    if seller_info:
        print(f"👤 Vendedor: {seller_info.get('nickname', 'N/A')}")
        print(f"⭐ Reputación: {seller_info.get('reputation', {}).get('transactions', 0)} transacciones\n")
    
    # Analizar ventas
    analyzer = SalesAnalyzer(ml_api)
    df_sales = analyzer.fetch_and_analyze_sales(max_results=1000)
    
    if not df_sales.empty:
        # Exportar a Excel (recomendado)
        excel_path = analyzer.export_to_excel()
        
        # También exportar a CSV
        csv_path = analyzer.export_to_csv()
        
        print("\n" + "="*60)
        print("📊 RESUMEN DE VENTAS".center(60))
        print("="*60)
        print(analyzer._generate_summary())
        print("="*60 + "\n")
        
        print(f"✅ Archivos generados:")
        print(f"   📁 Excel: {excel_path}")
        print(f"   📁 CSV: {csv_path}\n")
    else:
        print("❌ No se pudieron obtener las ventas\n")


if __name__ == "__main__":
    main()
