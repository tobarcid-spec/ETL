# Análisis Completo de Archivos Python - ETL c:\procesos\ETL\

**Fecha de Análisis:** 22 de abril de 2026  
**Total de Archivos:** 32 scripts Python

---

## 📋 Tabla de Contenidos Rápida

| # | Archivo | Plataforma | Tipo | Estado |
|---|---------|-----------|------|--------|
| 1 | mango_historia.py | Mango | Importador de Histórico | ✓ |
| 2 | insert_rrss.py | RRSS | Inserción de Datos | ✓ |
| 3 | insert_comentarios_rrss.py | RRSS | Procesador de Comentarios | ✓ |
| 4 | get_ml_token.py | MercadoLibre | Gestor de OAuth | ✓ |
| 5 | flow_trae_factura.py | Flow (Chile) | Consultor de Facturas | ✓ |
| 6 | flow_moroso.py | Flow (Chile) | Análisis de Pagos | ✓ |
| 7 | flow_impago.py | Flow (Chile) | Detector de Impagos | ✓ |
| 8 | flow.py | Flow (Chile) | Inspector de Invoices | ✓ |
| 9 | fb_vod_import_new.py | Facebook | Importador VOD | ✓ |
| 10 | fb_vod_import.py | Facebook | Importador VOD (Legacy) | ✓ |
| 11 | fb_live_import.py | Facebook | Cargador LIVE Streamlit | ✓ |
| 12 | youtube_playslist_auto.py | YouTube | Auto-Carga Playlists | ✓ |
| 13 | youtube_playslist.py | YouTube | Carga Manual Playlists | ✓ |
| 14 | tiktok_scraper_comentarios.py | TikTok | Web Scraper Comentarios | ✓ |
| 15 | tiktok_info_playslist.py | TikTok | Extractor de Playlists | ✓ |
| 16 | T13_rudo_import.py | Rudo + T13 | Importador Histórico | ✓ |
| 17 | T13_metricas_import.py | Mango + T13 | Métricas Diarias | ✓ |
| 18 | T13_mango_import.py | Mango + T13 | Carga VOD Histórica | ✓ |
| 19 | T13_articulos_import.py | T13 | Importador Artículos | ✓ |
| 20 | rudo_import.py | Rudo | Importador de Videos | ✓ |
| 21 | c13_rudo_historia.py | Rudo + C13 | Carga Histórica | ✓ |
| 22 | consulta_notas_t13.py | T13 | Monitor WhatsApp | ✓ |
| 23 | carga_pdigitales.py | YouTube | Cargador Plataforma Digital | ✓ |
| 24 | metricas_import.py | Mango + C13 | Métricas Diarias | ✓ |
| 25 | mercadolibre_api.py | MercadoLibre | Cliente API Completo | ✓ |
| 26 | mango_live_historia_fast.py | Mango | Carga FAST Histórica | ✓ |
| 27 | mango_live_historia.py | Mango | Carga LIVE Histórica | ✓ |
| 28 | mango_live_import.py | Mango | Importador LIVE Diario | ✓ |
| 29 | articulos_import.py | C13 | Importador Artículos | ✓ |
| 30 | 13GO_Arbol.py | 13GO | Sincronizador (Modo Turbo) | ✓ |
| 31 | 13GO_arbol_import.py | 13GO | Sincronizador con Reportes | ✓ |
| 32 | analisis_sentimiento.py | RRSS | Analizador de Sentimiento | ✓ |

---

## 📊 Detalles por Archivo

### 1. **mango_historia.py**
- **Propósito:** Importador histórico de métricas de plataforma Mango (VOD)
- **Funcionalidad:** Consulta métricas agregadas por día desde la API Mango y las carga en histórico
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - API Mango (endpoint: `https://api-mango.digitalproserver.com/`)
  - Rango de fechas parametrizable (default: Mar 2026)
  - Token de autenticación: `9feb892a7cc282a6829354b7db9449afeeeb39e8eb5b4c4e2a94532bedc2c487`
- **Outputs:**
  - Tabla: `c13_metricas_video` (plays, streams, devices, time_total, average_time)
  - Log por día procesado
- **Plataformas:** Mango, C13
- **Frecuencia:** Manual/Puntual (histórico)

---

### 2. **insert_rrss.py**
- **Propósito:** Función auxiliar para insertar métricas diarias de RRSS
- **Funcionalidad:** Inserta o actualiza registros de alcance y clics de Facebook
- **Dependencias:** `mysql.connector`
- **Inputs:**
  - Parámetros: fecha, alcance, clics
- **Outputs:**
  - Tabla: `RRSS_diarias` (campos: fecha, alcance_face, clics_face)
- **Plataformas:** Facebook
- **Frecuencia:** On-demand (función auxiliar)

---

### 3. **insert_comentarios_rrss.py**
- **Propósito:** Consolidador de comentarios desde múltiples redes sociales
- **Funcionalidad:** Procesa archivos JSON descargados desde Apify y consolida comentarios en BD
- **Dependencias:** `json`, `os`, `mysql.connector`
- **Inputs:**
  - Carpeta: `descargas_apify/` con archivos JSON de Apify
  - Detecta red social (Facebook, TikTok, Instagram) por estructura de datos
- **Outputs:**
  - Tabla: `comentarios_rrss_consolidado`
  - Campos: red_social, video_url, usuario, comentario, likes_num
- **Plataformas:** Facebook, TikTok, Instagram
- **Frecuencia:** Manual

---

### 4. **get_ml_token.py**
- **Propósito:** Gestor de autenticación OAuth 2.0 para MercadoLibre
- **Funcionalidad:** Intercambia AUTH_CODE por tokens; gestiona refresh automático
- **Dependencias:** `requests`, `datetime`, `logging`
- **Inputs:**
  - Código de autorización (AUTH_CODE) de MercadoLibre
  - Credenciales: client_id, client_secret, redirect_uri
- **Outputs:**
  - access_token, refresh_token, expiración
  - Información del usuario (user_id, scope)
- **Plataformas:** MercadoLibre
- **Frecuencia:** Inicial + refresh automático (cada 6 horas)

---

### 5. **flow_trae_factura.py**
- **Propósito:** Inspector de detalle de facturas/invoices en Flow
- **Funcionalidad:** Consulta API Flow para obtener datos completos de una factura específica
- **Dependencias:** `requests`, `hashlib`, `hmac`, `json`
- **Inputs:**
  - Invoice ID (ej: 6413650)
  - Credenciales: API_KEY, SECRET_KEY (Flow)
- **Outputs:**
  - JSON con detalles: status, customerId, amount, attemp_count, dueDate
  - Impresión en consola (modo debug)
- **Plataformas:** Flow (proveedor de pagos)
- **Frecuencia:** Manual/Debug

---

### 6. **flow_moroso.py**
- **Propósito:** Buscador de clientes morosos (pagos atrasados)
- **Funcionalidad:** Consulta suscriptores en período de gracia con próximo intento de cobro
- **Dependencias:** `requests`, `hashlib`, `hmac`, `json`, `csv`, `datetime`
- **Inputs:**
  - Plan ID: `s-13go-B001`
  - Filtros: período_fin = TARGET_DATE, intentos = 1
- **Outputs:**
  - CSV con clientes: customerId, externalId, email, periodo_fin
  - Tabla: período de gracia para facturación manual
- **Plataformas:** Flow + C13
- **Frecuencia:** Diaria

---

### 7. **flow_impago.py**
- **Propósito:** Consultor de facturas vencidas sin cobro
- **Funcionalidad:** Obtiene detalles de invoice específico de Flow
- **Dependencias:** `requests`, `hashlib`, `hmac`, `json`
- **Inputs:**
  - Invoice ID (ej: 6218748)
- **Outputs:**
  - Detalles: status, monto, intentos, fecha vencimiento
- **Plataformas:** Flow
- **Frecuencia:** Manual

---

### 8. **flow.py**
- **Propósito:** Inspector rápido de invoices (debug/testing)
- **Funcionalidad:** Consulta datos de una factura y muestra estructura JSON
- **Dependencias:** `requests`, `hashlib`, `hmac`, `json`
- **Inputs:**
  - Invoice ID configurado en script
- **Outputs:**
  - JSON formateado para inspección
- **Plataformas:** Flow
- **Frecuencia:** Manual

---

### 9. **fb_vod_import_new.py**
- **Propósito:** Cargador interactivo Streamlit para videos Facebook
- **Funcionalidad:** UI para cargar CSV de Facebook, clasificar automáticamente por programa
- **Dependencias:** `streamlit`, `pandas`, `mysql.connector`, `re`
- **Inputs:**
  - Archivo CSV desde exportación de Facebook Insights
  - Detección automática de columnas (ID, Título, Vistas, Alcance, Fecha)
- **Outputs:**
  - Tabla: `fb_video` (video_id, titulo, etiqueta, fecha, vistas, alcance)
  - Pre-visualización interactiva en Streamlit
- **Plataformas:** Facebook
- **Frecuencia:** Manual (carga puntual)

---

### 10. **fb_vod_import.py**
- **Propósito:** Cargador Streamlit legacy para videos Facebook
- **Funcionalidad:** Similar a fb_vod_import_new, interfaz para carga de videos
- **Dependencias:** `streamlit`, `pandas`, `mysql.connector`, `re`
- **Inputs:** CSV de Facebook
- **Outputs:** Tabla `fb_video`
- **Plataformas:** Facebook
- **Frecuencia:** Manual

---

### 11. **fb_live_import.py**
- **Propósito:** Cargador Streamlit para Facebook LIVE
- **Funcionalidad:** Carga y clasifica automáticamente transmisiones en vivo
- **Dependencias:** `streamlit`, `pandas`, `mysql.connector`
- **Inputs:**
  - CSV con tipo de publicación = "LIVE/EN VIVO"
  - Diccionario de etiquetas: Rubias, Canaliza, React MO, Mejor Tarde, King League
- **Outputs:**
  - Tabla: `fb_live_video` (video_id, titulo, etiqueta, fecha, vistas)
- **Plataformas:** Facebook LIVE
- **Frecuencia:** Manual

---

### 12. **youtube_playslist_auto.py**
- **Propósito:** Extractor automático de playlists desde Excel
- **Funcionalidad:** Lee Excel con URLs de playlists, descarga todos los videos y carga en BD
- **Dependencias:** `mysql.connector`, `googleapiclient`, `pandas`, `re`
- **Inputs:**
  - Archivo: `playlists.xlsx` (columnas: etiqueta, url)
  - API KEY: `AIzaSyDc75yPe--BM4npEhN5Yak3xdUnbKh_0Jc`
- **Outputs:**
  - Tabla: `c13_yt_metricas` (etiqueta, id_playlist, video_id, titulo, vistas, fecha_publicacion)
- **Plataformas:** YouTube, C13
- **Frecuencia:** Diaria (automática)

---

### 13. **youtube_playslist.py**
- **Propósito:** Extractor manual de playlists YouTube
- **Funcionalidad:** Entrada interactiva de URLs de playlists, extrae videos y actualiza métricas
- **Dependencias:** `mysql.connector`, `googleapiclient`, `re`
- **Inputs:**
  - Entrada usuario: URL playlist + nombre programa
  - API YouTube
- **Outputs:**
  - Tabla: `c13_yt_metricas`
  - Actualiza vistas sin sobrescribir títulos
- **Plataformas:** YouTube, C13
- **Frecuencia:** Manual

---

### 14. **tiktok_scraper_comentarios.py**
- **Propósito:** Web scraper async de comentarios TikTok
- **Funcionalidad:** Usa Playwright para extraer comentarios de videos TikTok
- **Dependencias:** `asyncio`, `playwright`, `mysql.connector`
- **Inputs:**
  - URL de video TikTok
  - Manejo de pop-ups y lazy-loading
- **Outputs:**
  - Tabla: `comentarios_rrss_consolidado` (red_social='TikTok')
  - Usuario, comentario, likes
- **Plataformas:** TikTok
- **Frecuencia:** Manual

---

### 15. **tiktok_info_playslist.py**
- **Propósito:** Extractor de playlist info TikTok
- **Funcionalidad:** Extrae videos de playlist TikTok con contador de vistas
- **Dependencias:** `asyncio`, `playwright`, `mysql.connector`
- **Inputs:**
  - URL playlist TikTok
  - Scroll profundo para cargar videos
- **Outputs:**
  - Tabla: `tiktok_playlist_stats` (playlist_name, video_n, titulo, vistas_num)
- **Plataformas:** TikTok
- **Frecuencia:** Manual

---

### 16. **T13_rudo_import.py**
- **Propósito:** Importador histórico de videos Rudo para T13
- **Funcionalidad:** Consulta API Rudo por lotes, inserta en tabla T13
- **Dependencias:** `requests`, `mysql.connector`, `time`
- **Inputs:**
  - API Rudo: `https://api.rudo.video/api/getvideos`
  - API KEY: `1fc63b2840d5d7985fa39a4eed0c8821ff539c7393ea5f5c157fa4804079122a`
  - Parámetros: start, limit, sortCol, colOrder
- **Outputs:**
  - Tabla: `T13_videos_rudo` (28 campos incluyendo tags)
  - Procesa 2000 videos por ejecución
- **Plataformas:** Rudo, T13
- **Frecuencia:** Puntual (histórico)

---

### 17. **T13_metricas_import.py**
- **Propósito:** Importador diario de métricas Mango para T13
- **Funcionalidad:** Consulta Mango para el día anterior y carga métricas cerradas
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - API Mango
  - Slug: T13
  - Fecha: ayer
- **Outputs:**
  - Tabla: `T13_metricas_video`
- **Plataformas:** Mango, T13
- **Frecuencia:** Diaria (automática)

---

### 18. **T13_mango_import.py**
- **Propósito:** Importador histórico de datos Mango para T13
- **Funcionalidad:** Carga histórica de VOD desde fecha inicio hasta fin
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - Rango de fechas (default: Mar 2026)
  - Slug: T13
- **Outputs:**
  - Tabla: `T13_metricas_video`
- **Plataformas:** Mango, T13
- **Frecuencia:** Puntual

---

### 19. **T13_articulos_import.py**
- **Propósito:** Importador de artículos T13
- **Funcionalidad:** Consulta API T13 (JSON), carga artículos con fecha y categorías
- **Dependencias:** `requests`, `mysql.connector`, `logging`
- **Inputs:**
  - API: `https://www.T13.cl/export/T13/recientes.json`
  - Conversión de fechas: DD/MM/YYYY → YYYY-MM-DD HH:MM:SS
- **Outputs:**
  - Tabla: `T13_articulos` (url_id como PK, on_duplicate_key_update)
  - Campos: titulo, bajada, autor, fecha, imagen, categorias, temas
- **Plataformas:** T13
- **Frecuencia:** Diaria

---

### 20. **rudo_import.py**
- **Propósito:** Importador de videos Rudo
- **Funcionalidad:** Consulta API Rudo, carga videos con todos los campos disponibles
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - API Rudo
  - API KEY: `836a8d85a4f60d312efc09db30b0dd00206810018eb1f48b2cc729c4e4f5cd4b` (T13)
  - Limit: 2000 videos
- **Outputs:**
  - Tabla: `T13_videos_rudo` (28 campos)
- **Plataformas:** Rudo, T13
- **Frecuencia:** Manual

---

### 21. **c13_rudo_historia.py**
- **Propósito:** Carga histórica masiva de Rudo para C13
- **Funcionalidad:** Importa hasta 5000 videos en bloques de 200, con manejo de tags
- **Dependencias:** `requests`, `mysql.connector`, `time`
- **Inputs:**
  - API Rudo
  - API KEY: `836a8d85a4f60d312efc09db30b0dd00206810018eb1f48b2cc729c4e4f5cd4b`
  - Parámetros: START_INICIAL=0, TOTAL_A_TRAER=5000, BLOQUE=200
- **Outputs:**
  - Tabla: `T13_videos_rudo` (con tags procesados: max 3, separados por |)
- **Plataformas:** Rudo, C13
- **Frecuencia:** Puntual

---

### 22. **consulta_notas_t13.py**
- **Propósito:** Monitor de noticias T13 con notificaciones WhatsApp
- **Funcionalidad:** Polling de API JSON, detecta artículos nuevos, envía WhatsApp
- **Dependencias:** `requests`, `pywhatkit`, `time`
- **Inputs:**
  - API: `https://www.t13.cl/export/t13/recientes.json`
  - Número telefónico: `+56951967939`
  - Intervalo de polling: 60 segundos
- **Outputs:**
  - Mensaje WhatsApp con: título, fecha, link
  - Historial en set (evita duplicados)
- **Plataformas:** T13
- **Frecuencia:** Continua (daemon)

---

### 23. **carga_pdigitales.py**
- **Propósito:** Cargador de plataforma digital YouTube
- **Funcionalidad:** Procesa playlists YouTube, extrae videos y carga estadísticas
- **Dependencias:** `os`, `googleapiclient`, `mysql.connector`
- **Inputs:**
  - 5 Playlist IDs de YouTube hardcodeados
  - API KEY YouTube
- **Outputs:**
  - Tabla: `C13_Pdigitales`
  - Campos: programa, capitulo, video_id, v_youtube (vistas)
  - Usa UPSERT (UPDATE o INSERT)
- **Plataformas:** YouTube, C13
- **Frecuencia:** Manual

---

### 24. **metricas_import.py**
- **Propósito:** Importador diario de métricas Mango para C13
- **Funcionalidad:** Carga diaria de métricas del día anterior
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - API Mango, slug: c13
  - Fecha: ayer
- **Outputs:**
  - Tabla: `c13_metricas_video`
- **Plataformas:** Mango, C13
- **Frecuencia:** Diaria

---

### 25. **mercadolibre_api.py**
- **Propósito:** Cliente completo para API de MercadoLibre
- **Funcionalidad:** OAuth 2.0, consulta de vendedor, órdenes, análisis de ventas/gastos
- **Dependencias:** `requests`, `json`, `pandas`, `logging`
- **Inputs:**
  - Credenciales OAuth (client_id, client_secret, redirect_uri)
  - O access_token directo
- **Outputs:**
  - Reportes de transacciones: cobros, gastos, utilidad
  - Métodos: get_auth_url(), set_access_token(), authenticate()
- **Plataformas:** MercadoLibre
- **Frecuencia:** On-demand

---

### 26. **mango_live_historia_fast.py**
- **Propósito:** Cargador histórico de FAST (canales segundarios)
- **Funcionalidad:** Importa métricas LIVE de canales FAST en rango de fechas
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - Fecha inicio/fin (default: Mar 2026)
  - 16 canales: 13CULTURA, 13FESTIVAL, 13COCINA, etc.
- **Outputs:**
  - Tabla: `Fast_live_video` (canal, plays, streams, devices)
- **Plataformas:** Mango, C13 FAST
- **Frecuencia:** Puntual

---

### 27. **mango_live_historia.py**
- **Propósito:** Cargador histórico LIVE agregado
- **Funcionalidad:** Importa datos LIVE históricos de C13
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - Rango de fechas, slug: c13
- **Outputs:**
  - Tabla: `c13_live_video` (canal fijo='c13')
- **Plataformas:** Mango, C13
- **Frecuencia:** Puntual

---

### 28. **mango_live_import.py**
- **Propósito:** Importador diario de LIVE
- **Funcionalidad:** Carga diaria de métricas LIVE para todos los canales
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - Fecha: ayer
  - Canales mapeados (c13, T13, 13CULTURA, etc.)
- **Outputs:**
  - Tablas: `c13_live_video`, `T13_live_video`, `Fast_live_video`
- **Plataformas:** Mango, C13, T13
- **Frecuencia:** Diaria

---

### 29. **articulos_import.py**
- **Propósito:** Importador diario de artículos C13
- **Funcionalidad:** Consulta API C13, inserta nuevos artículos con IGNORE
- **Dependencias:** `requests`, `mysql.connector`
- **Inputs:**
  - API: `https://www.13.cl/export/13/recientes.json`
  - Conversión de fechas
- **Outputs:**
  - Tabla: `c13_articulos`
  - Solo inserta nuevos (INSERT IGNORE)
- **Plataformas:** C13
- **Frecuencia:** Diaria

---

### 30. **13GO_Arbol.py**
- **Propósito:** Sincronizador de contenido 13GO (modo turbo paralelo)
- **Funcionalidad:** Sincroniza LIVE (señales) y capítulos VOD desde API 13GO
- **Dependencias:** `requests`, `mysql.connector`, `concurrent.futures`, `hashlib`
- **Inputs:**
  - API: `https://www.13.cl/13go-premium/feed/` + paths
  - Múltiples playlists de programas
  - Hash para detectar cambios
- **Outputs:**
  - Tablas: `13go_senales_live`, `13go_capitulos_vod`
  - Reporte de cambios detectados
- **Plataformas:** 13GO, C13
- **Frecuencia:** Manual (turbo mode)

---

### 31. **13GO_arbol_import.py**
- **Propósito:** Sincronizador de contenido 13GO con reportes a archivo
- **Funcionalidad:** Similar a 13GO_Arbol.py pero genera reportes CSV
- **Dependencias:** `requests`, `mysql.connector`, `hashlib`, `pandas`, `concurrent.futures`
- **Inputs:**
  - API 13GO
  - Log file: `ejecucion_log.txt` (modo append)
  - Report dir: `./reportes/`
- **Outputs:**
  - Tablas: `13go_senales_live`, `13go_capitulos_vod`
  - CSV reporte: `reportes/` con timestamp
- **Plataformas:** 13GO, C13
- **Frecuencia:** Automática (programada)

---

### 32. **analisis_sentimiento.py**
- **Propósito:** Analizador de sentimiento en comentarios de RRSS
- **Funcionalidad:** Clasifica comentarios con modelos RobERTa + BERT + heurística chilena
- **Dependencias:** `mysql.connector`, `pysentimiento`, `transformers`
- **Inputs:**
  - Comentarios de tabla: `comentarios_rrss_consolidado`
  - Modelos: RobERTa (español), BERT (robertuito)
  - Diccionarios: emojis, sarcasmo, modismos chilenos (bacán, fome, etc.)
- **Outputs:**
  - Tabla: `comentarios_rrss_consolidado` (nuevos campos)
  - Campos: sent_robertito, sent_bert, sent_consenso
  - Valores: POS (positivo), NEG (negativo), NEU (neutro)
- **Plataformas:** RRSS (Facebook, TikTok, Instagram)
- **Frecuencia:** Manual (puede resetear y reanalizar)

---

## 🔗 Flujo General de Datos

```
┌─────────────────────────────────────────────────────────────────┐
│                      FUENTES EXTERNAS                            │
├─────────────────────────────────────────────────────────────────┤
│  API Mango ──→ [mango_*.py] ──→ c13/T13_metricas_video          │
│  API Rudo ───→ [*_rudo_import.py] ──→ T13/c13_videos_rudo       │
│  API YouTube → [youtube_*.py] ──→ c13_yt_metricas               │
│  API T13 ────→ [articulos_import.py] ──→ c13_articulos          │
│  API Flow ───→ [flow_*.py] ──→ Reportes CSV                     │
│  API ML ─────→ [mercadolibre_api.py] ──→ Reportes/Datos         │
│  Web Scraper → [tiktok_*.py] ──→ comentarios_rrss_consolidado   │
│  RRSS ───────→ [insert_*.py] ──→ comentarios_rrss_consolidado   │
│  Excel/CSV ──→ [*_import.py] ──→ Streamlit/Base de datos        │
│  13GO Feed ──→ [13GO_*.py] ──→ 13go_capitulos_vod/senales_live  │
└─────────────────────────────────────────────────────────────────┘
                            ↓↓↓
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESAMIENTO/ANÁLISIS                        │
├─────────────────────────────────────────────────────────────────┤
│  [analisis_sentimiento.py] ──→ Clasifica comentarios: POS/NEU/NEG
│  [Streamlit Apps] ──────────→ Interfaz interactiva para carga    │
│  [consulta_notas_t13.py] ───→ Monitor con notificaciones         │
└─────────────────────────────────────────────────────────────────┘
                            ↓↓↓
┌─────────────────────────────────────────────────────────────────┐
│                   BASE DE DATOS MySQL (MEDIOS_DIGITALES)         │
├─────────────────────────────────────────────────────────────────┤
│  Tablas VOD:             Tablas LIVE:        Tablas Artículos:   │
│  • c13_metricas_video    • c13_live_video    • c13_articulos     │
│  • T13_metricas_video    • T13_live_video    • T13_articulos     │
│  • c13_videos_rudo       • Fast_live_video   • c13_notas         │
│  • T13_videos_rudo       • c13_yt_metricas   • comentarios_rrss  │
│  • fb_video              • c13_Pdigitales    • 13go_capitulos_vod
│  • ig_video                                   • 13go_senales_live
│                                               • tiktok_playlist_stats
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Tablas MySQL Principales

| Tabla | Contenido | Fuentes | Frecuencia |
|-------|-----------|---------|-----------|
| c13_metricas_video | Métricas VOD C13 | Mango API | Diaria + Histórico |
| T13_metricas_video | Métricas VOD T13 | Mango API | Diaria + Histórico |
| c13_live_video | Métricas LIVE C13 | Mango API | Diaria + Histórico |
| T13_live_video | Métricas LIVE T13 | Mango API | Diaria |
| Fast_live_video | Métricas FAST channels | Mango API | Diaria + Histórico |
| c13_videos_rudo | Videos Rudo C13 | Rudo API | Manual + Histórico |
| T13_videos_rudo | Videos Rudo T13 | Rudo API | Manual + Histórico |
| c13_yt_metricas | Videos YouTube C13 | YouTube API | Diaria |
| c13_Pdigitales | Plataforma Digital C13 | YouTube API | Manual |
| c13_articulos | Artículos C13 | C13 API JSON | Diaria |
| T13_articulos | Artículos T13 | T13 API JSON | Diaria |
| c13_notas | Notas T13 | T13 API Monitor | Continua (WhatsApp) |
| comentarios_rrss_consolidado | Comentarios (FB/TK/IG) | Apify + Web Scraper | Manual |
| 13go_capitulos_vod | Capítulos 13GO | 13GO Feed | Diaria |
| 13go_senales_live | Señales LIVE 13GO | 13GO Feed | Diaria |
| tiktok_playlist_stats | Stats Playlists TK | TikTok Scraper | Manual |
| fb_video | Videos Facebook | CSV Facebook Insights | Manual |
| ig_video | Videos Instagram | CSV Meta Insights | Manual |

---

## 🔐 Credenciales & Configuración

### APIs y Tokens
- **Mango API Token:** `9feb892a7cc282a6829354b7db9449afeeeb39e8eb5b4c4e2a94532bedc2c487`
- **YouTube API Key:** `AIzaSyDc75yPe--BM4npEhN5Yak3xdUnbKh_0Jc`
- **Rudo API Key (T13):** `836a8d85a4f60d312efc09db30b0dd00206810018eb1f48b2cc729c4e4f5cd4b`
- **Rudo API Key (Alt):** `1fc63b2840d5d7985fa39a4eed0c8821ff539c7393ea5f5c157fa4804079122a`
- **Flow API:** KEY=`653BA8F3-0BCC-4571-AF8F-1L440B0751CF`, SECRET=`43ed83a62b6efcd88a5c9281728d257e99541757`

### Base de Datos
- **Host:** 217.160.158.217
- **User:** user_md_new
- **Password:** md_secuo_c13.$2025
- **Database:** MEDIOS_DIGITALES

### Configuración General
- **Rango Histórico Típico:** Marzo 2026
- **Intervalo Polling:** 60 segundos (consulta_notas_t13.py)
- **Timeout API:** 25-60 segundos
- **Batch Size:** 100-200 registros

---

## 📈 Patrón de Ejecución

### Diarios (Automáticos)
1. **Temprano (06:00)** → metricas_import.py, T13_metricas_import.py
2. **Cada hora** → consulta_notas_t13.py (daemon)
3. **Mañana/Tarde** → mango_live_import.py, articulos_import.py, T13_articulos_import.py
4. **Noche** → 13GO_arbol_import.py

### Manuales (Puntual)
- Importadores históricos (mango_historia.py, c13_rudo_historia.py)
- Cargadores Streamlit (fb_vod_import.py, fb_live_import.py)
- Web scrapers (tiktok_scraper_comentarios.py)
- Queries de Flow (flow_moroso.py)

---

## 🎯 Casos de Uso

### Monitoreo de Métricas
→ `metricas_import.py` + `mango_live_import.py` → Dashboards en tiempo real

### Gestión de Contenido
→ `13GO_arbol_import.py` + `mango_live_historia.py` → Catálogo actualizado

### Análisis de Audiencia
→ `analisis_sentimiento.py` + comentarios RRSS → Engagement por sentimiento

### Reportes de Pago
→ `flow_moroso.py` + `flow_impago.py` → Seguimiento de cobranza

### Social Listening
→ `tiktok_scraper_comentarios.py` + `insert_comentarios_rrss.py` → Conversación social

---

## ⚠️ Notas Importantes

1. **Credenciales en código:** Los archivos contienen credenciales hardcodeadas (considerar migrar a variables de entorno)
2. **Hashes de cambios:** 13GO_*.py usan SHA256 para detectar cambios en contenido
3. **Paralelización:** 13GO_Arbol.py usa ThreadPoolExecutor para procesamiento paralelo
4. **Manejo de duplicados:** Mayoría usa INSERT IGNORE o ON DUPLICATE KEY UPDATE
5. **Modelos NLP:** analisis_sentimiento.py requiere ~500MB en modelos (transformers)
6. **Logs:** 13GO_arbol_import.py genera ejecucion_log.txt para auditoría
7. **Timeout de APIs:** Algunos scripts tienen retry logic implícito en try/except

---

**Documento generado:** 22 de abril de 2026  
**Versión:** 1.0  
**Autor:** Análisis Automatizado

