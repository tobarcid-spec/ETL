import argparse
import requests
import hashlib
import hmac
import sys
import time
import csv
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"


def make_flow_signature(params, secret):
    sorted_keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()


def get_active_plans():
    """Obtiene todos los planes activos desde la API de Flow."""
    endpoint = f"{BASE_URL}/plans/list"
    params = {"apiKey": API_KEY}
    params["s"] = make_flow_signature(params, SECRET_KEY)

    try:
        response = requests.get(endpoint, params=params)
        if response.status_code != 200:
            print(f"Error al obtener planes: {response.status_code} - {response.text}")
            return []
        data = response.json()
        if isinstance(data, list):
            plans = data
        else:
            plans = data.get('data', data.get('plans', []))
        plan_ids = [p.get('planId') or p.get('id') for p in plans if p.get('planId') or p.get('id')]
        print(f"Planes activos encontrados: {plan_ids}")
        return plan_ids
    except Exception as e:
        print(f"Error obteniendo planes: {e}")
        return []


def get_customer_details(customer_id):
    endpoint = f"{BASE_URL}/customer/get"
    params = {
        "apiKey": API_KEY,
        "customerId": str(customer_id)
    }
    params["s"] = make_flow_signature(params, SECRET_KEY)

    try:
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                "email": data.get('email', 'N/A'),
                "externalId": data.get('externalId', 'N/A')
            }
    except Exception as e:
        print(f"Error obteniendo cliente {customer_id}: {e}")
    return {"email": "N/A", "externalId": "N/A"}


def get_subscriptions_cancelled_by_day(plan_id, target_day, status=4):
    """Obtiene suscripciones canceladas cuyo subscription_end coincide exactamente con el día indicado."""
    endpoint = f"{BASE_URL}/subscription/list"
    subscriptions = []
    start = 0
    limit = 100

    print(f"\nConsultando plan {plan_id} - subscription_end del día: {target_day}")

    while True:
        params = {
            "apiKey": API_KEY,
            "planId": plan_id,
            "start": str(start),
            "limit": str(limit),
            "status": str(status)
        }
        params["s"] = make_flow_signature(params, SECRET_KEY)

        try:
            response = requests.get(endpoint, params=params)
            print(f"  Llamada API: start={start}, limit={limit}, status_code={response.status_code}")

            if response.status_code != 200:
                print(f"  Error {response.status_code}: {response.text}")
                break

            data = response.json()
            items = data.get('lists', []) or data.get('data', [])

            if not items:
                print(f"  No hay más suscripciones (encontradas para este plan: {len(subscriptions)})")
                break

            print(f"  Obtenidas {len(items)} suscripciones en este batch")

            for subscription in items:
                subscription_end_str = subscription.get('subscription_end')
                if not subscription_end_str:
                    continue
                try:
                    subscription_end_day = datetime.strptime(subscription_end_str, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    print(f"  Fecha inválida en subscription_end: {subscription_end_str}")
                    continue

                if subscription_end_day != target_day:
                    continue

                customer_id = subscription.get('customerId')
                customer_data = get_customer_details(customer_id)

                period_start_str = subscription.get('period_start')
                period_end_str = subscription.get('period_end')
                dias_plan = None
                if period_start_str and period_end_str:
                    try:
                        fmt = '%Y-%m-%d %H:%M:%S'
                        dias_plan = (datetime.strptime(period_end_str, fmt) - datetime.strptime(period_start_str, fmt)).days
                    except ValueError:
                        pass

                subscriptions.append({
                    "planId": plan_id,
                    "subscriptionId": subscription.get('subscriptionId') or subscription.get('id') or 'N/A',
                    "customerId": customer_id,
                    "externalId": customer_data['externalId'],
                    "email": customer_data['email'],
                    "name": subscription.get('name') or subscription.get('customerName') or 'N/A',
                    "status": subscription.get('status', 'N/A'),
                    "period_start": period_start_str,
                    "period_end": period_end_str,
                    "dias_plan": dias_plan,
                    "subscription_end": subscription.get('subscription_end'),
                    "cancel_at": subscription.get('cancel_at')
                })

            if len(items) < limit:
                print(f"  Fin del listado del plan {plan_id}")
                break

            start += limit
            time.sleep(0.05)

        except Exception as e:
            print(f"  Error consultando suscripciones: {e}")
            break

    return subscriptions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Listar suscriptores cancelados filtrando por día exacto de subscription_end. '
                    'Si no se indica --plan, consulta todos los planes activos.'
    )
    parser.add_argument('--plan', default=None, help='ID de un plan específico (ej: s-13go-A003). Omitir para todos los planes.')
    parser.add_argument('--status', default=4, type=int, help='Estado de suscripción (4=canceladas)')
    parser.add_argument(
        '--date',
        required=True,
        help='Día exacto para filtrar subscription_end en formato YYYY-MM-DD (obligatorio)'
    )
    args = parser.parse_args()

    try:
        target_day = datetime.strptime(args.date, '%Y-%m-%d').date()
    except ValueError:
        print("Error: Formato de fecha inválido. Use YYYY-MM-DD.")
        sys.exit(1)

    # Determinar planes a consultar
    if args.plan:
        planes = [args.plan]
    else:
        print("Obteniendo planes activos desde la API...")
        planes = get_active_plans()
        if not planes:
            print("No se encontraron planes activos. Verifique la API.")
            sys.exit(1)

    print(f"\n=== Cancelados por Día - Día: {args.date} - Planes: {planes} ===")

    all_subscriptions = []
    for plan_id in planes:
        subs = get_subscriptions_cancelled_by_day(plan_id, target_day, status=args.status)
        all_subscriptions.extend(subs)
        print(f"  -> Plan {plan_id}: {len(subs)} cancelados el {args.date}")

    print(f"\nTotal general de cancelados el {args.date}: {len(all_subscriptions)}")

    if all_subscriptions:
        date_safe = args.date.replace('-', '')
        plan_label = args.plan if args.plan else "todos"
        filename = f"reporte_cancelados_dia_{date_safe}_{plan_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        keys = [
            "planId", "subscriptionId", "customerId", "externalId",
            "email", "name", "status", "period_start", "period_end", "dias_plan",
            "subscription_end", "cancel_at"
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_subscriptions)

        print(f"Archivo generado: {filename}")
    else:
        print(f"No se encontraron cancelados con subscription_end el {args.date}.")
