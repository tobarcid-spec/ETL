import streamlit as st
import pandas as pd
import mysql.connector
import re
from datetime import datetime
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# ==========================================
# 1. CONFIGURACIÓN Y DICCIONARIO
# ==========================================

DICCIONARIO_ETIQUETAS = {
    "BODA": ["Mininovelas | Mi boda es una trampa"],
    "OBRERO": ["OBRERO"],
    "BLOG": ["BlogDeLaFeña"] ,
    "ENAMORADAS": ["Enamoradas"]
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
    if pd.isna(valor) or valor == "": return 0
    if isinstance(valor, (int, float)): return int(valor)
    limpio = re.sub(r'[^0-9]', '', str(valor))
    return int(limpio) if limpio else 0

def procesar_solo_fecha(valor):
    if pd.isna(valor) or str(valor).strip() == "" or valor == "N/A": 
        return None
    try:
        dt = pd.to_datetime(valor, errors='coerce')
        return dt.strftime('%Y-%m-%d') if not pd.isna(dt) else None
    except:
        return None

def detectar_columna(headers, opciones):
    for opcion in opciones:
        for h in headers:
            if opcion.lower() in str(h).lower():
                return h
    return None

# ==========================================
# 3. INTERFAZ STREAMLIT
# ==========================================
st.set_page_config(page_title="Cargador fb_video", layout="wide")
st.title("🎬 Cargador de Videos (Tabla: fb_video)")

archivo_subido = st.file_uploader("Cargar reporte CSV", type=["csv"])

if archivo_subido:
    try:
        df_raw = pd.read_csv(archivo_subido, encoding='utf-8')
    except:
        df_raw = pd.read_csv(archivo_subido, encoding='latin-1')

    headers = df_raw.columns.tolist()

    col_id = detectar_columna(headers, ["Identificador de la publicación", "Post ID", "ID"])
    col_tit = detectar_columna(headers, ["Título", "Title"])
    col_vis = detectar_columna(headers, ["Visualizaciones", "Views"])
    col_alc = detectar_columna(headers, ["Alcance", "Reach"])
    col_fec = detectar_columna(headers, ["Hora de publicación", "Fecha"])

    data_total = []
    for _, row in df_raw.iterrows():
        id_v = row.get(col_id)
        if pd.isna(id_v) or str(id_v).strip() == "": continue
        
        titulo_v = str(row.get(col_tit)) if not pd.isna(row.get(col_tit)) else ""
        
        data_total.append({
            "seleccionar": True, 
            "video_id": str(id_v).split('.')[0].strip(),
            "titulo": titulo_v,
            "etiqueta": auto_etiquetar(titulo_v),
            "fecha": procesar_solo_fecha(row.get(col_fec)),
            "vistas": limpiar_numero(row.get(col_vis)),
            "alcance": limpiar_numero(row.get(col_alc))
        })
    
    df_final = pd.DataFrame(data_total)

    if not df_final.empty:
        st.divider()
        
        busqueda = st.text_input("🔍 Buscar en títulos cargados:", placeholder="Ej: Mundos Opuestos...")
        
        if busqueda:
            df_mostrar = df_final[df_final['titulo'].str.contains(busqueda, case=False, na=False)]
        else:
            df_mostrar = df_final

        st.subheader(f"Listado de videos ({len(df_mostrar)} filas)")

        # --- CAMBIO AQUÍ: 'titulo' habilitado para edición ---
        df_editado = st.data_editor(
            df_mostrar,
            column_config={
                "seleccionar": st.column_config.CheckboxColumn("¿Cargar?", default=True),
                "video_id": st.column_config.TextColumn("ID Video", disabled=True),
                "titulo": st.column_config.TextColumn("Título ✍️", width="large"), # Habilitado
                "etiqueta": st.column_config.TextColumn("Etiqueta ✍️"),
                "fecha": st.column_config.DateColumn("Fecha Pub", disabled=True),
                "vistas": st.column_config.NumberColumn("Vistas", disabled=True),
                "alcance": st.column_config.NumberColumn("Alcance", disabled=True),
            },
            hide_index=True,
            use_container_width=True
        )

        df_a_cargar = df_editado[df_editado['seleccionar'] == True]

        if st.button(f"🔥 Cargar {len(df_a_cargar)} registros a 'fb_video'", use_container_width=True):
            if df_a_cargar.empty:
                st.warning("No hay videos seleccionados para la carga.")
            else:
                conn = conectar_db()
                if conn:
                    cursor = conn.cursor()
                    # --- CAMBIO AQUÍ: SQL no actualiza título si ya existe uno ---
                    sql = """
                        INSERT INTO fb_video (video_id, titulo, etiqueta, fecha_publicacion, vistas, alcance) 
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
                        st.success(f"✅ Se procesaron {len(df_a_cargar)} registros. Los títulos existentes se mantuvieron intactos.")
                    except Exception as err:
                        st.error(f"Error en Base de Datos: {err}")
                    finally:
                        conn.close()
    else:
        st.warning("No se encontraron datos válidos en el CSV.")