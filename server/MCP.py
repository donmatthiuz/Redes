# server.py
from fastmcp import FastMCP
from functions.GitManager import git_manager

mcp = FastMCP("MCP Server")

@mcp.tool()
async def clone_repo(url: str, name: str):
    return git_manager.setup_repo(url, name)

@mcp.tool()
async def add_file(filename: str, content: str, message: str):
    return git_manager.create_file_and_commit(filename, content, message)
