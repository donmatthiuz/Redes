import requests
from rich import console
from ms_graph import generate_access_token, GRAPH_API_ENDPOINT

console = console.Console()
APP_ID = 'b18aff7a-5941-4f6e-bda9-eef6e789fe60'
SCOPES = ['Calendars.ReadWrite']

# Step 1. Generate Access Token
access_token = generate_access_token(APP_ID, SCOPES)
headers = {
    'Authorization': 'Bearer ' + access_token['access_token']
}

# Step 2.1 Create an event
def construct_event_detail(event_name, **event_details):
    request_body = {
        'subject': event_name
    }
    for key, val in event_details.items():
        request_body[key] = val
    return request_body

# Crear reunión para hoy 21 de septiembre de 2025
event_name = 'Reunión del 21 de Septiembre'
body = {
    'contentType': 'html',
    'content': '<b>Reunión importante programada para hoy</b><br>Favor confirmar asistencia.'
}
start = {
    'dateTime': '2025-09-21T10:00:00',  # 10:00 AM hora local
    'timeZone': 'America/Guatemala'  # Zona horaria de Guatemala
}
end = {
    'dateTime': '2025-09-21T11:00:00',  # 11:00 AM hora local
    'timeZone': 'America/Guatemala'
}
location = {
    'displayName': 'Sala de Conferencias Principal'
}
attendees = [
    {
        'emailAddress': {
            'address': 'ejemplo@empresa.com'  # Cambiar por email real
        }, 
        'type': 'required'
    }
]

# Crear la reunión
response_create_meeting = requests.post(
    GRAPH_API_ENDPOINT + f'/me/events',
    headers=headers,
    json=construct_event_detail(
        event_name,
        body=body,
        location=location,
        start=start,
        end=end,
        attendees=attendees,
    )
)

console.print("Reunión creada:")
console.print(response_create_meeting.json())

# Obtener el ID del evento creado
if response_create_meeting.status_code == 201:
    event_id = response_create_meeting.json()['id']
    console.print(f"[green]✓ Reunión creada exitosamente con ID: {event_id}[/green]")
else:
    console.print(f"[red]✗ Error al crear la reunión: {response_create_meeting.status_code}[/red]")
    console.print(response_create_meeting.text)