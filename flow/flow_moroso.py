import requests
import hashlib
import hmac
import json

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"
PLAN_FIXED = "s-13go-B001"
TARGET_DATE = "2026-05-16" # Solo fecha, sin hora

def make_flow_signature(params, secret):
    """Genera la firma 's' obligatoria."""
    clean_params = {k: str(v) for k, v in params.items()}
    sorted_keys = sorted(clean_params.keys())
    to_sign = "".join(f"{k}{clean_params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

def find_formatted_match():
    endpoint = f"{BASE_URL}/invoice/getOverDue"
    start = 0
    limit = 100
    
    print(f"--- Buscando en Plan: {PLAN_FIXED} ---")
    print(f"--- Filtros: Intentos=1, Reintento Programado, Fecha={TARGET_DATE} ---\n")

    while True:
        params = {
            "apiKey": API_KEY,
            "planId": PLAN_FIXED,
            "start": str(start),
            "limit": str(limit)
        }
        params["s"] = make_flow_signature(params, SECRET_KEY)
        
        try:
            response = requests.get(endpoint, params=params)
            if response.status_code != 200:
                print(f"Error API: {response.text}")
                break
            
            data = response.json()
            items = data.get('data', [])
            
            if not items:
                print("\nNo se encontraron más registros.")
                break

            for inv in items:
                # 1. FORMATEO DE PERIOD_END (quitamos la hora)
                raw_period_end = str(inv.get('period_end', ''))
                # Extraemos solo YYYY-MM-DD (los primeros 10 caracteres)
                formatted_period_end = raw_period_end[:10]
                
                # 2. Validar Intentos
                attempts = str(inv.get('attemp_count') or inv.get('attempt_count') or "0")
                
                # 3. Validar Fecha de Próximo Intento
                next_date = inv.get('next_attemp_date') or inv.get('next_attempt_date')

                # EVALUACIÓN
                is_correct_date = (formatted_period_end == TARGET_DATE)
                is_first_attempt = (attempts == "1")
                has_retry = next_date and str(next_date).strip() not in ["", "0000-00-00 00:00:00", "null"]

                if is_correct_date and is_first_attempt and has_retry:
                    print("🎯 ¡COINCIDENCIA ENCONTRADA CON FECHA FORMATEADA!")
                    print("=" * 60)
                    print(f"ID Factura: {inv.get('invoiceId')}")
                    print(f"Period End Original: {raw_period_end}")
                    print(f"Period End Comparado: {formatted_period_end}")
                    print("-" * 60)
                    print(json.dumps(inv, indent=4, ensure_ascii=False))
                    print("=" * 60)
                    return 

            print(f" > Analizados {start + len(items)} registros...", end="\r")
            
            if len(items) < limit:
                print("\nFin de registros sin hallazgos.")
                break
            start += limit

        except Exception as e:
            print(f"\nError: {e}")
            break

if __name__ == "__main__":
    find_formatted_match()