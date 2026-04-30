import requests
import time
import pywhatkit as pwk
from datetime import datetime

# Configuración
URL_JSON = "https://www.t13.cl/export/t13/recientes.json"
PHONE_NUMBER = "+56951967939" # Reemplaza con tu número
INTERVALO = 60 

# Historial para no repetir noticias
ids_vistos = set()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def enviar_whatsapp(titulo, fecha, url):
    mensaje = (
        f"🚨 *NUEVA NOTICIA T13*\n\n"
        f"*Título:* {titulo}\n"
        f"*Publicado:* {fecha}\n\n"
        f"🔗 *Link:* https://www.t13.cl{url}"
    )
    try:
        # wait_time=15 da margen para que cargue WhatsApp Web
        # tab_close=True cierra la pestaña después de enviar
        pwk.sendwhatmsg_instantly(PHONE_NUMBER, mensaje, wait_time=15, tab_close=True)
        print(f"✅ WhatsApp enviado: {titulo[:30]}...")
    except Exception as e:
        print(f"❌ Error al enviar WhatsApp: {e}")

def monitor_t13():
    global ids_vistos
    timestamp_log = datetime.now().strftime('%H:%M:%S')
    
    try:
        response = requests.get(URL_JSON, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            return

        # Revisamos los 3 registros más recientes del JSON
        noticias_recientes = data[:3]

        # Si es la primera ejecución, llenamos el set para tener un punto de partida
        if not ids_vistos:
            for n in noticias_recientes:
                ids_vistos.add(str(n.get('id')))
            print(f"[{timestamp_log}] Monitor iniciado. Esperando noticias nuevas...")
            return

        # Procesamos de la más antigua a la más nueva (dentro de las 3)
        # para que el orden de los mensajes en WhatsApp sea lógico
        for noticia in reversed(noticias_recientes):
            n_id = str(noticia.get('id'))
            n_titulo = noticia.get('title')
            # Extraemos la fecha (ajusta el nombre del campo si el JSON usa otro)
            n_fecha = noticia.get('fecha_publicacion', 'Recién publicado') 
            n_url = noticia.get('url')

            if n_id not in ids_vistos:
                print(f"[{timestamp_log}] Detectada: {n_titulo}")
                
                # Acción: Enviar a WhatsApp
                enviar_whatsapp(n_titulo, n_fecha, n_url)
                
                # Registrar en el historial
                ids_vistos.add(n_id)
                
                # Pequeña pausa entre envíos si hay más de una noticia
                time.sleep(2)

        # Limpieza periódica del set para no saturar memoria
        if len(ids_vistos) > 100:
            ids_vistos = set(list(ids_vistos)[-50:])

    except Exception as e:
        print (f"[{timestamp_log}] ❌ Error: {e}")
        
if __name__ == "__main__":
    print("--- Monitor T13 Activo con Notificaciones WhatsApp ---")
    while True:
        monitor_t13()
        time.sleep(INTERVALO)