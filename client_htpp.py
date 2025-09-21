import asyncio
import os
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv

async def authenticate_user(client, user_id: str):
    """Flujo completo de autenticación de usuario"""
    print(f"\n🔐 Iniciando autenticación para usuario: {user_id}")
    
    # 1. Verificar si ya está autenticado
    auth_status_result = await client.call_tool("check_outlook_auth_status", {"user_id": user_id})
    auth_status = auth_status_result.data  # Acceder a la propiedad .data
    print("Estado de autenticación:", auth_status)
    
    # Si ya está autenticado, no hacer nada más
    if "está autenticado y listo" in auth_status:
        return True
    
    # 2. Iniciar proceso de autenticación
    auth_start_result = await client.call_tool("start_outlook_auth", {"user_id": user_id})
    auth_start = auth_start_result.data  # Acceder a la propiedad .data
    print("Inicio de autenticación:")
    print(auth_start)
    
    # 3. Esperar a que el usuario complete la autenticación
    input("\n⏸️  Presiona ENTER después de completar la autenticación en el navegador...")
    
    # 4. Completar autenticación
    auth_complete_result = await client.call_tool("complete_outlook_auth", {"user_id": user_id})
    auth_complete = auth_complete_result.data  # Acceder a la propiedad .data
    print("Resultado de autenticación:")
    print(auth_complete)
    
    return "completada exitosamente" in auth_complete

async def create_sample_event(client, user_id: str):
    """Crear un evento de ejemplo"""
    print(f"\n📅 Creando evento de ejemplo para usuario: {user_id}")
    
    event_result = await client.call_tool("create_outlook_event", {
        "user_id": user_id,
        "event_name": "Reunión de Prueba MCP",
        "event_date": "2025-09-22",  # Mañana
        "start_time": "14:00",
        "end_time": "15:00",
        "description": "<b>Esta es una reunión de prueba</b><br>Creada mediante MCP multi-usuario",
        "attendees": "ejemplo@empresa.com"  # Cambiar por email real
    })
    
    print("Resultado de creación de evento:")
    print(event_result.data)  # Acceder a la propiedad .data

async def main():
    load_dotenv()
    url = os.getenv("URL")
    
    # Identificador único del usuario - puede ser email, username, etc.
    user_id = input("Ingresa tu identificador de usuario (email recomendado): ").strip()
    
    if not user_id:
        print("❌ Debes proporcionar un identificador de usuario")
        return
    
    transport = StreamableHttpTransport(f"{url}/mcp/")
    
    async with Client(transport=transport) as client:
        # Ping para verificar conexión
        await client.ping()
        print("✅ Conexión establecida con el servidor MCP")
        
        # Listar herramientas disponibles
        tools = await client.list_tools()
        print(f"\n🔧 Herramientas disponibles: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # Flujo de autenticación
        authenticated = await authenticate_user(client, user_id)
        
        if authenticated:
            print(f"\n🎉 Usuario {user_id} autenticado correctamente!")
            
            # Crear evento de ejemplo
            await create_sample_event(client, user_id)
            
            # Menú interactivo
            while True:
                print("\n" + "="*50)
                print("MENÚ DE OPCIONES:")
                print("1. Crear nuevo evento")
                print("2. Verificar estado de autenticación")
                print("3. Salir")
                
                choice = input("Selecciona una opción (1-3): ").strip()
                
                if choice == "1":
                    await create_custom_event(client, user_id)
                elif choice == "2":
                    status_result = await client.call_tool("check_outlook_auth_status", {"user_id": user_id})
                    print(status_result.data)  # Acceder a la propiedad .data
                elif choice == "3":
                    print("👋 ¡Hasta luego!")
                    break
                else:
                    print("❌ Opción no válida")
        else:
            print(f"❌ No se pudo autenticar el usuario {user_id}")

async def create_custom_event(client, user_id: str):
    """Permite al usuario crear un evento personalizado"""
    print("\n📝 Crear nuevo evento:")
    
    event_name = input("Nombre del evento: ").strip()
    event_date = input("Fecha (YYYY-MM-DD): ").strip()
    start_time = input("Hora de inicio (HH:MM): ").strip()
    end_time = input("Hora de fin (HH:MM): ").strip()
    description = input("Descripción: ").strip()
    attendees = input("Invitados (emails separados por comas): ").strip()
    
    if all([event_name, event_date, start_time, end_time]):
        result = await client.call_tool("create_outlook_event", {
            "user_id": user_id,
            "event_name": event_name,
            "event_date": event_date,
            "start_time": start_time,
            "end_time": end_time,
            "description": description or "Sin descripción",
            "attendees": attendees or ""
        })
        print("Resultado:", result.data)  # Acceder a la propiedad .data
    else:
        print("❌ Faltan campos obligatorios")

if __name__ == "__main__":
    asyncio.run(main())