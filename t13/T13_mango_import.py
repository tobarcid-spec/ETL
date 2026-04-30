import requests
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

API_URL_MANGO = "https://api-mango.digitalproserver.com/"

# Fecha de ayer para traer métricas cerradas
ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

PAYLOAD = {
    "token": "9feb892a7cc282a6829354b7db9449afeeeb39e8eb5b4c4e2a94532bedc2c487",
    "slug": "T13",
    "date_start": f"{ayer} 00:00:00",
    "date_end": f"{ayer} 23:59:59",
    "type": "overview",
    "format": "vod"
}

def obtener_metricas():
    try:
        # Enviamos por POST como solicita la API
        response = requests.post(API_URL_MANGO, data=PAYLOAD)
        response.raise_for_status()
        res_json = response.json()
        
        # Mango suele devolver la lista en una llave 'data' o directo
        if isinstance(res_json, dict):
            return res_json.get('vod', [])
        return res_json
    except Exception as e:
        print(f"❌ Error API Mango: {e}")
        return []

def cargar_metricas(data):
    if not data:
        print("⚠️ No hay métricas para cargar.")
        return

    connection = None
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        sql = """
            INSERT IGNORE INTO T13_metricas_video (
                video_id, epoch, plays, streams, devices, 
                time_total, average_time, epoch_start_tmp, epoch_end_tmp, fecha_consulta
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        valores = []
        for m in data:
            fila = (
                m.get('id'),
                m.get('epoch'),
                m.get('plays'),
                m.get('streams'),
                m.get('devices'),
                m.get('time_total'),
                m.get('average_time'),
                m.get('epoch_start_tmp'),
                m.get('epoch_end_tmp'),
                ayer # Guardamos la fecha a la que corresponden las métricas
            )
            valores.append(fila)

        cursor.executemany(sql, valores)
        connection.commit()
        print(f"✅ Métricas de {ayer} cargadas. Registros nuevos: {cursor.rowcount}")

    except Error as e:
        print(f"❌ Error MySQL: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    print(f"Consultando métricas Mango para la fecha: {ayer}")
    metricas = obtener_metricas()
    cargar_metricas(metricas)