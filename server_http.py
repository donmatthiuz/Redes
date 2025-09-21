# server.py
import sys
import asyncio
from fastmcp import FastMCP
from functions.GitManager import git_manager, GIT
from functions.Voicer import WhisperTranscriber
from datetime import datetime
import shutil
import os
from functions.Voicer import WhisperTranscriber
import yaml
from functions.calendar_manager import create_event
from dotenv import load_dotenv
# Configurar el servidor MCP
mcp = FastMCP("MCP Server")

@mcp.tool()
def clone_repo(url: str, name: str) -> str:
    
    try:
        result = git_manager.setup_repo(url, name)
        return f"✅ Repositorio clonado exitosamente: {result}"
    except Exception as e:
        return f"❌ Error clonando repositorio: {str(e)}"

@mcp.tool()
def add_file(filename: str, content: str, message: str) -> str:
    
    try:
        result = git_manager.create_file_and_commit(filename, content, message)
        return f"✅ Archivo creado y commit realizado: {result}"
    except Exception as e:
        return f"❌ Error creando archivo: {str(e)}"
    




@mcp.tool()
def create_outlook_event( event_name: str, event_date: str, start_time: str, end_time: str, description: str, attendees: str) -> str:
    
    try:
        load_dotenv()
        app_id = os.getenv("APP_ID")
        emails = [email.strip() for email in attendees.split(",")]
        result = create_event(
            app_id=app_id,
            event_name=event_name,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            description=description,
            attendees_emails=emails
        )
        return f"✅ Evento procesado: {result}"
    except Exception as e:
        return f"❌ Error en create_outlook_event: {str(e)}"



@mcp.tool()
def apunte(repo, clase, contenido) -> str:
    try:
        # 2️⃣ Configurar repo y crear carpeta/apunte
        result = git_manager.setup_repo(repo, "apuntes")
        ahora = datetime.now()
        fecha_hoy = ahora.strftime("%Y-%m-%d")
        
        with open("data/publicar-notebooks.yml", "r", encoding="utf-8") as f:
            contenido_yaml = f.read() 
        
        result = git_manager.overwrite_file_and_commit(
            f".github/workflows/publicar-notebooks.yml", 
            contenido_yaml, 
            f"workflow"
        )
        
        # 3️⃣ Crear archivo y commit del apunte
        result = git_manager.create_file_and_commit(
            f"{clase}/apunte.md", 
            contenido, 
            f"Apunte-{fecha_hoy}-clase-{clase}"
        )
        
        
        
        return "✅ Apunte creado correctamente"
        
    except Exception as e:
        return f"❌ Error apunte: {str(e)}"






@mcp.tool()
def voice_to_text(voice_path):
    try:
        print(f"🟢 [DEBUG] Iniciando transcripción de: {voice_path}")

        # Inicializar el modelo
        import time
        start_model = time.time()
        transcriber = WhisperTranscriber(model_name="tiny")
        end_model = time.time()
        print(f"🟢 [DEBUG] Modelo cargado en {end_model - start_model:.2f} segundos")

        # Transcribir audio
        start_trans = time.time()
        texto = transcriber.transcribe(voice_path)
        end_trans = time.time()
        print(f"🟢 [DEBUG] Transcripción completada en {end_trans - start_trans:.2f} segundos")

        # Retornar resultado
        print(f"🟢 [DEBUG] Texto transcrito (primeros 100 chars): {texto[:100]}...")
        return {"result": texto}

    except Exception as e:
        print(f"🔴 [ERROR] Durante voice_to_text: {e}")
        return {"result": f"❌ Error texto: {str(e)}"}


    
    
    

if __name__ == "__main__":
    # FastMCP maneja automáticamente STDIO cuando se ejecuta directamente
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)