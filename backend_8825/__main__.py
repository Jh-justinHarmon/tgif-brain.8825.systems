"""
8825 Backend - Entrypoint
Run as: python -m backend_8825 [--local|--cloud] [--port PORT]
"""

import argparse
import sys
import os
import uvicorn
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend_8825.server import app


def run_local(port: int = 8825):
    """Run local Maestra backend (no CORS restrictions for local use)"""
    print(f"🚀 Starting Maestra Backend (LOCAL) on http://localhost:{port}")
    print(f"   Canonical endpoint: POST http://localhost:{port}/api/maestra/core")
    print(f"   Health check: GET http://localhost:{port}/health")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info"
    )


def run_cloud(port: int = 8825):
    """Run cloud Maestra backend (CORS enabled for cross-origin)"""
    print(f"🚀 Starting Maestra Backend (CLOUD) on 0.0.0.0:{port}")
    print(f"   Canonical endpoint: POST http://0.0.0.0:{port}/api/maestra/core")
    print(f"   Health check: GET http://0.0.0.0:{port}/health")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Maestra Backend - Unified HTTP service for all surfaces"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="Run mode: local (127.0.0.1) or cloud (0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8825,
        help="Port to listen on (default: 8825)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "local":
        run_local(args.port)
    else:
        run_cloud(args.port)


if __name__ == "__main__":
    main()
