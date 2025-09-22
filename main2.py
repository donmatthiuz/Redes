import os
from dotenv import load_dotenv
from cliente.ClienteFinal import LLMClientAsync
import asyncio

async def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    llm = LLMClientAsync(api_key)
    
    
    # Pregunta
    
    respuesta = llm.chat_normal("Quien fue alan turing")
    print(respuesta)

    # MCP compañero
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

    # 2️⃣ MCP remoto HTTP
    url = os.getenv("URL")
    print("URL", url)
    print("\n🔹 Conectando a MCP remoto HTTP...")
    await llm.conectar_mcp(url, use_http=True)
    tools_remote = await llm.listar_herramientas_mcp()
    print("Herramientas MCP remoto:", tools_remote)
    await llm.cerrar_mcp()

if __name__ == "__main__":
    asyncio.run(main())
