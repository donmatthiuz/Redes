import os
from dotenv import load_dotenv
from cliente.ClienteFinal import LLMClientAsync
import asyncio
import uvicorn

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
    await server.serve()  # Esto es asíncrono

async def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    llm = LLMClientAsync(api_key)

    # Levantar servidor en paralelo
    uvicorn_task = asyncio.create_task(levantar_uvicorn())
    
    # Espera un momento a que el servidor inicie
    await asyncio.sleep(2)

    # Pregunta normal
    respuesta =  llm.chat_normal("Quien fue alan turing")
    print(respuesta)

    # MCP compañero local
    print("\n🔹 Conectando a MCP local...")
    await llm.conectar_mcp("arxiv_mcp_server.py")
    tools_local = await llm.listar_herramientas_mcp()
    print("Herramientas MCP local:", tools_local)
    await llm.cerrar_mcp()
    
    # MCP local 2
    print("\n🔹 Conectando a MCP local...")
    await llm.conectar_mcp("server.py")
    tools_local = await llm.listar_herramientas_mcp()
    print("Herramientas MCP local:", tools_local)
    await llm.cerrar_mcp()
    
    
    # MCP local 
    print("\n🔹 Conectando a MCP local...")
    await llm.conectar_mcp("http://127.0.0.1:8001/jsonrpc", use_http=True)
    tools_remote = await llm.listar_herramientas_mcp()
    print("Herramientas MCP remoto:", tools_remote)
    await llm.cerrar_mcp()

    # MCP remoto HTTP
    url = os.getenv("URL")
    print("\n🔹 Conectando a MCP remoto HTTP...", url)
    await llm.conectar_mcp(url, use_http=True)
    tools_remote = await llm.listar_herramientas_mcp()
    print("Herramientas MCP remoto:", tools_remote)
    await llm.cerrar_mcp()

    
    # Cancelar uvicorn al finalizar
    uvicorn_task.cancel()
    try:
        await uvicorn_task
    except asyncio.CancelledError:
        pass  # Esto evita que se vea el traceback


if __name__ == "__main__":
    asyncio.run(main())
