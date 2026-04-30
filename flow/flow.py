import requests
import hashlib
import hmac
import time
import csv
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"

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
            # Retornamos los campos solicitados
            return {
                "email": data.get('email', 'N/A'),
                "externalId": data.get('externalId', 'N/A')
            }
    except Exception as e:
        print(f"\nError obteniendo cliente {customer_id}: {e}")
    return {"email": "N/A", "externalId": "N/A"}

def get_all_plans():
    """Obtiene la lista de IDs de planes."""
    endpoint = f"{BASE_URL}/plans/list"
    plans = []
    params = {"apiKey": API_KEY}
    params["s"] = make_flow_signature(params, SECRET_KEY)
    
    try:
        response = requests.get(endpoint, params=params)
        res_json = response.json()
        # Intentamos obtener desde 'data' o 'lists' según corresponda
        items = res_json.get('data', []) or res_json.get('lists', [])
        for p in items:
            pid = p.get('planId') or p.get('id')
            if pid: plans.append(pid)
    except Exception as e:
        print(f"Aviso: Error listando planes: {e}")
    
    return plans

def get_grace_period_subs(plan_id):
    """Extrae suscriptores en periodo de gracia incorporando datos de cliente."""
    endpoint = f"{BASE_URL}/subscription/list"
    found = []
    start = 0
    limit = 100

    while True:
        params = {
            "apiKey": API_KEY,
            "planId": plan_id,
            "start": str(start),
            "limit": str(limit),
            "status": "1" # Solo Activos
        }
        params["s"] = make_flow_signature(params, SECRET_KEY)
        
        try:
            response = requests.get(endpoint, params=params)
            if response.status_code != 200: break
            
            res_json = response.json()
            # Usamos 'lists' que es la llave confirmada para suscripciones
            items = res_json.get('lists', []) or res_json.get('data', [])
            if not items: break
            
            for s in items:
                sub_end = s.get('subscription_end') or s.get('cancel_at')
                
                # Lógica: Tiene fecha de término programada
                if sub_end and str(sub_end).strip() not in ["", "0", "0000-00-00 00:00:00"]:
                    cust_id = s.get('customerId')
                    
                    # CONSULTA ADICIONAL: Datos del cliente
                    cust_data = get_customer_details(cust_id)
                    
                    found.append({
                        "customerId": cust_id,
                        "externalId": cust_data["externalId"], # Nuevo campo
                        "email": cust_data["email"],           # Nuevo campo
                        "name": s.get('name') or s.get('customerName') or "N/A",
                        "period_start": s.get('period_start'),
                        "period_end": s.get('period_end'),
                        "subscription_end": sub_end,
                        "planExternalId": plan_id
                    })
            
            if len(items) < limit: break
            start += limit
            time.sleep(0.05) 
        except:
            break
            
    return found

if __name__ == "__main__":
    plan_list = get_all_plans()
    
    if not plan_list:
        print("Usando lista de planes manual...")
        plan_list = ["s-13go-B001"] 
    
    print(f"Iniciando escaneo en {len(plan_list)} planes...")
    
    final_report = []
    for pid in plan_list:
        print(f" > Procesando plan: {pid} (Encontrados: {len(final_report)})", end="\r")
        subs = get_grace_period_subs(pid)
        final_report.extend(subs)
    
    print(f"\n\nEscaneo completo. Total en Periodo de Gracia: {len(final_report)}")
    
    if final_report:
        filename = f"reporte_gracia_clientes_{datetime.now().strftime('%Y%m%d')}.csv"
        # Campos actualizados con email y externalId
        keys = ["customerId", "externalId", "email", "name", "period_start", "period_end", "subscription_end", "planExternalId"]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(final_report)
            
        print(f"Archivo generado con datos de clientes: {filename}")
    else:
        print("No se encontraron registros con término programado.")