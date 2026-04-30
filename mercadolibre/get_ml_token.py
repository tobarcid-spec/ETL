"""
Script para intercambiar AUTH_CODE por Access Token y Refresh Token en MercadoLibre
Utiliza el flujo OAuth 2.0 de MercadoLibre
"""

import requests
import json
from datetime import datetime, timedelta
import logging
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MercadoLibreOAuth:
    """Gestiona el flujo OAuth 2.0 de MercadoLibre"""
    
    TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8000"):
        """
        Inicializa el cliente OAuth
        
        Args:
            client_id: ID de tu aplicación en MercadoLibre
            client_secret: Secret de tu aplicación
            redirect_uri: URI de redirección configurado en MercadoLibre
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
    
    def exchange_auth_code_for_token(self, auth_code: str) -> dict:
        """
        Intercambia el código de autorización por access_token y refresh_token
        
        Args:
            auth_code: Código obtenido del flujo de autorización de MercadoLibre
            
        Returns:
            Diccionario con los tokens obtenidos
        """
        try:
            payload = {
                'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'redirect_uri': self.redirect_uri
            }
            
            logger.info("🔄 Intercambiando AUTH_CODE por tokens...")
            
            response = requests.post(self.TOKEN_URL, data=payload, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Guardar tokens
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            # Calcular expiración
            expires_in = token_data.get('expires_in', 21600)  # 6 horas por defecto
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("✅ Tokens obtenidos exitosamente")
            
            return {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expires_in': expires_in,
                'token_expiry': self.token_expiry.isoformat(),
                'user_id': token_data.get('user_id'),
                'scope': token_data.get('scope'),
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en intercambio de tokens: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"   Detalle: {e.response.text}")
            return {}
    
    def refresh_access_token(self) -> dict:
        """
        Usa el refresh_token para obtener un nuevo access_token
        
        Returns:
            Diccionario con el nuevo access_token
        """
        if not self.refresh_token:
            logger.error("❌ No hay refresh_token disponible")
            return {}
        
        try:
            payload = {
                'grant_type': 'refresh_token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token
            }
            
            logger.info("🔄 Renovando access_token...")
            
            response = requests.post(self.TOKEN_URL, data=payload, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            self.access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 21600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info("✅ Access token renovado exitosamente")
            
            return {
                'access_token': self.access_token,
                'expires_in': expires_in,
                'token_expiry': self.token_expiry.isoformat(),
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error renovando token: {e}")
            return {}


def main():
    """Función principal"""
    
    print("\n" + "="*70)
    print(" 🔐 MercadoLibre OAuth 2.0 - Token Exchange".center(70))
    print("="*70 + "\n")
    
    # ==================== INGRESA TUS CREDENCIALES ====================
    
    CLIENT_ID = input("📝 Ingresa tu CLIENT_ID: ").strip()
    if not CLIENT_ID:
        print("❌ CLIENT_ID es obligatorio")
        return
    
    CLIENT_SECRET = input("📝 Ingresa tu CLIENT_SECRET: ").strip()
    if not CLIENT_SECRET:
        print("❌ CLIENT_SECRET es obligatorio")
        return
    
    AUTH_CODE = input("📝 Ingresa tu AUTH_CODE: ").strip()
    if not AUTH_CODE:
        print("❌ AUTH_CODE es obligatorio")
        return
    
    REDIRECT_URI = input("📝 Ingresa tu REDIRECT_URI (Enter para usar http://localhost:8000): ").strip()
    if not REDIRECT_URI:
        REDIRECT_URI = "http://localhost:8000"
    
    # ==================== INTERCAMBIAR CÓDIGOS POR TOKENS ====================
    
    oauth = MercadoLibreOAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    
    token_result = oauth.exchange_auth_code_for_token(AUTH_CODE)
    
    if token_result:
        print("\n" + "="*70)
        print(" ✅ TOKENS OBTENIDOS EXITOSAMENTE".center(70))
        print("="*70 + "\n")
        
        # Mostrar información
        print(f"👤 User ID:              {token_result.get('user_id', 'N/A')}")
        print(f"🔑 Access Token:         {token_result['access_token'][:50]}...")
        
        refresh_token = token_result.get('refresh_token')
        if refresh_token:
            print(f"🔄 Refresh Token:        {refresh_token[:50]}...")
        else:
            print(f"🔄 Refresh Token:        No disponible (algunos scopes no lo requieren)")
        
        print(f"⏱️  Expira en:            {token_result['expires_in']} segundos")
        print(f"📅 Fecha de Expiración:  {token_result['token_expiry']}")
        print(f"📌 Scope:                {token_result.get('scope', 'N/A')}")
        print(f"🏷️  Token Type:           {token_result['token_type']}")
        
        # ==================== GUARDAR TOKENS EN ARCHIVO ====================
        
        save_tokens = input("\n¿Deseas guardar los tokens en un archivo JSON? (s/n): ").strip().lower()
        
        if save_tokens == 's':
            filename = input("📁 Nombre del archivo (Enter para usar '../data/ml_token.json'): ").strip()
            if not filename:
                filename = os.path.join(os.path.dirname(__file__), '..', 'data', 'ml_token.json')
            
            tokens_to_save = {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI,
                'access_token': token_result['access_token'],
                'refresh_token': token_result.get('refresh_token'),
                'user_id': token_result.get('user_id'),
                'token_expiry': token_result['token_expiry'],
                'expires_in': token_result['expires_in'],
                'obtained_at': datetime.now().isoformat()
            }
            
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(tokens_to_save, f, indent=2, ensure_ascii=False)
                print(f"\n✅ Tokens guardados en: {filename}")
                print(f"⚠️  IMPORTANTE: Protege este archivo ya que contiene tus credenciales")
            except Exception as e:
                logger.error(f"❌ Error guardando archivo: {e}")
        
        # ==================== OPCIÓN PARA USAR LOS TOKENS ====================
        
        use_tokens = input("\n¿Deseas usar estos tokens en el script mercadolibre_api.py? (s/n): ").strip().lower()
        
        if use_tokens == 's':
            print("\n📋 Para usar estos tokens en mercadolibre_api.py:")
            print("   1. Abre el archivo mercadolibre_api.py")
            print("   2. En la sección 'CONFIGURACIÓN' (línea ~378), reemplaza:")
            print(f"      CLIENT_ID = \"{CLIENT_ID}\"")
            print(f"      CLIENT_SECRET = \"{CLIENT_SECRET}\"")
            print(f"      AUTH_CODE = \"{AUTH_CODE}\"")
    
    else:
        print("\n❌ No se pudieron obtener los tokens. Verifica tus credenciales.\n")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
