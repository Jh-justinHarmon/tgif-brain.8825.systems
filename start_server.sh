#!/bin/bash
# Start Jh Brain MCP server

# Navigate to script directory
cd "$(dirname "$0")" || exit

# Initialize database
python3 seed_db.py

# Start FastAPI server
python3 server.py &

echo "Jh Brain MCP running at http://127.0.0.1:5060"
