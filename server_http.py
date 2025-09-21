from fastmcp import FastMCP
import os


from dotenv import load_dotenv
from functions.ms_graph import MultiUserGraphAuth

# Configurar el servidor MCP
mcp = FastMCP("MCP Server Multi-User")

# Instancia global del manejador de autenticación
auth_manager = None

def init_auth_manager():
    """Inicializa el manejador de autenticación"""
    global auth_manager
    if auth_manager is None:
        load_dotenv()
        app_id = os.getenv("APP_ID")
        if not app_id:
            raise Exception("APP_ID no encontrado en variables de entorno")
        auth_manager = MultiUserGraphAuth(app_id)
    return auth_manager

@mcp.tool()
def start_outlook_auth(user_id: str) -> str:
    """
    Inicia el proceso de autenticación de Outlook para un usuario específico
    
    Args:
        user_id: Identificador único del usuario (puede ser email, username, etc.)
    
    Returns:
        Información del proceso de autenticación incluyendo el código a ingresar
    """
    try:
        auth_mgr = init_auth_manager()
        scopes = ['Calendars.ReadWrite', 'Mail.Read', 'User.Read']
        
        # Verificar si ya está autenticado
        if auth_mgr.is_user_authenticated(user_id):
            return f"✅ Usuario {user_id} ya está autenticado. Puedes usar create_outlook_event directamente."
        
        auth_info = auth_mgr.initiate_auth_flow(user_id, scopes)
        
        return f"""
🔐 Proceso de autenticación iniciado para: {user_id}

📱 INSTRUCCIONES:
1. Ve a: {auth_info['verification_uri']}
2. Ingresa este código: {auth_info['user_code']}
3. Completa el login en tu navegador
4. Luego ejecuta: complete_outlook_auth con tu user_id

⏰ El código expira en {auth_info['expires_in']} segundos
"""
    except Exception as e:
        return f"❌ Error al iniciar autenticación: {str(e)}"

@mcp.tool()
def complete_outlook_auth(user_id: str) -> str:
    """
    Completa el proceso de autenticación de Outlook para un usuario específico
    
    Args:
        user_id: Identificador único del usuario que inició la autenticación
    
    Returns:
        Resultado del proceso de autenticación
    """
    try:
        auth_mgr = init_auth_manager()
        result = auth_mgr.complete_auth_flow(user_id)
        
        if result['success']:
            return f"✅ Autenticación completada exitosamente para: {user_id}. Ya puedes crear eventos de Outlook."
        else:
            return f"❌ Error en la autenticación: {result['error']}"
    except Exception as e:
        return f"❌ Error al completar autenticación: {str(e)}"

@mcp.tool()
def check_outlook_auth_status(user_id: str) -> str:
    """
    Verifica el estado de autenticación de un usuario
    
    Args:
        user_id: Identificador único del usuario
    
    Returns:
        Estado de autenticación del usuario
    """
    try:
        auth_mgr = init_auth_manager()
        is_authenticated = auth_mgr.is_user_authenticated(user_id)
        
        if is_authenticated:
            return f"✅ Usuario {user_id} está autenticado y listo para usar Outlook"
        else:
            return f"❌ Usuario {user_id} NO está autenticado. Usa start_outlook_auth primero."
    except Exception as e:
        return f"❌ Error al verificar autenticación: {str(e)}"

@mcp.tool()
def create_outlook_event(user_id: str, event_name: str, event_date: str, start_time: str, end_time: str, description: str, attendees: str) -> str:
    """
    Crea un evento en Outlook para un usuario autenticado específico
    
    Args:
        user_id: Identificador único del usuario autenticado
        event_name: Nombre del evento
        event_date: Fecha del evento (YYYY-MM-DD)
        start_time: Hora de inicio (HH:MM)
        end_time: Hora de fin (HH:MM) 
        description: Descripción del evento
        attendees: Emails de invitados separados por comas
    
    Returns:
        Resultado de la creación del evento
    """
    try:
        auth_mgr = init_auth_manager()
        
        # Verificar autenticación
        if not auth_mgr.is_user_authenticated(user_id):
            return f"❌ Usuario {user_id} no está autenticado. Ejecuta start_outlook_auth primero."
        
        # Obtener token del usuario
        scopes = ['Calendars.ReadWrite']
        token_response = auth_mgr.get_user_access_token(user_id, scopes)
        
        if not token_response:
            return f"❌ No se pudo obtener token válido para {user_id}. Reautentica usando start_outlook_auth."
        
        # Procesar emails de asistentes
        emails = [email.strip() for email in attendees.split(",")]
        
        # Aquí usarías tu función create_event existente pero con el token específico del usuario
        result = create_event_with_token(
            access_token=token_response['access_token'],
            event_name=event_name,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees_emails=emails
        )
        
        return f"✅ Evento creado para usuario {user_id}: {result}"
    except Exception as e:
        return f"❌ Error en create_outlook_event: {str(e)}"

def create_event_with_token(access_token: str, event_name: str, event_date: str, start_time: str, end_time: str, description: str, attendees_emails: list) -> str:
    """
    Función auxiliar para crear eventos con un token específico
    Aquí deberías adaptar tu función create_event existente
    """
    import requests
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Construir el cuerpo del evento
    attendees = []
    for email in attendees_emails:
        attendees.append({
            'emailAddress': {
                'address': email
            },
            'type': 'required'
        })
    
    event_body = {
        'subject': event_name,
        'body': {
            'contentType': 'html',
            'content': description
        },
        'start': {
            'dateTime': f'{event_date}T{start_time}:00',
            'timeZone': 'America/Guatemala'
        },
        'end': {
            'dateTime': f'{event_date}T{end_time}:00',
            'timeZone': 'America/Guatemala'
        },
        'attendees': attendees
    }
    
    response = requests.post(
        'https://graph.microsoft.com/v1.0/me/events',
        headers=headers,
        json=event_body
    )
    
    if response.status_code == 201:
        event_data = response.json()
        return f"Evento '{event_name}' creado con ID: {event_data['id']}"
    else:
        return f"Error al crear evento: {response.status_code} - {response.text}"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)