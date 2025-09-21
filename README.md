

# Documentación de herramientas MCP Server

## 1️⃣ `clone_repo`

Clona un repositorio Git.

**Parámetros:**

| Parámetro | Tipo | Descripción                   |
| --------- | ---- | ----------------------------- |
| `url`     | str  | URL del repositorio Git.      |
| `name`    | str  | Nombre del repositorio local. |

**Retorna:** Mensaje de éxito o error.

---

## 2️⃣ `add_file`

Crea un archivo y realiza commit en un repositorio Git.

**Parámetros:**

| Parámetro  | Tipo | Descripción                        |
| ---------- | ---- | ---------------------------------- |
| `filename` | str  | Ruta y nombre del archivo a crear. |
| `content`  | str  | Contenido del archivo.             |
| `message`  | str  | Mensaje del commit.                |

**Retorna:** Mensaje de éxito o error.

---

## 3️⃣ `create_outlook_event`

Crea un evento en Outlook (Microsoft Graph).

**Parámetros:**

| Parámetro     | Tipo | Descripción                           |
| ------------- | ---- | ------------------------------------- |
| `event_name`  | str  | Nombre del evento.                    |
| `event_date`  | str  | Fecha del evento (`YYYY-MM-DD`).      |
| `start_time`  | str  | Hora de inicio (`HH:MM`).             |
| `end_time`    | str  | Hora de finalización (`HH:MM`).       |
| `description` | str  | Descripción del evento.               |
| `attendees`   | str  | Lista de correos separados por comas. |

**Retorna:** Mensaje de éxito o error.

---

## 4️⃣ `apunte`

Crea un apunte académico en un repositorio Git.

**Parámetros:**

| Parámetro   | Tipo | Descripción                                    |
| ----------- | ---- | ---------------------------------------------- |
| `repo`      | str  | URL del repositorio donde se creará el apunte. |
| `clase`     | str  | Nombre de la carpeta de la clase.              |
| `contenido` | str  | Contenido del apunte en formato Markdown.      |

**Retorna:** Mensaje de éxito o error.

---

## 5️⃣ `voice_to_text`

Transcribe un archivo de audio a texto usando Whisper.

**Parámetros:**

| Parámetro    | Tipo | Descripción                |
| ------------ | ---- | -------------------------- |
| `voice_path` | str  | Ruta del archivo de audio. |

**Retorna:** Diccionario con clave `result` conteniendo el texto transcrito o mensaje de error.

---
