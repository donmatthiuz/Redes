import os
import asyncio
import logging
from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from typing import Any, Optional

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

    def chat_normal(self, mensaje: str) -> str:
        self.conversation_history.append({"role": "user", "content": mensaje})
        try:
            # Comprobación especial para mostrar servers MCP
            if "servers mcp" in mensaje.lower():
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
            self.conversation_history.append({"role": "assistant", "content": respuesta})
            logger.info(f"Usuario: {mensaje} | LLM: {respuesta}")
            self.log_completo.append({
                "accion": "chat_normal",
                "mensaje_usuario": mensaje,
                "respuesta_llm": respuesta
            })
            return respuesta
        except Exception as e:
            logger.error(f"Error al comunicarse con OpenAI: {e}")
            return f"Error al comunicarse con OpenAI: {e}"

    def mostrar_log_completo(self):
        logger.info("=== LOG COMPLETO ===")
        for entry in self.log_completo:
            logger.info(entry)

