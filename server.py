# server.py
import sys
import asyncio
from fastmcp import FastMCP
from functions.GitManager import git_manager

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
    

if __name__ == "__main__":
    # FastMCP maneja automáticamente STDIO cuando se ejecuta directamente
    mcp.run()