import asyncio
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client

async def main():
    transport = StreamableHttpTransport("http://127.0.0.1:8001/jsonrpc")
    
    try:
        async with Client(transport=transport) as client:
            print("✅ Cliente conectado exitosamente")
            
            # Listar herramientas disponibles
            print("\n📋 Listando herramientas...")
            tools = await client.list_tools()
            print("Herramientas disponibles:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Llamar a la herramienta analyze_logs
            print("\n🔍 Analizando archivo de log...")
            result = await client.call_tool("analyze_logs", {
                "file_path": "data/sample.log"
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
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("Asegúrate de que el servidor esté corriendo en http://127.0.0.1:8001")

if __name__ == "__main__":
    asyncio.run(main())