import os
import asyncio
from cliente.LLM import LLMClient
from dotenv import load_dotenv

def main():
    """Función principal del cliente LLM con MCP."""
    # Cargar variables de entorno
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: No se encontró la API Key de OpenAI en las variables de entorno.")
        print("💡 Asegúrate de tener OPENAI_API_KEY en tu archivo .env")
        return

    print("🚀 Iniciando Cliente LLM con MCP Server")
    print("="*50)
    
    # Crear el cliente LLM con MCP
    cliente = LLMClient(api_key=api_key, server_script="server.py")
    
    try:
        print("\n🔧 Verificando conexión MCP...")
        herramientas = cliente._get_available_tools()
        if herramientas:
            print(f"✅ Herramientas MCP disponibles: {herramientas}")
        else:
            print("⚠️ No se pudieron obtener las herramientas MCP")
        
        # Conversación de prueba
        print("\n1️⃣ Pregunta general:")
        respuesta = cliente.preguntar("¿Quién fue Alan Turing?")
        print(f"🤖 {respuesta}\n")
        
        print("2️⃣ Pregunta de seguimiento:")
        respuesta = cliente.preguntar("¿En qué fecha nació?")
        print(f"🤖 {respuesta}\n")
        
        print("3️⃣ Acción MCP - Clonar repositorio:")
        respuesta = cliente.preguntar("Quiero clonar repo")
        print(f"🤖 {respuesta}\n")
        
        # Opcionalmente, probar agregar archivo
        continuar = input("¿Quieres probar agregar un archivo? (s/n): ").lower().strip()
        if continuar == 's':
            print("\n4️⃣ Acción MCP - Agregar archivo:")
            respuesta = cliente.preguntar("Quiero agregar archivo")
            print(f"🤖 {respuesta}\n")
        
        # Permitir interacción continua
        print("\n5️⃣ Modo interactivo (escribe 'salir' para terminar):")
        while True:
            try:
                user_input = input("\n👤 Tú: ").strip()
                if user_input.lower() in ['salir', 'exit', 'quit']:
                    break
                if user_input:
                    respuesta = cliente.preguntar(user_input)
                    print(f"🤖 {respuesta}")
            except KeyboardInterrupt:
                print("\n⚠️ Saliendo del modo interactivo...")
                break
    
    except KeyboardInterrupt:
        print("\n⚠️ Operación interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Mostrar log y cerrar
        print("\n" + "="*50)
        print("📋 MOSTRANDO LOG COMPLETO:")
        cliente.mostrar_log()
        
        print("\n🔄 Cerrando conexiones...")
        cliente.cerrar()
        print("✅ Programa finalizado correctamente")

def test_mcp_connection():
    """Función para probar solo la conexión MCP."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: No se encontró la API Key de OpenAI")
        return
    
    print("🧪 Probando conexión MCP...")
    cliente = LLMClient(api_key=api_key, server_script="server.py")
    
    try:
        herramientas = cliente.obtener_herramientas_disponibles()
        print(f"✅ Herramientas disponibles: {herramientas}")
        
        # Probar una herramienta simple
        if "clone_repo" in herramientas:
            print("🔧 Probando herramienta clone_repo...")
            # Test con datos dummy
            resultado = cliente._call_mcp_tool("clone_repo", {
                "url": "https://github.com/test/test.git",
                "name": "test_repo"
            })
            print(f"📤 Resultado: {resultado}")
            
    except Exception as e:
        print(f"❌ Error en prueba MCP: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cliente.cerrar()

if __name__ == "__main__":
    # Uncomment para probar solo la conexión MCP
    # test_mcp_connection()
    
    # Ejecutar programa principal
    main()