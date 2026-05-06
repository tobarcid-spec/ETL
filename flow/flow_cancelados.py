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
PLAN_ID = "s-13go-B004"


def make_flow_signature(params, secret):
    """Genera la firma 's' obligatoria."""
    sorted_keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()


def get_customer_details(customer_id):
    """Obtiene email y externalId desde la API de clientes."""
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


def get_subscriptions_from_plan(plan_id, status=4, target_date=None):
    """Obtiene suscripciones canceladas de un plan para el mes de una fecha target.

    Args:
        plan_id: ID del plan (ej: 's-13go-A003')
        status: Estado de suscripción (4=canceladas)
        target_date: Fecha específica para filtrar el mes (YYYY-MM-DD). Si es None, usa el mes actual.
    """
    endpoint = f"{BASE_URL}/subscription/list"
    subscriptions = []
    start = 0
    limit = 100

    if target_date:
        try:
            target_month = datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Formato de fecha inválido. Use YYYY-MM-DD.")
    else:
        target_month = datetime.now()

    month_start = target_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    month_end = month_end.replace(hour=23, minute=59, second=59)

    print(f"Consultando suscripciones canceladas del plan {plan_id}...")
    print(f"Filtrando subscription_end entre {month_start.strftime('%Y-%m-%d')} y {month_end.strftime('%Y-%m-%d')}")

    while True:
        params = {
            "apiKey": API_KEY,
            "planId": plan_id,
            "start": str(start),
            "limit": str(limit)
        }
        
        if status:
            params["status"] = str(status)
        
        params["s"] = make_flow_signature(params, SECRET_KEY)

        try:
            response = requests.get(endpoint, params=params)
            print(f"  Llamada API: start={start}, limit={limit}, status_code={response.status_code}")
            
            if response.status_code != 200:
                print(f"Error {response.status_code}: {response.text}")
                break

            data = response.json()
            items = data.get('lists', []) or data.get('data', [])
            
            if not items:
                print(f"  No hay más suscripciones (total obtenidas: {len(subscriptions)})")
                break

            print(f"  Obtenidas {len(items)} suscripciones en este batch")

            for subscription in items:
                # Filtrar por subscription_end del mes objetivo
                subscription_end_str = subscription.get('subscription_end')
                if subscription_end_str:
                    try:
                        subscription_end = datetime.strptime(subscription_end_str, '%Y-%m-%d %H:%M:%S')
                        if not (month_start <= subscription_end <= month_end):
                            continue  # No cumple con el filtro de mes objetivo
                    except ValueError:
                        print(f"  Fecha inválida en subscription_end: {subscription_end_str}")
                        continue

                customer_id = subscription.get('customerId')
                customer_data = get_customer_details(customer_id)

                subscriptions.append({
                    "planId": plan_id,
                    "subscriptionId": subscription.get('subscriptionId') or subscription.get('id') or 'N/A',
                    "customerId": customer_id,
                    "externalId": customer_data['externalId'],
                    "email": customer_data['email'],
                    "name": subscription.get('name') or subscription.get('customerName') or 'N/A',
                    "status": subscription.get('status', 'N/A'),
                    "period_start": subscription.get('period_start'),
                    "period_end": subscription.get('period_end'),
                    "subscription_end": subscription.get('subscription_end'),
                    "cancel_at": subscription.get('cancel_at')
                })

            if len(items) < limit:
                print(f"  Fin del listado alcanzado")
                break

            start += limit
            time.sleep(0.05)

        except Exception as e:
            print(f"Error consultando suscripciones: {e}")
            break

    return subscriptions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Listar suscriptores cancelados de un plan Flow por fecha de subscription_end.')
    parser.add_argument('--plan', default=PLAN_ID, help='ID del plan Flow (ej: s-13go-A003)')
    parser.add_argument('--status', default=4, type=int, help='Estado de suscripción (4=canceladas)')
    parser.add_argument('--date', help='Fecha específica para filtrar el mes de subscription_end en formato YYYY-MM-DD')
    args = parser.parse_args()

    target_date = args.date
    plan_id = args.plan
    status = args.status

    title_date = target_date if target_date else datetime.now().strftime('%Y-%m-%d')
    print(f"=== Listado de Suscriptores Cancelados - Plan {plan_id} - Fecha objetivo: {title_date} ===\n")

    try:
        subscriptions = get_subscriptions_from_plan(plan_id, status=status, target_date=target_date)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"\nTotal de suscripciones canceladas obtenidas: {len(subscriptions)}")

    if subscriptions:
        output_date = target_date if target_date else datetime.now().strftime('%Y-%m-%d')
        output_date_safe = output_date.replace('-', '')
        filename = f"reporte_suscriptores_cancelados_{output_date_safe}_{plan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        keys = [
            "planId",
            "subscriptionId",
            "customerId",
            "externalId",
            "email",
            "name",
            "status",
            "period_start",
            "period_end",
            "subscription_end",
            "cancel_at"
        ]

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(subscriptions)

        print(f"Archivo generado: {filename}")
    else:
        print("No se encontraron suscripciones canceladas para el mes seleccionado y este plan.")