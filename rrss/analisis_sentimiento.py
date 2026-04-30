import mysql.connector
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import warnings
import logging
import re
from config.config import DB_CONFIG

# 1. SILENCIAR ADVERTENCIAS
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)

from pysentimiento import create_analyzer
from transformers import pipeline

# --- CARGA DE MODELOS ---
print("🚀 Cargando Motores. Activando Protocolo Anti-Neutro...")
roberta_analyzer = create_analyzer(task="sentiment", lang="es")
bert_analyzer = pipeline("sentiment-analysis", model="pysentimiento/robertuito-sentiment-analysis")

# --- DICCIONARIOS AGRESIVOS (CHILE & TIKTOK) ---
EMOJIS_POS = ['🤣', '😂', '😍', '❤️', '🙌', '👏', '🔥', '🥰', '💕', '🫶', '💖']
EMOJIS_NEG = ['💩', '🤮', '😡', '🤬', '🤦', '🤡', '🙄', '👎', '😒', '🥱']

SARCASMO_FRASES = ["qué buena", "que buena", "genial", "lindo el", "bonita la", "super", "súper", "excelente"]

# Usamos minúsculas para el match exacto
MODISMOS_CHILE_POS = ['bacán', 'bacan', 'preciosa', 'seca', 'crack', 'buena', 'buenisimo', 'apaño', 'valiente', 'linda', 'amo', 'me encanta', 'weon bueno', 'wn bueno']
MODISMOS_CHILE_NEG = ['fome', 'penca', 'rasca', 'asco', 'ordinario', 'ctm', 'weon malo', 'wn malo', 'nefasta', 'malo', 'mala', 'horrible', 'aburrido']

def fuerza_bruta_chilena(texto, consenso_ia):
    """
    Si la IA dice NEU, esta función revisa si hay emojis o modismos evidentes
    para FORZAR el cambio a POS o NEG.
    """
    if consenso_ia != 'NEU':
        return consenso_ia # Si la IA ya se decidió, le creemos.
        
    t_low = str(texto).lower()
    
    # 1. Chequeo de Sarcasmo
    if any(p in t_low for p in SARCASMO_FRASES) and any(e in t_low for e in EMOJIS_NEG):
        return 'NEG'
        
    # 2. Chequeo por Emojis Fuertes
    if any(e in t_low for e in EMOJIS_POS): return 'POS'
    if any(e in t_low for e in EMOJIS_NEG): return 'NEG'
        
    # 3. Chequeo de Modismos con Regex (Búsqueda de palabra exacta)
    for palabra in MODISMOS_CHILE_POS:
        if re.search(rf'\b{palabra}\b', t_low): return 'POS'
        
    for palabra in MODISMOS_CHILE_NEG:
        if re.search(rf'\b{palabra}\b', t_low): return 'NEG'
        
    return 'NEU' # Si sobrevive a todo esto, realmente es neutro.

def obtener_analisis_final(texto):
    if not texto or len(str(texto).strip()) < 2:
        return 'NEU', 'NEU', 'NEU'
    
    t_raw = str(texto).strip()
    
    try:
        # 1. Predicción Pura de IA
        res_rob = roberta_analyzer.predict(t_raw).output
        res_bert_raw = bert_analyzer(t_raw[:512])[0]['label']
        map_labels = {'POS': 'POS', 'NEG': 'NEG', 'NEU': 'NEU', 'Others': 'NEU'}
        res_bert = map_labels.get(res_bert_raw, 'NEU')
        
        # 2. Consenso Base (Prioriza emoción sobre neutralidad)
        if res_rob != 'NEU':
            consenso_base = res_rob
        elif res_bert != 'NEU':
            consenso_base = res_bert
        else:
            consenso_base = 'NEU'
            
        # 3. Filtro Agresivo Chileno/TikTok
        consenso_final = fuerza_bruta_chilena(t_raw, consenso_base)
        
        return res_rob, res_bert, consenso_final
    except Exception as e:
        return 'NEU', 'NEU', 'NEU'

def resetear_tabla(cursor):
    print("🧹 Borrando análisis anteriores (Modo Reset: ON)...")
    cursor.execute("UPDATE comentarios_rrss_consolidado SET sent_robertito = NULL, sent_bert = NULL, sent_consenso = NULL")
    print("✅ Tabla limpia. Lista para análisis profundo.")

def ejecutar():
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # BORRAMOS LOS DATOS VIEJOS
        resetear_tabla(cursor)
        
        cursor.execute("SELECT id, comentario FROM comentarios_rrss_consolidado WHERE sent_consenso IS NULL")
        pendientes = cursor.fetchall()

        if pendientes:
            total = len(pendientes)
            print(f"🧠 Analizando {total} registros con Filtro Anti-Neutro...")
            query = "UPDATE comentarios_rrss_consolidado SET sent_robertito=%s, sent_bert=%s, sent_consenso=%s WHERE id=%s"
            batch = []
            
            # Variables para ver el impacto en tiempo real
            cont_pos, cont_neg, cont_neu = 0, 0, 0
            
            for i, fila in enumerate(pendientes):
                rob, bert, cons = obtener_analisis_final(fila['comentario'])
                
                # Contadores para el print
                if cons == 'POS': cont_pos += 1
                elif cons == 'NEG': cont_neg += 1
                else: cont_neu += 1
                
                batch.append((rob, bert, cons, fila['id']))
                
                if len(batch) >= 50 or (i+1) == total:
                    cursor.executemany(query, batch)
                    print(f"💾 Progreso: {i+1}/{total} | Acumulado -> POS: {cont_pos} | NEG: {cont_neg} | NEU: {cont_neu}")
                    batch = []
        else:
            print("✨ No hay datos.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close(); conn.close()
        sys.exit(0)

if __name__ == "__main__":
    ejecutar()