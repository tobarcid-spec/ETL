import requests
import mysql.connector
import logging
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("script_t13.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

API_URL = "https://www.T13.cl/export/T13/recientes.json"
TABLE_ARTICULOS = "T13_articulos"

def convertir_fecha(raw_fecha):
    if not raw_fecha:
        return None
    try:
        dt_object = datetime.strptime(raw_fecha, "%d/%m/%Y - %H:%M")
        return dt_object.strftime("%Y-%m-%d %H:%M:00")
    except (ValueError, TypeError):
        return None

def fetch_and_store_data_mysql():
    fecha_ejecucion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info("Iniciando proceso de actualizacion...")
    
    conn = None
    cursor = None
    
    try:
        # 1. Obtener datos de la API
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        articulos = response.json()
            
        if not articulos:
            logger.warning("No se recibieron articulos de la API.")
            return

        # 2. Preparar datos
        registros_a_insertar = []
        for item in articulos:
            url_id = item.get("url")
            if not url_id: continue

            registros_a_insertar.append((
                url_id, item.get("titulo"), item.get("bajada"), item.get("url"), 
                item.get("autor"), convertir_fecha(item.get("fecha")), item.get("imagen"), 
                item.get("categorias"), item.get("temas"), item.get("cuerpo"), 
                item.get("cuerpo_extension"), item.get("tipo"), fecha_ejecucion
            ))

        # 3. DB Operaciones
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        columnas = "(id_articulo, titulo, bajada, url, autor, fecha, imagen, categorias, temas, cuerpo, cuerpo_extension, tipo, fecha_descarga)"
        placeholders = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        
        # SQL con detección de duplicados
        sql_insert = f"""
            INSERT INTO {TABLE_ARTICULOS} {columnas} 
            VALUES {placeholders}
            ON DUPLICATE KEY UPDATE 
                fecha_descarga = VALUES(fecha_descarga),
                titulo = VALUES(titulo)
        """
        
        # Ejecutamos uno a uno o por lotes para contar mejor
        # Para mayor precisión en el conteo, usamos un bucle o analizamos el rowcount acumulado
        cursor.executemany(sql_insert, registros_a_insertar)
        
        # Lógica de conteo de MySQL: 
        # total_afectados = (nuevos * 1) + (actualizados * 2)
        total_afectados = cursor.rowcount
        total_procesados = len(registros_a_insertar)
        
        # Estimación de conteos basada en el comportamiento de MySQL
        # Nota: Esto es una aproximación técnica estándar para ON DUPLICATE KEY
        actualizados = total_afectados - total_procesados
        nuevos = total_procesados - actualizados

        conn.commit()
        
        logger.info(f"RESUMEN DE OPERACION:")
        logger.info(f"  - Total procesados de la API: {total_procesados}")
        logger.info(f"  - Nuevos insertados: {max(0, nuevos)}")
        logger.info(f"  - Existentes actualizados: {max(0, actualizados)}")

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected():
            conn.close()
            logger.info("Conexion cerrada.")

if __name__ == "__main__":
    fetch_and_store_data_mysql()