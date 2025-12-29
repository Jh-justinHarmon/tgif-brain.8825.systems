# Maestra Backend v2.0.0

Unified HTTP service for Maestra across all surfaces (Windsurf, browser extension, CLI, mobile).

## Quick Start

### Installation (macOS)

```bash
cd 8825_core/maestra_backend
bash install_maestra_local.sh
```

This will:
- Create `~/.maestra` venv
- Install dependencies
- Register launchctl service
- Auto-start on login

### Manual Start

```bash
# Local mode (127.0.0.1, no CORS restrictions)
python -m maestra_backend --mode local --port 8825

# Cloud mode (0.0.0.0, CORS enabled)
python -m maestra_backend --mode cloud --port 8825
```

### Health Check

```bash
curl http://localhost:8825/health
```

Response:
```json
{
  "status": "healthy",
  "service": "8825 Backend - Quick Start Guide",
  "version": "2.0.0",
  "brain_id": "maestra",
  "uptime_seconds": 1234,
  "port": 8825,
  "timestamp": "2025-12-28T14:42:00",
  "dependencies": {
    "jh_brain": "unknown",
    "memory_hub": "unknown",
    "conversation_hub": "unknown",
    "deep_research": "unknown"
  }
}
```

## API

### Canonical Endpoint: POST /api/maestra/core

**Request:**
```json
{
  "user_id": "justinharmon",
  "surface_id": "windsurf",
  "conversation_id": "conv_2025-12-28_jh_test",
  "message": "What should I do next?",
  "mode_hint": "advisor",
  "surface_context": {
    "file_path": "/path/to/file.py",
    "workspace": "/path/to/workspace",
    "screen_context": null,
    "page_url": null,
    "selection": null
  }
}
```

**Response:**
```json
{
  "reply": "Based on your context, here's what I recommend...",
  "mode": "advisor",
  "conversation_id": "conv_2025-12-28_jh_test",
  "source": "local",
  "version": "2.0.0",
  "artifacts": [
    {
      "type": "knowledge",
      "id": "K-001",
      "title": "Relevant Knowledge",
      "confidence": 0.95
    }
  ],
  "actions": [],
  "meta": {
    "latency_ms": 234,
    "model": "gpt4o-mini",
    "tokens": 150,
    "cost_usd": 0.001
  }
}
```

### Legacy Endpoint: POST /api/maestra/advisor/ask

For backward compatibility with existing clients.

**Request:**
```json
{
  "session_id": "conv_2025-12-28_jh_test",
  "user_id": "justinharmon",
  "message": "What should I do next?",
  "mode": "quick",
  "context_hints": []
}
```

**Response:**
```json
{
  "answer": "Based on your context...",
  "session_id": "conv_2025-12-28_jh_test",
  "job_id": null,
  "sources": [],
  "trace_id": "conv_2025-12-28_jh_test",
  "mode": "quick",
  "processing_time_ms": 234
}
```

## Modes

- **advisor** - Quick answers and recommendations
- **tutorial** - Step-by-step teaching
- **router** - Decide which brain/tool to use
- **capture** - Extract learnings from sessions
- **project_conductor** - Multi-step project orchestration
- **web_companion** - Browser context assistance
- **focus_coach** - Focus context management (TGIF, RAL, LHL, 76)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Maestra Backend v2.0                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Surfaces:                                                   │
│  ├─ Windsurf MCP (conversation-hub-mcp)                    │
│  ├─ Browser Extension (HTTP)                               │
│  ├─ CLI (HTTP)                                             │
│  └─ Mobile (HTTP)                                          │
│                                                              │
│  ↓                                                           │
│                                                              │
│  FastAPI Server (localhost:8825 or 0.0.0.0:8825)           │
│  ├─ GET /health                                            │
│  ├─ POST /api/maestra/core (canonical)                     │
│  └─ POST /api/maestra/advisor/ask (legacy)                 │
│                                                              │
│  ↓                                                           │
│                                                              │
│  Maestra Core Orchestration                                │
│  ├─ Mode Selection                                         │
│  ├─ Tool/Brain Routing                                     │
│  ├─ Conversation Hub Logging                               │
│  └─ Response Envelope Creation                             │
│                                                              │
│  ↓                                                           │
│                                                              │
│  Integrations:                                              │
│  ├─ Conversation Hub (state persistence)                   │
│  ├─ Memory Hub (artifact linking)                          │
│  ├─ Jh Brain (knowledge)                                   │
│  ├─ Project Brains (TGIF, RAL, LHL, 76)                   │
│  └─ Deep Research MCP (research jobs)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Logs

**Location:** `~/Library/Logs/`

- `maestra_backend.log` - Standard output
- `maestra_backend_error.log` - Error output

**View logs:**
```bash
tail -f ~/Library/Logs/maestra_backend.log
```

## Troubleshooting

### Service not starting

```bash
# Check if service is loaded
launchctl list | grep maestra

# Check logs
tail -f ~/Library/Logs/maestra_backend.log

# Manually start for debugging
python -m maestra_backend --mode local --port 8825
```

### Port already in use

The installer automatically falls back to ports 8826-8829 if 8825 is occupied.

Check which port is being used:
```bash
cat ~/.maestra/port
```

### Dependencies missing

Reinstall dependencies:
```bash
~/.maestra/venv/bin/pip install -r 8825_core/maestra_backend/requirements.txt
```

## Management

### Restart service

```bash
launchctl stop com.8825.maestra
launchctl start com.8825.maestra
```

### View status

```bash
launchctl list | grep maestra
```

### Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.8825.maestra.plist
rm -rf ~/.maestra
```

## Development

### Local development (with hot reload)

```bash
cd 8825_core/maestra_backend
pip install -r requirements.txt
python -m maestra_backend --mode local --port 8825
```

### Testing

```bash
# Health check
curl http://localhost:8825/health

# Test canonical endpoint
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "jh",
    "surface_id": "test",
    "conversation_id": "test_conv",
    "message": "hello"
  }'

# Test legacy endpoint
curl -X POST http://localhost:8825/api/maestra/advisor/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "test_session",
    "user_id": "jh",
    "message": "hello"
  }'
```

## Next Steps

1. **Sprint 3:** MCP Hardening - Simplify conversation-hub-mcp proxy
2. **Sprint 4:** State Spine - Wire Conversation Hub integration
3. **Sprint 5:** Cloud Deploy - Deploy to Replit
4. **Sprint 6-9:** Security, observability, testing, formalization
