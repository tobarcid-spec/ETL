import mysql.connector
from mysql.connector import Error
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import pickle
from datetime import datetime, timedelta
from urllib.parse import urlparse 
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
from google.auth.transport.requests import Request
from config.config import DB_CONFIG

# --- CONFIGURACIÓN ---
TABLE_ARTICULOS = "T13_articulos"
TABLE_METRICAS = "T13_metricas" 
PROPERTY_ID = "322070910" 
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'token.pickle') 
METRICS_LOOKBACK_DAYS = 30
ga4_client = None

COLUMNAS_METRICAS = [
    'articulo_url', 'path_pagina', 'fecha_hora_actualizacion', 'vistas', 'usuarios_unicos'
]

# --- UTILIDADES ---
def get_mysql_connection():
    """Establece la conexión a MySQL."""
    try:
        conn = mysql.connector.connect(
            autocommit=False,
            connect_timeout=600, 
            **DB_CONFIG
        )
        return conn
    except Error as err:
        print(f"❌ Error al conectar a MySQL: {err}")
        return None

def extract_page_path(url):
    try:
        path = urlparse(url).path 
        return path if path.startswith('/') else '/' + path
    except Exception:
        return None

def authenticate_ga4_client():
    global ga4_client
    if ga4_client: return ga4_client
    if not os.path.exists(TOKEN_FILE): 
        print("❌ Error: 'token.pickle' no encontrado.")
        return None
        
    try:
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
        ga4_client = BetaAnalyticsDataClient(credentials=credentials)
        return ga4_client
    except Exception:
        print("❌ Error de autenticación GA4.")
        return None

def get_ga_metrics_for_all_paths(client):
    """Obtiene vistas y usuarios de GA4 masivamente."""
    start_date = f"{METRICS_LOOKBACK_DAYS}daysAgo" 
    
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_date, end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="activeusers")],
        limit=200000 
    )
    
    try:
        response = client.run_report(request)
        metrics_map = {}
        for row in response.rows:
            path = row.dimension_values[0].value
            vistas = int(row.metric_values[0].value)
            usuarios = int(row.metric_values[1].value)
            metrics_map[path] = (vistas, usuarios)
        return metrics_map
    except Exception as e:
        print(f"Error consultando GA4 masivamente: {e}")
        return None

# --- TAREA PRINCIPAL ---
def fetch_and_store_analytics():
    """Tarea única de sincronización de métricas."""
    client = authenticate_ga4_client()
    if not client: return

    fecha_hora_actualizacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n--- INICIO PROCESO MÉTRICAS: {fecha_hora_actualizacion} ---")
    
    mysql_conn = get_mysql_connection()
    if not mysql_conn: return
    mysql_cursor = mysql_conn.cursor()

    print("⏳ Consultando GA4...")
    ga4_metrics_map = get_ga_metrics_for_all_paths(client)
    if not ga4_metrics_map:
        mysql_conn.close()
        return
    
    # Filtrar URLs de los últimos 30 días
    lookback_date = (datetime.now() - timedelta(days=METRICS_LOOKBACK_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    sql_select_urls = f"SELECT id_articulo FROM {TABLE_ARTICULOS} WHERE fecha_descarga >= %s"
    
    try:
        mysql_cursor.execute(sql_select_urls, (lookback_date,))
        urls_con_path = []
        for (url_articulo,) in mysql_cursor.fetchall():
            path = extract_page_path(url_articulo)
            if path: 
                urls_con_path.append((url_articulo, path))
            
        if not urls_con_path:
            print("ℹ️ No hay URLs recientes para procesar.")
            return

        registros_a_insertar = []
        for url, path in urls_con_path:
            metrics = ga4_metrics_map.get(path) 
            if metrics:
                registros_a_insertar.append((url, path, fecha_hora_actualizacion, metrics[0], metrics[1]))
            
        if not registros_a_insertar:
            print("ℹ️ No se encontraron métricas en GA4 para las URLs de la base de datos.")
            return

        # Inserción masiva
        columnas_str = f"({', '.join(COLUMNAS_METRICAS)})"
        placeholders = ', '.join(['%s'] * len(COLUMNAS_METRICAS))
        update_set = ", ".join([f"{col} = VALUES({col})" for col in COLUMNAS_METRICAS[1:]]) 
        
        sql_insert_update = f"""
            INSERT INTO {TABLE_METRICAS} 
            {columnas_str} VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_set}
        """
        
        mysql_cursor.executemany(sql_insert_update, registros_a_insertar)
        mysql_conn.commit() 
        print(f"✅ Éxito: Se procesaron {len(registros_a_insertar)} métricas.")
        
    except Error as e:
        print(f"❌ Error MySQL: {e}")
        mysql_conn.rollback()
    finally:
        mysql_cursor.close()
        mysql_conn.close()
        print("🔌 Conexiones cerradas.")

# --- EJECUCIÓN ÚNICA PARA PROGRAMADOR DE TAREAS ---
if __name__ == "__main__":
    fetch_and_store_analytics()