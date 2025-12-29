# TGIF Brain Replit Setup

**Status:** Consolidated into Maestra Backend  
**Date:** 2025-12-28  
**Port:** 8000 (cloud mode)

## Problem Solved

TGIF brain was running as a separate stale MCP server on Replit (port 3080), causing "nothing happens" when trying to use it.

**Solution:** Consolidate TGIF brain into the unified Maestra Backend on port 8000 (cloud mode).

## Setup Instructions

### Step 1: Update Replit `.replit` File

Replace the current `.replit` in the TGIF brain Replit project with:

```
run = "python -m maestra_backend --mode cloud --port 8000"
language = "python3"
modules = ["python-3.10"]
```

This runs the Maestra Backend in cloud mode on port 8000.

### Step 2: Set Environment Variables

In Replit Secrets panel, set:

```
MAESTRA_MODE=cloud
MAESTRA_PORT=8000
MAESTRA_API_KEY=<your_api_key>
MAESTRA_RATE_LIMIT_REQUESTS=100
MAESTRA_RATE_LIMIT_WINDOW=60
```

### Step 3: Copy Maestra Backend Code

Copy the entire `8825_core/maestra_backend/` directory to the Replit project root.

### Step 4: Restart Replit

Click "Run" button or restart the project.

### Step 5: Verify

Test the endpoints:

```bash
# Health check
curl https://your-replit-url/health

# TGIF brain endpoint
curl -X POST https://your-replit-url/tgif/ask \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $MAESTRA_API_KEY" \
  -d '{
    "user_id": "test",
    "surface_id": "tgif_brain",
    "conversation_id": "conv_tgif_test",
    "message": "Hello TGIF brain"
  }'

# TGIF health check
curl https://your-replit-url/tgif/health
```

## TGIF Brain Endpoints

All endpoints are now on the unified Maestra Backend:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |
| `/tgif/ask` | POST | TGIF brain query |
| `/tgif/health` | GET | TGIF-specific health check |
| `/api/maestra/core` | POST | Canonical endpoint (with mode_hint="focus_coach") |

## Request Format

### TGIF Brain Request

```json
{
  "user_id": "justinharmon",
  "surface_id": "tgif_brain",
  "conversation_id": "conv_tgif_123",
  "message": "What should we focus on this week?",
  "mode_hint": "focus_coach"
}
```

### Response

```json
{
  "reply": "Based on TGIF context...",
  "mode": "focus_coach",
  "conversation_id": "conv_tgif_123",
  "source": "cloud",
  "version": "2.0.0",
  "artifacts": [],
  "actions": [],
  "meta": {
    "latency_ms": 45,
    "model": "placeholder",
    "tokens": 0,
    "cost_usd": 0.0
  }
}
```

## Architecture

```
TGIF Brain (Replit)
    ↓
Maestra Backend (port 8000, cloud mode)
    ├─ /tgif/ask (routes to focus_coach mode)
    ├─ /tgif/health
    ├─ /api/maestra/core (canonical)
    ├─ /health
    └─ /metrics
```

## Migration from Old MCP Server

**Old Architecture:**
- Separate brain MCP server on port 3080 (stale, unresponsive)
- No integration with Maestra Backend
- No conversation persistence

**New Architecture:**
- Single unified Maestra Backend on port 8000
- TGIF requests routed through `/tgif/ask`
- Conversations persisted in Conversation Hub
- Cross-surface continuity

## Troubleshooting

### "Nothing happens" when calling TGIF brain

1. Check if Maestra Backend is running:
   ```bash
   curl https://your-replit-url/health
   ```

2. Check logs in Replit Console

3. Verify API key is set in Secrets

4. Test TGIF health endpoint:
   ```bash
   curl https://your-replit-url/tgif/health
   ```

### Port 8000 already in use

1. Restart Replit project
2. Check for zombie processes: `pkill -f maestra_backend`
3. Check logs for startup errors

### API key errors

1. Verify `MAESTRA_API_KEY` is set in Secrets
2. Include header: `X-API-Key: <your_key>`
3. Check rate limiting: `MAESTRA_RATE_LIMIT_REQUESTS=100`

## Files

- `8825_core/maestra_backend/` - Unified backend (copy to Replit)
- `8825_core/maestra_backend/tgif_brain_integration.py` - Integration helpers
- `8825_core/maestra_backend/.replit` - Replit configuration
- `8825_core/maestra_backend/server.py` - Contains `/tgif/ask` endpoint

## Next Steps

1. Update Replit `.replit` file
2. Set environment variables
3. Copy Maestra Backend code
4. Restart Replit
5. Test endpoints
6. Monitor logs for errors

---

**Status:** Ready for deployment  
**Consolidated:** Yes (into Maestra Backend)  
**Port:** 8000 (cloud mode)  
**Last Updated:** 2025-12-28
