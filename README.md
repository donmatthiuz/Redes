# Propuesta de MCP Server – Analizador y Reconocedor de Voz con Generación de Notas
**Nombre:** Mathew Cordero Aquino 22982

## 1. Nombre del servidor
**VoiceAnalyzer-MCP**

## 2. Objetivo
Implementar un servidor MCP local que:
- Analice archivos de audio de voz humana (duración, pitch, energía, silencios, emoción)
- Reconozca la voz de personas previamente entrenadas
- Transcriba el audio a texto
- Genere automáticamente un archivo `.md` con notas estructuradas
- Integre con Google Calendar para crear recordatorios automáticos
- Use Git para versionado de notas y modelos de voz

## 3. Funcionalidad Principal
- **Análisis de voz:** métricas de tono, energía, pausas y emoción
- **Entrenamiento de voz personalizada:** guardar un modelo de la voz específica
- **Reconocimiento de hablante:** identificar si la voz corresponde a alguien entrenado
- **Transcripción a texto:** convertir lo dicho en palabras escritas
- **Generación de notas en Markdown (.md)** con estructura profesional
- **Automatización avanzada** con integración externa

## 4. Integración Técnica Detallada

### 4.1 Integración con MCP Git
**Propósito:** Versionado automático de notas generadas y modelos de voz entrenados.

**Implementación técnica:**
```python
# Dentro del MCP Server
import subprocess
import os
from datetime import datetime

class GitIntegration:
    def __init__(self, repo_path="./voice_notes_repo"):
        self.repo_path = repo_path
        self._init_repo_if_needed()
    
    def _init_repo_if_needed(self):
        if not os.path.exists(f"{self.repo_path}/.git"):
            subprocess.run(["git", "init"], cwd=self.repo_path)
            subprocess.run(["git", "config", "user.name", "VoiceAnalyzer-MCP"], cwd=self.repo_path)
            subprocess.run(["git", "config", "user.email", "mcp@voiceanalyzer.local"], cwd=self.repo_path)
    
    def commit_notes(self, file_path, person_name, audio_filename):
        # Agregar archivo al staging
        subprocess.run(["git", "add", file_path], cwd=self.repo_path)
        
        # Commit con mensaje descriptivo
        commit_msg = f"Notas: {person_name} - {audio_filename} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.repo_path)
        
        return f"Commit realizado: {commit_msg}"
    
    def commit_voice_model(self, model_path, person_name):
        subprocess.run(["git", "add", model_path], cwd=self.repo_path)
        commit_msg = f"Modelo de voz entrenado: {person_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=self.repo_path)
        return f"Modelo versionado: {commit_msg}"
    
    def get_history(self, file_pattern="*.md"):
        result = subprocess.run(
            ["git", "log", "--oneline", "--", file_pattern], 
            cwd=self.repo_path, 
            capture_output=True, 
            text=True
        )
        return result.stdout.strip().split('\n') if result.stdout else []
```

**Flujo de integración:**
1. Cada nota generada se guarda en `./voice_notes_repo/notas/`
2. Los modelos de voz entrenados se guardan en `./voice_notes_repo/models/`
3. Automáticamente se hace `git add` y `git commit` con metadata
4. Se puede consultar historial de cambios por persona o fecha

### 4.2 Integración con Google Calendar API
**Propósito:** Crear eventos automáticamente basados en tareas detectadas en el audio.

**Implementación técnica:**
```python
import re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import dateparser

class CalendarIntegration:
    def __init__(self, credentials_path="credentials.json"):
        self.service = self._authenticate(credentials_path)
    
    def _authenticate(self, creds_path):
        # Autenticación OAuth2 con Google Calendar API
        creds = Credentials.from_authorized_user_file(creds_path)
        return build('calendar', 'v3', credentials=creds)
    
    def detect_tasks_and_dates(self, transcription):
        """
        Detecta tareas y fechas mencionadas en la transcripción usando NLP
        """
        tasks_found = []
        
        # Patrones para detectar tareas
        task_patterns = [
            r"(entregar|presentar|hacer|completar|terminar|revisar)\s+([^.!?]+)",
            r"(tarea|proyecto|ensayo|informe|examen)\s*:?\s*([^.!?]+)",
            r"para\s+(el\s+)?(lunes|martes|miércoles|jueves|viernes|sábado|domingo|mañana|próxima semana)",
        ]
        
        # Buscar patrones de fechas
        date_patterns = [
            r"(el\s+)?(lunes|martes|miércoles|jueves|viernes|sábado|domingo)",
            r"(mañana|pasado mañana|próxima semana|el próximo)",
            r"(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
        ]
        
        for pattern in task_patterns:
            matches = re.findall(pattern, transcription, re.IGNORECASE)
            for match in matches:
                task_text = match[1] if isinstance(match, tuple) else match
                
                # Buscar fecha asociada en el contexto
                date_found = self._extract_date_from_context(transcription, task_text)
                
                tasks_found.append({
                    "task": task_text.strip(),
                    "date": date_found,
                    "raw_match": match
                })
        
        return tasks_found
    
    def _extract_date_from_context(self, text, task):
        """Extrae fecha del contexto cercano a la tarea"""
        # Usar dateparser para interpretar fechas en español
        sentences = text.split('.')
        for sentence in sentences:
            if task.lower() in sentence.lower():
                # Buscar fechas en la misma oración
                parsed_date = dateparser.parse(sentence, languages=['es'])
                if parsed_date:
                    return parsed_date
        
        return datetime.now() + timedelta(days=1)  # Por defecto: mañana
    
    def create_calendar_event(self, task, date, person_name):
        """Crear evento en Google Calendar"""
        event = {
            'summary': f"📝 {task}",
            'description': f"Tarea detectada automáticamente de notas de {person_name}\nGenerado por VoiceAnalyzer-MCP",
            'start': {
                'dateTime': date.isoformat(),
                'timeZone': 'America/Guatemala',
            },
            'end': {
                'dateTime': (date + timedelta(hours=1)).isoformat(),
                'timeZone': 'America/Guatemala',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                    {'method': 'popup', 'minutes': 60},       # 1 hora antes
                ],
            },
        }
        
        result = self.service.events().insert(calendarId='primary', body=event).execute()
        return {
            "event_id": result['id'],
            "event_link": result.get('htmlLink'),
            "task": task,
            "date": date.isoformat()
        }
```

**Configuración requerida:**
1. **Credenciales OAuth2:** El servidor necesita `credentials.json` de Google Cloud Console
2. **Scopes necesarios:** `https://www.googleapis.com/auth/calendar`
3. **Dependencias:** `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client`, `dateparser`

## 5. Endpoints del MCP Actualizados

### 5.1 analyze_voice
```json
{
  "input": {"file_path": "audios/clase.wav"},
  "output": {
    "duration": 1230.5,
    "avg_pitch": 145.2,
    "energy_levels": [0.7, 0.8, 0.6],
    "emotion_detected": "neutral",
    "silence_ratio": 0.15
  }
}
```

### 5.2 train_voice
```json
{
  "input": {
    "file_path": "audios/profesor_train.wav",
    "person_name": "Dr. García"
  },
  "output": {
    "status": "trained",
    "person_name": "Dr. García",
    "model_path": "./voice_notes_repo/models/dr_garcia_voice_model.pkl",
    "git_commit": "Modelo de voz entrenado: Dr. García - 2025-09-04 14:30"
  }
}
```

### 5.3 recognize_and_notes
```json
{
  "input": {
    "file_path": "audios/clase1.wav",
    "create_calendar_events": true,
    "version_with_git": true
  },
  "output": {
    "recognized_person": "Dr. García",
    "confidence": 0.89,
    "transcription": "Hoy vamos a hablar de redes TCP/IP. Para el viernes necesito que entreguen el informe de protocolos. El examen será el próximo martes.",
    "notes_file_created": "./voice_notes_repo/notas/notas_dr_garcia_2025-09-04_14-30.md",
    "tasks_detected": [
      {
        "task": "entregar el informe de protocolos",
        "detected_date": "2025-09-06",
        "context": "Para el viernes necesito que entreguen"
      },
      {
        "task": "examen",
        "detected_date": "2025-09-10",
        "context": "El examen será el próximo martes"
      }
    ],
    "calendar_events_created": [
      {
        "event_id": "abc123def456",
        "task": "Entregar informe de protocolos",
        "date": "2025-09-06T09:00:00",
        "event_link": "https://calendar.google.com/event?eid=abc123def456"
      }
    ],
    "git_operations": {
      "notes_commit": "Notas: Dr. García - clase1.wav - 2025-09-04 14:30",
      "commit_hash": "a1b2c3d4"
    }
  }
}
```

### 5.4 get_history (Nuevo endpoint)
```json
{
  "input": {"person_name": "Dr. García", "limit": 10},
  "output": {
    "notes_history": [
      {
        "commit": "a1b2c3d4",
        "date": "2025-09-04 14:30",
        "file": "notas_dr_garcia_2025-09-04_14-30.md",
        "message": "Notas: Dr. García - clase1.wav"
      }
    ],
    "total_notes": 15,
    "calendar_events_created_total": 8
  }
}
```

## 6. Arquitectura del Sistema

```
VoiceAnalyzer-MCP Server
├── Audio Processing Module
│   ├── librosa (análisis de características)
│   ├── Whisper (transcripción)
│   └── SpeechBrain (reconocimiento de hablante)
├── Git Integration Module
│   ├── Automatic versioning
│   ├── Commit with metadata
│   └── History tracking
├── Google Calendar Module
│   ├── OAuth2 authentication
│   ├── Task detection (NLP)
│   ├── Date parsing
│   └── Event creation
└── Notes Generation Module
    ├── Markdown formatting
    ├── Template system
    └── Metadata injection
```

## 7. Ejemplo de Flujo Completo

1. **Audio Input:** `"Hoy estudiamos TCP/IP. Entreguen el proyecto el viernes a las 10 AM."`
2. **Voice Recognition:** Identifica como "Dr. García" (89% confianza)
3. **Transcription:** Convierte audio a texto
4. **Task Detection:** Detecta "entregar proyecto el viernes 10 AM"
5. **Notes Generation:** Crea `notas_dr_garcia_2025-09-04.md`
6. **Git Commit:** Versiona la nota automáticamente
7. **Calendar Event:** Crea recordatorio para el viernes 10 AM
8. **Response:** Retorna JSON con todos los resultados

## 8. No Trivialidad y Diferenciación

**Vs. LLM simple:**
- **Reconocimiento de voz personalizado:** Modelos entrenados para personas específicas
- **Automatización de flujo completo:** Audio → Notas → Git → Calendar
- **Persistencia y versionado:** Historial completo con Git
- **Integración con servicios externos:** Google Calendar API
- **Detección inteligente de tareas:** NLP especializado en contexto académico/profesional

## 9. Tecnologías y Dependencias

### Core Audio Processing:
- `librosa`: Análisis de características de audio
- `torch`, `torchaudio`: Deep learning para reconocimiento
- `openai-whisper`: Transcripción speech-to-text
- `speechbrain`: Reconocimiento de hablante

### Integraciones Externas:
- `google-auth`, `google-api-python-client`: Google Calendar API
- `gitpython` o `subprocess`: Control de Git
- `dateparser`: Procesamiento de fechas en español
- `spacy`: NLP para detección de tareas

### MCP Framework:
- `mcp-server`: Framework base del servidor
- `pydantic`: Validación de datos
- `asyncio`: Operaciones asíncronas

## 10. Configuración Inicial Requerida

1. **Google Cloud Console:**
   - Crear proyecto y habilitar Calendar API
   - Descargar `credentials.json`
   - Configurar OAuth2 consent screen

2. **Git Repository:**
   - Inicializar repositorio local
   - Configurar usuario Git para commits automáticos

3. **Modelos de IA:**
   - Descargar Whisper base model
   - Configurar SpeechBrain para reconocimiento
