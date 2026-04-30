import requests
import mysql.connector
from datetime import datetime
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- CONFIGURACIÓN GENERAL ---
API_URL = "https://www.13.cl/export/13/recientes.json"
TABLE_ARTICULOS = "c13_articulos"

# --- UTILIDADES ---
def convertir_fecha(raw_fecha):
    """Convierte 'DD/MM/YYYY - HH:MM' a 'YYYY-MM-DD HH:MM:SS'."""
    try:
        dt_object = datetime.strptime(raw_fecha, "%d/%m/%Y - %H:%M")
        return dt_object.strftime("%Y-%m-%d %H:%M:00")
    except (ValueError, TypeError):
        return raw_fecha

def get_mysql_connection():
    """Establece y devuelve la conexión a MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error al conectar a MySQL: {err}")
        return None

def fetch_and_store_data_mysql():
    """Consulta la API e inserta/ignora artículos en MySQL."""
    
    fecha_ejecucion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n--- INICIO DE ACTUALIZACIÓN: {fecha_ejecucion} ---")
    
    conn = get_mysql_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    try:
        # Obtener datos de la API
        print(f"🌐 Consultando API: {API_URL}")
        with requests.Session() as session:
            response = session.get(API_URL, timeout=30) # Añadido timeout por seguridad
            response.raise_for_status() 
            articulos = response.json()
            
        registros_a_insertar = []
        
        for item in articulos:
            url_id = item.get("url")
            if not url_id:
                continue

            fecha_formateada = convertir_fecha(item.get("fecha"))
            
            cuerpo_extension = item.get("cuerpo_extension")
            try:
                cuerpo_extension = int(cuerpo_extension) if cuerpo_extension else None
            except (ValueError, TypeError):
                cuerpo_extension = None
            
            registros_a_insertar.append((
                url_id, item.get("titulo"), item.get("bajada"), item.get("url"), item.get("autor"), 
                fecha_formateada, item.get("imagen"), item.get("categorias"), item.get("temas"), 
                item.get("cuerpo"), cuerpo_extension, item.get("tipo"), fecha_ejecucion
            ))

        # Preparar SQL
        columnas = "(id_articulo, titulo, bajada, url, autor, fecha, imagen, categorias, temas, cuerpo, cuerpo_extension, tipo, fecha_descarga)"
        placeholders = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        sql_insert = f"INSERT IGNORE INTO {TABLE_ARTICULOS} {columnas} VALUES {placeholders}"
        
        # Ejecutar inserción
        cursor.executemany(sql_insert, registros_a_insertar)
        nuevos_registros = cursor.rowcount 
        conn.commit()
        
        print(f"💾 Proceso terminado.")
        print(f"📊 Resumen: {nuevos_registros} registros nuevos insertados.")
        print(f"📊 Total procesados: {len(registros_a_insertar)}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red o API: {e}")
    except mysql.connector.Error as e:
        print(f"❌ Error de Base de Datos: {e}")
    finally:
        # Asegurar siempre el cierre de recursos
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("🔌 Conexión a MySQL cerrada.")

# --- EJECUCIÓN ÚNICA ---
if __name__ == "__main__":
    fetch_and_store_data_mysql()