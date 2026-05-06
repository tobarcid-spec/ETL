import requests
import hashlib
import hmac
import json
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = "653BA8F3-0BCC-4571-AF8F-1L440B0751CF"
SECRET_KEY = "43ed83a62b6efcd88a5c9281728d257e99541757"
BASE_URL = "https://www.flow.cl/api"
PLAN_ID = "s-13go-A001"


def make_flow_signature(params, secret):
    """Genera la firma 's' obligatoria."""
    sorted_keys = sorted(params.keys())
    to_sign = "".join(f"{k}{params[k]}" for k in sorted_keys)
    return hmac.new(secret.encode('utf-8'), to_sign.encode('utf-8'), hashlib.sha256).hexdigest()


# Test 1: subscription/list con status=4 (canceladas)
print("=" * 80)
print("TEST 1: /subscription/list (status=4 - canceladas)")
print("=" * 80)

endpoint = f"{BASE_URL}/subscription/list"
params = {
    "apiKey": API_KEY,
    "planId": PLAN_ID,
    "start": "0",
    "limit": "5",
    "status": "4"
}
params["s"] = make_flow_signature(params, SECRET_KEY)

try:
    response = requests.get(endpoint, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    data = response.json()
    print(f"\nTotal de suscripciones canceladas: {data.get('total', 0)}")
    
    # Filtrar solo las que tienen subscription_end en mayo 2026
    filtered_data = []
    if 'data' in data:
        for subscription in data['data']:
            subscription_end = subscription.get('subscription_end')
            if subscription_end and subscription_end.startswith('2026-05'):
                filtered_data.append(subscription)
    
    print(f"Suscripciones canceladas en mayo 2026: {len(filtered_data)}")
    
    print("\nJSON Response (filtrado mayo 2026):")
    filtered_response = data.copy()
    filtered_response['data'] = filtered_data
    filtered_response['total'] = len(filtered_data)
    print(json.dumps(filtered_response, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
    print(f"Response text: {response.text}")

# Test 2: customer/get con el primer cliente
print("\n" + "=" * 80)
print("TEST 2: /customer/get")
print("=" * 80)

endpoint = f"{BASE_URL}/customer/get"
params = {
    "apiKey": API_KEY,
    "customerId": "123456"  # ID de prueba
}
params["s"] = make_flow_signature(params, SECRET_KEY)

try:
    response = requests.get(endpoint, params=params)
    print(f"Status Code: {response.status_code}")
    print("\nJSON Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
    print(f"Response text: {response.text}")

# Test 3: plans/list
print("\n" + "=" * 80)
print("TEST 3: /plans/list")
print("=" * 80)

endpoint = f"{BASE_URL}/plans/list"
params = {
    "apiKey": API_KEY
}
params["s"] = make_flow_signature(params, SECRET_KEY)

try:
    response = requests.get(endpoint, params=params)
    print(f"Status Code: {response.status_code}")
    print("\nJSON Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
    print(f"Response text: {response.text}")
