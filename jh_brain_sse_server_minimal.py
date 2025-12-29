#!/usr/bin/env python3
"""
Jh Brain SSE Server - Minimal standalone version for Replit
HTTP + SSE for ChatGPT MCP Connector
Port: 5161
"""

import json
import os
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Store active SSE connections
connections = {}


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "server": "jh-brain-sse",
        "version": "1.0.0",
        "active_connections": len(connections)
    })


@app.route('/sse', methods=['GET', 'POST'])
def sse_endpoint():
    """SSE endpoint for MCP protocol."""
    if request.method == 'POST':
        # Handle MCP JSON-RPC messages
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body"}), 400
        
        method = data.get('method')
        request_id = data.get('id')
        
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "jh-brain",
                        "version": "1.0.0"
                    }
                }
            elif method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": "jh_brain_query",
                            "description": "Query Jh Brain for tool recommendations",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "need": {"type": "string"}
                                },
                                "required": ["need"]
                            }
                        }
                    ]
                }
            else:
                raise ValueError(f"Unknown method: {method}")
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)}
            }
        
        return jsonify(response)
    
    # GET: SSE stream
    def event_stream():
        yield f"data: {json.dumps({'status': 'connected'})}\n\n"
        try:
            while True:
                import time
                time.sleep(30)
                yield ": keepalive\n\n"
        except GeneratorExit:
            pass
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5161))
    print(f"🧠 Jh Brain SSE Server starting on port {port}...")
    print(f"   Health: http://localhost:{port}/health")
    print(f"   SSE: http://localhost:{port}/sse")
    app.run(host='0.0.0.0', port=port, debug=False)
