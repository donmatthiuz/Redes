import os
import asyncio
import nest_asyncio
import logging
from typing import Any, Optional
from openai import OpenAI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# Permite ejecutar coroutines dentro de un loop ya corriendo
nest_asyncio.apply()

# ------------------- Configuración del logger -------------------
logger = logging.getLogger("LLMClientAsync")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("llm_mcp.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ------------------- Clase LLMClientAsync -------------------
class LLMClientAsync:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.conversation_history = []
        self.log_completo = []
        self.mcp_client: Optional[Client] = None
        self.tools_disponibles: list[dict] = []
        self.servers_tools: dict[str, list[str]] = {}  # server -> herramientas

    # ------------------- Conexión MCP -------------------
    async def conectar_mcp(self, server_path_or_url: str, use_http: bool = False):
        if use_http:
            transport = StreamableHttpTransport(server_path_or_url)
            self.mcp_client = await Client(transport=transport).__aenter__()
        else:
            self.mcp_client = await Client(server_path_or_url).__aenter__()

        self.tools_disponibles = await self.mcp_client.list_tools()
        tool_names = [t.name for t in self.tools_disponibles]
        self.servers_tools[server_path_or_url] = tool_names

        logger.info(f"Conectado a MCP '{server_path_or_url}' con herramientas: {tool_names}")
        self.log_completo.append({
            "accion": "conectar_mcp",
            "server": server_path_or_url,
            "tools": tool_names
        })

    async def cerrar_mcp(self):
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
            self.mcp_client = None
            logger.info("Conexión MCP cerrada")
            self.log_completo.append({"accion": "cerrar_mcp"})

    # ------------------- Llamada a herramientas MCP -------------------
    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> Any:
        if not self.mcp_client:
            result = {"error": "No hay conexión MCP activa"}
        elif tool_name not in [t.name for t in self.tools_disponibles]:
            result = {"error": f"Herramienta '{tool_name}' no encontrada. Disponibles: {[t.name for t in self.tools_disponibles]}"}
        else:
            try:
                result = await self.mcp_client.call_tool(tool_name, arguments)
            except Exception as e:
                result = {"error": str(e)}

        logger.info(f"Llamada a herramienta MCP '{tool_name}' con args {arguments}. Resultado: {result}")
        self.log_completo.append({
            "accion": "call_tool",
            "tool": tool_name,
            "arguments": arguments,
            "resultado": result
        })
        return result

    async def listar_herramientas_mcp(self):
        if self.mcp_client:
            tools = [tool.name for tool in await self.mcp_client.list_tools()]
            logger.info(f"Herramientas MCP disponibles: {tools}")
            self.log_completo.append({"accion": "listar_herramientas", "resultado": tools})
            return tools
        return []

    async def mostrar_servers_y_tools(self):
        """Devuelve todos los servers y sus herramientas"""
        return self.servers_tools

    # ------------------- Casos de uso de cada servidor MCP -------------------
    async def listar_casos_uso_mcp(self):
        casos_uso = {}
        for server, tools in self.servers_tools.items():
            s = server.lower()
            if "arxiv" in s:
                casos_uso[server] = "Buscar y descargar papers de arXiv, generar BibTeX"
            elif "127.0.0.1:8001" in s or "log-analyzer" in s:
                casos_uso[server] = "Analizar archivos de logs y detectar anomalías"
            elif "redes-yel3" in s or "multi-user" in s:
                casos_uso[server] = "Autenticación multiusuario y gestión de eventos de Outlook"
            elif "server.py" in s or "mcp server" in s:
                casos_uso[server] = "Clonar repositorios, gestionar archivos, convertir voz a texto y crear apuntes"
            else:
                casos_uso[server] = "Caso de uso no definido aún"
        return casos_uso

    # ------------------- Funciones vacías por servidor -------------------
    async def caso_uso_arxiv(self, **kwargs):
        return "Función arxiv ejecutada (vacía por ahora)"

    async def caso_uso_log_analyzer(self, **kwargs):
        return "Función log-analyzer ejecutada (vacía por ahora)"

    async def caso_uso_multiuser(self, **kwargs):
        return "Función multi-user ejecutada (vacía por ahora)"

    async def caso_uso_server_py(self, **kwargs):
        return "Función server.py ejecutada (vacía por ahora)"

    async def ejecutar_caso_uso(self, server_name: str, **kwargs):
        server_lower = server_name.lower()
        if "arxiv" in server_lower:
            return await self.caso_uso_arxiv(**kwargs)
        elif "127.0.0.1:8001" in server_lower or "log-analyzer" in server_lower:
            return await self.caso_uso_log_analyzer(**kwargs)
        elif "redes-yel3" in server_lower or "multi-user" in server_lower:
            return await self.caso_uso_multiuser(**kwargs)
        elif "server.py" in server_lower or "mcp server" in server_lower:
            return await self.caso_uso_server_py(**kwargs)
        else:
            return f"No se reconoce el servidor {server_name}"

    # ------------------- Chat normal con LLM -------------------
    def chat_normal(self, mensaje: str) -> str:
        self.conversation_history.append({"role": "user", "content": mensaje})
        try:
            if "listar casos de uso" in mensaje.lower():
                respuesta = asyncio.run(self.listar_casos_uso_mcp())
            elif "ejecutar caso de uso" in mensaje.lower():
                # Extraemos el servidor del mensaje
                server = mensaje.split("ejecutar caso de uso")[-1].strip()
                respuesta = asyncio.run(self.ejecutar_caso_uso(server))
            elif "servers mcp" in mensaje.lower():
                servers_info = "\n".join(f"{srv}: {tools}" for srv, tools in self.servers_tools.items())
                respuesta = f"Servidores MCP conectados y sus herramientas:\n{servers_info or 'No hay servidores conectados'}"
            else:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.conversation_history,
                    max_tokens=500,
                    temperature=0.7
                )
                respuesta = response.choices[0].message.content

            self.conversation_history.append({"role": "assistant", "content": str(respuesta)})
            logger.info(f"Usuario: {mensaje} | LLM: {respuesta}")
            self.log_completo.append({
                "accion": "chat_normal",
                "mensaje_usuario": mensaje,
                "respuesta_llm": str(respuesta)
            })
            return str(respuesta)
        except Exception as e:
            logger.error(f"Error al comunicarse con OpenAI: {e}")
            return f"Error al comunicarse con OpenAI: {e}"

    # ------------------- Mostrar log completo -------------------
    def mostrar_log_completo(self):
        logger.info("=== LOG COMPLETO ===")
        for entry in self.log_completo:
            logger.info(entry)
