import os
import sys
from googleapiclient.discovery import build
from typing import List, Dict, Any
from datetime import datetime
import mysql.connector
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- 1. Configuración de la API de YouTube ---
# ⚠️ ADVERTENCIA: REEMPLAZAR CON SU CLAVE DE API REAL.
API_KEY = "AIzaSyDc75yPe--BM4npEhN5Yak3xdUnbKh_0Jc" 

# --- 2. IDs de las Playlists ---
# Incluye los IDs de las playlists de los distintos programas.
PLAYLIST_IDS = [
    #"PLnDONcPxnlq1nd_fUgWP1HRRfC0IM-Yid", #rubias
   #"PLnDONcPxnlq0gsDqssXR_4qLJw6nZxr0P",   #mejor tarde que nunca
   #"PLnDONcPxnlq1EIJBdDudf8nevmiOa1F3e", #mas alla
  # "PLnDONcPxnlq2TP6-7tGeziddRi6lXpaXB", #react mundos opuestos 3
    "PLnDONcPxnlq2-RSqqPKQqJI4uX7nOJAWc",#capitulos
    "PLnDONcPxnlq119ofzfS0-5B0khdaYtGsW", #señal fanaticos
    "PLnDONcPxnlq2rx9ACstBKfnvD31CAzFsq", #señal extendida
    "PLnDONcPxnlq1tGG4AObU4k2dNL2XTRT79", # momnentos mundos
    "PLnDONcPxnlq1bR1AHL1Xy097-MhteCJgk" # resumen capitulos
]
# --- 3. Configuración de MySQL ---

# Nombre de la tabla
TABLE_NAME = "C13_Pdigitales"

# =================================================================
# 🔗 FUNCIONES DE MYSQL
# =================================================================

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar con MySQL: {err}")
        return None

def upsert_youtube_stats(conn: Any, stats: Dict[str, Any]):
    """
    Intenta actualizar o insertar un registro usando el video_id como clave única.
    """
    cursor = conn.cursor()
    fecha_carga = datetime.now().strftime("%Y-%m-%d")
    
    # 1. INTENTAR ACTUALIZAR (UPDATE)
    
    # Valores para UPDATE: v_youtube, fecha_carga, fecha, programa, capitulo
    update_values = (
        stats['view_count'],          
        fecha_carga,                  
        stats['published_at'],        
        stats['programa'],            
        stats['capitulo'],
        # Clave WHERE
        stats['video_id']             # video_id (WHERE)
    )

    update_query = f"""
    UPDATE {TABLE_NAME}
    SET 
        v_youtube = %s,
        fecha_carga = %s,
        fecha = %s,              -- Actualizamos la fecha de publicación por si se corrigió el dato
        programa = %s,           -- Actualizamos el programa por si se corrigió el parseo
        capitulo = %s            -- Actualizamos el capítulo por si el título cambió
    WHERE 
        video_id = %s            -- USAMOS EL ID PERMANENTE DEL VIDEO
    """
    
    cursor.execute(update_query, update_values)
    
    # Si la actualización afectó a 0 filas, el registro no existe, por lo que INSERTAMOS.
    if cursor.rowcount == 0:
        # 2. INSERTAR (Si no existe)
        print(f"   -> [INSERTANDO]: Video ID: {stats['video_id']} | Capítulo: {stats['capitulo']}")
        insert_query = f"""
        INSERT INTO {TABLE_NAME} 
            (fecha_carga, fecha, v_youtube, programa, capitulo, video_id)
        VALUES 
            (%s, %s, %s, %s, %s, %s)
        """
        
        insert_values = (
            fecha_carga,             # fecha_carga
            stats['published_at'],   # fecha
            stats['view_count'],     # v_youtube
            stats['programa'],        # programa
            stats['capitulo'],         # capitulo
            stats['video_id']         # video_id (Nuevo campo)
        )
        
        cursor.execute(insert_query, insert_values)
    else:
        print(f"   -> [ACTUALIZANDO]: Video ID: {stats['video_id']} | Capítulo: {stats['capitulo']}")

    conn.commit()
    cursor.close()

# =================================================================
# ☁️ FUNCIONES DE YOUTUBE (MODIFICADAS)
# =================================================================

def get_youtube_service():
    """Inicializa y devuelve el servicio de la API de YouTube."""
    try:
        if API_KEY == "SU_API_KEY_AQUI":
            print("ERROR: Por favor, actualice 'API_KEY' en la sección de configuración.")
            return None
        return build("youtube", "v3", developerKey=API_KEY)
    except Exception as e:
        print(f"Error al inicializar el servicio de YouTube: {e}")
        return None

def get_all_video_ids_from_playlist(youtube: Any, playlist_id: str) -> List[str]:
    """Obtiene todos los IDs de video de una lista de reproducción, manejando la paginación."""
    print(f"-> Buscando IDs de video en la playlist: {playlist_id}")
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
            video_id = item["contentDetails"]["videoId"]
            video_ids.append(video_id)
        
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
        
    print(f"-> ¡Paginación completa! Total de videos encontrados: {len(video_ids)}")
    return video_ids

def get_video_stats(youtube: Any, video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Obtiene las estadísticas, fecha de publicación, y PARSEA el título
    para obtener el nombre del programa y el capítulo.
    """
    all_stats = []
    BATCH_SIZE = 50 
    
    print("\n-> Obteniendo estadísticas de vistas y fechas de publicación...")

    for i in range(0, len(video_ids), BATCH_SIZE):
        batch_ids = video_ids[i:i + BATCH_SIZE]
        id_string = ",".join(batch_ids) 
        
        request = youtube.videos().list(
            part="snippet,statistics", 
            id=id_string
        )
        response = request.execute()
        
        for item in response.get("items", []):
            try:
                full_title = item["snippet"]["title"].strip()
                published_at_str = item["snippet"]["publishedAt"]
                view_count = int(item["statistics"].get("viewCount", 0)) 
                
                # --- Lógica de PARSEO MODIFICADA ---
                # Divide el título por el primer '|'
                if "|" in full_title:
                    programa_name = full_title.split("|")[0].strip()
                    capitulo_name = full_title.split("|", 1)[1].strip() # Resto del título como capítulo
                else:
                    # Caso de respaldo si no hay '|'
                    programa_name = "Sin Programa Identificado"
                    capitulo_name = full_title
                
                # Formato de fecha
                published_datetime = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                
                all_stats.append({
                    "video_id": item["id"],
                    "programa": programa_name,       # Nombre del programa (antes del '|')
                    "capitulo": capitulo_name,       # Resto del título (después del '|')
                    "view_count": view_count,
                    "published_at": published_datetime.strftime("%Y-%m-%d") 
                })
            except KeyError as e:
                print(f"   [AVISO] No se pudieron obtener estadísticas para el video {item.get('id', 'N/A')}. Error: {e}")
            
    return all_stats

# =================================================================
# 🚀 FUNCIÓN PRINCIPAL ADAPTADA
# =================================================================

def main():
    """Función principal para coordinar la obtención de datos de YouTube y la actualización de MySQL."""
    
    if API_KEY == "SU_API_KEY_AQUI":
        print("❌ ERROR: Por favor, actualice 'API_KEY' en la sección de configuración.")
        return

    # Conexión a MySQL
    db_conn = get_db_connection()
    if not db_conn:
        print("❌ Fallo al conectar con la base de datos. Saliendo.")
        return

    # Inicialización del servicio de YouTube
    youtube = get_youtube_service()
    if not youtube:
        db_conn.close()
        return

    # Iterar sobre todas las Playlists configuradas
    print(f"\n{'='*70}\n✨ INICIANDO PROCESO PARA {len(PLAYLIST_IDS)} PLAYLISTS ✨\n{'='*70}")
    
    total_videos_procesados = 0
    total_vistas_totales = 0

    for i, playlist_id in enumerate(PLAYLIST_IDS):
        print(f"\n--- [PLAYLIST {i+1} de {len(PLAYLIST_IDS)}: ID {playlist_id}] ---")
        
        # 1. Obtener todos los IDs de la playlist
        video_ids = get_all_video_ids_from_playlist(youtube, playlist_id)

        if not video_ids:
            print("No se encontraron videos en la playlist.")
            continue

        # 2. Obtener estadísticas, fechas y PARSEAR el título
        stats_list = get_video_stats(youtube, video_ids)
        total_videos_procesados += len(stats_list)

        if not stats_list:
            print("No se pudieron obtener estadísticas para los videos.")
            continue
            
        # 3. Procesar e insertar/actualizar en MySQL
        print(f"\n-> Iniciando proceso de UPSERT en MySQL para {len(stats_list)} videos...")
        playlist_views = 0
        
        for stats in stats_list:
            upsert_youtube_stats(db_conn, stats)
            playlist_views += stats['view_count']

        total_vistas_totales += playlist_views
        views_formatted = f"{playlist_views:,}".replace(",", ".") 
        print(f"\n✅ Playlist {i+1} completada. Vistas totales de esta playlist: {views_formatted}")
    
    # Cierre de la conexión
    db_conn.close()
    
    views_total_formatted = f"{total_vistas_totales:,}".replace(",", ".") 
    print(f"\n{'='*70}")
    print(f"🎉 PROCESO FINALIZADO.")
    print(f"Total de Videos Procesados: {total_videos_procesados}")
    print(f"Vistas Totales Agregadas/Actualizadas: {views_total_formatted}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()