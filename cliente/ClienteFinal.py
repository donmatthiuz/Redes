import os
import asyncio
import nest_asyncio
import logging
from typing import Any, Optional
from openai import OpenAI
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from functions.cliente_http_outlok import authenticate_user, create_sample_event, create_event_target
import ast
import re
import json

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

        self.mcp_clients: dict[str, Client] = {}  # servidor -> cliente
        self.tools_disponibles: dict[str, list[str]] = {}  # servidor -> lista de herramientas

    # ------------------- Conexión MCP -------------------
    async def conectar_mcp(self, server_path_or_url: str, use_http: bool = False):
        if use_http:
            transport = StreamableHttpTransport(server_path_or_url)
            client = await Client(transport=transport).__aenter__()
        else:
            client = await Client(server_path_or_url).__aenter__()

        tools = await client.list_tools()
        tool_names = [t.name for t in tools]

        self.mcp_clients[server_path_or_url] = client
        self.tools_disponibles[server_path_or_url] = tool_names

        logger.info(f"Conectado a MCP '{server_path_or_url}' con herramientas: {tool_names}")
        self.log_completo.append({
            "accion": "conectar_mcp",
            "server": server_path_or_url,
            "tools": tool_names
        })

    async def cerrar_mcp(self):
        for server, client in self.mcp_clients.items():
            await client.__aexit__(None, None, None)
            logger.info(f"Conexión MCP '{server}' cerrada")
        self.mcp_clients.clear()
        self.tools_disponibles.clear()
        self.log_completo.append({"accion": "cerrar_mcp"})

    # ------------------- Llamada a herramientas MCP -------------------
    async def call_mcp_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        if server_name not in self.mcp_clients:
            return {"error": "No hay conexión MCP activa para este servidor"}

        client = self.mcp_clients[server_name]
        if tool_name not in self.tools_disponibles.get(server_name, []):
            return {"error": f"Herramienta '{tool_name}' no encontrada en {server_name}"}

        try:
            result = await client.call_tool(tool_name, arguments)
        except Exception as e:
            result = {"error": str(e)}

        logger.info(f"Servidor: {server_name} | Llamada a herramienta: {tool_name} | Args: {arguments} | Resultado: {result}")
        self.log_completo.append({
            "accion": "call_tool",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "resultado": result
        })
        return result

    async def listar_herramientas_mcp(self, server_name: str):
        if server_name in self.mcp_clients:
            tools = [tool.name for tool in await self.mcp_clients[server_name].list_tools()]
            self.tools_disponibles[server_name] = tools
            return tools
        return []

    async def mostrar_servers_y_tools(self):
        return self.tools_disponibles

    # ------------------- Casos de uso de cada servidor MCP -------------------
    async def listar_casos_uso_mcp(self):
        casos_uso = {}
        for server in self.mcp_clients.keys():
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
    async def caso_uso_arxiv(self, server_name: str, query: str = "cat:cs.AI deep learning", paper_id: str = None, filename: str = "paper.pdf"):
        mcp = self.mcp_clients.get(server_name)
        if not mcp:
            return {"error": "No hay conexión MCP activa para este servidor"}

        search_result = await mcp.call_tool("search_arxiv", {
            "query": query,
            "sort_by": "relevance",
            "sort_order": "descending"
        })

        print("\n=== RESULTADOS DE BÚSQUEDA ===\n", search_result)

        download_dir = await mcp.call_tool("get_download_root")
        
        print("\nCarpeta de descargas:", download_dir)

        download_result = await mcp.call_tool("download_paper_arxiv", {
            "id": paper_id,
            "filename": filename
        })

        print("\nResultado descarga:", download_result)

        bibtex = await mcp.call_tool("generate_bibtex", {
            "title": "An Example Paper",
            "authors": "John Doe",
            "year": "2023"
        })

        print("\nBibTeX generado:\n", bibtex)


        

    async def caso_uso_log_analyzer(self, server_name: str, filepath: str):
        mcp = self.mcp_clients.get(server_name)
        if not mcp:
            return {"error": "No hay conexión MCP activa para este servidor"}
        
        result = await mcp.call_tool("analyze_logs", {
                "file_path": filepath
            })
        print("\n📊 Resultado del análisis:")
        
        # El resultado viene en el formato MCP estándar
        if result and hasattr(result, 'content'):
            for content_item in result.content:
                if content_item.type == 'text':
                    print(content_item.text)
        elif isinstance(result, dict) and 'content' in result:
            for content_item in result['content']:
                if content_item['type'] == 'text':
                    print(content_item['text'])
        else:
            print(f"Resultado inesperado: {result}")

    async def caso_uso_multiuser(self, server_name: str, **kwargs):
        return "Función multi-user ejecutada (vacía por ahora)"

    async def caso_uso_server_py(self, server_name: str, **kwargs):
        mcp = self.mcp_clients.get(server_name)
        if not mcp:
            return {"error": "No hay conexión MCP activa para este servidor"}
        
        repo = input("📁 Repo donde guardar el apunte: ").strip()
        clase = input("🏫 Nombre de la clase: ").strip()
        audio_path = input("🎵 Ruta del archivo mp3: ").strip()

        print("⏳ Transcribiendo audio...")
        resultado_transcripcion = await mcp.call_tool("voice_to_text", {"voice_path": audio_path})

        print("RESULTADO TRANSCRIPCION", resultado_transcripcion)

        if isinstance(resultado_transcripcion, dict) and "error" in resultado_transcripcion:
            print(f"❌ Error en transcripción: {resultado_transcripcion['error']}")
            return

        texto_transcrito = resultado_transcripcion
        print("✅ Transcripción completada.")

        from datetime import datetime
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""
            Toma este texto transcrito de un audio y conviértelo en formato README para apuntes de clase.
            - Añade un título con la fecha inicial: {fecha_hoy}
            - Mantén secciones claras y encabezados si es posible
            - Modifica el texto para que tenga secciones y subtitulos: {texto_transcrito}
            - Agrega las funciones, ecuaciones si se llegan a mencionar
            - Extiende un poco para que tenga sentido o si faltan cosas
            """
        
        texto_formateado = self.chat_normal(prompt)
        

        print(f"⏳ Creando apunte en el repo...", texto_formateado)
        resultado_apunte = await mcp.call_tool("apunte", {
            "repo": repo,
            "clase": clase,
            "contenido": texto_formateado
        })

        if isinstance(resultado_apunte, dict) and "error" in resultado_apunte:
            print(f"❌ Error creando apunte: {resultado_apunte['error']}")
        else:
            print(f"✅ Apunte creado correctamente en repo '{repo}', clase '{clase}'")


        prompt_calendario = f'''Ahora obteniendo del texto {texto_transcrito} haz lo siguiente.
            Pon los parametros en formato de esta manera si detectaste un evento como parcial , proyecto, clase, repaso,tareas etc.
            FECHA(YYYY-MM-DD), HORA(HH:MM y en formato 24 horas), Descripcion.

            - Si dice que la tarea es de mañana toma la fecha de hoy y sumale un dia
            - Si dice que la tarea es la proxima semana sumale una semana al dia de hoy

            Esto para los eventos detectados que tendras que ponerlos en una lista de tipo
            [
            ["FECHA(YYYY-MM-DD)", "HORA(HH:MM)", "Descripcion"],
            ["FECHA2(YYYY-MM-DD)", "HORA2(HH:MM)", "Descripcion2"]
            ]

            Si solo hay un evento igualr ponerlo en un 
            [
            ["FECHA(YYYY-MM-DD)", "HORA(HH:MM:00)", "Descripcion"]
            ]

            Ojo mucho ojo solo quiero el texto de la lista sin respuestas tuyas, ni conclusiones , descripciones y o cosas tuyas. SOLO EL TEXTO EN EL FORMATO QUE TE DI
            '''

        

        texto_calendario = self.chat_normal(prompt_calendario)

        print(texto_calendario)

       

        user_id = input("Ingresa tu identificador de usuario para el calendario (email recomendado): ").strip()
        
        if not user_id:
            print("❌ Debes proporcionar un identificador de usuario")
            return
        mcp_remoto = self.mcp_clients.get(f"https://redes-yel3.onrender.com/mcp/")

        authenticated = await authenticate_user(mcp_remoto, user_id)

        if authenticated:
            print(f"\n🎉 Usuario {user_id} autenticado correctamente!")
            eventos = json.loads(texto_calendario)
            for evento in eventos:
                fecha, hora, descripcion = evento
                hora_partes = hora.split(':')
                print(hora)

                hora_fin = f"{(int(hora_partes[0]) + 1) % 24:02d}:{hora_partes[1]}"
                print(hora_fin)

                await create_event_target(
                    client=mcp_remoto,
                    user_id=user_id,
                    eventname=descripcion,
                    eventadate=fecha,
                    start=hora,
                    end=hora_fin,
                    descrip=descripcion
                )


    
        
        return "Caso de uso reportado"
    

    async def ejecutar_caso_uso(self, server_name: str, **kwargs):
        server_lower = server_name.lower()
        if "arxiv" in server_lower:
            paperid = kwargs.get("paper_id") or input("Coloque el id del paper (ejemplo: 2301.12345v1): ")
            filename = kwargs.get("filename") or input("Coloque nombre al paper: ")
            return await self.caso_uso_arxiv(server_name, paper_id=paperid, filename=filename)
        elif "127.0.0.1:8001" in server_lower or "log-analyzer" in server_lower:

            filepath = input("Coloque el path del .log a analizar: ")

            return await self.caso_uso_log_analyzer(server_name, filepath)
        elif "redes-yel3" in server_lower or "multi-user" in server_lower:
            return await self.caso_uso_multiuser(server_name, **kwargs)
        elif "server.py" in server_lower or "mcp server" in server_lower:
            return await self.caso_uso_server_py(server_name, **kwargs)
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
                servers_info = "\n".join(f"{srv}: {tools}" for srv, tools in self.tools_disponibles.items())
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
