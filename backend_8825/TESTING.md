# Maestra Backend - Testing Guide

## Overview

Comprehensive testing for Maestra Backend across local, cloud, and mixed deployment scenarios.

## Running Smoke Tests

### Prerequisites

```bash
# Install test dependencies
pip install httpx pytest pytest-asyncio

# Set environment variables (optional for cloud tests)
export MAESTRA_CLOUD_URL=https://maestra.replit.dev
export MAESTRA_API_KEY=your_api_key_here
```

### Run All Tests

```bash
cd 8825_core/maestra_backend
python test_smoke.py
```

### Run Specific Test

```bash
# Local backend only
python -c "
import asyncio
from test_smoke import test_local_backend
asyncio.run(test_local_backend())
"

# Cloud backend only
python -c "
import asyncio
from test_smoke import test_cloud_backend
asyncio.run(test_cloud_backend())
"

# Mixed scenario
python -c "
import asyncio
from test_smoke import test_mixed_scenario
asyncio.run(test_mixed_scenario())
"

# Rate limiting
python -c "
import asyncio
from test_smoke import test_rate_limiting
asyncio.run(test_rate_limiting())
"
```

## Test Scenarios

### 1. Local Backend Tests

**What it tests:**
- Health check endpoint
- Metrics endpoint
- Canonical `/api/maestra/core` endpoint
- Legacy `/api/maestra/advisor/ask` endpoint
- Cross-surface continuity

**Prerequisites:**
- Local backend running: `python -m maestra_backend --mode local --port 8825`

**Expected results:**
- All endpoints respond with 200 status
- Conversation is created and stored
- Messages logged to Conversation Hub
- Metrics tracked

### 2. Cloud Backend Tests

**What it tests:**
- Health check endpoint
- Metrics endpoint
- API key authentication
- Canonical endpoint with API key
- Invalid API key rejection

**Prerequisites:**
- Cloud backend deployed to Replit
- `MAESTRA_API_KEY` environment variable set
- `MAESTRA_CLOUD_URL` environment variable set

**Expected results:**
- All endpoints respond with 200 status
- Valid API key accepted
- Invalid API key rejected with 401
- Metrics tracked

### 3. Mixed Scenario Tests

**What it tests:**
- Local backend availability
- Cloud backend availability (if configured)
- Conversation continuity across surfaces
- Conversation storage and retrieval

**Prerequisites:**
- Local backend running
- Cloud backend available (optional)
- Conversation Hub storage working

**Expected results:**
- Messages from multiple surfaces stored in same conversation
- Conversation file contains all messages
- Surfaces list includes all participating surfaces

### 4. Rate Limiting Tests

**What it tests:**
- Rate limit enforcement on cloud
- Rate limit headers in responses
- 429 Too Many Requests response

**Prerequisites:**
- Cloud backend deployed
- Rate limiting enabled
- `MAESTRA_API_KEY` set

**Expected results:**
- Requests within limit accepted
- Requests exceeding limit rejected with 429
- Rate limit headers present in responses

## Manual Testing

### Test Health Check

```bash
# Local
curl http://localhost:8825/health

# Cloud
curl https://maestra.replit.dev/health
```

### Test Metrics

```bash
# Local
curl http://localhost:8825/metrics

# Cloud
curl -H "X-API-Key: $MAESTRA_API_KEY" https://maestra.replit.dev/metrics
```

### Test Canonical Endpoint

```bash
# Local (no API key required)
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user",
    "surface_id": "windsurf",
    "conversation_id": "conv_test_123",
    "message": "Hello from local"
  }'

# Cloud (API key required)
curl -X POST https://maestra.replit.dev/api/maestra/core \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $MAESTRA_API_KEY" \
  -d '{
    "user_id": "test_user",
    "surface_id": "windsurf",
    "conversation_id": "conv_test_123",
    "message": "Hello from cloud"
  }'
```

### Test Legacy Endpoint

```bash
curl -X POST http://localhost:8825/api/maestra/advisor/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "conv_test_123",
    "user_id": "test_user",
    "message": "Hello from legacy"
  }'
```

### Test Cross-Surface Continuity

```bash
# Message 1: Windsurf
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user",
    "surface_id": "windsurf",
    "conversation_id": "conv_continuity_test",
    "message": "Message from Windsurf"
  }'

# Message 2: Browser Extension (same conversation_id)
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test_user",
    "surface_id": "browser_ext",
    "conversation_id": "conv_continuity_test",
    "message": "Message from Browser"
  }'

# Verify conversation
cat ~/.8825/conversations/conv_continuity_test.json | jq '.surfaces'
# Should output: ["windsurf", "browser_ext"]
```

### Test Rate Limiting

```bash
# Send requests rapidly to trigger rate limit
for i in {1..101}; do
  curl -X POST https://maestra.replit.dev/api/maestra/core \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: $MAESTRA_API_KEY" \
    -d '{"user_id":"test","surface_id":"test","conversation_id":"conv_test","message":"test"}' \
    -w "\nStatus: %{http_code}\n"
  sleep 0.5
done
# Request 101 should get 429 Too Many Requests
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Maestra Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r 8825_core/maestra_backend/requirements.txt
          pip install httpx pytest pytest-asyncio
      
      - name: Start local backend
        run: |
          python -m maestra_backend --mode local --port 8825 &
          sleep 2
      
      - name: Run smoke tests
        run: |
          cd 8825_core/maestra_backend
          python test_smoke.py
```

## Performance Testing

### Load Test

```bash
# Install locust
pip install locust

# Create locustfile.py
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between
import json

class MaestraUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def ask_maestra(self):
        payload = {
            "user_id": "load_test_user",
            "surface_id": "test",
            "conversation_id": "conv_load_test",
            "message": "Hello"
        }
        self.client.post("/api/maestra/core", json=payload)
    
    @task
    def check_health(self):
        self.client.get("/health")
EOF

# Run load test
locust -f locustfile.py -u 10 -r 2 -t 60s --headless -H http://localhost:8825
```

## Troubleshooting

### Tests Failing

1. **Local backend not responding**
   ```bash
   # Check if backend is running
   curl http://localhost:8825/health
   
   # If not running, start it
   python -m maestra_backend --mode local --port 8825
   ```

2. **Cloud backend not responding**
   ```bash
   # Check API key
   echo $MAESTRA_API_KEY
   
   # Check cloud URL
   echo $MAESTRA_CLOUD_URL
   
   # Test connectivity
   curl $MAESTRA_CLOUD_URL/health
   ```

3. **Conversation storage issues**
   ```bash
   # Check storage directory
   ls -la ~/.8825/conversations/
   
   # Check permissions
   chmod 700 ~/.8825/conversations/
   chmod 600 ~/.8825/conversations/*.json
   ```

4. **Rate limiting not working**
   ```bash
   # Check rate limit config
   echo $MAESTRA_RATE_LIMIT_REQUESTS
   echo $MAESTRA_RATE_LIMIT_WINDOW
   
   # Check Replit logs for slowapi errors
   ```

## Test Coverage

| Component | Test | Status |
|-----------|------|--------|
| Health endpoint | ✅ | Covered |
| Metrics endpoint | ✅ | Covered |
| Canonical endpoint | ✅ | Covered |
| Legacy endpoint | ✅ | Covered |
| API key auth | ✅ | Covered |
| Rate limiting | ✅ | Covered |
| Conversation storage | ✅ | Covered |
| Cross-surface continuity | ✅ | Covered |
| Error handling | ⚠️ | Partial |
| Performance | ⚠️ | Manual only |

## Next Steps

1. **Sprint 9:** Formalization - Agent factory integration, generate protocol/README/runbook
2. **Checkpoint:** Validate Maestra works across all surfaces with auto-start and cloud fallback

## Files

- `test_smoke.py` - Smoke test suite
- `TESTING.md` - This document

## Status

✅ **Sprint 8 Complete**
- Smoke tests implemented (local, cloud, mixed, rate limiting)
- Manual testing procedures documented
- CI/CD examples provided
- Load testing guide included
- Ready for Sprint 9 (Formalization)
