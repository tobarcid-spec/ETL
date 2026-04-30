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
FECHA_INICIO = datetime(2026,3, 1)  
FECHA_FIN = datetime(2026, 3, 31)    

def generar_rango_fechas(start_date, end_date):
    """Genera una lista de días entre el rango definido."""
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

def procesar_dia_live(fecha_obj):
    """Consulta e inserta los datos agregados de Live de un día específico."""
    fecha_str = fecha_obj.strftime('%Y-%m-%d')
    
    payload = {
        "token": TOKEN,
        "slug": "c13",
        "date_start": f"{fecha_str} 00:00:00",
        "date_end": f"{fecha_str} 23:59:59",
        "type": "overview",  # Se mantiene overview para el total diario
        "format": "live"
    }

    try:
        response = requests.post(API_URL_MANGO, data=payload)
        response.raise_for_status()
        data = response.json()
        
        # Validar si recibimos datos (La respuesta de Live suele ser un diccionario directo)
        if not data or 'plays' not in data:
            print(f"Empty: No hay datos Live para el día {fecha_str}")
            return

        # Inserción en la nueva tabla c13_live_video
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # SQL adaptado para los campos de Live y valor fijo C13
        sql = """
            INSERT INTO c13_live_video (
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

        # Mapeo directo de la respuesta JSON
        valores = (
            "c13", 
            data.get('plays', 0), 
            data.get('streams', 0),
            data.get('devices', 0), 
            data.get('time_total', ""), 
            data.get('average_time', ""), 
            fecha_str
        )

        cursor.execute(sql, valores)
        connection.commit()
        
        print(f"✅ {fecha_str}: Datos Live cargados (Plays: {data.get('plays')})")
        
        cursor.close()
        connection.close()

    except Exception as e:
        print(f"❌ Error procesando el día {fecha_str}: {e}")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    print(f"Iniciando carga histórica LIVE desde {FECHA_INICIO.date()} hasta {FECHA_FIN.date()}...")
    
    for solo_dia in generar_rango_fechas(FECHA_INICIO, FECHA_FIN):
        procesar_dia_live(solo_dia)
        
    print("🚀 Carga histórica Live finalizada.")