import asyncio
from fastmcp import Client
 
async def main():
    async with Client("arxiv_mcp_server.py") as client:
        # 1. Listar herramientas
        tools = await client.list_tools()
        print("Herramientas disponibles:", tools)

        # 2. Buscar papers
        search_result = await client.call_tool("search_arxiv", {
            "query": "cat:cs.AI deep learning",
            "sort_by": "relevance",
            "sort_order": "descending"
        })
        print("\n=== RESULTADOS DE BÚSQUEDA ===\n", search_result)

        # 3. Obtener la carpeta de descargas
        download_dir = await client.call_tool("get_download_root")
        print("\nCarpeta de descargas:", download_dir)

        # 4. Descargar un paper (ejemplo usando un ID de ArXiv)
        download_result = await client.call_tool("download_paper_arxiv", {
            "id": "2301.12345v1",
            "filename": "paper1.pdf"
        })
        print("\nResultado descarga:", download_result)

        # 5. Generar BibTeX
        bibtex = await client.call_tool("generate_bibtex", {
            "title": "An Example Paper",
            "authors": "John Doe",
            "year": "2023"
        })
        print("\nBibTeX generado:\n", bibtex)

if __name__ == "__main__":
    asyncio.run(main())
