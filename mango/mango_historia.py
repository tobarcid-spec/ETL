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
FECHA_INICIO = datetime(2026,3,1)  # Año, Mes, Día de inicio
FECHA_FIN = datetime(2026,3,31)    # Hasta hoy o una fecha específica

def generar_rango_fechas(start_date, end_date):
    """Genera una lista de días entre el rango definido."""
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def procesar_dia(fecha_obj):
    """Consulta e inserta los datos de un día específico."""
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    
    payload = {
        "token": TOKEN,
        "slug": "c13",
        "date_start": f"{fecha_str} 00:00:00",
        "date_end": f"{fecha_str} 23:59:59",
        "type": "overview",
        "format": "vod"
    }

    try:
        response = requests.post(API_URL_MANGO, data=payload)
        response.raise_for_status()
        data = response.json()
        
        # Extraer lista de videos (ajustar si la llave es 'data' o similar)
        if isinstance(data, dict):
            videos = data.get('vod', [])
        else:
            videos = data

        if not videos:
            print(f"Empty: No hay datos para el día {fecha_str}")
            return

        # Inserción en MySQL
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        sql = """
            INSERT IGNORE INTO c13_metricas_video (
                video_id, epoch, plays, streams, devices, 
                time_total, average_time, epoch_start_tmp, epoch_end_tmp, fecha_consulta
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        valores = []
        for m in videos:
            valores.append((
                m.get('id'), m.get('epoch'), m.get('plays'), m.get('streams'),
                m.get('devices'), m.get('time_total'), m.get('average_time'),
                m.get('epoch_start_tmp'), m.get('epoch_end_tmp'), fecha_str
            ))

        cursor.executemany(sql, valores)
        connection.commit()
        print(f"✅ {fecha_str}: {cursor.rowcount} registros cargados.")
        
        cursor.close()
        connection.close()

    except Exception as e:
        print(f"❌ Error procesando el día {fecha_str}: {e}")

# --- EJECUCIÓN DEL FOR ---
if __name__ == "__main__":
    print(f"Iniciando carga histórica desde {FECHA_INICIO.date()} hasta {FECHA_FIN.date()}...")
    
    for solo_dia in generar_rango_fechas(FECHA_INICIO, FECHA_FIN):
        procesar_dia(solo_dia)
        
    print("🚀 Carga histórica finalizada.")