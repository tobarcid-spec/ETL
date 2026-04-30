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

# --- CONFIGURACIÓN DEL RANGO HISTÓRICO ---
FECHA_INICIO = datetime(2026, 3, 1)  # Ajusta tu fecha de inicio aquí
FECHA_FIN = datetime(2026, 3, 31)    # Ajusta tu fecha de fin aquí

# --- MAPEO DE CANALES (SOLO TABLA FAST) ---
CHANNELS_FAST = {
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

def generar_rango_fechas(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def ejecutar_carga_historica_fast():
    print(f"🚀 Iniciando CARGA HISTÓRICA FAST desde {FECHA_INICIO.date()} hasta {FECHA_FIN.date()}...")
    
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Recorremos cada día del rango
        for fecha_obj in generar_rango_fechas(FECHA_INICIO, FECHA_FIN):
            fecha_str = fecha_obj.strftime('%Y-%m-%d')
            print(f"\n--- Procesando fecha: {fecha_str} ---")

            # Recorremos solo los canales del mapeo FAST
            for slug_api, tabla_destino in CHANNELS_FAST.items():
                current_slug = str(slug_api)
                
                payload = {
                    "token": TOKEN,
                    "slug": current_slug,
                    "date_start": f"{fecha_str} 00:00:00",
                    "date_end": f"{fecha_str} 23:59:59",
                    "type": "overview",
                    "format": "live"
                }

                try:
                    response = requests.post(API_URL_MANGO, data=payload, timeout=25)
                    response.raise_for_status()
                    data = response.json()

                    if not data or 'plays' not in data:
                        print(f"   [!] {current_slug}: Sin datos.")
                        continue

                    sql = f"""
                        INSERT INTO {tabla_destino} (
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

                    cursor.execute(sql, valores)
                    conn.commit() 
                    print(f"   [OK] {current_slug} guardado.")

                except Exception as e:
                    print(f"   [ERROR] En {current_slug} para el día {fecha_str}: {e}")

        cursor.close()

    except Error as e:
        print(f"❌ ERROR DE CONEXIÓN A DB: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("\n==========================================")
            print("CARGA HISTÓRICA FINALIZADA")
            print("==========================================")

if __name__ == "__main__":
    ejecutar_carga_historica_fast()