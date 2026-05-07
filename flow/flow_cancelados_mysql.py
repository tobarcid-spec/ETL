import sys
import os
import csv
import requests
import hashlib
import hmac
import time
from datetime import datetime

import mysql.connector

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

# --- CONFIGURACIÓN FLOW ---
API_KEY    = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL   = "https://www.flow.cl/api"

# Columnas del CSV del Google Sheet
COL_USER_ID   = 'user_id'
COL_EMAIL     = 'email'
COL_SUBMITTED = 'Submitted At'
COL_TOKEN     = 'Token'
COL_MOTIVO    = '¿Por qué finalizas tu suscripción?'

TABLE = 'flow_cancelados'


# ── Helpers Flow ──────────────────────────────────────────────────────────────

def sign(params):
    keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in keys)
    return hmac.new(SECRET_KEY.encode(), to_sign.encode(), hashlib.sha256).hexdigest()


def get_active_plans():
    params = {"apiKey": API_KEY}
    params["s"] = sign(params)
    r = requests.get(f"{BASE_URL}/plans/list", params=params)
    if r.status_code == 200:
        data = r.json()
        plans = data if isinstance(data, list) else data.get('data', data.get('plans', []))
        return [p.get('planId') or p.get('id') for p in plans if p.get('planId') or p.get('id')]
    return []


def get_external_id(customer_id):
    params = {"apiKey": API_KEY, "customerId": str(customer_id)}
    params["s"] = sign(params)
    r = requests.get(f"{BASE_URL}/customer/get", params=params)
    if r.status_code == 200:
        return r.json().get('externalId')
    return None


def fetch_active_with_subscription_end(plan_id):
    """Retorna dict externalId → datos de suscripción activa con subscription_end."""
    results = {}
    start = 0
    limit = 100
    while True:
        params = {
            "apiKey": API_KEY, "planId": plan_id,
            "start": str(start), "limit": str(limit), "status": "1"
        }
        params["s"] = sign(params)
        r = requests.get(f"{BASE_URL}/subscription/list", params=params)
        if r.status_code != 200:
            break
        data = r.json()
        items = data.get('lists', []) or data.get('data', [])
        if not items:
            break
        for sub in items:
            if not sub.get('subscription_end') and not sub.get('cancel_at_period_end'):
                continue
            customer_id = sub.get('customerId')
            if not customer_id:
                continue
            ext_id = get_external_id(customer_id)
            time.sleep(0.03)
            if ext_id:
                results[ext_id] = {
                    'plan':             sub.get('planExternalId') or plan_id,
                    'subscription_end': sub.get('subscription_end'),
                    'inicio_plan':      sub.get('period_start'),
                    'fin_plan':         sub.get('period_end'),
                }
        if len(items) < limit:
            break
        start += limit
        time.sleep(0.03)
    return results


# ── Helpers fecha ─────────────────────────────────────────────────────────────

def parse_dt(value):
    if not value:
        return None
    for fmt in ('%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def calc_dias(dt1, dt2):
    if dt1 and dt2:
        return (dt2 - dt1).days
    return None


# ── MySQL ─────────────────────────────────────────────────────────────────────

def get_connection(autocommit=False):
    conn = mysql.connector.connect(**DB_CONFIG)
    conn.autocommit = autocommit
    return conn


def create_table_if_not_exists(conn):
    sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        id                  INT AUTO_INCREMENT PRIMARY KEY,
        user_id             VARCHAR(128) NOT NULL,
        email               VARCHAR(255),
        submitted_at        DATETIME,
        token               VARCHAR(255),
        motivo_cancelacion  TEXT,
        plan                VARCHAR(50),
        inicio_plan         DATETIME,
        fin_plan            DATETIME,
        subscription_end    DATETIME,
        dias_hasta_fin      INT,
        mail_enviado        TINYINT DEFAULT 0 COMMENT '0=no enviado, 3=enviado a 3 dias, 14=enviado a 14 dias',
        created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_id (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        try:
            cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN motivo_cancelacion TEXT AFTER token")
            print(f"Columna 'motivo_cancelacion' agregada a '{TABLE}'.")
        except Exception:
            pass  # Ya existe
    print(f"Tabla '{TABLE}' verificada/creada.")


def insert_sheet_rows(conn, rows):
    """Paso 1: inserta filas del sheet. Ignora duplicados por user_id."""
    sql = f"""
    INSERT IGNORE INTO {TABLE} (user_id, email, submitted_at, token, motivo_cancelacion)
    VALUES (%s, %s, %s, %s, %s)
    """
    inserted = 0
    with conn.cursor() as cur:
        for row in rows:
            user_id   = row.get(COL_USER_ID, '').strip()
            email     = row.get(COL_EMAIL, '').strip()
            submitted = row.get(COL_SUBMITTED, '').strip()
            token     = row.get(COL_TOKEN, '').strip()
            motivo    = row.get(COL_MOTIVO, '').strip()
            if not user_id:
                continue
            submitted_dt = parse_dt(submitted)
            cur.execute(sql, (user_id, email or None, submitted_dt, token or None, motivo or None))
            if cur.rowcount:
                inserted += 1
    return inserted


def get_rows_without_plan(conn):
    """Retorna user_id de filas que aún no tienen datos de Flow."""
    with conn.cursor(dictionary=True) as cur:
        cur.execute(f"SELECT user_id, submitted_at FROM {TABLE} WHERE plan IS NULL")
        return cur.fetchall()


def update_flow_data(conn, user_id, data, submitted_at):
    subscription_end_dt = parse_dt(data['subscription_end'])
    inicio_dt           = parse_dt(data['inicio_plan'])
    fin_dt              = parse_dt(data['fin_plan'])
    dias                = calc_dias(submitted_at, subscription_end_dt)

    sql = f"""
    UPDATE {TABLE}
    SET plan = %s, inicio_plan = %s, fin_plan = %s,
        subscription_end = %s, dias_hasta_fin = %s
    WHERE user_id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            data['plan'], inicio_dt, fin_dt,
            subscription_end_dt, dias, user_id
        ))
    conn.commit()


# ── Lectura de fuentes ────────────────────────────────────────────────────────

def read_from_csv(filepath):
    """Lee filas desde un CSV local."""
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader)


def read_from_google_sheets(sheet_url):
    """Lee filas desde una URL de Google Sheets publicada como CSV."""
    import io
    r = requests.get(sheet_url, timeout=30)
    if r.status_code != 200:
        print(f"Error al descargar sheet: HTTP {r.status_code}")
        sys.exit(1)
    r.encoding = 'utf-8-sig'
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Carga cancelados del sheet a MySQL y completa con datos de Flow API.\n'
                    'Fuente: --file (CSV local) o --sheet-url + --credentials (Google Sheets).'
    )
    # Fuente de datos (una de las dos)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--file',      help='CSV descargado del Google Sheet')
    source.add_argument('--sheet-url', help='URL publicada de Google Sheets (formato pub?output=csv)')
    args = parser.parse_args()

    # Leer datos según la fuente elegida
    if args.file:
        print(f"Fuente: CSV local — {args.file}")
        try:
            sheet_rows = read_from_csv(args.file)
        except FileNotFoundError:
            print(f"Error: No se encontró '{args.file}'")
            sys.exit(1)
    else:
        print(f"Fuente: Google Sheets — {args.sheet_url}")
        sheet_rows = read_from_google_sheets(args.sheet_url)

    print(f"Filas en el sheet: {len(sheet_rows)}")

    conn = get_connection(autocommit=True)

    # PASO 1 — Crear tabla y cargar sheet (solo nuevos)
    create_table_if_not_exists(conn)
    inserted = insert_sheet_rows(conn, sheet_rows)
    print(f"Paso 1 — Nuevos registros insertados: {inserted}")

    # PASO 2 — Obtener registros sin datos de Flow
    pendientes = get_rows_without_plan(conn)
    print(f"Paso 2 — Registros sin datos de Flow: {len(pendientes)}")

    if pendientes:
        # Construir lookup Flow: externalId → datos suscripción
        print("Obteniendo planes activos desde Flow...")
        planes = get_active_plans()
        print(f"Planes: {planes}")

        lookup = {}
        for plan_id in planes:
            print(f"  Buscando activos con subscription_end en {plan_id}...")
            data = fetch_active_with_subscription_end(plan_id)
            lookup.update(data)
            print(f"    -> {len(data)} encontrados")

        print(f"Total en lookup Flow: {len(lookup)}")

        # PASO 3 — Actualizar filas con datos de Flow
        actualizados = 0
        for row in pendientes:
            user_id      = row['user_id']
            submitted_at = row['submitted_at']
            if isinstance(submitted_at, str):
                submitted_at = parse_dt(submitted_at)

            sub_data = lookup.get(user_id)
            if sub_data:
                update_flow_data(conn, user_id, sub_data, submitted_at)
                actualizados += 1

        print(f"Paso 3 — Registros actualizados con datos Flow: {actualizados}")
    else:
        print("Paso 3 — No hay pendientes, todo está al día.")

    conn.close()
    print("\nProceso completado.")
