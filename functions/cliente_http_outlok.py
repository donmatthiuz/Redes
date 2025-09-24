

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



async def create_event_target(client, 
                             user_id: str, 
                             eventname:str, 
                             eventadate:str, 
                             start:str, 
                             end:str, 
                             descrip:str):
    print(f"\n📅 Creando evento de ejemplo para usuario: {user_id}")
    
    event_result = await client.call_tool("create_outlook_event", {
        "user_id": user_id,
        "event_name": eventname,
        "event_date": eventadate,  # Mañana
        "start_time": start,
        "end_time": end,
        "description": descrip,
        "attendees": ""
    })
    
    print("Resultado de creación de evento:")
    print(event_result.data)  # Acceder a la propiedad .data



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
