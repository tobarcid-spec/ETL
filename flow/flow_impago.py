import requests
import hashlib
import hmac
import json

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"

# El ID solicitado por el usuario
INVOICE_ID = 6218748 

def make_flow_signature(params, secret):
    """Genera la firma 's' obligatoria."""
    # Ordenamos llaves y concatenamos k1v1k2v2...
    sorted_keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

def inspect_invoice_detail():
    endpoint = f"{BASE_URL}/invoice/get"
    
    # Parámetros estrictos solicitados: apiKey, invoiceId (como número), s
    # Nota: Para la firma y la URL, tratamos los valores como string
    params = {
        "apiKey": API_KEY,
        "invoiceId": str(INVOICE_ID)
    }
    
    # Generar firma obligatoria
    params["s"] = make_flow_signature(params, SECRET_KEY)
    
    print(f"--- Consultando Detalle de Invoice ID: {INVOICE_ID} ---")
    
    try:
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Imprimimos el JSON completo para ver la estructura exacta
            print("\nESTRUCTURA DE DATOS RECIBIDA:")
            print(json.dumps(data, indent=4, ensure_ascii=False))
            
            # Análisis rápido de campos clave
            print("\n" + "="*40)
            print("RESUMEN DE CAMPOS ENCONTRADOS:")
            print(f"- Status: {data.get('status')}")
            print(f"- Monto: {data.get('amount')}")
            print(f"- Intentos (attemp_count): {data.get('attemp_count')}")
            print(f"- Fecha Vencimiento: {data.get('dueDate')}")
            print("="*40)
            
        else:
            print(f"\nERROR {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"\nERROR DE CONEXIÓN: {e}")

if __name__ == "__main__":
    inspect_invoice_detail()