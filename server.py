# server.py
import sys
import asyncio
from fastmcp import FastMCP
from functions.GitManager import git_manager
from functions.Voicer import WhisperTranscriber
from datetime import datetime
import shutil
import os
from functions.Voicer import WhisperTranscriber

# Configurar el servidor MCP
mcp = FastMCP("MCP Server")

@mcp.tool()
def clone_repo(url: str, name: str) -> str:
    """
    Clona un repositorio Git desde una URL a un directorio local.
    
    Args:
        url: URL del repositorio Git
        name: Nombre del directorio local donde clonar
    
    Returns:
        str: Mensaje de resultado de la operación
    """
    try:
        result = git_manager.setup_repo(url, name)
        return f"✅ Repositorio clonado exitosamente: {result}"
    except Exception as e:
        return f"❌ Error clonando repositorio: {str(e)}"

@mcp.tool()
def add_file(filename: str, content: str, message: str) -> str:
    """
    Crea un archivo con contenido y hace commit al repositorio.
    
    Args:
        filename: Nombre del archivo a crear
        content: Contenido del archivo
        message: Mensaje del commit
    
    Returns:
        str: Mensaje de resultado de la operación
    """
    try:
        result = git_manager.create_file_and_commit(filename, content, message)
        return f"✅ Archivo creado y commit realizado: {result}"
    except Exception as e:
        return f"❌ Error creando archivo: {str(e)}"
    

# @mcp.tool()
# def text_to_voice() -> str:
#     try:
#         # lo convertimos a texto y lueog lo ponemos aqui como filename
#         result = git_manager.create_file_and_commit(filename, content, message)
#         return f"✅ Archivo creado y commit realizado: {result}"
#     except Exception as e:
#         return f"❌ Error creando archivo: {str(e)}"



@mcp.tool()
def apunte(repo, clase, contenido) -> str:
    try:
        # 1️⃣ Verificar si existe la carpeta repos/apuntes
        if os.path.exists("repos/apuntes"):
            workflow_src = "data/publicar-notebooks.yml"
            workflow_dest_dir = ".github/workflows"
            workflow_dest = os.path.join(workflow_dest_dir, "publicar-notebooks.yml")
            
            os.makedirs(workflow_dest_dir, exist_ok=True)
            shutil.copy(workflow_src, workflow_dest)
            print(f"✅ Copiado workflow a {workflow_dest}")

            # Hacer commit del workflow antes de subir el apunte
            git_manager.create_file_and_commit(
                ".github/workflows/publicar-notebooks.yml",
                open(workflow_src).read(),
                "Agregar workflow de publicación de notebooks"
            )

        # 2️⃣ Configurar repo y crear carpeta/apunte
        result = git_manager.setup_repo(repo, "apuntes")
        ahora = datetime.now()
        fecha_hoy = ahora.strftime("%Y-%m-%d")
        
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
        transcriber = WhisperTranscriber(model_name="base")
        texto = transcriber.transcribe(voice_path)
        return texto
    except Exception as e:
        return f"❌ Error texto: {str(e)}"
    
    
    

if __name__ == "__main__":
    # FastMCP maneja automáticamente STDIO cuando se ejecuta directamente
    mcp.run()