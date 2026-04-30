import requests
import hashlib
import hmac
import json

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"

# El ID que quieres inspeccionar
INVOICE_ID = "6413650" 

def make_flow_signature(params, secret):
    """Genera la firma 's' obligatoria."""
    sorted_keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

def inspect_single_invoice():
    endpoint = f"{BASE_URL}/invoice/get"
    
    # Parámetros requeridos según documentación
    params = {
        "apiKey": API_KEY,
        "invoiceId": INVOICE_ID
    }
    
    # Generar firma
    params["s"] = make_flow_signature(params, SECRET_KEY)
    
    print(f"--- Consultando Detalle de Invoice: {INVOICE_ID} ---\n")
    
    try:
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Mostramos el JSON completo para ver la estructura
            print("ESTRUCTURA DE DATOS RECIBIDA:")
            print(json.dumps(data, indent=4, ensure_ascii=False))
            
            # Verificación de campos críticos
            print("\n" + "="*40)
            print("DATOS CLAVE DETECTADOS:")
            print(f"- Status: {data.get('status')}")
            print(f"- Cliente ID: {data.get('customerId')}")
            print(f"- Monto: {data.get('amount')}")
            print(f"- Intentos: {data.get('attemp_count') or data.get('attempt_count', 'N/A')}")
            print(f"- Fecha Vencimiento: {data.get('dueDate')}")
            print("="*40)
            
        else:
            print(f"Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    inspect_single_invoice()