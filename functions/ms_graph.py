import webbrowser
from datetime import datetime
import json
import os
import msal
import hashlib
from typing import Dict, Optional

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'

class MultiUserGraphAuth:
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.tokens_dir = "user_tokens"
        if not os.path.exists(self.tokens_dir):
            os.makedirs(self.tokens_dir)
    
    def _get_user_token_path(self, user_id: str) -> str:
        """Genera un path único para el token del usuario"""
        # Usar hash del user_id para evitar caracteres problemáticos en nombres de archivo
        user_hash = hashlib.md5(user_id.encode()).hexdigest()
        return os.path.join(self.tokens_dir, f"token_{user_hash}.json")
    
    def initiate_auth_flow(self, user_id: str, scopes: list) -> Dict:
        """Inicia el flujo de autenticación para un usuario específico"""
        access_token_cache = msal.SerializableTokenCache()
        client = msal.PublicClientApplication(client_id=self.app_id, token_cache=access_token_cache)
        
        # Iniciar flujo de dispositivo
        flow = client.initiate_device_flow(scopes=scopes)
        
        # Guardar el flow temporalmente para este usuario
        temp_flow_path = os.path.join(self.tokens_dir, f"temp_flow_{hashlib.md5(user_id.encode()).hexdigest()}.json")
        with open(temp_flow_path, 'w') as f:
            json.dump({
                'flow': flow,
                'client_id': self.app_id,
                'user_id': user_id,
                'scopes': scopes
            }, f)
        
        return {
            'user_code': flow['user_code'],
            'device_code': flow['device_code'],
            'verification_uri': flow['verification_uri'],
            'message': f"Ve a {flow['verification_uri']} e ingresa el código: {flow['user_code']}",
            'expires_in': flow['expires_in']
        }
    
    def complete_auth_flow(self, user_id: str) -> Dict:
        """Completa el flujo de autenticación para un usuario específico"""
        user_hash = hashlib.md5(user_id.encode()).hexdigest()
        temp_flow_path = os.path.join(self.tokens_dir, f"temp_flow_{user_hash}.json")
        
        if not os.path.exists(temp_flow_path):
            raise Exception("No se encontró flujo de autenticación iniciado para este usuario")
        
        # Cargar el flow guardado
        with open(temp_flow_path, 'r') as f:
            flow_data = json.load(f)
        
        access_token_cache = msal.SerializableTokenCache()
        client = msal.PublicClientApplication(client_id=self.app_id, token_cache=access_token_cache)
        
        # Completar el flujo
        token_response = client.acquire_token_by_device_flow(flow_data['flow'])
        
        if 'access_token' in token_response:
            # Guardar el token del usuario
            user_token_path = self._get_user_token_path(user_id)
            with open(user_token_path, 'w') as f:
                f.write(access_token_cache.serialize())
            
            # Limpiar archivo temporal
            os.remove(temp_flow_path)
            
            return {
                'success': True,
                'message': 'Autenticación completada exitosamente',
                'user_id': user_id
            }
        else:
            return {
                'success': False,
                'error': token_response.get('error_description', 'Error desconocido')
            }
    
    def get_user_access_token(self, user_id: str, scopes: list) -> Optional[Dict]:
        """Obtiene el token de acceso para un usuario específico"""
        user_token_path = self._get_user_token_path(user_id)
        
        if not os.path.exists(user_token_path):
            return None
        
        # Cargar cache del token del usuario
        access_token_cache = msal.SerializableTokenCache()
        access_token_cache.deserialize(open(user_token_path, "r").read())
        
        # Verificar si el token ha expirado
        try:
            token_detail = json.loads(access_token_cache.serialize())
            if token_detail.get('AccessToken'):
                token_detail_key = list(token_detail['AccessToken'].keys())[0]
                token_expiration = datetime.fromtimestamp(int(token_detail['AccessToken'][token_detail_key]['expires_on']))
                if datetime.now() > token_expiration:
                    os.remove(user_token_path)
                    return None
        except:
            return None
        
        # Crear cliente y obtener token
        client = msal.PublicClientApplication(client_id=self.app_id, token_cache=access_token_cache)
        accounts = client.get_accounts()
        
        if accounts:
            token_response = client.acquire_token_silent(scopes, accounts[0])
            if 'access_token' in token_response:
                # Actualizar cache
                with open(user_token_path, 'w') as f:
                    f.write(access_token_cache.serialize())
                return token_response
        
        return None
    
    def is_user_authenticated(self, user_id: str) -> bool:
        """Verifica si un usuario está autenticado"""
        user_token_path = self._get_user_token_path(user_id)
        return os.path.exists(user_token_path)

# Funciones de compatibilidad con el código existente
def generate_access_token_for_user(app_id: str, user_id: str, scopes: list) -> Optional[Dict]:
    """Función de compatibilidad para obtener token de un usuario específico"""
    auth_manager = MultiUserGraphAuth(app_id)
    return auth_manager.get_user_access_token(user_id, scopes)