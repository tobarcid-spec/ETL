import json
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import mysql.connector
from datetime import datetime
from config.config import DB_CONFIG

def guardar_en_mysql(datos_lista):
    if not datos_lista:
        print("⚠️ No hay datos válidos para insertar.")
        return

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Tabla consolidada para todas las RRSS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comentarios_rrss_consolidado (
                id INT AUTO_INCREMENT PRIMARY KEY,
                red_social VARCHAR(50),
                video_url TEXT,
                usuario VARCHAR(255),
                comentario TEXT,
                likes_num INT,
                fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        query = """INSERT INTO comentarios_rrss_consolidado 
                   (red_social, video_url, usuario, comentario, likes_num) 
                   VALUES (%s, %s, %s, %s, %s)"""
        
        cursor.executemany(query, datos_lista)
        conn.commit()
        print(f"✅ Éxito: Se insertaron {cursor.rowcount} registros en la base de datos.")
        
    except mysql.connector.Error as err:
        print(f"❌ Error MySQL: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def mapear_datos_rrss(item):
    """
    Detecta la red social basándose en los campos típicos de Apify
    y retorna una tupla (red_social, url, usuario, texto, likes)
    """
    # 1. DETECCIÓN DE FACEBOOK
    if 'facebookUrl' in item or 'facebookId' in item:
        red = 'Facebook'
        url = item.get('facebookUrl') or item.get('postUrl') or 'URL FB no disponible'
        usuario = item.get('profileName') or item.get('facebookId') or 'Anónimo FB'
        texto = item.get('commentText') or item.get('text', '')
        likes = item.get('reactionsCount') or item.get('likesCount', 0)
    
    # 2. DETECCIÓN DE TIKTOK
    elif 'videoWebUrl' in item or 'aweme_id' in item:
        red = 'TikTok'
        url = item.get('videoWebUrl') or item.get('videoUrl') or 'URL TikTok no disponible'
        usuario = item.get('uniqueId') or item.get('authorMeta', {}).get('name', 'Anónimo TK')
        texto = item.get('text', '')
        likes = item.get('diggCount', 0)
        
    # 3. DETECCIÓN DE INSTAGRAM
    elif 'ownerUsername' in item or 'shortCode' in item:
        red = 'Instagram'
        url = item.get('postUrl') or f"https://www.instagram.com/p/{item.get('shortCode')}/"
        usuario = item.get('ownerUsername') or item.get('ownerId') or 'Anónimo IG'
        texto = item.get('text', '')
        likes = item.get('likesCount', 0)
        
    else:
        # Si no reconoce los campos, intenta una detección genérica
        red = 'Desconocida'
        url = 'N/A'
        usuario = 'N/A'
        texto = item.get('text', 'Sin contenido')
        likes = 0
        return None # Omitir si no se reconoce

    return (red, url, usuario, texto, likes)

def procesar_carpeta(carpeta_path):
    registros_finales = []
    
    if not os.path.exists(carpeta_path):
        print(f"❌ Carpeta '{carpeta_path}' no encontrada.")
        return []

    for archivo in os.listdir(carpeta_path):
        if archivo.endswith('.json'):
            print(f"📂 Analizando: {archivo}...")
            with open(os.path.join(carpeta_path, archivo), 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    lista_items = data if isinstance(data, list) else [data]
                    
                    for item in lista_items:
                        tupla_mapeada = mapear_datos_rrss(item)
                        if tupla_mapeada:
                            registros_finales.append(tupla_mapeada)
                except Exception as e:
                    print(f"⚠️ Error en archivo {archivo}: {e}")

    return registros_finales

if __name__ == "__main__":
    # Coloca aquí la carpeta donde guardas todos tus JSON de Apify
    CARPETA_INPUT = "./descargas_apify" 
    
    datos_para_bd = procesar_carpeta(CARPETA_INPUT)
    
    if datos_para_bd:
        print(f"📊 Total de registros detectados: {len(datos_para_bd)}")
        guardar_en_mysql(datos_para_bd)