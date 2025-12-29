#!/usr/bin/env python3
"""
Jh Brain Auto-Ingestion

Scans system registries and MCP configs to auto-discover tools.
Updates capability_map.json with new tools.

Run on startup or periodically.
"""

import json
from pathlib import Path
from datetime import datetime

# Paths
BASE_PATH = Path(__file__).parent.parent.parent.parent
CAPABILITY_MAP_PATH = BASE_PATH / "8825_core/brain/capability_map.json"
SYSTEM_REGISTRY_PATH = BASE_PATH / "8825_core/registry/SYSTEM_REGISTRY.json"
MCP_REGISTRY_PATH = BASE_PATH / "8825_core/system/mcp_registry.json"
MCP_SERVERS_DIR = BASE_PATH / "8825_core/mcp_servers"


def load_capability_map():
    """Load current capability map."""
    with open(CAPABILITY_MAP_PATH) as f:
        return json.load(f)


def save_capability_map(data):
    """Save updated capability map."""
    data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(CAPABILITY_MAP_PATH, "w") as f:
        json.dump(data, f, indent=2)


def scan_mcp_servers():
    """Scan MCP servers directory for new tools."""
    discovered = []
    
    if not MCP_SERVERS_DIR.exists():
        return discovered
    
    for server_dir in MCP_SERVERS_DIR.iterdir():
        if not server_dir.is_dir():
            continue
        
        # Look for server.py or *_mcp_server.py
        server_files = list(server_dir.glob("*server*.py"))
        if not server_files:
            continue
        
        tool_id = server_dir.name.replace("_", "-")
        
        # Check if already in capability map
        cap_map = load_capability_map()
        if tool_id in cap_map.get("tools", {}):
            continue
        
        discovered.append({
            "tool_id": tool_id,
            "name": server_dir.name.replace("_", " ").title(),
            "path": str(server_dir.relative_to(BASE_PATH)),
            "type": "mcp",
            "source": "auto_discovered"
        })
    
    return discovered


def scan_system_registry():
    """Scan SYSTEM_REGISTRY.json for services."""
    discovered = []
    
    if not SYSTEM_REGISTRY_PATH.exists():
        return discovered
    
    with open(SYSTEM_REGISTRY_PATH) as f:
        registry = json.load(f)
    
    cap_map = load_capability_map()
    existing_tools = cap_map.get("tools", {})
    
    # Look for services with ports (HTTP services)
    for script in registry.get("scripts", []):
        name = script.get("name", "")
        
        # Skip if already tracked
        tool_id = name.replace(".py", "").replace(".sh", "").replace("_", "-")
        if tool_id in existing_tools:
            continue
        
        # Only interested in services/daemons
        if script.get("type") not in ["service", "daemon", "server"]:
            continue
        
        discovered.append({
            "tool_id": tool_id,
            "name": name.replace("_", " ").title(),
            "path": script.get("path", ""),
            "type": "service",
            "source": "system_registry"
        })
    
    return discovered


def ingest_discovered_tools(tools: list, dry_run: bool = True):
    """Add discovered tools to capability map."""
    if not tools:
        print("No new tools discovered.")
        return
    
    cap_map = load_capability_map()
    
    for tool in tools:
        tool_id = tool["tool_id"]
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Adding tool: {tool_id}")
        
        if not dry_run:
            # Add to tools
            cap_map["tools"][tool_id] = {
                "name": tool["name"],
                "type": tool["type"],
                "path": tool["path"],
                "tier": 1,  # Default to tier 1 (not core)
                "auto_discovered": True
            }
            
            # Generate basic capability entry
            cap_id = tool_id.replace("-", "_")
            cap_map["capabilities"][cap_id] = {
                "keywords": tool_id.replace("-", " ").split(),
                "tool_id": tool_id,
                "description": f"Auto-discovered: {tool['name']}"
            }
    
    if not dry_run:
        save_capability_map(cap_map)
        print(f"✅ Added {len(tools)} tools to capability map")


def run_ingestion(dry_run: bool = True):
    """Run full ingestion scan."""
    print("🔍 Scanning for new tools...")
    
    # Scan sources
    mcp_tools = scan_mcp_servers()
    registry_tools = scan_system_registry()
    
    all_discovered = mcp_tools + registry_tools
    
    print(f"Found {len(all_discovered)} new tools")
    
    if all_discovered:
        ingest_discovered_tools(all_discovered, dry_run=dry_run)
    
    return all_discovered


if __name__ == "__main__":
    import sys
    
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("Running in DRY RUN mode. Use --execute to actually update.")
    
    run_ingestion(dry_run=dry_run)
