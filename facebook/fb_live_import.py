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
    "RUBIAS": ["No hables con las rubias"],
    "CANALIZA": ["MÁS ALLÁ"],
    "REACT MO": ["React Pepsi", "Mundos Opuestos"],
    "MEJOR TARDE": ["Mejor tarde que nunca"],
    "KING LEAGUE": ["Kings World Cup", "Kings League"],
    "ELECCIONES2025":["ELECCION","Presidencial" ],
    "FUTSAL 2026":["FUTSAL" ]
}

def auto_etiquetar(titulo):
    """Lógica de respaldo si no hay separadores '|' en el título"""
    if pd.isna(titulo): return "Otros_Live"
    titulo_min = str(titulo).lower()
    for etiqueta, frases in DICCIONARIO_ETIQUETAS.items():
        for frase in frases:
            if frase.lower() in titulo_min:
                return etiqueta
    return "Otros_Live"

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
st.set_page_config(page_title="Cargador LIVE Pro", layout="wide")
st.title("🚀 Cargador LIVE: Clasificación Automática + Edición")

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
    col_tipo = detectar_columna(headers, ["Tipo de publicación", "Tipo", "Type"])

    data_live = []
    for _, row in df_raw.iterrows():
        tipo_str = str(row.get(col_tipo, "")).lower()
        es_live = any(k in tipo_str for k in ["live", "en vivo", "vivo", "broadcast"])
        
        if es_live:
            id_v = row.get(col_id)
            if pd.isna(id_v) or str(id_v).strip() == "": continue
            
            # --- LÓGICA DE PROCESAMIENTO ---
            texto_completo = str(row.get(col_tit)) if not pd.isna(row.get(col_tit)) else ""
            
            # Dividimos por el caracter "|" y limpiamos espacios
            partes = [p.strip() for p in texto_completo.split('|') if p.strip()]
            
            if len(partes) >= 2:
                etiqueta_v = partes[0]
                titulo_v = partes[-1]
            else:
                titulo_v = texto_completo
                etiqueta_v = auto_etiquetar(texto_completo)
            
            data_live.append({
                "video_id": str(id_v).split('.')[0].strip(),
                "titulo_referencia": texto_completo, # Columna solo para ver
                "titulo": titulo_v,                  # Esto se cargará a la DB
                "etiqueta": etiqueta_v,              # Esto se cargará a la DB
                "fecha": procesar_solo_fecha(row.get(col_fec)),
                "vistas": limpiar_numero(row.get(col_vis)),
                "alcance": limpiar_numero(row.get(col_alc))
            })
    
    df_final = pd.DataFrame(data_live)

    if not df_final.empty:
        st.subheader("📝 Revisar y Editar Datos")
        st.info("La columna 'Título Original' es solo de referencia y no se guardará.")

        # EDITOR DE DATOS
        df_editado = st.data_editor(
            df_final,
            column_config={
                "video_id": st.column_config.TextColumn("ID Video", disabled=True),
                "titulo_referencia": st.column_config.TextColumn("Título Original (Referencia)", disabled=True, width="medium"),
                "titulo": st.column_config.TextColumn("Título Final (Capítulo) ✍️", width="medium"),
                "etiqueta": st.column_config.TextColumn("Etiqueta (Programa) ✍️"),
                "fecha": st.column_config.DateColumn("Fecha Pub", disabled=True),
                "vistas": st.column_config.NumberColumn("Vistas", disabled=True),
                "alcance": st.column_config.NumberColumn("Alcance", disabled=True),
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button(f"🔥 Guardar {len(df_editado)} videos en Base de Datos", use_container_width=True):
            conn = conectar_db()
            if conn:
                cursor = conn.cursor()
                # Nota: No incluimos 'titulo_referencia' en el SQL
                sql = """
                    INSERT INTO fb_video_live (video_id, titulo, etiqueta, fecha_publicacion, vistas, alcance) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        titulo = IF(titulo IS NULL OR titulo = '', VALUES(titulo), titulo),
                        vistas = VALUES(vistas), 
                        alcance = VALUES(alcance),
                        etiqueta = VALUES(etiqueta),
                        fecha_carga = CURRENT_TIMESTAMP
                """
                # Extraemos solo las columnas necesarias para la DB
                filas = [
                    (r['video_id'], r['titulo'], r['etiqueta'], r['fecha'], r['vistas'], r['alcance']) 
                    for _, r in df_editado.iterrows()
                ]
                
                try:
                    cursor.executemany(sql, filas)
                    conn.commit()
                    st.success("✅ Carga finalizada con éxito.")
                except Exception as err:
                    st.error(f"Error DB: {err}")
                finally:
                    conn.close()
    else:
        st.warning("No se encontraron transmisiones 'En Vivo'.")