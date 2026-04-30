import requests
import mysql.connector
import hashlib
import json
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

def generar_hash(data):
    """Crea una huella digital única del objeto JSON."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def procesar_capitulos_programa(full_path, index, total, ahora):
    """
    Función optimizada para ser ejecutada en paralelo.
    Cada hilo gestiona su propia conexión a la BD.
    """
    slug = full_path.split('/')[-1]
    url_capitulos = f"https://www.13.cl/13go-premium/feed{full_path}"
    reporte_local = []
    
    try:
        # Cada hilo abre su propia conexión para evitar colisiones
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Petición HTTP
        res_caps = requests.get(url_capitulos, timeout=15)
        if res_caps.status_code != 200:
            return [], f"   [{index}/{total}] {slug} >> ⚠️ Error HTTP {res_caps.status_code}"
        
        caps_data = res_caps.json()
        lista_caps = []
        if isinstance(caps_data, dict):
            for k in caps_data:
                if isinstance(caps_data[k], list): lista_caps.extend(caps_data[k])
        else:
            lista_caps = caps_data

        cambios_detectados = 0
        for cap in lista_caps:
            id_cap = str(cap.get('id'))
            if not id_cap: continue
            
            # En capítulos SÍ consideramos la imagen para el Hash
            n_hash_cap = generar_hash(cap)
            
            cursor.execute("""
                SELECT id_version, hash_version FROM 13go_capitulos_vod 
                WHERE id_original = %s AND programa_slug = %s AND fecha_fin IS NULL
            """, (id_cap, slug))
            actual_cap = cursor.fetchone()
            
            if not actual_cap or actual_cap['hash_version'] != n_hash_cap:
                if actual_cap:
                    cursor.execute("UPDATE 13go_capitulos_vod SET fecha_fin = %s WHERE id_version = %s", 
                                   (ahora, actual_cap['id_version']))
                
                packs_str = ",".join(cap.get('packs', [])) if isinstance(cap.get('packs'), list) else ""
                
                sql_cap = """INSERT INTO 13go_capitulos_vod 
                             (id_original, programa_slug, titulo, imagen_url, url_video, video_key, duracion, programa_nombre, enlace_web, restriccion, packs_acceso, hash_version, fecha_inicio) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                
                cursor.execute(sql_cap, (
                    id_cap, slug, cap.get('title'), cap.get('image'), cap.get('url_video'), 
                    cap.get('key'), cap.get('duration'), cap.get('show'), cap.get('link'), 
                    cap.get('restriction'), packs_str, n_hash_cap, ahora
                ))
                reporte_local.append({"Fuente": "CAPITULO", "ID": f"{slug}|{id_cap}", "Status": f"Actualizado: {cap.get('title')}"})
                cambios_detectados += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        return reporte_local, f"   [{index}/{total}] {slug} >> ✅ {len(lista_caps)} caps ({cambios_detectados} cambios)"
        
    except Exception as e:
        return [], f"   [{index}/{total}] {slug} >> ❌ Error: {str(e)}"

def main():
    reporte_total = []
    ahora = datetime.now()
    
    try:
        print(f"\n[{ahora}] >> INICIANDO SINCRONIZACIÓN TOTAL (MODO TURBO)")
        print("="*80)
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # --- FASE 1: SEÑALES LIVE ---
        print("\n>> FASE 1: PROCESANDO SEÑALES LIVE")
        res_live = requests.get("https://www.13.cl/13go-premium/feed/senales.json", timeout=25).json()
        for item in res_live:
            id_id = str(item.get('id'))
            n_hash = generar_hash(item)
            print(f"   [*] Señal: {item.get('titulo')}...", end=" ", flush=True)
            cursor.execute("SELECT id_version, hash_version FROM 13go_senales_live WHERE id_original = %s AND fecha_fin IS NULL", (id_id,))
            actual = cursor.fetchone()
            if not actual or actual['hash_version'] != n_hash:
                if actual: cursor.execute("UPDATE 13go_senales_live SET fecha_fin = %s WHERE id_version = %s", (ahora, actual['id_version']))
                sql = """INSERT INTO 13go_senales_live (id_original, categoria, titulo, bajada, color_principal, epg_url, imagen_url, link_url, logo_blanco, logo_invertido, id_mango, restriction, assetkey, hash_version, fecha_inicio) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                cursor.execute(sql, (item.get('id'), item.get('categoria'), item.get('titulo'), item.get('bajada'), item.get('color_principal'), item.get('epg'), item.get('imagen'), item.get('link'), item.get('logo_blanco'), item.get('logo_invertido'), item.get('id_mango'), item.get('restriction'), item.get('assetkey'), n_hash, ahora))
                reporte_total.append({"Fuente": "LIVE", "ID": id_id, "Status": "Actualizado"})
                print("⚠️ CAMBIO")
            else: print("✔️ OK")

        # --- FASE 2: PROGRAMAS VOD ---
        print("\n>> FASE 2: PROCESANDO PROGRAMAS VOD")
        res_vod = requests.get("https://www.13.cl/13go-premium/feed/programas", timeout=25).json()
        procesados_vod = set()
        for seccion, lista in res_vod.items():
            print(f"   📂 Categoría: {seccion}")
            for p in lista:
                url_p, cat_p = p.get('url'), p.get('categoria')
                id_compuesto = f"{url_p}|{cat_p}"
                if id_compuesto in procesados_vod: continue
                
                p_para_hash = p.copy()
                if 'imagen_vertical' in p_para_hash: del p_para_hash['imagen_vertical']
                
                n_hash_vod = generar_hash(p_para_hash)
                cursor.execute("SELECT id_version, hash_version FROM 13go_programas_vod WHERE url_path = %s AND categoria_json = %s AND fecha_fin IS NULL", (url_p, cat_p))
                actual_v = cursor.fetchone()
                
                if not actual_v or actual_v['hash_version'] != n_hash_vod:
                    if actual_v: cursor.execute("UPDATE 13go_programas_vod SET fecha_fin = %s WHERE id_version = %s", (ahora, actual_v['id_version']))
                    sql_v = "INSERT INTO 13go_programas_vod (id_key, categoria_json, titulo, url_path, imagen_vertical, hash_version, fecha_inicio) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                    cursor.execute(sql_v, (p.get('key'), cat_p, p.get('titulo'), url_p, p.get('imagen_vertical'), n_hash_vod, ahora))
                    reporte_total.append({"Fuente": "VOD", "ID": id_compuesto, "Status": "Actualizado"})
                    procesados_vod.add(id_compuesto)

        conn.commit()

        # --- FASE 3: CAPÍTULOS VOD (MULTITHREADING) ---
        print("\n>> FASE 3: PROCESANDO CAPÍTULOS (PARALELIZADO)")
        print("-" * 40)
        cursor.execute("SELECT DISTINCT url_path FROM 13go_programas_vod WHERE fecha_fin IS NULL")
        unique_paths = [row['url_path'] for row in cursor.fetchall()]
        total_paths = len(unique_paths)
        
        # Ejecución en paralelo con un máximo de 5 hilos para no saturar el servidor
        with ThreadPoolExecutor(max_workers=5) as executor:
            futuros = [executor.submit(procesar_capitulos_programa, path, i, total_paths, ahora) 
                       for i, path in enumerate(unique_paths, 1)]
            
            for futuro in as_completed(futuros):
                items_reporte, mensaje = futuro.result()
                reporte_total.extend(items_reporte)
                print(mensaje)

        print("\n" + "="*80)
        print(f"🏁 SINCRONIZACIÓN FINALIZADA EXITOSAMENTE")
        print(f"📊 Registros nuevos/actualizados: {len(reporte_total)}")

        if reporte_total:
            fname = f"reporte_completo_13go_{ahora.strftime('%Y%m%d_%H%M')}.xlsx"
            pd.DataFrame(reporte_total).to_excel(fname, index=False)
            print(f"📄 Reporte generado: {fname}")

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("🔌 Conexión cerrada.")

if __name__ == "__main__":
    main()