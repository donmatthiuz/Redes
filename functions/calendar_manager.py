import requests
from rich import console
from functions.ms_graph import generate_access_token, GRAPH_API_ENDPOINT

console = console.Console()

def create_event(app_id, event_name, event_date, start_time, end_time, description, attendees_emails, location_name='Sala de Conferencias Principal', scopes=['Calendars.ReadWrite']):
   
    # 1. Generar token
    access_token = generate_access_token(app_id, scopes)
    headers = {'Authorization': 'Bearer ' + access_token['access_token']}
    
    # 2. Preparar cuerpo del evento
    body = {
        'contentType': 'html',
        'content': description
    }
    start = {'dateTime': f'{event_date}T{start_time}', 'timeZone': 'America/Guatemala'}
    end = {'dateTime': f'{event_date}T{end_time}', 'timeZone': 'America/Guatemala'}
    location = {'displayName': location_name}
    attendees = [{'emailAddress': {'address': email}, 'type': 'required'} for email in attendees_emails]

    event_payload = {
        'subject': event_name,
        'body': body,
        'start': start,
        'end': end,
        'location': location,
        'attendees': attendees
    }
    
    # 3. Crear evento
    response = requests.post(GRAPH_API_ENDPOINT + '/me/events', headers=headers, json=event_payload)
    
    if response.status_code == 201:
        event_id = response.json()['id']
        console.print(f"[green]✓ Reunión creada exitosamente con ID: {event_id}[/green]")
    else:
        console.print(f"[red]✗ Error al crear la reunión: {response.status_code}[/red]")
        console.print(response.text)
    
    return response.json()

