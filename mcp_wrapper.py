#!/usr/bin/env python3
"""
Jh Brain MCP Wrapper - Exposes Jh Brain as MCP tool
"""

import requests
import json
from fastapi import FastAPI

app = FastAPI()
JH_BRAIN_URL = "http://127.0.0.1:5060"

@app.post("/mcp")
async def handle_mcp_request(request: dict):
    """Handle MCP protocol requests"""
    method = request.get("method")
    params = request.get("params", {})
    
    if method == "tools/list":
        return {
            "tools": [{
                "name": "jh_brain_query",
                "description": "Query Jh Brain for tools matching a need",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "need": {"type": "string"}
                    },
                    "required": ["need"]
                }
            }]
        }
    elif method == "tools/call" and params.get("name") == "jh_brain_query":
        need = params.get("arguments", {}).get("need", "")
        response = requests.post(
            f"{JH_BRAIN_URL}/query_system",
            json={"need": need}
        )
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(response.json(), indent=2)
            }]
        }
    
    return {"error": "Unknown method"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5061)
