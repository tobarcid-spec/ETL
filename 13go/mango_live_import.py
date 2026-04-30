import requests
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

API_URL_MANGO = "https://api-mango.digitalproserver.com/"
TOKEN = "9feb892a7cc282a6829354b7db9449afeeeb39e8eb5b4c4e2a94532bedc2c487"

# --- MAPEO DE CANALES Y TABLAS ---
CHANNELS_MAPPING = {
    "c13": "c13_live_video",
    "T13": "T13_live_video",
    # Canales que van a la tabla FAST
    "13CULTURA": "Fast_live_video",
    "13FESTIVAL": "Fast_live_video",
    "13COCINA": "Fast_live_video",
    "13d": "Fast_live_video",
    "futgo": "Fast_live_video",
    "13KIDS": "Fast_live_video",
    "13POP": "Fast_live_video",
    "13REALITIES": "Fast_live_video",
    "13TELESERIES": "Fast_live_video",
    "13VIAJES": "Fast_live_video",
    "13evt5": "Fast_live_video",
    "13LIVE": "Fast_live_video",
    "realitypremium":"Fast_live_video",
    "13humor": "Fast_live_video",
    "13c": "Fast_live_video",
    "rectv": "Fast_live_video"
}

def ejecutar_carga_diaria():
    # 1. Definir fecha (Ayer)
    ayer = datetime.now() - timedelta(days=1)
    fecha_str = ayer.strftime('%Y-%m-%d')
    
    print(f"==========================================")
    print(f" INICIANDO CARGA DIARIA: {fecha_str}")
    print(f"==========================================")
    
    conn = None
    try:
        # 2. Conectar a la base de datos
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 3. Recorrer cada canal configurado
        for slug_api, tabla_destino in CHANNELS_MAPPING.items():
            # Variables de control locales para evitar persistencia de datos erróneos
            current_slug = str(slug_api)
            current_table = str(tabla_destino)
            
            print(f"-> Procesando {current_slug}...")

            payload = {
                "token": TOKEN,
                "slug": current_slug,
                "date_start": f"{fecha_str} 00:00:00",
                "date_end": f"{fecha_str} 23:59:59",
                "type": "overview",
                "format": "live"
            }

            try:
                # 4. Llamada a la API
                response = requests.post(API_URL_MANGO, data=payload, timeout=25)
                response.raise_for_status()
                data = response.json()

                if not data or 'plays' not in data:
                    print(f"   [!] Sin datos para {current_slug}")
                    continue

                # 5. Preparar SQL (Inserta o Actualiza si ya existe la dupla Fecha+Canal)
                sql = f"""
                    INSERT INTO {current_table} (
                        canal, plays, streams, devices, 
                        time_total, average_time, fecha_consulta
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        plays = VALUES(plays), 
                        streams = VALUES(streams),
                        devices = VALUES(devices),
                        time_total = VALUES(time_total),
                        average_time = VALUES(average_time)
                """

                valores = (
                    current_slug, 
                    data.get('plays', 0), 
                    data.get('streams', 0),
                    data.get('devices', 0), 
                    data.get('time_total', ""), 
                    data.get('average_time', ""), 
                    fecha_str
                )

                # 6. Ejecutar y confirmar
                cursor.execute(sql, valores)
                conn.commit() 
                print(f"   [OK] Guardado en {current_table} | Plays: {data.get('plays')}")

            except Exception as e:
                print(f"   [ERROR] Falló canal {current_slug}: {e}")

        cursor.close()

    except Error as e:
        print(f"❌ ERROR CRÍTICO DE CONEXIÓN: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            print(f"==========================================")
            print(f" PROCESO FINALIZADO - CONEXIÓN CERRADA")
            print(f"==========================================")

if __name__ == "__main__":
    ejecutar_carga_diaria()