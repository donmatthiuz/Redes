import asyncio
from openai import OpenAI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from typing import Any, Optional, Dict

class LLMClientAsync:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.conversation_history = []
        self.log_completo = []
        self.mcp_client: Optional[Client] = None
        self.tools_disponibles: list[dict] = []

    async def conectar_mcp(self, server_path_or_url: str, use_http: bool = False):
        """Conectar a cualquier servidor MCP (local o remoto)."""
        if use_http:
            transport = StreamableHttpTransport(server_path_or_url)
            self.mcp_client = await Client(transport=transport).__aenter__()
        else:
            self.mcp_client = await Client(server_path_or_url).__aenter__()

        self.tools_disponibles = await self.mcp_client.list_tools()
        print(f"✅ Conectado a MCP con herramientas: {[t.name for t in self.tools_disponibles]}")

    async def cerrar_mcp(self):
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
            self.mcp_client = None
            print("🔌 Conexión MCP cerrada")

    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> Any:
        """Llama a una herramienta MCP de manera asíncrona."""
        if not self.mcp_client:
            return {"error": "No hay conexión MCP activa"}
        
        tool_names = [t.name for t in self.tools_disponibles]
        if tool_name not in tool_names:
            return {"error": f"Herramienta '{tool_name}' no encontrada. Disponibles: {tool_names}"}

        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            return {"error": str(e)}
    async def listar_herramientas_mcp(self):
        if self.mcp_client:
            return [tool.name for tool in await self.mcp_client.list_tools()]
        return []


    def chat_normal(self, mensaje: str) -> str:
        """Chat con LLM (síncrono)."""
        self.conversation_history.append({"role": "user", "content": mensaje})
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                max_tokens=500,
                temperature=0.7
            )
            respuesta = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": respuesta})
            return respuesta
        except Exception as e:
            return f"Error al comunicarse con OpenAI: {e}"
