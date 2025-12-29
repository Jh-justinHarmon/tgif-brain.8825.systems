#!/usr/bin/env python3
"""
Jh Brain Pre-flight Context Injection

Analyzes user requests and injects relevant tool context.
Uses PromptGen for smarter prompt optimization.
"""

import sys
import json
import re
from pathlib import Path
from typing import Optional, List, Dict

# Load capability map (local first, then fallback)
CAPABILITY_MAP_PATH = Path(__file__).parent / "capability_map.json"
CAPABILITY_MAP = {}

if CAPABILITY_MAP_PATH.exists():
    try:
        with open(CAPABILITY_MAP_PATH) as f:
            CAPABILITY_MAP = json.load(f)
    except Exception:
        pass

# Load PromptGen (optional)
PROMPTGEN_PATH = Path(__file__).parent.parent.parent / "promptgen"
sys.path.insert(0, str(PROMPTGEN_PATH))
sys.path.insert(0, str(PROMPTGEN_PATH.parent))

try:
    from promptgen import get_shorthand
    HAS_PROMPTGEN = True
except ImportError:
    HAS_PROMPTGEN = False
    get_shorthand = lambda x: {}


# Keywords that indicate 8825 internal requests
INTERNAL_KEYWORDS = [
    # Actions
    "export", "capture", "ingest", "ocr", "scan", "transcribe",
    "deep dive", "analyze", "search", "find",
    # Formats
    "docx", "html", "pdf", "markdown",
    # Systems
    "8825", "hcss", "tgif", "joju", "ral", "lhl",
    # Tools
    "memory", "library", "dli", "pattern", "transcript",
    "export console", "memory hub", "brain",
    # Resilience stack keywords
    "resilience", "fallback", "local", "offline", "cost optimization",
    "unified llm", "openrouter", "ollama", "local search", "telemetry",
    "direct file processing", "duckduckgo", "tavily",
    # Mistral specialist triggers
    "code", "script", "function", "refactor", "python", "javascript",
    "reason", "strategy", "think through", "evaluate",
    "calculate", "math", "metrics", "numbers"
]

# Mistral specialist profile detection
MISTRAL_PROFILE_TRIGGERS = {
    "code": [
        "code", "coding", "script", "python", "javascript", "typescript",
        "function", "refactor", "implement", "write a", "create a",
        "goose", "mcp", "infrastructure", "cli", "api"
    ],
    "reasoning": [
        "reason", "reasoning", "think", "strategy", "evaluate", "analyze",
        "triage", "complex", "multi-step", "pattern", "decide", "compare",
        "tradeoff", "pros and cons", "should i", "which is better"
    ],
    "math": [
        "math", "calculate", "numeric", "metrics", "finance", "ops",
        "table", "numbers", "statistics", "percentage", "ratio",
        "compound", "interest", "roi", "budget"
    ],
    "general": [
        "summarize", "summary", "draft", "explain", "describe"
    ]
}


def detect_mistral_profile(text: str) -> Optional[str]:
    """Detect which Mistral specialist profile best matches the request."""
    text_lower = text.lower()
    scores = {}
    
    for profile, triggers in MISTRAL_PROFILE_TRIGGERS.items():
        score = sum(1 for t in triggers if t in text_lower)
        if score > 0:
            scores[profile] = score
    
    if not scores:
        return None
    
    # Return highest scoring profile (prefer specialists over general)
    sorted_profiles = sorted(scores.items(), key=lambda x: (-x[1], x[0] != "general"))
    return sorted_profiles[0][0]


def is_internal_request(text: str) -> bool:
    """Check if request is about 8825 internals."""
    text_lower = text.lower()
    
    for keyword in INTERNAL_KEYWORDS:
        if keyword in text_lower:
            return True
    
    return False


def extract_needs(text: str) -> List[str]:
    """Extract potential needs from user text."""
    needs = []
    text_lower = text.lower()
    
    # Check each capability's keywords
    for cap_id, cap_info in CAPABILITY_MAP["capabilities"].items():
        score = sum(1 for kw in cap_info["keywords"] if kw.lower() in text_lower)
        if score > 0:
            needs.append({
                "capability": cap_id,
                "description": cap_info["description"],
                "tool_id": cap_info["tool_id"],
                "score": score
            })
    
    # Sort by score
    needs.sort(key=lambda x: x["score"], reverse=True)
    return needs[:3]  # Top 3


def get_promptgen_optimization(capability: str, text: str) -> Optional[Dict]:
    """
    Get PromptGen optimization for a capability.
    
    Returns guidance (not commands) for optimal results.
    """
    if not HAS_PROMPTGEN:
        return None
    
    # Map capabilities to PromptGen ops
    cap_to_op = {
        "export_docx": "/EXPORT",
        "export_html": "/EXPORT",
        "export_markdown": "/EXPORT",
        "capture_session": "/CAPTURE",
        "assimilate_memory": "/CAPTURE",
        "deep_dive": "/DEEP_DIVE",
        "search_knowledge": "/SEARCH",
        "ocr_file": "/OCR",
        "ingest_transcript": "/INGEST"
    }
    
    op = cap_to_op.get(capability)
    if not op:
        return None
    
    try:
        shorthand = get_shorthand(op)
        if shorthand:
            return {
                "op": op,
                "invocation": shorthand.get("invocation", "PG:MICRO"),
                "output": shorthand.get("output", "flexible"),
                "guidance": shorthand.get("guidance", []),
                "quality_checks": shorthand.get("quality_checks", []),
                "flexibility": shorthand.get("flexibility", "high")
            }
    except Exception:
        pass
    
    return None


def get_context_injection(text: str) -> Optional[Dict]:
    """
    Analyze text and return context to inject.
    
    Returns None if not an internal request.
    Uses PromptGen for smarter prompt optimization.
    """
    if not is_internal_request(text):
        return None
    
    needs = extract_needs(text)
    
    if not needs:
        return {
            "is_internal": True,
            "tools_found": False,
            "message": "This appears to be an 8825 internal request, but no specific tools matched. Consider using jh_brain_query to find the right tool."
        }
    
    # Get tool details for top match
    top_need = needs[0]
    tool_info = CAPABILITY_MAP["tools"].get(top_need["tool_id"], {})
    
    context = {
        "is_internal": True,
        "tools_found": True,
        "primary_tool": {
            "id": top_need["tool_id"],
            "name": tool_info.get("name", top_need["tool_id"]),
            "type": tool_info.get("type", "unknown"),
            "capability": top_need["capability"],
            "description": top_need["description"]
        },
        "how_to_use": None,
        "other_matches": [n["capability"] for n in needs[1:]],
        "promptgen": None
    }
    
    # Add usage instructions based on tool type
    if tool_info.get("type") == "http_service":
        context["how_to_use"] = {
            "type": "http",
            "port": tool_info.get("port"),
            "endpoints": tool_info.get("endpoints", {}),
            "example": f"POST http://127.0.0.1:{tool_info.get('port')}{list(tool_info.get('endpoints', {}).values())[0] if tool_info.get('endpoints') else ''}"
        }
    elif tool_info.get("type") == "mcp":
        context["how_to_use"] = {
            "type": "mcp",
            "prefix": tool_info.get("mcp_prefix", ""),
            "tools": tool_info.get("tools", []),
            "example": f"Call {tool_info.get('mcp_prefix', '')}* tools"
        }
    
    # Add PromptGen optimization
    pg_opt = get_promptgen_optimization(top_need["capability"], text)
    if pg_opt:
        context["promptgen"] = pg_opt
    
    # Add philosophy guidance
    try:
        from philosophy import apply_scope_discipline, get_guidance_for_task
        
        # Determine task type from capability
        cap_to_task = {
            "export_docx": "export",
            "export_html": "export",
            "capture_session": "capture",
            "deep_dive": "analyze",
            "search_knowledge": "search",
            "ocr_file": "ocr",
            "ingest_transcript": "ingest"
        }
        task_type = cap_to_task.get(top_need["capability"], "general")
        
        context["philosophy"] = {
            "scope": apply_scope_discipline(text),
            "guidance": get_guidance_for_task(task_type)
        }
    except Exception:
        pass
    
    # MISTRAL SPECIALIST PROMOTION
    # Actively suggest Mistral specialists when appropriate
    mistral_profile = detect_mistral_profile(text)
    if mistral_profile:
        mistral_tool = CAPABILITY_MAP["tools"].get("mistral_gateway", {})
        context["mistral_suggestion"] = {
            "profile": mistral_profile,
            "description": mistral_tool.get("profiles", {}).get(mistral_profile, ""),
            "how_to_use": f"mcp13_mistral_generate with profile='{mistral_profile}'",
            "reason": f"Detected {mistral_profile} task - Mistral specialist available"
        }
    
    return context


def format_injection(context: Dict) -> str:
    """Format context as a string for injection."""
    if not context or not context.get("is_internal"):
        return ""
    
    if not context.get("tools_found"):
        return f"\n[Jh Brain] {context['message']}\n"
    
    tool = context["primary_tool"]
    lines = [
        f"\n[Jh Brain Context]",
        f"Tool: {tool['name']} ({tool['id']})",
        f"For: {tool['description']}"
    ]
    
    if context.get("how_to_use"):
        usage = context["how_to_use"]
        if usage["type"] == "http":
            lines.append(f"Use: {usage['example']}")
        elif usage["type"] == "mcp":
            lines.append(f"Use: {usage['example']}")
    
    # Add PromptGen guidance
    if context.get("promptgen"):
        pg = context["promptgen"]
        lines.append(f"PromptGen: {pg['op']} ({pg['invocation']}) [flexibility: {pg.get('flexibility', 'high')}]")
        if pg.get("guidance"):
            lines.append(f"Guidance: {pg['guidance'][0]}")  # First guidance item
        if pg.get("quality_checks"):
            lines.append(f"Check: {pg['quality_checks'][0]}")  # First quality check
    
    # MISTRAL SPECIALIST SUGGESTION (promoted)
    if context.get("mistral_suggestion"):
        ms = context["mistral_suggestion"]
        lines.append(f"\n💡 Mistral Specialist Available: {ms['profile'].upper()}")
        lines.append(f"   {ms['description']}")
        lines.append(f"   Use: {ms['how_to_use']}")
    
    if context.get("other_matches"):
        lines.append(f"Also relevant: {', '.join(context['other_matches'])}")
    
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    test_requests = [
        "export this as a docx for TGIF",
        "capture this session",
        "what's the weather like",
        "run a deep dive on the export pipeline",
        "ocr this screenshot",
        "write a python function to parse JSON",
        "think through the tradeoffs of using SQLite vs Postgres",
        "calculate the compound interest on $1000 at 7%",
        "summarize this transcript"
    ]
    
    for req in test_requests:
        print(f"\n--- Request: {req} ---")
        context = get_context_injection(req)
        if context:
            print(format_injection(context))
        else:
            print("[Not an internal request]")
