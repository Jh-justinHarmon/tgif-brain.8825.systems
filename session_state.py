#!/usr/bin/env python3
"""
Jh Brain Session State

Manages persistent session state across conversations:
- Session lifecycle (start, end, resume)
- Tool usage logging
- Learning weights based on success/failure

Now integrated with Memory Core for unified storage.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sys

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Database location (local cache, Memory Core is source of truth)
DB_PATH = Path(__file__).parent / "jh_brain_state.db"

# Try to import Memory Core
try:
    from memory_core.api import (
        upsert_entry, append_event as mc_append_event, 
        open_session as mc_open_session, close_session as mc_close_session,
        get_session_context as mc_get_context
    )
    from memory_core.schema import EntryType, EventType
    HAS_MEMORY_CORE = True
except ImportError:
    HAS_MEMORY_CORE = False


def init_db():
    """Initialize session state database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        started_at TEXT,
        ended_at TEXT,
        tool_calls INTEGER DEFAULT 0,
        successes INTEGER DEFAULT 0,
        failures INTEGER DEFAULT 0
    )
    """)
    
    # Tool usage table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tool_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        tool_id TEXT,
        need TEXT,
        timestamp TEXT,
        success INTEGER DEFAULT 1,
        notes TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(id)
    )
    """)
    
    # Learning weights - boost tools that work well
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tool_weights (
        tool_id TEXT PRIMARY KEY,
        weight REAL DEFAULT 1.0,
        total_uses INTEGER DEFAULT 0,
        successes INTEGER DEFAULT 0,
        last_used TEXT
    )
    """)
    
    conn.commit()
    conn.close()


def start_session() -> str:
    """Start a new session, return session ID."""
    init_db()
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (id, started_at) VALUES (?, ?)",
        (session_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return session_id


def log_tool_use(
    session_id: str,
    tool_id: str,
    need: str,
    success: bool = True,
    notes: str = "",
    user_id: str = "local"
) -> None:
    """
    Log a tool usage event.
    
    Also updates learning weights and writes to Memory Core.
    
    Args:
        session_id: Current session ID
        tool_id: Tool that was used
        need: What the user needed
        success: Whether the tool worked
        notes: Optional notes
        user_id: User ID for multi-user attribution
    """
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    # Log the usage
    cursor.execute("""
        INSERT INTO tool_usage (session_id, tool_id, need, success, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, tool_id, need, 1 if success else 0, notes, now))
    
    # Update session stats
    if success:
        cursor.execute("""
            UPDATE sessions SET tool_calls = tool_calls + 1, successes = successes + 1
            WHERE id = ?
        """, (session_id,))
    else:
        cursor.execute("""
            UPDATE sessions SET tool_calls = tool_calls + 1, failures = failures + 1
            WHERE id = ?
        """, (session_id,))
    
    conn.commit()
    conn.close()
    
    # Update learning weight (separate connection)
    update_tool_weight(tool_id, success)
    
    # Also write to Memory Core if available
    if HAS_MEMORY_CORE:
        try:
            upsert_entry(
                entry_type=EntryType.TOOL_USAGE,
                title=f"Tool: {tool_id}",
                content=f"Need: {need}\nSuccess: {success}\nNotes: {notes}\nUser: {user_id}",
                tags=[tool_id, "tool_usage", "success" if success else "failure", f"user:{user_id}"],
                provenance="jh_brain"
            )
            mc_append_event(
                session_id=session_id,
                event_type=EventType.TOOL_USE,
                payload={"tool_id": tool_id, "need": need, "success": success, "notes": notes, "user_id": user_id}
            )
        except Exception:
            pass  # Memory Core write failed, local cache still valid


def update_tool_weight(tool_id: str, success: bool) -> None:
    """Update learning weight for a tool based on success/failure."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO tool_weights (tool_id, weight, total_uses, successes, last_used)
        VALUES (?, 1.0, 1, ?, ?)
        ON CONFLICT(tool_id) DO UPDATE SET
            total_uses = total_uses + 1,
            successes = successes + excluded.successes,
            last_used = excluded.last_used,
            weight = CASE 
                WHEN excluded.successes > 0 THEN MIN(weight + 0.1, 2.0)
                ELSE MAX(weight - 0.1, 0.1)
            END
    """, (tool_id, 1 if success else 0, now))
    
    conn.commit()
    conn.close()


def get_tool_weight(tool_id: str) -> float:
    """Get learning weight for a tool."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT weight FROM tool_weights WHERE tool_id = ?", (tool_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else 1.0


def get_session_stats(session_id: Optional[str] = None) -> dict:
    """Get stats for a session or all sessions."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        
        cursor.execute(
            "SELECT tool_id, COUNT(*) as uses, SUM(success) as successes FROM tool_usage WHERE session_id = ? GROUP BY tool_id",
            (session_id,)
        )
        tools = cursor.fetchall()
        
        conn.close()
        
        return {
            "session": dict(session) if session else None,
            "tools_used": [dict(t) for t in tools]
        }
    else:
        # Get overall stats
        cursor.execute("SELECT COUNT(*) as total_sessions, SUM(tool_calls) as total_calls, SUM(successes) as total_successes FROM sessions")
        overall = cursor.fetchone()
        
        cursor.execute("SELECT * FROM tool_weights ORDER BY weight DESC LIMIT 10")
        top_tools = cursor.fetchall()
        
        conn.close()
        
        return {
            "overall": dict(overall),
            "top_tools": [dict(t) for t in top_tools]
        }


def get_recent_failures(limit: int = 10) -> list:
    """Get recent failures for debugging."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM tool_usage WHERE success = 0 ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    failures = cursor.fetchall()
    conn.close()
    
    return [dict(f) for f in failures]


# Current session tracking
_current_session: Optional[str] = None


def get_or_create_session() -> str:
    """Get current session or create new one."""
    global _current_session
    if _current_session is None:
        _current_session = start_session()
    return _current_session


def get_session_summary(limit: int = 5) -> dict:
    """
    Get summary of recent sessions for context injection.
    
    Returns:
        Summary of recent activity for session resume.
    """
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get recent sessions
    cursor.execute(
        "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
        (limit,)
    )
    sessions = [dict(s) for s in cursor.fetchall()]
    
    # Get tool usage patterns
    cursor.execute("""
        SELECT tool_id, COUNT(*) as uses, SUM(success) as successes,
               MAX(timestamp) as last_used
        FROM tool_usage
        GROUP BY tool_id
        ORDER BY uses DESC
        LIMIT 10
    """)
    tool_patterns = [dict(t) for t in cursor.fetchall()]
    
    # Get recent failures for awareness
    cursor.execute("""
        SELECT tool_id, need, notes, timestamp
        FROM tool_usage
        WHERE success = 0
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    recent_failures = [dict(f) for f in cursor.fetchall()]
    
    # Calculate totals
    cursor.execute("""
        SELECT COUNT(*) as total_sessions,
               SUM(tool_calls) as total_calls,
               SUM(successes) as total_successes,
               SUM(failures) as total_failures
        FROM sessions
    """)
    totals = dict(cursor.fetchone())
    
    conn.close()
    
    # Build summary
    summary = {
        "recent_sessions": len(sessions),
        "totals": totals,
        "most_used_tools": [
            {"tool": t["tool_id"], "uses": t["uses"], "success_rate": f"{(t['successes'] or 0) / t['uses'] * 100:.0f}%"}
            for t in tool_patterns[:5]
        ],
        "recent_failures": [
            {"tool": f["tool_id"], "need": f["need"], "notes": f["notes"]}
            for f in recent_failures
        ],
        "last_session": sessions[0] if sessions else None
    }
    
    return summary


def format_session_resume() -> str:
    """
    Format session summary as injectable context.
    """
    summary = get_session_summary()
    
    lines = ["[Jh Brain Session Context]"]
    
    if summary["totals"]["total_sessions"]:
        lines.append(f"Sessions: {summary['totals']['total_sessions']} | Calls: {summary['totals']['total_calls']} | Success: {summary['totals']['total_successes']}/{summary['totals']['total_calls']}")
    
    if summary["most_used_tools"]:
        tools = ", ".join([f"{t['tool']} ({t['success_rate']})" for t in summary["most_used_tools"][:3]])
        lines.append(f"Top tools: {tools}")
    
    if summary["recent_failures"]:
        lines.append(f"Recent issues: {len(summary['recent_failures'])} failures")
        for f in summary["recent_failures"][:2]:
            lines.append(f"  - {f['tool']}: {f['need'][:50]}")
    
    if summary["last_session"]:
        last = summary["last_session"]
        lines.append(f"Last session: {last['tool_calls']} calls, {last['successes']} succeeded")
    
    return "\n".join(lines)


def get_tool_weight(tool_id: str) -> float:
    """Get learning weight for a tool (higher = more successful)."""
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT weight FROM tool_weights WHERE tool_id = ?", (tool_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else 1.0


def get_weighted_tool_ranking(tool_ids: list) -> list:
    """
    Rank tools by their learned weights.
    
    Returns tools sorted by success rate (highest first).
    """
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    ranked = []
    for tool_id in tool_ids:
        cursor.execute(
            "SELECT weight, total_uses, successes FROM tool_weights WHERE tool_id = ?",
            (tool_id,)
        )
        row = cursor.fetchone()
        
        if row:
            success_rate = row["successes"] / row["total_uses"] if row["total_uses"] > 0 else 0.5
            ranked.append({
                "tool_id": tool_id,
                "weight": row["weight"],
                "uses": row["total_uses"],
                "success_rate": success_rate
            })
        else:
            # New tool, neutral weight
            ranked.append({
                "tool_id": tool_id,
                "weight": 1.0,
                "uses": 0,
                "success_rate": 0.5
            })
    
    conn.close()
    
    # Sort by weight * success_rate (compound score)
    ranked.sort(key=lambda x: x["weight"] * x["success_rate"], reverse=True)
    return ranked


if __name__ == "__main__":
    # Test
    init_db()
    session = start_session()
    print(f"Started session: {session}")
    
    log_tool_use(session, "export_console", "export docx", success=True)
    log_tool_use(session, "memory_hub", "capture session", success=True)
    log_tool_use(session, "dli_router", "deep dive", success=False, notes="timeout")
    
    print(json.dumps(get_session_stats(session), indent=2))
    print(json.dumps(get_session_stats(), indent=2))
