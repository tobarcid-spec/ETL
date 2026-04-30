import requests
import mysql.connector
from mysql.connector import Error
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

API_URL = "https://api.rudo.video/api/getvideos"
# Usando la API KEY que indicaste como funcional
API_KEY = "1fc63b2840d5d7985fa39a4eed0c8821ff539c7393ea5f5c157fa4804079122a"

CANTIDAD_A_TRAER = 2000

def obtener_datos(limit):
    """Consulta la API usando Headers para la autenticación."""
    params = {
        "start": 0,
        "limit": limit,
        "sortCol": "fecha",
        "colOrder": "desc"
    }
    
    headers = {
        "X-ACCESS-TOKEN": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(API_URL, params=params, headers=headers)
        response.raise_for_status()
        res_json = response.json()
        
        if isinstance(res_json, dict):
            return res_json.get('data', res_json.get('videos', []))
        return res_json if isinstance(res_json, list) else []
        
    except Exception as e:
        print(f"❌ Error al consultar la API: {e}")
        return []

def procesar_carga(videos):
    """Limpia los datos e inserta en MySQL incluyendo los TAGS."""
    if not videos or not isinstance(videos, list):
        print("⚠️ No se encontraron videos para procesar o el formato es incorrecto.")
        return

    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL actualizado con el campo 'tags' al final
        sql = """
            INSERT IGNORE INTO c13_videos_rudo (
                id, video_key, titulo, descripcion, descripcion_html, fecha, fecha_f,
                img_high, img_medium, img_small,
                estado, estado_num, estado_icon, tipo, compartir, publico, publico_icon,
                duracion, podcast, origen, nombre_carpeta, id_carpeta, is_square,
                url_download, url_firstvideo, url_lowvideo, url_hls, restriction, tags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        lista_insertar = []
        for v in videos:
            if not isinstance(v, dict):
                continue

            # Extraer imágenes de forma segura
            imgs = v.get('imagenes', {})
            if not isinstance(imgs, dict): imgs = {}
            
            # --- ADAPTACIÓN DE TAGS ---
            tags_list = v.get('tags', [])
            if isinstance(tags_list, list):
                # Extraemos 'nombre' de los primeros 3 tags que tengan contenido
                nombres_tags = [t.get('nombre') for t in tags_list[:3] if isinstance(t, dict) and t.get('nombre')]
                tags_string = " | ".join(nombres_tags) if nombres_tags else None
            else:
                tags_string = None

            fila = (
                v.get('id'),
                v.get('key'),
                v.get('titulo'),
                v.get('descripcion'),
                v.get('descripcion_html'),
                v.get('fecha'),
                v.get('fecha_f'),
                imgs.get('high'),
                imgs.get('medium'),
                imgs.get('small'),
                v.get('estado'),
                v.get('estado_num'),
                v.get('estado_icon'),
                v.get('tipo'),
                v.get('compartir'),
                v.get('publico'),
                v.get('publico_icon'),
                v.get('duracion'),
                v.get('podcast'),
                v.get('origen'),
                v.get('nombre_carpeta'),
                v.get('id_carpeta'),
                v.get('is_square'),
                v.get('download'),
                v.get('firstvideo'),
                v.get('lowvideo'),
                v.get('hls'),
                v.get('restriction'),
                tags_string  # Nuevo campo agregado
            )
            lista_insertar.append(fila)

        if lista_insertar:
            cursor.executemany(sql, lista_insertar)
            connection.commit()
            print(f"✅ Proceso completado.")
            print(f"- Elementos recibidos: {len(videos)}")
            print(f"- Nuevos videos guardados en MySQL: {cursor.rowcount}")
        else:
            print("No había datos válidos para insertar.")

    except Error as e:
        print(f"❌ Error de conexión o SQL: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

# --- 2. EJECUCIÓN ---
if __name__ == "__main__":
    print(f"--- Iniciando Importación Diaria con TAGS (Límite: {CANTIDAD_A_TRAER}) ---")
    datos_api = obtener_datos(CANTIDAD_A_TRAER)
    procesar_carga(datos_api)