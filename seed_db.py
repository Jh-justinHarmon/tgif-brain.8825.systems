#!/usr/bin/env python3
"""
Seed Jh Brain database from capability_map.json
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "jh_brain.db"
CAPABILITY_MAP_PATH = Path(__file__).parent.parent.parent / "brain/capability_map.json"

def init_tables(cursor):
    """Initialize database tables"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tools (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        path TEXT NOT NULL,
        kind TEXT NOT NULL,
        endpoints TEXT,
        protocol_doc TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS capabilities (
        id TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        tool_id TEXT NOT NULL,
        keywords TEXT NOT NULL,
        FOREIGN KEY(tool_id) REFERENCES tools(id)
    )
    """)

def seed_database():
    """Populate database from capability map"""
    with open(CAPABILITY_MAP_PATH) as f:
        data = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Initialize tables
    init_tables(cursor)
    
    # Clear existing data
    cursor.execute("DELETE FROM capabilities")
    cursor.execute("DELETE FROM tools")
    
    # Insert tools
    for tool_id, tool_info in data["tools"].items():
        cursor.execute(
            """
            INSERT INTO tools (id, name, path, kind, endpoints, protocol_doc)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                tool_id,
                tool_info["name"],
                tool_info.get("path", ""),
                tool_info["type"],
                json.dumps(tool_info.get("endpoints", {})),
                tool_info.get("protocol_doc", "")
            )
        )
    
    # Insert capabilities
    for cap_id, cap_info in data["capabilities"].items():
        cursor.execute(
            """
            INSERT INTO capabilities (id, description, tool_id, keywords)
            VALUES (?, ?, ?, ?)
            """,
            (
                cap_id,
                cap_info["description"],
                cap_info["tool_id"],
                json.dumps(cap_info["keywords"])
            )
        )
    
    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(data['tools'])} tools and {len(data['capabilities'])} capabilities")

if __name__ == "__main__":
    seed_database()
