import argparse
import requests
import hashlib
import hmac
import sys
import csv
import time
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"

# Columnas del CSV de Google Sheets
COL_USER_ID   = 'user_id'
COL_EMAIL     = 'email'
COL_SUBMITTED = 'Submitted At'
COL_TOKEN     = 'Token'


def make_flow_signature(params, secret):
    sorted_keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()


def get_active_plans():
    endpoint = f"{BASE_URL}/plans/list"
    params = {"apiKey": API_KEY}
    params["s"] = make_flow_signature(params, SECRET_KEY)
    try:
        r = requests.get(endpoint, params=params)
        if r.status_code == 200:
            data = r.json()
            plans = data if isinstance(data, list) else data.get('data', data.get('plans', []))
            return [p.get('planId') or p.get('id') for p in plans if p.get('planId') or p.get('id')]
    except Exception as e:
        print(f"Error obteniendo planes: {e}")
    return []


def get_external_id(customer_id):
    """Obtiene el externalId (Firebase UID) de un customerId de Flow."""
    endpoint = f"{BASE_URL}/customer/get"
    params = {"apiKey": API_KEY, "customerId": str(customer_id)}
    params["s"] = make_flow_signature(params, SECRET_KEY)
    try:
        r = requests.get(endpoint, params=params)
        if r.status_code == 200:
            return r.json().get('externalId')
    except Exception as e:
        print(f"  Error customer/get {customer_id}: {e}")
    return None


def fetch_active_with_subscription_end(plan_id):
    """Descarga suscripciones activas (status=1) que tienen cancel_at_period_end=1 o subscription_end."""
    endpoint = f"{BASE_URL}/subscription/list"
    results = {}
    start = 0
    limit = 100

    while True:
        params = {
            "apiKey": API_KEY,
            "planId": plan_id,
            "start": str(start),
            "limit": str(limit),
            "status": "1"
        }
        params["s"] = make_flow_signature(params, SECRET_KEY)
        try:
            r = requests.get(endpoint, params=params)
            if r.status_code != 200:
                print(f"  Error {r.status_code} plan {plan_id}")
                break
            data = r.json()
            items = data.get('lists', []) or data.get('data', [])
            if not items:
                break

            for sub in items:
                # Solo procesar los que tienen subscription_end (cancelación programada)
                if not sub.get('subscription_end') and not sub.get('cancel_at_period_end'):
                    continue

                customer_id = sub.get('customerId')
                if not customer_id:
                    continue

                external_id = get_external_id(customer_id)
                time.sleep(0.05)

                if external_id:
                    results[external_id] = {
                        'plan':             sub.get('planExternalId') or plan_id,
                        'subscription_end': sub.get('subscription_end'),
                        'period_start':     sub.get('period_start'),
                        'period_end':       sub.get('period_end'),
                    }

            if len(items) < limit:
                break
            start += limit
            time.sleep(0.05)

        except Exception as e:
            print(f"  Error: {e}")
            break

    return results


def parse_submitted_at(value):
    """Parsea submitted_at en formato DD/MM/YYYY HH:MM:SS o variantes."""
    for fmt in ('%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def calc_dias(dt1, dt2):
    """Días entre dos datetimes (dt2 - dt1)."""
    if dt1 and dt2:
        return (dt2 - dt1).days
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Cruza cancelados del sheet con suscripciones activas de Flow y calcula días hasta subscription_end.'
    )
    parser.add_argument('--file', required=True, help='CSV descargado del Google Sheet')
    args = parser.parse_args()

    # 1. Obtener planes activos
    print("Obteniendo planes activos...")
    planes = get_active_plans()
    if not planes:
        print("No se encontraron planes.")
        sys.exit(1)
    print(f"Planes: {planes}\n")

    # 2. Para cada plan, descargar activos con subscription_end y obtener su externalId
    lookup = {}  # externalId → datos suscripción
    for plan_id in planes:
        print(f"Buscando activos con subscription_end en plan {plan_id}...")
        plan_data = fetch_active_with_subscription_end(plan_id)
        lookup.update(plan_data)
        print(f"  -> {len(plan_data)} registros encontrados")

    print(f"\nTotal en lookup: {len(lookup)} suscripciones con subscription_end\n")

    # 3. Leer CSV del sheet
    try:
        with open(args.file, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"Error: No se encontró '{args.file}'")
        sys.exit(1)

    print(f"Filas en el sheet: {len(rows)}\n")

    # 4. Cruzar y calcular
    results = []
    con_datos = 0

    for row in rows:
        user_id   = row.get(COL_USER_ID, '').strip()
        email     = row.get(COL_EMAIL, '').strip()
        submitted = row.get(COL_SUBMITTED, '').strip()
        token     = row.get(COL_TOKEN, '').strip()

        sub = lookup.get(user_id)

        if sub:
            subscription_end_str = sub.get('subscription_end')
            plan                 = sub.get('plan')
            period_start         = sub.get('period_start')
            period_end           = sub.get('period_end')

            submitted_dt        = parse_submitted_at(submitted)
            subscription_end_dt = parse_submitted_at(subscription_end_str) if subscription_end_str else None
            dias_hasta_fin      = calc_dias(submitted_dt, subscription_end_dt)
            con_datos          += 1
        else:
            subscription_end_str = None
            plan                 = None
            period_start         = None
            period_end           = None
            dias_hasta_fin       = None

        results.append({
            "mail":             email,
            "user_id":          user_id,
            "submitted_at":     submitted,
            "token":            token,
            "plan":             plan,
            "inicio_plan":      period_start,
            "fin_plan":         period_end,
            "subscription_end": subscription_end_str,
            "dias_hasta_fin":   dias_hasta_fin,
        })

    print(f"Total procesados : {len(results)}")
    print(f"Con datos        : {con_datos}")
    print(f"Sin match        : {len(results) - con_datos}")

    if results:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reporte_plan_cancelados_{timestamp}.csv"
        keys = [
            "mail", "user_id", "submitted_at", "token",
            "plan", "inicio_plan", "fin_plan", "subscription_end", "dias_hasta_fin"
        ]
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"Archivo generado: {filename}")
