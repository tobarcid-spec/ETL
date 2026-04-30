import mysql.connector
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime
import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyDc75yPe--BM4npEhN5Yak3xdUnbKh_0Jc" # ⚠️ Tu API KEY real
FILE_NAME = "playlists.xlsx"

def inicializar_tabla():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
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
    except Exception as e:
        print(f"❌ Error DB: {e}")

def detect_type(url_or_id):
    if pd.isna(url_or_id): return None, None
    str_url = str(url_or_id).strip()
    if "list=" in str_url:
        match = re.search(r"list=([a-zA-Z0-9_-]+)", str_url)
        return "playlist", match.group(1) if match else str_url
    elif "v=" in str_url:
        match = re.search(r"v=([a-zA-Z0-9_-]+)", str_url)
        return "video", match.group(1) if match else str_url
    else:
        return ("video", str_url) if len(str_url) <= 15 else ("playlist", str_url)

def get_video_stats(youtube, video_ids):
    all_stats = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        res = youtube.videos().list(part="snippet,statistics", id=",".join(batch)).execute()
        for item in res.get("items", []):
            all_stats.append({
                'id': item['id'],
                'title': item['snippet']['title'],
                'views': int(item['statistics'].get('viewCount', 0)),
                'published': item['snippet']['publishedAt'][:10]
            })
    return all_stats

def save_data(etiqueta, id_playlist, video_stats):
    if not video_stats: return
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = """
        INSERT INTO c13_yt_metricas 
        (etiqueta, id_playlist, video_id, titulo, vistas, fecha_publicacion, fecha_carga) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE vistas = VALUES(vistas), fecha_carga = VALUES(fecha_carga)
    """
    valores = [(etiqueta, id_playlist, v['id'], v['title'], v['views'], v['published'], ahora) for v in video_stats]
    cursor.executemany(query, valores)
    conn.commit()
    cursor.close()
    conn.close()

def main():
    if not os.path.exists(FILE_NAME):
        print(f"❌ No se encontró {FILE_NAME}")
        return

    inicializar_tabla()
    
    # LEER EXCEL Y LIMPIAR COLUMNAS
    df = pd.read_excel(FILE_NAME)
    # Esto convierte 'URL ', 'Url', 'URL' -> 'url' automáticamente
    df.columns = [c.lower().strip() for c in df.columns]

    if 'url' not in df.columns or 'etiqueta' not in df.columns:
        print(f"❌ Error: El Excel debe tener columnas llamadas 'etiqueta' y 'url'. Columnas detectadas: {list(df.columns)}")
        return

    youtube = build("youtube", "v3", developerKey=API_KEY)
    print(f"🚀 Procesando {len(df)} registros...")

    for _, row in df.iterrows():
        etiqueta = row['etiqueta']
        tipo, content_id = detect_type(row['url'])
        if not content_id: continue

        try:
            if tipo == "playlist":
                v_ids = []
                next_page_token = None
                while True:
                    req = youtube.playlistItems().list(part="contentDetails", playlistId=content_id, maxResults=50, pageToken=next_page_token)
                    res = req.execute()
                    v_ids.extend([item["contentDetails"]["videoId"] for item in res.get("items", [])])
                    next_page_token = res.get("nextPageToken")
                    if not next_page_token: break
                stats = get_video_stats(youtube, v_ids)
                save_data(etiqueta, content_id, stats)
            else:
                stats = get_video_stats(youtube, [content_id])
                save_data(etiqueta, "SINGLE_VIDEO", stats)
            print(f"✅ {etiqueta} ok.")
        except Exception as e:
            print(f"❌ Error en {etiqueta}: {e}")

if __name__ == "__main__":
    main()