from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from server_parthers.server2.analyzer import analyze_log_file
import json
from dotenv import load_dotenv
import os

app = FastAPI(title="MCP Log Analyzer", version="1.0")
load_dotenv()
APIKEY = os.getenv("OTX_API_KEY")

# Información del servidor
SERVER_INFO = {
    "name": "log-analyzer-server",
    "version": "1.0.0"
}

# Herramientas disponibles
TOOLS = [
    {
        "name": "analyze_logs",
        "description": "Analiza un archivo de log para detectar patrones y anomalías",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Ruta al archivo de log a analizar"
                }
            },
            "required": ["file_path"]
        }
    }
]

def create_error_response(code, message, request_id=0):
    """Crea una respuesta de error JSON-RPC válida"""
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id if request_id is not None else 0
        }
    )

def create_success_response(result, request_id=0):
    """Crea una respuesta exitosa JSON-RPC válida"""
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id if request_id is not None else 0
        }
    )

@app.get("/status")
def get_status():
    return {"status": "OK"}

@app.post("/jsonrpc")
async def jsonrpc(request: Request):
    """
    Endpoint JSON-RPC compatible con protocolo MCP
    """
    jsonrpc_id = 0  # Default ID
    
    try:
        data = await request.json()
        jsonrpc_id = data.get("id", 0)
        method = data.get("method")
        params = data.get("params", {})

        if not method:
            return create_error_response(-32600, "Invalid Request", jsonrpc_id)

        # Método de inicialización MCP
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": SERVER_INFO
            }
            return create_success_response(result, jsonrpc_id)

        # Método para listar herramientas
        elif method == "tools/list":
            result = {"tools": TOOLS}
            return create_success_response(result, jsonrpc_id)

        # Método para llamar herramientas
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return create_error_response(-32602, "Missing tool name", jsonrpc_id)
            
            if tool_name == "analyze_logs":
                file_path = arguments.get("file_path")
                if not file_path:
                    return create_error_response(-32602, "Missing file_path parameter", jsonrpc_id)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        log_text = f.read()
                    
                    analysis_result = analyze_log_file(log_text, APIKEY)
                    
                    result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(analysis_result, indent=2)
                            }
                        ]
                    }
                    return create_success_response(result, jsonrpc_id)
                    
                except FileNotFoundError:
                    return create_error_response(-32000, f"File not found: {file_path}", jsonrpc_id)
                except Exception as e:
                    return create_error_response(-32000, f"Error analyzing log: {str(e)}", jsonrpc_id)
            else:
                return create_error_response(-32601, f"Unknown tool: {tool_name}", jsonrpc_id)

        # Método ping (opcional pero útil)
        elif method == "ping":
            return create_success_response({}, jsonrpc_id)

        # Método no encontrado
        else:
            return create_error_response(-32601, f"Method not found: {method}", jsonrpc_id)

    except json.JSONDecodeError:
        return create_error_response(-32700, "Parse error", jsonrpc_id)
    except Exception as e:
        return create_error_response(-32000, str(e), jsonrpc_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)