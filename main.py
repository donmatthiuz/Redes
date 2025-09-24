import os
import asyncio
import logging
from dotenv import load_dotenv
from cliente.ClienteFinal import LLMClientAsync
import uvicorn
import json

async def levantar_uvicorn():
    """Levanta el servidor FastAPI en otra corrutina."""
    config = uvicorn.Config(
        "mcp_server_otx:app",  # módulo:app
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve() 
    
async def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    url_remoto = os.getenv("URL")
    llm = LLMClientAsync(api_key)
    uvicorn_task = asyncio.create_task(levantar_uvicorn())
    
    
    await asyncio.sleep(2)
    
    # Conectar algunos MCP locales como ejemplo
    await llm.conectar_mcp("arxiv_mcp_server.py")
    await llm.conectar_mcp("server.py")
    await llm.conectar_mcp(f"{url_remoto}/mcp/", use_http=True)
    await llm.conectar_mcp("http://127.0.0.1:8001/jsonrpc", use_http=True)
    salida = True
    # Bucle infinito de interacción con LLM
    print("\n==============================")
    print("🤖 OPCIONES DISPONIBLES CON EL LLM")
    print("==============================")
    print("1️⃣  Preguntar libremente (chat normal con el modelo).")
    print("2️⃣  Escribir 'listar casos de uso' → muestra qué hace cada servidor MCP.")
    print("3️⃣  Escribir 'servers mcp' → lista los servidores conectados y sus herramientas.")
    print("4️⃣  Escribir 'ejecutar caso de uso <server>' → corre el caso de uso para ese servidor.")
    print("      🔹 Ejemplos de servidores:")
    print("         - arxiv_mcp_server.py → buscar papers de arXiv")
    print("         - server.py → transcribir audio, crear apuntes y eventos en calendario")
    print("         - http://127.0.0.1:8001/jsonrpc → analizar archivos .log")
    print("         - <URL_REMOTO>/mcp/ → autenticación multiusuario y eventos de Outlook")
    print("5️⃣  Escribir 'salir' → terminar programa.")
    print("==============================\n")

    while salida:
        mensaje = input("Tú: ")
        if mensaje.lower() in ["salir", "exit"]:
            salida = False
        respuesta = llm.chat_normal(mensaje)
        print(f"LLM: {respuesta}")

    # Cerrar todos los MCP abiertos al final
    await llm.cerrar_mcp()
    llm.mostrar_log_completo()

# ------------------- Ejecutar -------------------
if __name__ == "__main__":
    asyncio.run(main())