# mcp_server/local_log_server.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from mcp_server.analyzer import analyze_log_file

app = FastAPI(title="Local Log Analyzer MCP Server", version="1.0")

@app.get("/status")
def get_status():
    """Health check endpoint"""
    return {"status": "OK"}

@app.post("/analyze_log_file")
async def analyze_log_file_endpoint(file: UploadFile = File(...)):
    """Recibe un archivo de log y devuelve el análisis"""
    try:
        contents = await file.read()
        results = analyze_log_file(contents.decode("utf-8"))
        return JSONResponse(content=results)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
