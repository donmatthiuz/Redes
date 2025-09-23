import os
import asyncio
import logging
from dotenv import load_dotenv
from cliente.ClienteFinal import LLMClientAsync
import uvicorn
import json


# ------------------- Configurar logger -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("mcp_client.log", encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ------------------- Función para levantar Uvicorn -------------------
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

# ------------------- Función principal -------------------
async def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    llm = LLMClientAsync(api_key)

    # Levantar servidor local en paralelo
    uvicorn_task = asyncio.create_task(levantar_uvicorn())
    
    # Esperar a que el servidor inicie
    await asyncio.sleep(2)

    # Chat normal con LLM
    respuesta = llm.chat_normal("Quien fue alan turing")
    logger.info(f"LLM dice: {respuesta}")

    # ---------------- MCP local 1 ----------------
    local_mcp_1 = "arxiv_mcp_server.py"
    logger.info(f"🔹 Conectando a MCP local: {local_mcp_1}")
    await llm.conectar_mcp(local_mcp_1)
    tools = await llm.listar_herramientas_mcp()
    logger.info(f"Herramientas MCP local: {tools}")
    await llm.cerrar_mcp()

    # ---------------- MCP local 2 ----------------
    local_mcp_2 = "server.py"
    logger.info(f"🔹 Conectando a MCP local: {local_mcp_2}")
    await llm.conectar_mcp(local_mcp_2)
    tools = await llm.listar_herramientas_mcp()
    logger.info(f"Herramientas MCP local: {tools}")
    await llm.cerrar_mcp()

    # ---------------- MCP JSON-RPC local ----------------
    local_jsonrpc = "http://127.0.0.1:8001/jsonrpc"
    logger.info(f"🔹 Conectando a MCP local JSON-RPC: {local_jsonrpc}")
    await llm.conectar_mcp(local_jsonrpc, use_http=True)
    tools = await llm.listar_herramientas_mcp()
    logger.info(f"Herramientas MCP JSON-RPC: {tools}")

    # Llamar a la herramienta "analyze_logs" si existe
    
    # Llamar a la herramienta "analyze_logs"
    if "analyze_logs" in tools:
        logger.info("🔍 Analizando archivo de log...")
        result = await llm.call_mcp_tool("analyze_logs", {"file_path": "data/sample.log"})

        # Verificar si hubo error en el CallToolResult
        if getattr(result, "is_error", False):
            print("⚠ Error al llamar la herramienta analyze_logs")
            logger.error(f"Error analyze_logs: {result}")
        else:
            try:
                # content[0].text contiene el JSON como string
                content_json = result.content[0].text
                data = json.loads(content_json)
                formatted_result = json.dumps(data, indent=2, ensure_ascii=False)
                print("\n📄 Resultado formateado de analyze_logs:")
                print(formatted_result)
                logger.info(f"Resultado analyze_logs formateado:\n{formatted_result}")
            except Exception as e:
                print("⚠ Error al parsear JSON del resultado:", e)
                logger.error(f"Error al parsear JSON: {result}")
    else:
        logger.warning("La herramienta 'analyze_logs' no está disponible.")


    
    

    # ---------------- MCP remoto HTTP ----------------
    url_remoto = os.getenv("URL")
    logger.info(f"🔹 Conectando a MCP remoto HTTP: {url_remoto}")
    await llm.conectar_mcp(f"{url_remoto}/mcp/", use_http=True)
    tools = await llm.listar_herramientas_mcp()
    logger.info(f"Herramientas MCP remoto: {tools}")
    await llm.cerrar_mcp()

    # ---------------- Cancelar servidor ----------------
    uvicorn_task.cancel()
    try:
        await uvicorn_task
    except asyncio.CancelledError:
        logger.info("Servidor Uvicorn detenido.")

# ------------------- Ejecutar -------------------
if __name__ == "__main__":
    asyncio.run(main())
