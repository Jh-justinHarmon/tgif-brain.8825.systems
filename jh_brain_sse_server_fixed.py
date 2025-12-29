#!/usr/bin/env python3
"""
Jh Brain SSE Server - Fixed Version
Removes Dropbox dependency, uses local capability map

Port: $PORT (Replit auto-assigns)
"""

import json
import sys
import queue
import threading
import uuid
import os
from pathlib import Path
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Store active SSE connections
connections = {}

# Load capability map from local file (no Dropbox dependency)
BRAIN_DIR = Path(__file__).parent
CAPABILITY_MAP = {}

def load_capability_map():
    """Load capability map from local file."""
    global CAPABILITY_MAP
    
    # Try local file first
    local_path = BRAIN_DIR / "capability_map.json"
    if local_path.exists():
        try:
            with open(local_path) as f:
                CAPABILITY_MAP = json.load(f)
                return CAPABILITY_MAP
        except Exception as e:
            print(f"Failed to load local capability map: {e}", file=sys.stderr)
    
    # Fallback to minimal capability map
    CAPABILITY_MAP = {
        "capabilities": {
            "jh_brain_query": {
                "description": "Find canonical 8825 tool for a given need",
                "tier": 0
            }
        },
        "tools": {}
    }
    return CAPABILITY_MAP

# Load on startup
load_capability_map()

def build_context_injection() -> dict:
    """Build context injection for new connections."""
    return {
        "system_prompt": "You are connected to 8825, Justin Harmon's personal AI system.",
        "recent_decisions": [],
        "active_patterns": [],
        "knowledge": [],
        "philosophies": []
    }

def create_sse_message(data: dict, event_type: str = None) -> str:
    """Format SSE message per MCP spec."""
    lines = []
    if event_type:
        lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)

@app.route('/', methods=['GET'])
def root():
    """Root endpoint for Replit health checks."""
    return jsonify({
        "status": "ok",
        "server": "jh-brain-sse-fixed",
        "version": "2.0.0"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({
        "status": "ok",
        "server": "jh-brain-sse-fixed",
        "version": "2.0.0",
        "tools": len(CAPABILITY_MAP.get("tools", {})),
        "active_connections": len(connections)
    })

@app.route('/sse', methods=['GET', 'POST'])
def sse_endpoint():
    """SSE endpoint for MCP protocol."""
    if request.method == 'POST':
        # Handle MCP message
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body"}), 400
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        try:
            # Simple response for now
            result = {
                "status": "ok",
                "method": method,
                "capability_map": CAPABILITY_MAP
            }
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
        connection_id = str(uuid.uuid4())
        message_queue = queue.Queue()
        connections[connection_id] = message_queue
        
        context_injection = build_context_injection()
        
        # Send initialization
        yield create_sse_message({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {
                "context": context_injection,
                "capability_map": CAPABILITY_MAP
            }
        }, "message")
        
        # Keep connection alive
        try:
            while True:
                try:
                    msg = message_queue.get(timeout=30)
                    yield create_sse_message(msg, "message")
                except queue.Empty:
                    # Send heartbeat
                    yield create_sse_message({"type": "heartbeat"}, "heartbeat")
        except GeneratorExit:
            connections.pop(connection_id, None)
    
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/query', methods=['POST'])
def query():
    """Direct query endpoint (non-SSE)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    
    need = data.get('need', '')
    
    return jsonify({
        "status": "ok",
        "need": need,
        "capability_map": CAPABILITY_MAP,
        "message": "Query received. Capability map loaded successfully."
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
