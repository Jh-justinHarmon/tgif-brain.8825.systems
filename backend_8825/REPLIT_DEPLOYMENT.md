# Maestra Backend - Replit Cloud Deployment

## Overview

Deploy Maestra Backend to Replit as cloud fallback when local backend is unavailable.

## Deployment Steps

### 1. Create Replit Project

```bash
# Create new Replit project
# Name: maestra-backend
# Language: Python
# Import from GitHub: (optional)
```

### 2. Setup Environment

**Create `.env` file in Replit:**
```
MAESTRA_MODE=cloud
MAESTRA_PORT=8000
MAESTRA_API_KEY=your_api_key_here
MAESTRA_RATE_LIMIT_REQUESTS=100
MAESTRA_RATE_LIMIT_WINDOW=60
CONVERSATION_HUB_ROOT=/tmp/conversations
```

### 3. Install Dependencies

**Replit `pyproject.toml`:**
```toml
[project]
name = "maestra-backend"
version = "2.0.0"
description = "Unified HTTP service for Maestra"
requires-python = ">=3.9"
dependencies = [
    "fastapi==0.104.1",
    "uvicorn==0.24.0",
    "pydantic==2.5.0",
    "python-dotenv==1.0.0",
    "slowapi==0.1.9",  # Rate limiting
]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

### 4. Deploy Code

**Copy to Replit:**
```
maestra_backend/
├── __init__.py
├── __main__.py
├── models.py
├── server.py
├── conversation_hub_client.py
└── requirements.txt
```

### 5. Configure Rate Limiting

**Update `server.py` for cloud deployment:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiting (cloud only)
if os.getenv("MAESTRA_MODE") == "cloud":
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    
    @app.post("/api/maestra/core")
    @limiter.limit("100/minute")
    async def maestra_core(request: Request, req: MaestraRequest) -> MaestraEnvelope:
        # ... existing code ...
```

### 6. Setup Replit Secrets

**In Replit Secrets panel:**
- `MAESTRA_API_KEY` - API key for authentication
- `CONVERSATION_HUB_ROOT` - Path for conversation storage

### 7. Configure DNS

**Point domain to Replit:**
```
maestra.replit.dev → Replit deployment URL
```

Or use Replit's default domain:
```
maestra.username.repl.co
```

### 8. Start Server

**Replit `.replit` file:**
```
run = "python -m maestra_backend --mode cloud --port 8000"
```

## API Key Authentication

### Request with API Key

```bash
curl -X POST https://maestra.replit.dev/api/maestra/core \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your_api_key_here' \
  -d '{
    "user_id": "justinharmon",
    "surface_id": "windsurf",
    "conversation_id": "conv_2025-12-28_jh_test",
    "message": "hello"
  }'
```

### Middleware for API Key Validation

```python
from fastapi import Header, HTTPException

@app.post("/api/maestra/core")
async def maestra_core(
    request: MaestraRequest,
    x_api_key: Optional[str] = Header(None)
) -> MaestraEnvelope:
    """
    Canonical Maestra endpoint.
    Requires API key for cloud deployment.
    """
    # Validate API key if in cloud mode
    if os.getenv("MAESTRA_MODE") == "cloud":
        expected_key = os.getenv("MAESTRA_API_KEY")
        if not x_api_key or x_api_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    # ... existing code ...
```

## Rate Limiting

### Configuration

```python
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# Get rate limit config from env
RATE_LIMIT_REQUESTS = int(os.getenv("MAESTRA_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("MAESTRA_RATE_LIMIT_WINDOW", "60"))

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/maestra/core")
@limiter.limit(f"{RATE_LIMIT_REQUESTS}/{RATE_LIMIT_WINDOW}s")
async def maestra_core(request: Request, req: MaestraRequest) -> MaestraEnvelope:
    # ... existing code ...
```

### Rate Limit Response

```json
{
  "detail": "429 Too Many Requests"
}
```

## Conversation Storage on Cloud

### Ephemeral Storage

By default, Replit provides ephemeral storage (cleared on restart).

**For persistent storage, use:**
1. Replit Database (built-in key-value store)
2. External database (PostgreSQL, MongoDB)
3. Cloud storage (S3, GCS)

### Replit Database Integration

```python
from replit import db

def save_conversation_to_db(conversation_id: str, conversation: Dict[str, Any]):
    """Save conversation to Replit Database"""
    db[f"conversation:{conversation_id}"] = json.dumps(conversation)

def load_conversation_from_db(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Load conversation from Replit Database"""
    data = db.get(f"conversation:{conversation_id}")
    if data:
        return json.loads(data)
    return None
```

## Health Check

```bash
curl https://maestra.replit.dev/health
```

Response:
```json
{
  "status": "healthy",
  "service": "maestra-backend",
  "version": "2.0.0",
  "brain_id": "maestra",
  "uptime_seconds": 1234,
  "port": 8000,
  "timestamp": "2025-12-28T15:00:00",
  "dependencies": {
    "jh_brain": "unknown",
    "memory_hub": "unknown",
    "conversation_hub": "unknown",
    "deep_research": "unknown"
  }
}
```

## Monitoring

### Replit Logs

View logs in Replit console:
```
[timestamp] [MaestraBackend] INFO - Request from windsurf: What should I...
[timestamp] [MaestraBackend] INFO - Created conversation: conv_2025-12-28_jh_abc12345
[timestamp] [MaestraBackend] INFO - Appended message to conv_2025-12-28_jh_abc12345
```

### Error Tracking

```python
import logging

logger = logging.getLogger('MaestraBackend')

# Log errors with context
logger.error(f"[MaestraCore] Error: {e}", exc_info=True)
```

## Fallback Configuration

### Local MCP Configuration

Update `conversation_hub_mcp` environment:

```json
{
  "mcpServers": {
    "conversation-hub-mcp": {
      "command": "python",
      "args": ["-m", "conversation_hub_mcp.server"],
      "env": {
        "MAESTRA_LOCAL_URL": "http://127.0.0.1:8825",
        "MAESTRA_CLOUD_URL": "https://maestra.replit.dev",
        "MAESTRA_FALLBACK_ENABLED": "true"
      }
    }
  }
}
```

## Testing Cloud Deployment

### 1. Health Check

```bash
curl https://maestra.replit.dev/health
```

### 2. Test with API Key

```bash
curl -X POST https://maestra.replit.dev/api/maestra/core \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: test_key' \
  -d '{
    "user_id": "jh",
    "surface_id": "test",
    "conversation_id": "conv_cloud_test",
    "message": "hello from cloud"
  }'
```

### 3. Test Rate Limiting

```bash
# Send 101 requests in 60 seconds
for i in {1..101}; do
  curl -X POST https://maestra.replit.dev/api/maestra/core \
    -H 'Content-Type: application/json' \
    -H 'X-API-Key: test_key' \
    -d '{"user_id":"jh","surface_id":"test","conversation_id":"conv_test","message":"test"}'
  sleep 0.5
done
# Request 101 should get 429 Too Many Requests
```

### 4. Test Fallback

```bash
# Stop local backend
launchctl stop com.8825.maestra

# Make request - should fallback to cloud
curl -X POST http://127.0.0.1:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"jh","surface_id":"test","conversation_id":"conv_test","message":"test"}'
# Should route to cloud backend

# Restart local backend
launchctl start com.8825.maestra
```

## Troubleshooting

### 503 Service Unavailable

- Check Replit project is running
- Check environment variables are set
- Check logs in Replit console

### 401 Unauthorized

- Verify API key is correct
- Check `X-API-Key` header is present
- Verify `MAESTRA_API_KEY` env var in Replit

### 429 Too Many Requests

- Rate limit exceeded
- Wait for rate limit window to reset
- Check `MAESTRA_RATE_LIMIT_REQUESTS` and `MAESTRA_RATE_LIMIT_WINDOW`

### Conversation Storage Issues

- Use Replit Database for persistent storage
- Check `/tmp/conversations/` permissions
- Verify `CONVERSATION_HUB_ROOT` env var

## Next Steps

1. **Sprint 6:** Security & Privacy - Cost guardrails, data residency policy
2. **Sprint 7:** Observability - /metrics endpoint, JSON logging, Slack alerts
3. **Sprint 8:** Testing - Smoke tests for local/cloud/mixed scenarios
4. **Sprint 9:** Formalization - Agent factory integration, generate protocol/README

## Files

- `pyproject.toml` - Replit project configuration
- `.env` - Environment variables (Replit Secrets)
- `.replit` - Replit run configuration
- `server.py` - Updated with API key auth and rate limiting
