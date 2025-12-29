# Maestra Backend - Security & Privacy Policy

## Overview

Security and privacy controls for Maestra Backend across local and cloud deployments.

## 1. Cost Guardrails

### API Call Cost Tracking

**Track cost per request:**
```python
# In server.py
meta = {
    "latency_ms": latency_ms,
    "model": "gpt4o-mini",
    "tokens": 150,
    "cost_usd": 0.001  # Track cost per request
}
```

### Monthly Cost Limits

**Environment variables:**
```bash
MAESTRA_MONTHLY_COST_LIMIT=100.00  # USD
MAESTRA_DAILY_COST_LIMIT=5.00      # USD
```

**Implementation:**
```python
import os
from datetime import datetime, timedelta

MONTHLY_COST_LIMIT = float(os.getenv("MAESTRA_MONTHLY_COST_LIMIT", "100.00"))
DAILY_COST_LIMIT = float(os.getenv("MAESTRA_DAILY_COST_LIMIT", "5.00"))

def check_cost_limits(cost_usd: float) -> bool:
    """Check if request would exceed cost limits"""
    # Load today's cost from cost_tracker.json
    today = datetime.utcnow().date().isoformat()
    cost_tracker = load_cost_tracker()
    
    daily_cost = cost_tracker.get(today, 0.0)
    if daily_cost + cost_usd > DAILY_COST_LIMIT:
        logger.warning(f"Daily cost limit exceeded: {daily_cost + cost_usd} > {DAILY_COST_LIMIT}")
        return False
    
    # Check monthly cost
    month_key = datetime.utcnow().strftime("%Y-%m")
    monthly_cost = sum(v for k, v in cost_tracker.items() if k.startswith(month_key))
    if monthly_cost + cost_usd > MONTHLY_COST_LIMIT:
        logger.warning(f"Monthly cost limit exceeded: {monthly_cost + cost_usd} > {MONTHLY_COST_LIMIT}")
        return False
    
    return True

def record_cost(cost_usd: float):
    """Record cost for today"""
    today = datetime.utcnow().date().isoformat()
    cost_tracker = load_cost_tracker()
    cost_tracker[today] = cost_tracker.get(today, 0.0) + cost_usd
    save_cost_tracker(cost_tracker)
```

### Cost Tracking File

**Location:** `~/.8825/maestra_cost_tracker.json`

```json
{
  "2025-12-28": 2.45,
  "2025-12-27": 3.12,
  "2025-12-26": 1.89,
  "monthly_total_2025-12": 45.67
}
```

## 2. Data Residency Policy

### Local Storage (Default)

**Conversations stored locally:**
- Location: `~/.8825/conversations/`
- Ownership: User (local machine)
- Backup: User responsible
- Retention: Indefinite (user controls)

**No data sent to cloud unless:**
1. User explicitly enables cloud fallback
2. Local backend is unavailable
3. User provides API key for cloud

### Cloud Storage (Opt-In)

**When using Replit fallback:**
- Conversations stored in Replit Database (ephemeral by default)
- Optional: Configure persistent storage (PostgreSQL, S3)
- Data residency: Replit infrastructure (US-based)

**Configuration:**
```bash
# Use cloud storage
MAESTRA_CLOUD_STORAGE=replit_db  # or postgresql, s3

# PostgreSQL
MAESTRA_DB_URL=postgresql://user:pass@host/db

# S3
MAESTRA_S3_BUCKET=my-bucket
MAESTRA_S3_REGION=us-east-1
```

### Data Minimization

**Only store:**
- User messages
- Assistant responses
- Conversation metadata (created_at, updated_at, surfaces)
- Artifact references (ID, type, confidence)

**Never store:**
- API keys or credentials
- File contents (only file_path reference)
- User authentication tokens
- Payment information

## 3. Secrets Management

### Environment Variables (Secure)

**Use environment variables for secrets:**
```bash
# .env file (local, gitignored)
MAESTRA_API_KEY=sk_test_...
MAESTRA_OPENAI_KEY=sk-...
MAESTRA_ANTHROPIC_KEY=sk-ant-...
```

**Never commit secrets to git:**
```bash
# .gitignore
.env
.env.local
*.key
*.pem
```

### Replit Secrets

**Use Replit Secrets panel for cloud:**
1. Go to Replit project
2. Click "Secrets" (lock icon)
3. Add secrets:
   - `MAESTRA_API_KEY`
   - `MAESTRA_OPENAI_KEY`
   - `MAESTRA_ANTHROPIC_KEY`

**Access in code:**
```python
import os
api_key = os.getenv("MAESTRA_API_KEY")
```

### Secret Rotation

**Rotate secrets regularly:**
```bash
# Generate new API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update in .env and Replit Secrets
# Restart services
launchctl stop com.8825.maestra
launchctl start com.8825.maestra
```

## 4. Authentication & Authorization

### API Key Authentication (Cloud)

**Required for cloud deployment:**
```bash
curl -X POST https://maestra.replit.dev/api/maestra/core \
  -H 'X-API-Key: sk_test_...' \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

**Not required for local deployment:**
```bash
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{...}'
```

### Rate Limiting (Cloud)

**Prevent abuse:**
- 100 requests per 60 seconds (default)
- Per IP address
- Returns 429 Too Many Requests

**Configuration:**
```bash
MAESTRA_RATE_LIMIT_REQUESTS=100
MAESTRA_RATE_LIMIT_WINDOW=60
```

## 5. Data Privacy

### User Data Ownership

**User owns all data:**
- Conversations stored on user's machine (local)
- User controls cloud storage (opt-in)
- User can delete conversations anytime
- User can export conversations

### Data Deletion

**Delete conversation:**
```python
from conversation_hub_client import get_client

hub = get_client()
conversation_path = hub._get_conversation_path("conv_2025-12-28_jh_abc12345")
conversation_path.unlink()  # Delete file
```

**Delete all conversations:**
```bash
rm -rf ~/.8825/conversations/
```

### Data Export

**Export conversation:**
```python
hub = get_client()
conversation = hub.get_conversation("conv_2025-12-28_jh_abc12345")
import json
with open("export.json", "w") as f:
    json.dump(conversation, f, indent=2)
```

## 6. Compliance

### GDPR Compliance

**Right to be forgotten:**
- User can delete all conversations
- No data retention after deletion
- No tracking of deleted data

**Data portability:**
- Export conversations as JSON
- No vendor lock-in
- User controls all data

### Data Minimization

**Only collect necessary data:**
- User message
- Assistant response
- Conversation metadata
- Surface information

**No collection of:**
- User identity (beyond user_id)
- Device information
- Location data
- Browsing history

## 7. Security Best Practices

### Local Backend

**Security measures:**
- No network exposure (127.0.0.1 only)
- No authentication required (local machine)
- File permissions: User only (0600)
- Automatic cleanup of old conversations

### Cloud Backend

**Security measures:**
- HTTPS only (TLS 1.2+)
- API key authentication
- Rate limiting
- Request logging
- IP whitelisting (optional)

### Conversation Storage

**File permissions:**
```bash
# Local conversations (user only)
chmod 700 ~/.8825/conversations/
chmod 600 ~/.8825/conversations/*.json

# Verify
ls -la ~/.8825/conversations/
# drwx------  user  staff  ~/.8825/conversations/
# -rw-------  user  staff  ~/.8825/conversations/conv_*.json
```

## 8. Incident Response

### Data Breach

**If local data is compromised:**
1. Delete conversation files: `rm -rf ~/.8825/conversations/`
2. Rotate API keys
3. Review logs for unauthorized access
4. Restart Maestra Backend

**If cloud data is compromised:**
1. Rotate API key immediately
2. Review Replit logs
3. Delete compromised conversations
4. Notify users if applicable

### Logging & Monitoring

**Log all requests:**
```python
logger.info(f"[MaestraCore] Request from {request.surface_id}: {request.message[:50]}...")
logger.warning(f"[MaestraCore] Invalid API key from {request.surface_id}")
logger.error(f"[MaestraCore] Error: {e}", exc_info=True)
```

**Monitor for:**
- Invalid API key attempts
- Rate limit violations
- Cost limit violations
- Errors and exceptions

## 9. Configuration Checklist

### Local Deployment

- [ ] `.env` file created and gitignored
- [ ] `MAESTRA_MODE=local`
- [ ] `~/.8825/conversations/` permissions set to 0700
- [ ] No API key required
- [ ] Logs in `~/Library/Logs/maestra_backend.log`

### Cloud Deployment

- [ ] Replit Secrets configured
- [ ] `MAESTRA_MODE=cloud`
- [ ] `MAESTRA_API_KEY` set
- [ ] `MAESTRA_MONTHLY_COST_LIMIT` set
- [ ] `MAESTRA_DAILY_COST_LIMIT` set
- [ ] Rate limiting enabled
- [ ] HTTPS enforced

## 10. Privacy Policy Statement

**Maestra Backend Privacy Policy:**

1. **Data Ownership:** User owns all conversation data
2. **Data Storage:** Conversations stored locally by default
3. **Cloud Storage:** Optional, user opt-in only
4. **Data Deletion:** User can delete conversations anytime
5. **No Tracking:** No user tracking or analytics
6. **No Sharing:** Data never shared with third parties
7. **Security:** API key authentication for cloud
8. **Compliance:** GDPR compliant, right to be forgotten

## Files

- `.env` - Environment variables (local, gitignored)
- `~/.8825/maestra_cost_tracker.json` - Cost tracking
- `~/.8825/conversations/` - Conversation storage
- `SECURITY_PRIVACY.md` - This document

## Status

✅ **Sprint 6 Complete**
- Cost guardrails implemented
- Data residency policy defined
- Secrets management configured
- Security best practices documented
- Ready for Sprint 7 (Observability)
