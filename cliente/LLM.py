import os
import json
import subprocess
import asyncio
import time
from openai import OpenAI
from typing import Optional, Dict, Any

class LLMClient:
    def __init__(self, api_key: str, server_script: str = "server.py"):
        self.api_key = api_key
        self.server_script = server_script
        self.client = OpenAI(api_key=api_key)
        self.conversation_history = []
        self.mcp_process = None
        self.tools_disponibles = []
        self.log_completo = []
        self.message_id = 1  # Para tracking de mensajes MCP
        
        # Inicializar conexión MCP
        self._init_mcp_connection()
    
    def _init_mcp_connection(self):
        """Inicializa la conexión con el servidor MCP"""
        try:
            print("🔧 Conectando con servidor MCP...")
            
            # Verificar que el archivo del servidor existe
            if not os.path.exists(self.server_script):
                print(f"❌ Error: No se encontró el archivo {self.server_script}")
                return
            
            # Iniciar el proceso del servidor MCP
            self.mcp_process = subprocess.Popen(
                ["python", self.server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Sin buffer para comunicación inmediata
            )
            
            # Esperar un momento para que el servidor se inicie
            time.sleep(1)
            
            # Verificar que el proceso está corriendo
            if self.mcp_process.poll() is not None:
                stderr_output = self.mcp_process.stderr.read()
                print(f"❌ El servidor MCP terminó inmediatamente. Error: {stderr_output}")
                return
            
            # Enviar mensaje de inicialización MCP
            init_message = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "LLM Client",
                        "version": "1.0.0"
                    }
                }
            }
            
            # Enviar mensaje y leer respuesta
            if self._send_mcp_message(init_message):
                response = self._read_mcp_response()
                
                if response and "result" in response:
                    print("✅ Conexión MCP establecida")
                    
                    # Enviar mensaje de initialized notification
                    initialized_message = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                        "params": {}
                    }
                    self._send_mcp_message(initialized_message)
                    
                    # Obtener herramientas disponibles
                    self._get_available_tools()
                else:
                    print(f"❌ Error en la inicialización MCP. Respuesta: {response}")
            else:
                print("❌ Error enviando mensaje de inicialización")
                
        except Exception as e:
            print(f"❌ Error conectando con MCP: {e}")
            self.mcp_process = None
    
    def _get_next_id(self) -> int:
        """Obtiene el siguiente ID para mensajes MCP"""
        current_id = self.message_id
        self.message_id += 1
        return current_id
    
    def _send_mcp_message(self, message: dict) -> bool:
        """Envía un mensaje al servidor MCP"""
        if not self.mcp_process or not self.mcp_process.stdin:
            print("❌ No hay conexión MCP disponible")
            return False
        
        try:
            json_message = json.dumps(message) + "\n"
            self.mcp_process.stdin.write(json_message)
            self.mcp_process.stdin.flush()
            
            # Debug: mostrar mensaje enviado
            print(f"📤 Enviado: {message.get('method', 'unknown method')}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando mensaje MCP: {e}")
            return False
    
    def _read_mcp_response(self, timeout: float = 5.0) -> Optional[dict]:
        """Lee una respuesta del servidor MCP con timeout"""
        if not self.mcp_process or not self.mcp_process.stdout:
            return None
        
        try:
            # Leer con timeout básico
            import select
            ready, _, _ = select.select([self.mcp_process.stdout], [], [], timeout)
            
            if ready:
                line = self.mcp_process.stdout.readline()
                if line.strip():
                    response = json.loads(line.strip())
                    print(f"📥 Recibido: {response}")
                    return response
            else:
                print("⏰ Timeout esperando respuesta MCP")
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing MCP response: {e}")
            # Intentar leer stderr para más información
            try:
                if self.mcp_process.stderr:
                    error_output = self.mcp_process.stderr.readline()
                    if error_output:
                        print(f"❌ Error del servidor: {error_output.strip()}")
            except:
                pass
        except Exception as e:
            print(f"❌ Error leyendo respuesta MCP: {e}")
        
        return None
    
    def _get_available_tools(self):
        """Obtiene las herramientas disponibles del servidor MCP"""
        print("🔧 Solicitando herramientas MCP...")
        
        tools_message = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list",
            "params": {}
        }
        
        if self._send_mcp_message(tools_message):
            response = self._read_mcp_response()
            
            if response and "result" in response and "tools" in response["result"]:
                self.tools_disponibles = response["result"]["tools"]
                tool_names = [tool.get('name', 'unnamed') for tool in self.tools_disponibles]
                print(f"✅ Herramientas MCP disponibles: {tool_names}")
            else:
                print(f"❌ No se pudieron obtener las herramientas MCP. Respuesta: {response}")
                # Intentar debug adicional
                self._debug_mcp_connection()
        else:
            print("❌ Error enviando solicitud de herramientas")
    
    def _debug_mcp_connection(self):
        """Función de debug para diagnosticar problemas de conexión MCP"""
        print("\n🔍 DEBUG: Verificando estado de conexión MCP")
        
        if not self.mcp_process:
            print("❌ No hay proceso MCP")
            return
        
        poll_result = self.mcp_process.poll()
        if poll_result is not None:
            print(f"❌ Proceso MCP terminado con código: {poll_result}")
            
            # Leer stderr para errores
            try:
                stderr_output = self.mcp_process.stderr.read()
                if stderr_output:
                    print(f"❌ Errores del servidor: {stderr_output}")
            except:
                pass
        else:
            print("✅ Proceso MCP sigue corriendo")
        
        # Verificar que FastMCP esté instalado
        try:
            import fastmcp
            print("✅ FastMCP está instalado")
        except ImportError:
            print("❌ FastMCP no está instalado. Instalar con: pip install fastmcp")
    
    def _call_mcp_tool(self, tool_name: str, arguments: dict) -> Any:
        """Llama a una herramienta MCP"""
        if not self.tools_disponibles:
            return {"error": "No hay herramientas MCP disponibles"}
        
        # Verificar que la herramienta existe
        tool_exists = any(tool.get('name') == tool_name for tool in self.tools_disponibles)
        if not tool_exists:
            available_tools = [tool.get('name') for tool in self.tools_disponibles]
            return {"error": f"Herramienta '{tool_name}' no encontrada. Disponibles: {available_tools}"}
        
        tool_message = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        if self._send_mcp_message(tool_message):
            response = self._read_mcp_response(timeout=10.0)  # Timeout más largo para herramientas
            
            if response and "result" in response:
                return response["result"]
            else:
                return {"error": f"Error ejecutando herramienta: {response}"}
        else:
            return {"error": "Error enviando solicitud a herramienta MCP"}
    
    def _detectar_intencion(self, mensaje: str) -> tuple[str, dict]:
        """Detecta la intención del usuario y extrae parámetros"""
        mensaje_lower = mensaje.lower()
        
        if "clonar" in mensaje_lower or "clone" in mensaje_lower:
            return "clone_repo", self._extraer_parametros_clone(mensaje)
        elif "agregar archivo" in mensaje_lower or "add file" in mensaje_lower:
            return "add_file", self._extraer_parametros_file(mensaje)
        elif "listar" in mensaje_lower or "list" in mensaje_lower:
            return "list_repos", {}
        
        return "chat", {}
    
    def _extraer_parametros_clone(self, mensaje: str) -> dict:
        """Extrae parámetros para clonar repositorio interactivamente"""
        print("\n🔧 Detectada solicitud de clonado de repositorio")
        
        url = input("📁 Ingrese la URL del repo: ").strip()
        name = input("📝 Ingrese el nombre del repo local: ").strip()
        
        return {"url": url, "name": name}
    
    def _extraer_parametros_file(self, mensaje: str) -> dict:
        """Extrae parámetros para agregar archivo interactivamente"""
        print("\n📝 Detectada solicitud de agregar archivo")
        
        filename = input("📄 Nombre del archivo: ").strip()
        content = input("💭 Contenido del archivo: ").strip()
        message = input("💬 Mensaje del commit: ").strip()
        
        return {"filename": filename, "content": content, "message": message}
    
    def mostrar_herramientas(self):
        """Muestra las herramientas MCP disponibles"""
        if not self.tools_disponibles:
            print("❌ No hay herramientas MCP disponibles")
            return
        
        print("\n🔧 Herramientas MCP disponibles:")
        for i, tool in enumerate(self.tools_disponibles, 1):
            print(f"{i}. {tool.get('name', 'Sin nombre')}")
            if 'description' in tool:
                print(f"   📝 {tool['description']}")
    
    def preguntar(self, mensaje: str) -> str:
        """Procesa una pregunta del usuario"""
        self.log_completo.append(f"Usuario: {mensaje}")
        
        # Detectar intención
        intencion, parametros = self._detectar_intencion(mensaje)
        
        if intencion == "chat":
            # Pregunta normal al LLM
            respuesta = self._chat_normal(mensaje)
        else:
            # Acción MCP
            print(f"⏳ Ejecutando {intencion} via MCP...")
            resultado = self._call_mcp_tool(intencion, parametros)
            
            if isinstance(resultado, dict) and "error" in resultado:
                respuesta = f"❌ Error: {resultado['error']}"
            else:
                respuesta = f"✅ Resultado: {resultado}"
        
        self.log_completo.append(f"Asistente: {respuesta}")
        return respuesta
    
    def _chat_normal(self, mensaje: str) -> str:
        """Maneja conversación normal con el LLM"""
        # Agregar mensaje a historial
        self.conversation_history.append({"role": "user", "content": mensaje})
        
        try:
            # Llamar a OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                max_tokens=500,
                temperature=0.7
            )
            
            respuesta = response.choices[0].message.content
            
            # Agregar respuesta al historial
            self.conversation_history.append({"role": "assistant", "content": respuesta})
            
            return respuesta
            
        except Exception as e:
            return f"Error al comunicarse con OpenAI: {str(e)}"
    
    def mostrar_log(self):
        """Muestra el log completo de la conversación"""
        print("\n" + "="*60)
        print("📋 LOG COMPLETO DE LA CONVERSACIÓN:")
        print("="*60)
        for entrada in self.log_completo:
            print(entrada)
        print("="*60)
    
    def verificar_conexion_mcp(self):
        """Verifica el estado de la conexión MCP"""
        if not self.mcp_process:
            print("❌ No hay proceso MCP")
            return False
        
        poll_result = self.mcp_process.poll()
        if poll_result is not None:
            print(f"❌ Proceso MCP terminado con código: {poll_result}")
            return False
        
        print("✅ Conexión MCP activa")
        print(f"📊 Herramientas disponibles: {len(self.tools_disponibles)}")
        return True
    
    def cerrar(self):
        """Cierra la conexión con el servidor MCP"""
        if self.mcp_process:
            try:
                # Enviar mensaje de cierre si es posible
                if self.mcp_process.poll() is None:  # Proceso aún corriendo
                    close_message = {
                        "jsonrpc": "2.0",
                        "method": "notifications/cancelled",
                        "params": {}
                    }
                    self._send_mcp_message(close_message)
                    
                    # Esperar un momento para que el servidor procese
                    time.sleep(0.5)
                
                # Terminar proceso gracefully
                self.mcp_process.terminate()
                
                # Esperar hasta 5 segundos para terminación graceful
                try:
                    self.mcp_process.wait(timeout=5)
                    print("🔌 Conexión MCP cerrada correctamente")
                except subprocess.TimeoutExpired:
                    # Si no termina gracefully, forzar terminación
                    self.mcp_process.kill()
                    self.mcp_process.wait()
                    print("⚠️ Conexión MCP terminada forzosamente")
                    
            except Exception as e:
                print(f"⚠️ Error cerrando conexión MCP: {e}")
                try:
                    self.mcp_process.kill()
                    self.mcp_process.wait()
                except:
                    pass