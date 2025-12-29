#!/usr/bin/env python3
"""
Jh Brain Philosophy Module

Core philosophies that guide all decisions:
- 8825 system principles
- HCSS methodology
- Decision frameworks
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# Load 8825 core (optional - works standalone if file doesn't exist)
CORE_PATH = Path(__file__).parent.parent.parent / "system/8825_core.json"
CORE_DATA = {}
if CORE_PATH.exists():
    try:
        with open(CORE_PATH) as f:
            CORE_DATA = json.load(f)
    except Exception:
        pass  # Fallback to hardcoded philosophies below

# Core Philosophies - extracted from 8825_core.json and HCSS methodology
CORE_PHILOSOPHIES = {
    "scope_discipline": {
        "rule": "Default to minimal viable solution. Solve the specific request, nothing more.",
        "impact_levels": {
            "low": "Single file, operational → do it",
            "medium": "2-3 files, new patterns → state time options",
            "high": "Architecture, system-wide → recommend comprehensive"
        },
        "forbidden": "No automatic library/lexicon/stats updates for operational changes unless explicitly requested",
        "expansion_triggers": ["document this", "build it properly", "add to library", "make it comprehensive"],
        "default": "Focused fix"
    },
    
    "decision_matrix": {
        "description": "Framework for self-resolving decisions: intent × stakes × efficiency",
        "thresholds": {
            "proceed": 0.7,  # Confidence >= 0.7 → proceed
            "ask": 0.5,      # Confidence < 0.5 → ask
            "default": 0.5   # Between 0.5-0.7 → use default option
        },
        "rule": "State choice + rationale in 1-2 lines when self-resolving"
    },
    
    "hcss_methodology": {
        "core": "Every business problem sits inside a process",
        "principles": [
            "Good methodology turns emotion-heavy situations into objective conversations",
            "Best/better practices increase enterprise value",
            "People, not just processes, determine whether improvements stick"
        ],
        "operating_pattern": [
            "Clarify process/project and success criteria",
            "Structure via templates/frameworks",
            "Measure with lightweight, meaningful metrics",
            "Facilitate meetings/decisions/follow-through",
            "Learn via issues/actions and refinement"
        ]
    },
    
    "data_sovereignty": {
        "rule": "Design for data sovereignty and user control as non-negotiable",
        "principles": [
            "User owns their data",
            "No lock-in to platforms",
            "Portable, exportable formats"
        ]
    },
    
    "progressive_revelation": {
        "rule": "Don't dump all memory at once",
        "approach": "confidence check → confirm → load full context",
        "reason": "Avoid overwhelming, stay focused"
    },
    
    "tool_usage": {
        "rule": "Use existing tools before building new ones",
        "protocol": [
            "Query Jh Brain first",
            "Use canonical tool if found",
            "Only search codebase if no tool exists",
            "Log usage for learning"
        ]
    },
    
    "response_format": {
        "template": ["Findings", "Decisions", "Next actions", "Refs used", "Summary"],
        "style": "Concise bullet points, single-block responses, no verbose paragraphs"
    }
}


def get_philosophy(key: str) -> Optional[Dict]:
    """Get a specific philosophy by key."""
    return CORE_PHILOSOPHIES.get(key)


def get_all_philosophies() -> Dict:
    """Get all core philosophies."""
    return CORE_PHILOSOPHIES


def apply_scope_discipline(request: str, impact: str = "low") -> Dict:
    """
    Apply scope discipline to a request.
    
    Returns guidance on how to handle the request.
    """
    scope = CORE_PHILOSOPHIES["scope_discipline"]
    
    # Check for expansion triggers
    triggers_found = [t for t in scope["expansion_triggers"] if t.lower() in request.lower()]
    
    if triggers_found:
        return {
            "approach": "comprehensive",
            "reason": f"Expansion trigger found: {triggers_found}",
            "guidance": "Build it properly with documentation"
        }
    
    if impact == "high":
        return {
            "approach": "ask",
            "reason": "High-impact change detected",
            "guidance": "State: 'High-impact: quick patch risks debt, proper build ensures stability. Recommend comprehensive?'"
        }
    elif impact == "medium":
        return {
            "approach": "offer_options",
            "reason": "Medium-impact change",
            "guidance": "State: 'Quick (X min) or comprehensive (Y min)?'"
        }
    else:
        return {
            "approach": "focused",
            "reason": "Low-impact, operational change",
            "guidance": scope["default"]
        }


def apply_decision_matrix(confidence: float, stakes: str = "low") -> Dict:
    """
    Apply decision matrix to determine action.
    
    Args:
        confidence: 0.0 to 1.0
        stakes: "low", "medium", "high"
    """
    matrix = CORE_PHILOSOPHIES["decision_matrix"]
    
    # High stakes always require confirmation
    if stakes == "high" and confidence < 0.9:
        return {
            "action": "ask",
            "reason": "High stakes require high confidence",
            "guidance": "Confirm with user before proceeding"
        }
    
    if confidence >= matrix["thresholds"]["proceed"]:
        return {
            "action": "proceed",
            "reason": f"Confidence {confidence:.0%} >= {matrix['thresholds']['proceed']:.0%}",
            "guidance": "State choice + rationale in 1-2 lines"
        }
    elif confidence < matrix["thresholds"]["ask"]:
        return {
            "action": "ask",
            "reason": f"Confidence {confidence:.0%} < {matrix['thresholds']['ask']:.0%}",
            "guidance": "Ask user for clarification"
        }
    else:
        return {
            "action": "default",
            "reason": f"Confidence {confidence:.0%} in default range",
            "guidance": "Use default option, state choice briefly"
        }


# Pattern Index integration
PATTERNS_PATH = Path(__file__).parent.parent.parent / "patterns"
PROTOCOLS_PATH = Path(__file__).parent.parent.parent / "protocols"


def get_relevant_patterns(task_type: str, need: str) -> List[Dict]:
    """
    Get relevant patterns for a task from the Pattern Index.
    """
    patterns = []
    
    # Map task types to pattern files
    task_to_patterns = {
        "export": ["export_patterns.md", "document_patterns.md"],
        "capture": ["session_patterns.md", "learning_patterns.md"],
        "analyze": ["analysis_patterns.md", "deep_dive_patterns.md"],
        "build": ["development_patterns.md", "architecture_patterns.md"],
        "ingest": ["ingestion_patterns.md", "transcript_patterns.md"]
    }
    
    # Also search Pattern Engine index
    try:
        pattern_index_path = Path(__file__).parent.parent.parent / "testing/ai_comparison_test/pattern_index.json"
        if pattern_index_path.exists():
            with open(pattern_index_path) as f:
                index = json.load(f)
            
            # Search for relevant patterns
            need_lower = need.lower()
            for doc in index.get("documents", []):
                if doc.get("doc_type") == "pattern":
                    # Check if pattern is relevant
                    title = doc.get("title", "").lower()
                    if any(kw in title for kw in need_lower.split()):
                        patterns.append({
                            "title": doc.get("title"),
                            "path": doc.get("path"),
                            "focus": doc.get("focus"),
                            "tier": doc.get("tier", 1)
                        })
    except Exception:
        pass
    
    return patterns[:5]  # Top 5


def get_relevant_protocols(task_type: str, need: str) -> List[Dict]:
    """
    Get relevant protocols for a task.
    """
    protocols = []
    
    # Key protocols by task type
    task_to_protocols = {
        "export": ["EXPORT_CONSOLE_PROTOCOL.md"],
        "capture": ["SESSION_CAPTURE_PROTOCOL.md", "MEMORY_PROTOCOL.md"],
        "analyze": ["DLI_ROUTING_PROTOCOL.md", "DEEP_DIVE_PROTOCOL.md"],
        "build": ["DEVELOPMENT_PROTOCOL.md", "PROJECT_CREATION_PROTOCOL.md"],
        "ingest": ["TRANSCRIPT_PROTOCOL.md", "INGESTION_PROTOCOL.md"],
        "ocr": ["OCR_ROUTING_RULES_SPEC.md"]
    }
    
    # Get protocols for this task type
    protocol_files = task_to_protocols.get(task_type, [])
    
    for pf in protocol_files:
        protocol_path = PROTOCOLS_PATH / pf
        if protocol_path.exists():
            protocols.append({
                "name": pf.replace(".md", "").replace("_", " ").title(),
                "path": str(protocol_path.relative_to(PROTOCOLS_PATH.parent.parent)),
                "file": pf
            })
    
    # Also search for protocols matching the need
    if PROTOCOLS_PATH.exists():
        need_lower = need.lower()
        for pf in PROTOCOLS_PATH.glob("*.md"):
            name_lower = pf.stem.lower()
            if any(kw in name_lower for kw in need_lower.split()):
                if pf.name not in protocol_files:
                    protocols.append({
                        "name": pf.stem.replace("_", " ").title(),
                        "path": str(pf.relative_to(PROTOCOLS_PATH.parent.parent)),
                        "file": pf.name
                    })
    
    return protocols[:5]  # Top 5


def get_guidance_for_task(task_type: str, context: Dict = None, need: str = "") -> Dict:
    """
    Get philosophy-based guidance for a task type.
    Now includes patterns and protocols.
    """
    guidance = {
        "philosophies_applied": [],
        "recommendations": [],
        "patterns": [],
        "protocols": []
    }
    
    # Always apply tool usage philosophy
    guidance["philosophies_applied"].append("tool_usage")
    guidance["recommendations"].append(
        "Query Jh Brain first before searching codebase"
    )
    
    # Task-specific guidance
    if task_type in ["export", "capture", "ingest"]:
        guidance["philosophies_applied"].append("scope_discipline")
        guidance["recommendations"].append(
            "Use focused fix unless expansion trigger present"
        )
    
    if task_type in ["analyze", "deep_dive", "research"]:
        guidance["philosophies_applied"].append("progressive_revelation")
        guidance["recommendations"].append(
            "Don't dump all context at once - reveal progressively"
        )
    
    if task_type in ["build", "create", "implement"]:
        guidance["philosophies_applied"].append("hcss_methodology")
        guidance["recommendations"].append(
            "Clarify success criteria first, then structure with templates"
        )
    
    # Always include response format
    guidance["philosophies_applied"].append("response_format")
    guidance["recommendations"].append(
        "Use: Findings → Decisions → Next actions → Refs → Summary"
    )
    
    # Add relevant patterns and protocols
    guidance["patterns"] = get_relevant_patterns(task_type, need)
    guidance["protocols"] = get_relevant_protocols(task_type, need)
    
    return guidance


if __name__ == "__main__":
    # Test
    print("=== Core Philosophies ===")
    for key, value in CORE_PHILOSOPHIES.items():
        print(f"\n{key}:")
        if isinstance(value, dict) and "rule" in value:
            print(f"  Rule: {value['rule']}")
    
    print("\n=== Scope Discipline Test ===")
    print(apply_scope_discipline("export this as docx"))
    print(apply_scope_discipline("build it properly"))
    
    print("\n=== Decision Matrix Test ===")
    print(apply_decision_matrix(0.8))
    print(apply_decision_matrix(0.4))
    print(apply_decision_matrix(0.6))
