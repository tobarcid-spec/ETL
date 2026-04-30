import streamlit as st
import pandas as pd
import mysql.connector
import re
import io
from datetime import datetime
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS
# ==========================================

DICCIONARIO_ETIQUETAS = {
    "BODA": ["Mi boda es una trampa"],
    "OBRERO": ["OBRERO"],
    "BLOG": ["BlogDeLaFeña"],
    "ENAMORADAS": ["Enamoradas", "Enamoradas13"]
}

def auto_etiquetar(titulo):
    if pd.isna(titulo): return "Otros_Video"
    titulo_min = str(titulo).lower()
    for etiqueta, frases in DICCIONARIO_ETIQUETAS.items():
        for frase in frases:
            if frase.lower() in titulo_min:
                return etiqueta
    return "Otros_Video"

# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def conectar_db():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Exception as e:
        st.error(f"Error conectando a MySQL: {e}")
        return None

def limpiar_numero(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).lower() == "nan": return 0
    try:
        if isinstance(valor, (int, float)): return int(valor)
        limpio = re.sub(r'[^0-9]', '', str(valor))
        return int(limpio) if limpio else 0
    except:
        return 0

def procesar_fecha_rrss(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).lower() == "total": return None
    try:
        # Formato detectado en tu archivo: 03/02/2026 09:27
        dt = pd.to_datetime(valor, dayfirst=True, errors='coerce')
        return dt.strftime('%Y-%m-%d %H:%M:%S') if not pd.isna(dt) else None
    except:
        return None

def detectar_columna(headers, opciones):
    for opcion in opciones:
        for h in headers:
            if opcion.lower() == str(h).lower() or opcion.lower() in str(h).lower():
                return h
    return None

# ==========================================
# 3. INTERFAZ STREAMLIT
# ==========================================
st.set_page_config(page_title="Cargador RRSS Multicanal", layout="wide")

st.title("🚀 Cargador de Métricas de Redes Sociales")
st.markdown("Carga archivos CSV de Facebook o Instagram y selecciona qué publicaciones subir a la base de datos.")

# Selector de Red Social en el Sidebar
red_social = st.sidebar.radio("1. Selecciona la Red Social:", ["Instagram", "Facebook"])
tabla_destino = "ig_video" if red_social == "Instagram" else "fb_video"

st.sidebar.divider()
st.sidebar.write(f"**Tabla destino:** `{tabla_destino}`")

archivo_subido = st.file_uploader(f"2. Cargar reporte CSV de {red_social}", type=["csv"])

if archivo_subido:
    # Leer el archivo detectando el separador (coma o punto y coma)
    try:
        # Leemos una muestra para detectar el separador
        sample = archivo_subido.read(2048).decode('utf-8', errors='ignore')
        archivo_subido.seek(0)
        separator = ';' if ';' in sample else ','
        
        df_raw = pd.read_csv(archivo_subido, sep=separator, encoding='utf-8', engine='python')
    except Exception as e:
        archivo_subido.seek(0)
        df_raw = pd.read_csv(archivo_subido, sep=None, encoding='latin-1', engine='python')

    headers = df_raw.columns.tolist()

    # Mapeo de columnas según el archivo real entregado
    if red_social == "Instagram":
        col_id = detectar_columna(headers, ["Identificador de la publicación", "ID"])
        col_tit = detectar_columna(headers, ["Descripción", "Caption", "Título"])
        col_vis = detectar_columna(headers, ["Visualizaciones", "Views", "Reproducciones"])
        col_alc = detectar_columna(headers, ["Alcance", "Reach"])
        col_fec = detectar_columna(headers, ["Hora de publicación", "Fecha"])
    else:
        col_id = detectar_columna(headers, ["Identificador de la publicación", "Post ID", "ID"])
        col_tit = detectar_columna(headers, ["Título", "Descripción", "Title"])
        col_vis = detectar_columna(headers, ["Visualizaciones", "Views"])
        col_alc = detectar_columna(headers, ["Alcance", "Reach"])
        col_fec = detectar_columna(headers, ["Hora de publicación", "Fecha"])

    data_total = []
    for _, row in df_raw.iterrows():
        # Limpieza del Identificador (quitar decimales si vienen como float)
        raw_id = row.get(col_id)
        if pd.isna(raw_id) or str(raw_id).strip() == "" or str(raw_id).lower() == "nan": 
            continue
        
        id_v = str(raw_id).split('.')[0].strip()
        titulo_v = str(row.get(col_tit)) if not pd.isna(row.get(col_tit)) else ""
        
        # Omitir filas de resumen que Meta a veces incluye
        if "total" in str(row.get(col_fec)).lower(): continue

        data_total.append({
            "seleccionar": True, 
            "video_id": id_v,
            "titulo": titulo_v,
            "etiqueta": auto_etiquetar(titulo_v),
            "fecha": procesar_fecha_rrss(row.get(col_fec)),
            "vistas": limpiar_numero(row.get(col_vis)),
            "alcance": limpiar_numero(row.get(col_alc))
        })
    
    df_final = pd.DataFrame(data_total)

    if not df_final.empty:
        st.divider()
        
        # Filtro de búsqueda
        busqueda = st.text_input("🔍 Buscar por título o palabra clave:", placeholder="Ej: CAPÍTULO 10...")
        
        if busqueda:
            df_mostrar = df_final[df_final['titulo'].str.contains(busqueda, case=False, na=False)]
        else:
            df_mostrar = df_final

        st.subheader(f"Listado de {red_social} ({len(df_mostrar)} publicaciones encontradas)")

        # Editor de datos para pre-visualizar y editar antes de cargar
        df_editado = st.data_editor(
            df_mostrar,
            column_config={
                "seleccionar": st.column_config.CheckboxColumn("¿Cargar?", default=True),
                "video_id": st.column_config.TextColumn("ID", disabled=True),
                "titulo": st.column_config.TextColumn("Título/Descripción ✍️", width="large"),
                "etiqueta": st.column_config.TextColumn("Etiqueta ✍️"),
                "fecha": st.column_config.TextColumn("Fecha Pub", disabled=True),
                "vistas": st.column_config.NumberColumn("Vistas", format="%d"),
                "alcance": st.column_config.NumberColumn("Alcance", format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )

        df_a_cargar = df_editado[df_editado['seleccionar'] == True]

        if st.button(f"🔥 Cargar {len(df_a_cargar)} registros seleccionados", use_container_width=True):
            if df_a_cargar.empty:
                st.warning("No hay filas seleccionadas para cargar.")
            else:
                conn = conectar_db()
                if conn:
                    cursor = conn.cursor()
                    
                    # SQL que maneja inserción y actualización
                    sql = f"""
                        INSERT INTO {tabla_destino} (video_id, titulo, etiqueta, fecha_publicacion, vistas, alcance) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                            titulo = IF(titulo IS NULL OR titulo = '', VALUES(titulo), titulo),
                            vistas = VALUES(vistas), 
                            alcance = VALUES(alcance),
                            etiqueta = VALUES(etiqueta),
                            fecha_carga = CURRENT_TIMESTAMP
                    """
                    
                    filas = [
                        (r['video_id'], r['titulo'], r['etiqueta'], r['fecha'], r['vistas'], r['alcance']) 
                        for _, r in df_a_cargar.iterrows()
                    ]
                    
                    try:
                        cursor.executemany(sql, filas)
                        conn.commit()
                        st.balloons()
                        st.success(f"✅ ¡Proceso completado! Se sincronizaron {len(df_a_cargar)} registros en `{tabla_destino}`.")
                    except Exception as err:
                        st.error(f"Error en Base de Datos: {err}")
                    finally:
                        conn.close()
    else:
        st.warning("No se encontraron datos válidos en el archivo. Verifica el formato del CSV.")