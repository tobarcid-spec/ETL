import asyncio
from playwright.async_api import async_playwright
import re
import mysql.connector
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

def limpiar_titulo_a_capitulo(texto):
    """
    Extrae el número del texto y devuelve 'CAPÍTULO XX'.
    Si no encuentra número, devuelve 'CAPÍTULO 00' o el texto original.
    """
    if not texto:
        return "SIN TÍTULO"
    
    # Busca el primer grupo de dígitos en el texto
    match = re.search(r'(\d+)', texto)
    if match:
        numero = match.group(1)
        # Formatea a dos dígitos (ej: 1 -> 01, 12 -> 12)
        numero_formateado = numero.zfill(2)
        return f"CAPÍTULO {numero_formateado}"
    
    return "CAPÍTULO 00"

def convertir_views_a_numeros(texto_completo):
    if not texto_completo: return 0
    match = re.search(r'([\d.,]+[KM]?)', texto_completo, re.IGNORECASE)
    if not match: return 0
    valor_str = match.group(1).upper().replace(',', '.')
    try:
        if 'M' in valor_str:
            return int(float(valor_str.replace('M', '')) * 1_000_000)
        elif 'K' in valor_str:
            return int(float(valor_str.replace('K', '')) * 1_000)
        else:
            solo_num = re.sub(r'[^\d.]', '', valor_str)
            return int(float(solo_num)) if solo_num else 0
    except: return 0

def guardar_en_mysql(datos_lista, nombre_playlist):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tiktok_playlist_stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                playlist_name VARCHAR(255),
                video_n VARCHAR(10),
                titulo TEXT,
                vistas_num BIGINT,
                fecha_extraccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        query = "INSERT INTO tiktok_playlist_stats (playlist_name, video_n, titulo, vistas_num) VALUES (%s, %s, %s, %s)"
        valores = [(nombre_playlist, d['n_formateado'], d['titulo'], d['vistas_int']) for d in datos_lista]
        
        cursor.executemany(query, valores)
        conn.commit()
        print(f"✅ Guardados {cursor.rowcount} registros de: '{nombre_playlist}'")
        
    except mysql.connector.Error as err:
        print(f"❌ Error MySQL: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

async def extraer_playlist(browser, url):
    context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    page = await context.new_page()
    
    try:
        print(f"\n🚀 Procesando URL: {url}")
        await page.goto(url, timeout=60000)
        await asyncio.sleep(5)
        
        nombre_pl = await page.title()
        ITEM_SELECTOR = 'div[class*="DivVideoDescContainer"]'

        print("⏬ Realizando scroll profundo...")
        prev_count = 0
        intentos_sin_cambio = 0
        
        while intentos_sin_cambio < 2:
            items_actuales = page.locator(ITEM_SELECTOR)
            count = await items_actuales.count()
            
            if count > 0:
                await items_actuales.last.scroll_into_view_if_needed()
                await asyncio.sleep(2)
            
            if count == prev_count:
                intentos_sin_cambio += 1
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            else:
                prev_count = count
                intentos_sin_cambio = 0
            print(f"   Videos detectados: {count}...")

        final_items = await page.locator(ITEM_SELECTOR).all()
        resultados = []
        
        for i, item in enumerate(final_items):
            try:
                # 1. Formatear número de orden de la lista
                n_orden = str(i + 1).zfill(2)
                
                # 2. Extraer y Limpiar Título (Ahora solo "CAPÍTULO XX")
                titulo_el = item.locator('span[data-e2e="new-desc-span"]')
                titulo_raw = await titulo_el.first.inner_text() if await titulo_el.count() > 0 else ""
                
                # USAMOS LA NUEVA FUNCIÓN AQUÍ:
                titulo_solo_cap = limpiar_titulo_a_capitulo(titulo_raw.strip())
                
                # 3. Vistas
                vistas_el = item.locator('span[class*="SpanVideoViews"]')
                vistas_raw = await vistas_el.first.inner_text() if await vistas_el.count() > 0 else "0"
                
                resultados.append({
                    'n_formateado': n_orden,
                    'titulo': titulo_solo_cap,
                    'vistas_int': convertir_views_a_numeros(vistas_raw)
                })
            except: continue
        
        return resultados, nombre_pl

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return [], "Error"
    finally:
        await page.close()

async def main():
    urls = [
       "https://www.tiktok.com/@el13cl/playlist/El%20Obrero%20Que%20Me%20Enamor%C3%B3%20-7566676590613302072",
        "https://www.tiktok.com/@el13cl/playlist/El%20Blog%20de%20la%20Fe%C3%B1a%F0%9F%92%96-7579659165866543928",
        "https://www.tiktok.com/@el13cl/playlist/Mi%20boda%20es%20una%20trampa-7556663640867359500",
        "https://www.tiktok.com/@el13cl/playlist/Mini%20Novelas%20%7C%20Enamoradas-7613834731599203080",
        "https://www.tiktok.com/@el13cl/playlist/Mininovelas-El%20millonario-7626751000711269128"

    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for url in urls:
            data, nombre_pl = await extraer_playlist(browser, url)
            if data:
                guardar_en_mysql(data, nombre_pl)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())