import asyncio
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async def example():
    transport = StreamableHttpTransport("http://127.0.0.1:8000/mcp/")
    
    async with Client(transport=transport) as cliente:
        await cliente.ping()
        print("Hizo bien el ping")
        
        tools = await cliente.list_tools()
        print("Las tools", tools)
        
        ## Uso
        #greeting = await cliente.call_tool("greet", {"name": "Alice"})
        #print("Gretting result", greeting)
        

if __name__== "__main__":
    asyncio.run(example())