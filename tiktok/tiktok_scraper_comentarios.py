import asyncio
from playwright.async_api import async_playwright
import re
import mysql.connector
from datetime import datetime
import random
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- CONFIGURACIÓN DE MYSQL ---

def convertir_a_numero(texto):
    if not texto: return 0
    texto = texto.upper().replace(',', '.')
    try:
        if 'M' in texto: return int(float(texto.replace('M', '')) * 1_000_000)
        if 'K' in texto: return int(float(texto.replace('K', '')) * 1_000)
        solo_num = re.sub(r'[^\d.]', '', texto)
        return int(float(solo_num)) if solo_num else 0
    except: return 0

def guardar_comentarios_mysql(datos_lista):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

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
        
        valores = [('TikTok', d['url'], d['usuario'], d['texto'], d['likes']) for d in datos_lista]
        
        cursor.executemany(query, valores)
        conn.commit()
        print(f"✅ Éxito: {cursor.rowcount} comentarios guardados.")
        
    except mysql.connector.Error as err:
        print(f"❌ Error MySQL: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

async def extraer_comentarios_video(context, url):
    # Limpiar URL de parámetros de rastreo para evitar bloqueos
    url_limpia = url.split('?')[0]
    page = await context.new_page()
    
    try:
        print(f"\n🚀 Accediendo a: {url_limpia}")
        
        # 1. Navegación con espera de red inactiva
        await page.goto(url_limpia, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(3, 5)) # Espera "humana" aleatoria

        # 2. Intentar cerrar el molesto Pop-up de Login que bloquea el scroll
        try:
            close_btn = page.locator('div[data-e2e="modal-close-inner-button"]')
            if await close_btn.is_visible():
                await close_btn.click()
                print("🔘 Modal de login cerrado.")
        except: pass

        # 3. Esperar el selector de comentarios con mayor margen de tiempo
        COMMENT_SELECTOR = '[data-e2e="comment-level-1"]'
        print("⏳ Esperando que aparezcan los comentarios...")
        
        try:
            await page.wait_for_selector(COMMENT_SELECTOR, timeout=30000, state="visible")
        except Exception:
            # Si falla, intentamos un scroll rápido para "despertar" la carga
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(2)
            await page.wait_for_selector(COMMENT_SELECTOR, timeout=15000)

        # 4. Scroll dinámico para cargar más comentarios
        print("⏬ Cargando más comentarios (scroll)...")
        for _ in range(5): 
            await page.keyboard.press("End")
            await asyncio.sleep(random.uniform(1.5, 3))

        # 5. Extracción de datos
        comentarios_web = await page.locator(COMMENT_SELECTOR).all()
        resultados = []

        for item in comentarios_web:
            try:
                # Selectores específicos de la interfaz actual de TikTok
                usuario = await item.locator('[data-e2e="comment-author-name"]').first.inner_text()
                texto = await item.locator('[data-e2e="comment-display-text"]').first.inner_text()
                likes_raw = await item.locator('[data-e2e="comment-like-count"]').first.inner_text()
                
                resultados.append({
                    'url': url_limpia,
                    'usuario': usuario.strip(),
                    'texto': texto.strip(),
                    'likes': convertir_a_numero(likes_raw)
                })
            except: continue
        
        return resultados

    except Exception as e:
        print(f"⚠️ Error extrayendo {url_limpia}: {e}")
        return []
    finally:
        await page.close()

async def main():
    urls_videos = [
        "https://www.tiktok.com/@el13cl/video/7613505585488661778",
        # Agrega más URLs aquí
    ]

    async with async_playwright() as p:
        # Lanzamos con un User Agent moderno y Viewport de escritorio
        browser = await p.chromium.launch(headless=False) # Cambiar a False si quieres ver el proceso
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        todo_comentarios = []
        for url in urls_videos:
            data = await extraer_comentarios_video(context, url)
            if data:
                todo_comentarios.extend(data)
        
        if todo_comentarios:
            guardar_comentarios_mysql(todo_comentarios)
        else:
            print("❌ No se obtuvieron comentarios. Verifica si TikTok solicitó Captcha.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())