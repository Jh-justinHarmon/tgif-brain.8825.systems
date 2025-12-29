#!/usr/bin/env python3
"""
Jh Brain SSE Server - HTTP + SSE for ChatGPT MCP Connector

Exposes all Jh Brain tools via SSE protocol for external LLM access.
Port: 5161
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

# Local imports (self-contained brain directory)
BRAIN_DIR = Path(__file__).parent
sys.path.insert(0, str(BRAIN_DIR))

# Import from MCP server (which handles Dropbox API)
from jh_brain_mcp_server import CAPABILITY_MAP, find_tool_for_need, get_context_from_dli

app = Flask(__name__)
CORS(app)  # Allow cross-origin for ChatGPT

# Store active SSE connections
connections = {}


def build_context_injection() -> dict:
    """Build context injection for new connections."""
    context = {
        "system_prompt": """You are connected to 8825, Justin Harmon's personal AI system.

## Your Context
You have access to 8825's brain via the api_tool interface. This gives you:
- Tool routing (ask what tool to use for any task)
- Philosophy-based guidance (8825 principles for decision-making)
- Session context and memory

## How to Use 8825
1. For any task, first call jh_brain_query with what you need
2. For guidance on approach, call jh_brain_guidance
3. Log tool usage with jh_brain_log_use so the system learns

You are an extension of 8825, not a separate system. Act accordingly.""",
        "recent_decisions": [],
        "active_patterns": [],
        "knowledge": [],
        "philosophies": []
    }
    return context


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
        "server": "jh-brain-sse",
        "version": "1.0.0"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({
        "status": "ok",
        "server": "jh-brain-sse",
        "version": "1.0.0",
        "tools": 8,
        "active_connections": len(connections)
    })


@app.route('/sse', methods=['GET', 'POST'])
def sse_endpoint():
    """
    SSE endpoint for MCP protocol.
    GET: Establish SSE connection
    POST: Handle MCP JSON-RPC messages
    """
    if request.method == 'POST':
        # Handle MCP message directly on /sse endpoint
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body"}), 400
        
        method = data.get('method')
        params = data.get('params', {})
        request_id = data.get('id')
        
        try:
            result = process_mcp_request(method, params)
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
        
        # Build context injection on connect
        context_injection = build_context_injection()
        
        # Send initialization with context
        yield create_sse_message({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {
                "context": context_injection
            }
        }, "message")
        
        # Send system prompt with persistent context
        yield create_sse_message({
            "jsonrpc": "2.0", 
            "method": "notifications/context",
            "params": {
                "type": "system_context",
                "content": context_injection["system_prompt"]
            }
        }, "message")
        
        try:
            while True:
                try:
                    message = message_queue.get(timeout=30)
                    yield create_sse_message(message, "message")
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            connections.pop(connection_id, None)
    
    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/messages', methods=['POST'])
def handle_message():
    """Handle MCP messages from ChatGPT (alternate endpoint)."""
    connection_id = request.args.get('connection_id')
    data = request.get_json()
    
    method = data.get('method')
    params = data.get('params', {})
    request_id = data.get('id')
    
    try:
        result = process_mcp_request(method, params)
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
    
    # If connection exists, push to SSE stream
    if connection_id and connection_id in connections:
        connections[connection_id].put(response)
    
    return jsonify(response)


def process_mcp_request(method: str, params: dict) -> dict:
    """Process MCP request and return result."""
    
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "jh-brain",
                "version": "1.0.0",
                "description": "8825 System Brain - Tool routing, guidance, and memory"
            }
        }
    
    elif method == "tools/list":
        return {
            "tools": [
                {
                    "name": "jh_brain_query",
                    "description": "Find the canonical 8825 tool for a given need. Call this FIRST before trying to do anything in 8825.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "need": {
                                "type": "string",
                                "description": "What you need to do (e.g., 'export docx', 'capture session', 'search knowledge')"
                            }
                        },
                        "required": ["need"]
                    }
                },
                {
                    "name": "jh_brain_preflight",
                    "description": "Analyze a user request and get context injection. Returns relevant tools and approach for 8825 tasks.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "The user's request text to analyze"
                            }
                        },
                        "required": ["text"]
                    }
                },
                {
                    "name": "jh_brain_guidance",
                    "description": "Get philosophy-based guidance for a task. Applies 8825 principles to determine the right approach.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_type": {
                                "type": "string",
                                "description": "Type of task (export, capture, analyze, build, search, etc.)"
                            },
                            "request": {
                                "type": "string",
                                "description": "The user's request text"
                            },
                            "confidence": {
                                "type": "number",
                                "description": "Your confidence level (0.0-1.0)",
                                "default": 0.7
                            },
                            "impact": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Impact level of the change",
                                "default": "low"
                            }
                        },
                        "required": ["task_type", "request"]
                    }
                },
                {
                    "name": "jh_brain_log_use",
                    "description": "Log tool usage for learning. Call after using a tool to track success/failure.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tool_id": {"type": "string", "description": "The tool that was used"},
                            "need": {"type": "string", "description": "What the user needed"},
                            "success": {"type": "boolean", "description": "Whether the tool worked", "default": True},
                            "notes": {"type": "string", "description": "Optional notes"}
                        },
                        "required": ["tool_id", "need"]
                    }
                },
                {
                    "name": "jh_brain_stats",
                    "description": "Get Jh Brain usage statistics and learning weights.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "jh_brain_resume",
                    "description": "Get session context from previous sessions. Call at start of new session.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "jh_brain_rank_tools",
                    "description": "Rank tools by learned success rates when multiple could work.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "tool_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tool IDs to rank"
                            }
                        },
                        "required": ["tool_ids"]
                    }
                },
                {
                    "name": "jh_brain_list_capabilities",
                    "description": "List all available 8825 capabilities and tools.",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "jh_brain_get_context",
                    "description": "Get context on any topic from 8825's knowledge base. Use this to learn about HCSS, Joju, past decisions, or any 8825 domain knowledge. This runs a DLI deep dive internally.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The topic to get context on (e.g., 'HCSS open projects', 'Joju architecture', 'recent decisions')"
                            },
                            "focus": {
                                "type": "string",
                                "enum": ["global", "hcss", "joju", "jh_personal"],
                                "description": "Focus area to scope the context (default: global)",
                                "default": "global"
                            }
                        },
                        "required": ["topic"]
                    }
                }
            ]
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name == "jh_brain_query":
            result = find_tool_for_need(tool_args.get("need", ""))
            
        elif tool_name == "jh_brain_preflight":
            from preflight import get_context_injection, format_injection
            text = tool_args.get("text", "")
            context = get_context_injection(text)
            result = {
                "context": context,
                "formatted": format_injection(context) if context else None
            }
            
        elif tool_name == "jh_brain_guidance":
            from philosophy import (
                apply_scope_discipline,
                apply_decision_matrix,
                get_guidance_for_task,
                get_all_philosophies
            )
            task_type = tool_args.get("task_type", "")
            request_text = tool_args.get("request", "")
            confidence = tool_args.get("confidence", 0.7)
            impact = tool_args.get("impact", "low")
            
            result = {
                "task_guidance": get_guidance_for_task(task_type, need=request_text),
                "scope_discipline": apply_scope_discipline(request_text, impact),
                "decision_matrix": apply_decision_matrix(confidence),
                "core_philosophies": list(get_all_philosophies().keys())
            }
            
        elif tool_name == "jh_brain_log_use":
            from session_state import log_tool_use, get_or_create_session
            session_id = get_or_create_session()
            log_tool_use(
                session_id=session_id,
                tool_id=tool_args.get("tool_id", ""),
                need=tool_args.get("need", ""),
                success=tool_args.get("success", True),
                notes=tool_args.get("notes", "")
            )
            result = {"logged": True, "session_id": session_id}
            
        elif tool_name == "jh_brain_stats":
            from session_state import get_session_stats
            result = get_session_stats()
            
        elif tool_name == "jh_brain_resume":
            from session_state import get_session_summary, format_session_resume
            result = {
                "summary": get_session_summary(),
                "formatted": format_session_resume()
            }
            
        elif tool_name == "jh_brain_rank_tools":
            from session_state import get_weighted_tool_ranking
            tool_ids = tool_args.get("tool_ids", [])
            ranked = get_weighted_tool_ranking(tool_ids)
            result = {
                "ranked_tools": ranked,
                "recommendation": ranked[0]["tool_id"] if ranked else None
            }
            
        elif tool_name == "jh_brain_list_capabilities":
            result = {
                "capabilities": list(CAPABILITY_MAP.get("capabilities", {}).keys()),
                "tools": list(CAPABILITY_MAP.get("tools", {}).keys()),
                "total_capabilities": len(CAPABILITY_MAP.get("capabilities", {})),
                "total_tools": len(CAPABILITY_MAP.get("tools", {}))
            }
            
        elif tool_name == "jh_brain_get_context":
            topic = tool_args.get("topic", "")
            focus = tool_args.get("focus", "global")
            
            if not topic:
                raise ValueError("Topic is required")
            
            result = get_context_from_dli(topic, focus)
            
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
        }
    
    else:
        raise ValueError(f"Unknown method: {method}")


# Also expose direct HTTP endpoints for non-MCP clients
@app.route('/api/query', methods=['POST'])
def api_query():
    """Direct HTTP endpoint for tool queries."""
    try:
        data = request.get_json()
        need = data.get('need', '')
        result = find_tool_for_need(need)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "need": need}), 500


@app.route('/api/capabilities', methods=['GET'])
def api_capabilities():
    """List all capabilities."""
    try:
        return jsonify({
            "capabilities": CAPABILITY_MAP.get("capabilities", {}),
            "tools": CAPABILITY_MAP.get("tools", {}),
            "status": "ok"
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route('/api/guidance', methods=['POST'])
def api_guidance():
    """Get guidance for a task."""
    try:
        from philosophy import (
            apply_scope_discipline,
            apply_decision_matrix,
            get_guidance_for_task
        )
        data = request.get_json()
        task_type = data.get('task_type', '')
        request_text = data.get('request', '')
        confidence = data.get('confidence', 0.7)
        impact = data.get('impact', 'low')
        
        return jsonify({
            "task_guidance": get_guidance_for_task(task_type, need=request_text),
            "scope_discipline": apply_scope_discipline(request_text, impact),
            "decision_matrix": apply_decision_matrix(confidence),
            "status": "ok"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "task_type": task_type,
            "status": "error"
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5161))
    print(f"🧠 Jh Brain SSE Server starting on port {port}...")
    print(f"   SSE endpoint: http://0.0.0.0:{port}/sse")
    print(f"   Health check: http://0.0.0.0:{port}/health")
    print(f"   API endpoints: /api/query, /api/capabilities, /api/guidance")
    app.run(host='0.0.0.0', port=port, threaded=True)
