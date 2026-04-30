import mysql.connector
from googleapiclient.discovery import build
from datetime import datetime
import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyDc75yPe--BM4npEhN5Yak3xdUnbKh_0Jc" # ⚠️ RECOMENDACIÓN: Cambia esta clave por seguridad

def inicializar_tabla():
    """Crea la tabla con el Collation correcto para evitar errores de match."""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    # Forzamos utf8mb4_unicode_ci para que coincida con Facebook y el Mapa de Contenidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS c13_yt_metricas (
            id_registro INT AUTO_INCREMENT PRIMARY KEY,
            etiqueta VARCHAR(255),
            id_playlist VARCHAR(100),
            video_id VARCHAR(50),
            titulo TEXT,
            vistas BIGINT,
            fecha_publicacion DATE,
            fecha_carga DATETIME,
            UNIQUE KEY (id_playlist, video_id)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)
    conn.commit()
    cursor.close()
    conn.close()

def extract_playlist_id(url_or_id):
    match = re.search(r"list=([a-zA-Z0-9_-]+)", url_or_id)
    return match.group(1) if match else url_or_id

def get_playlist_videos(youtube, playlist_id):
    video_ids = []
    next_page_token = None
    while True:
        request = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()
        for item in response.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        next_page_token = response.get("nextPageToken")
        if not next_page_token: break
    return video_ids

def save_data(nombre_programa, id_playlist, video_stats):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # MODIFICACIÓN CLAVE: Quitamos 'titulo = VALUES(titulo)' del UPDATE.
    # Así, si el video ya existe, se respeta el título (que ya puede estar limpio por SQL).
    query = """
        INSERT INTO c13_yt_metricas 
        (etiqueta, id_playlist, video_id, titulo, vistas, fecha_publicacion, fecha_carga) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            vistas = VALUES(vistas),
            fecha_carga = VALUES(fecha_carga)
    """
    
    valores = []
    for v in video_stats:
        valores.append((
            nombre_programa, id_playlist, v['id'], v['title'], 
            v['views'], v['published'], ahora
        ))
            
    cursor.executemany(query, valores)
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ [{nombre_programa}] Procesados {len(video_stats)} videos. Vistas actualizadas, títulos preservados.")

def main():
    inicializar_tabla()
    
    youtube = build("youtube", "v3", developerKey=API_KEY)
    tasks = []

    print("📋 CONFIGURACIÓN DE CARGA - YOUTUBE TV DIGITAL")
    while True:
        url = input("\nIngrese URL o ID de Playlist (o 'fin' para procesar): ").strip()
        if url.lower() == 'fin': break
        
        prog_name = input(f"Nombre del programa para esta playlist: ").strip()
        tasks.append({'id': extract_playlist_id(url), 'name': prog_name})

    if not tasks: return

    for task in tasks:
        print(f"Obteniendo videos de '{task['name']}'...")
        v_ids = get_playlist_videos(youtube, task['id'])
        
        all_v_stats = []
        for i in range(0, len(v_ids), 50):
            batch = v_ids[i:i+50]
            res = youtube.videos().list(part="snippet,statistics", id=",".join(batch)).execute()
            for item in res.get("items", []):
                all_v_stats.append({
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'views': int(item['statistics'].get('viewCount', 0)),
                    'published': item['snippet']['publishedAt'][:10]
                })
        
        save_data(task['name'], task['id'], all_v_stats)

if __name__ == "__main__":
    main()