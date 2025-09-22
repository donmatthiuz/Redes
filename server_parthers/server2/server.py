# mcp_server/server.py

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from mcp_server.analyzer import analyze_log_file
import json

app = FastAPI(title="MCP Log Analyzer", version="1.0")

# -------------------------------
# Endpoint de salud
# -------------------------------
@app.get("/status")
def get_status():
    """Health check endpoint"""
    return {"status": "OK"}

# -------------------------------
# Endpoint tradicional con archivo
# -------------------------------
@app.post("/analyze_logs")
async def analyze_logs(file: UploadFile = File(...)):
    """Recibe un log y analiza su contenido"""
    contents = await file.read()
    result = analyze_log_file(contents.decode("utf-8"))
    return result

# -------------------------------
# Endpoint JSON-RPC
# -------------------------------
@app.post("/jsonrpc")
async def jsonrpc(request: Request):
    """
    Soporta llamadas JSON-RPC:
    {
        "jsonrpc": "2.0",
        "method": "analyze_logs",
        "params": { "file_path": "mcp_server/example_logs/sample.log" },
        "id": 1
    }
    """
    try:
        data = await request.json()
        jsonrpc_id = data.get("id")
        method = data.get("method")
        params = data.get("params", {})

        if method != "analyze_logs":
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": "Method not found"},
                    "id": jsonrpc_id
                }
            )

        file_path = params.get("file_path")
        if not file_path:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "Missing file_path parameter"},
                    "id": jsonrpc_id
                }
            )

        with open(file_path, "r", encoding="utf-8") as f:
            log_text = f.read()
        
        result = analyze_log_file(log_text)

        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "result": result,
                "id": jsonrpc_id
            }
        )

    except Exception as e:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": None
            }
        )
