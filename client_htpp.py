import asyncio
import os
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from dotenv import load_dotenv

async def example():
    load_dotenv()
    url = os.getenv("URL")
    transport = StreamableHttpTransport(f"{url}/mcp/")
    
    async with Client(transport=transport) as cliente:
        await cliente.ping()
        print("Hizo bien el ping")
        
        tools = await cliente.list_tools()
        print("Las tools", tools)
        
        ## Uso
        greeting = await cliente.call_tool("voice_to_text", {"voice_path": "functions/Grabación-_2_.wav"})
        print("Gretting result", greeting)
        

if __name__== "__main__":
    asyncio.run(example())