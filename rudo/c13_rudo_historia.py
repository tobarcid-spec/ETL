import requests
import mysql.connector
from mysql.connector import Error
import time
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

API_URL = "https://api.rudo.video/api/getvideos"
#836a8d85a4f60d312efc09db30b0dd00206810018eb1f48b2cc729c4e4f5cd4b  T13
#158756bd0a1cf79aad55f8285c87d51349c4fe2c1640dbafcbe55422e4b16e12  C13
API_KEY = "836a8d85a4f60d312efc09db30b0dd00206810018eb1f48b2cc729c4e4f5cd4b"  # Cambia por la clave de C13 si es necesario

# CONFIGURACIÓN DEL HISTÓRICO
START_INICIAL = 0 # Punto de inicio para la paginación
TOTAL_A_TRAER = 5000  # Ajusta según tus necesidades
BLOQUE = 200 # Cantidad de registros a traer por bloque (máximo recomendado: 200)

def obtener_datos(start, limit):
    """Consulta un bloque específico de la API."""
    params = {
        "start": start,
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
        print(f"❌ Error al consultar la API en start {start}: {e}")
        return []

def procesar_carga(videos):
    """Inserta el bloque de videos en MySQL incluyendo los tags."""
    if not videos:
        return 0

    connection = None
    nuevos = 0
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        sql = """
            INSERT IGNORE INTO T13_videos_rudo (
                id, video_key, titulo, descripcion, descripcion_html, fecha, fecha_f,
                img_high, img_medium, img_small,
                estado, estado_num, estado_icon, tipo, compartir, publico, publico_icon,
                duracion, podcast, origen, nombre_carpeta, id_carpeta, is_square,
                url_download, url_firstvideo, url_lowvideo, url_hls, restriction, tags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        lista_insertar = []
        for v in videos:
            if not isinstance(v, dict): continue
            
            imgs = v.get('imagenes', {})
            if not isinstance(imgs, dict): imgs = {}
            
            # --- PROCESAMIENTO DE TAGS (Máximo 3, separados por |) ---
            tags_list = v.get('tags', [])
            if isinstance(tags_list, list):
                # Extraemos el 'nombre' de los primeros 3 y unimos con |
                nombres_tags = [t.get('nombre') for t in tags_list[:3] if isinstance(t, dict)]
                tags_string = " | ".join(nombres_tags)
            else:
                tags_string = None

            fila = (
                v.get('id'), v.get('key'), v.get('titulo'), v.get('descripcion'),
                v.get('descripcion_html'), v.get('fecha'), v.get('fecha_f'),
                imgs.get('high'), imgs.get('medium'), imgs.get('small'),
                v.get('estado'), v.get('estado_num'), v.get('estado_icon'),
                v.get('tipo'), v.get('compartir'), v.get('publico'), v.get('publico_icon'),
                v.get('duracion'), v.get('podcast'), v.get('origen'),
                v.get('nombre_carpeta'), v.get('id_carpeta'), v.get('is_square'),
                v.get('download'), v.get('firstvideo'), v.get('lowvideo'),
                v.get('hls'), v.get('restriction'), tags_string
            )
            lista_insertar.append(fila)

        if lista_insertar:
            cursor.executemany(sql, lista_insertar)
            connection.commit()
            nuevos = cursor.rowcount
            
    except Error as e:
        print(f"❌ Error de MySQL: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
    return nuevos

if __name__ == "__main__":
    current_start = START_INICIAL
    fin_objetivo = START_INICIAL + TOTAL_A_TRAER
    total_nuevos_acumulados = 0

    print(f"🚀 Iniciando carga histórica con TAGS (sep: |) desde {START_INICIAL} a {fin_objetivo}...")

    while current_start < fin_objetivo:
        print(f"📥 Solicitando bloque: start={current_start}, limit={BLOQUE}...", end=" ")
        datos_bloque = obtener_datos(current_start, BLOQUE)
        
        if not datos_bloque:
            print("\nFin de datos.")
            break
            
        nuevos_en_bloque = procesar_carga(datos_bloque)
        total_nuevos_acumulados += nuevos_en_bloque
        
        print(f"OK (+{nuevos_en_bloque} nuevos)")
        current_start += BLOQUE
        time.sleep(0.5)

    print(f"\n✨ Proceso terminado.")
    print(f"📊 Total analizados: {current_start - START_INICIAL}")
    print(f"💾 Total nuevos insertados: {total_nuevos_acumulados}")