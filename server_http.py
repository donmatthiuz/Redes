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
    

if __name__ == "__main__":
    # FastMCP maneja automáticamente STDIO cuando se ejecuta directamente
    port = int(os.getenv("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)