# Maestra Backend - Deployment & Broadcast Guide

**Status:** Production Ready  
**Version:** 2.0.0  
**Date:** 2025-12-28

## Quick Start

### Local Deployment (macOS)

```bash
cd 8825_core/maestra_backend
bash install_maestra_local.sh
```

**What happens:**
1. Creates ~/.maestra venv
2. Installs dependencies
3. Generates launchctl plist
4. Registers auto-start service
5. Detects available port (8825-8829)

**Verify:**
```bash
curl http://localhost:8825/health
# Should return: {"status": "healthy", "version": "2.0.0", ...}
```

### Cloud Deployment (Replit)

1. Create Replit project: `maestra-backend`
2. Set environment variables (Secrets panel):
   ```
   MAESTRA_MODE=cloud
   MAESTRA_PORT=8000
   MAESTRA_API_KEY=sk_your_key_here
   MAESTRA_RATE_LIMIT_REQUESTS=100
   MAESTRA_RATE_LIMIT_WINDOW=60
   ```
3. Deploy code from `8825_core/maestra_backend/`
4. Test: `curl -H "X-API-Key: $MAESTRA_API_KEY" https://maestra.replit.dev/health`

## Deployment Checklist

### Pre-Deployment

- [ ] All tests pass: `python test_smoke.py`
- [ ] Dependencies locked: `requirements.txt` updated
- [ ] Documentation reviewed: README.md, PROTOCOL.md
- [ ] Security settings configured: API keys, rate limits
- [ ] Conversation Hub storage ready: `~/.8825/conversations/`

### Local Deployment

- [ ] Run install script
- [ ] Verify launchctl registration
- [ ] Test health endpoint
- [ ] Test canonical endpoint
- [ ] Check conversation storage
- [ ] Verify auto-start (restart and check)

### Cloud Deployment

- [ ] Create Replit project
- [ ] Set environment variables
- [ ] Deploy code
- [ ] Configure DNS (optional)
- [ ] Test with API key
- [ ] Verify rate limiting
- [ ] Test fallback from local

### MCP Integration

- [ ] Register conversation-hub-mcp in Windsurf
- [ ] Configure environment variables
- [ ] Test maestra_ask tool
- [ ] Test maestra_health tool
- [ ] Test maestra_legacy_ask tool

## Broadcast Materials

### Team Announcement

**Subject:** Maestra Backend v2.0.0 - Production Ready

**Message:**

Maestra Backend is now production-ready as a unified HTTP service for all surfaces (Windsurf, browser extension, CLI, mobile).

**Key Features:**
- Single canonical `/api/maestra/core` endpoint
- Auto-start on login (macOS launchctl)
- Durable conversation state persistence
- Cross-surface continuity (Windsurf → Browser → CLI)
- Cloud fallback (Replit) with API key auth
- Rate limiting (100 req/60s)
- Comprehensive observability (/metrics, JSON logging)

**Getting Started:**

1. **Local Backend** (recommended for development):
   ```bash
   bash 8825_core/maestra_backend/install_maestra_local.sh
   ```

2. **Cloud Backend** (optional fallback):
   - Create Replit project
   - Set environment variables
   - Deploy code

3. **Documentation:**
   - `8825_core/protocols/MAESTRA_BACKEND_PROTOCOL.md` - Formal protocol
   - `8825_core/maestra_backend/README.md` - Quick start
   - `8825_core/maestra_backend/TESTING.md` - Testing guide

**Integration Points:**
- Windsurf: Via conversation-hub-mcp
- Browser Extension: Direct HTTP to localhost:8825
- CLI: Python requests to localhost:8825
- Mobile: Via cloud fallback (Replit)

**Questions?** See MAESTRA_BACKEND_PROTOCOL.md or TESTING.md

---

### Protocol Document

**Location:** `8825_core/protocols/MAESTRA_BACKEND_PROTOCOL.md`

**Contents:**
- Architecture overview
- Canonical endpoint specification
- Deployment modes (local, cloud)
- Installation & setup
- Key features
- Operational procedures
- Integration points
- Maintenance schedule
- Success metrics

### Documentation Index

| Document | Purpose |
|----------|---------|
| `README.md` | Quick start & overview |
| `MAESTRA_BACKEND_PROTOCOL.md` | Formal Tier-0 protocol |
| `CONVERSATION_HUB_INTEGRATION.md` | State persistence details |
| `REPLIT_DEPLOYMENT.md` | Cloud deployment guide |
| `SECURITY_PRIVACY.md` | Security & privacy controls |
| `OBSERVABILITY.md` | Metrics & monitoring |
| `TESTING.md` | Testing procedures |
| `CHECKPOINT_VALIDATION.md` | Validation checklist |
| `DEPLOYMENT_GUIDE.md` | This document |

## Integration Instructions

### Windsurf MCP Registration

**File:** `mcp_config.json` (in Windsurf settings)

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

**Tools available:**
- `maestra_ask` - Ask Maestra a question
- `maestra_health` - Check backend health
- `maestra_legacy_ask` - Legacy advisor endpoint

### Browser Extension Integration

**Endpoint:** `http://localhost:8825/api/maestra/core`

**Example:**
```javascript
const response = await fetch('http://localhost:8825/api/maestra/core', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'justinharmon',
    surface_id: 'browser_ext',
    conversation_id: 'conv_...',
    message: 'Hello'
  })
});
```

### CLI Integration

**Endpoint:** `http://localhost:8825/api/maestra/core`

**Example:**
```python
import requests

response = requests.post('http://localhost:8825/api/maestra/core', json={
    'user_id': 'justinharmon',
    'surface_id': 'cli',
    'conversation_id': 'conv_...',
    'message': 'Hello'
})
print(response.json()['reply'])
```

## Monitoring & Maintenance

### Daily Checks

```bash
# Health check
curl http://localhost:8825/health

# Metrics
curl http://localhost:8825/metrics

# Logs
tail -f ~/Library/Logs/maestra_backend.log
```

### Weekly Tasks

- Review error logs
- Check conversation count: `ls ~/.8825/conversations/ | wc -l`
- Monitor cost tracking: `cat ~/.8825/maestra_metrics.jsonl | jq '.cost_usd' | awk '{sum+=$1} END {print sum}'`

### Monthly Tasks

- Rotate API keys
- Review rate limit violations
- Audit security settings
- Update dependencies

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
tail -f ~/Library/Logs/maestra_backend.log

# Check port
lsof -i :8825

# Restart
launchctl stop com.8825.maestra
launchctl start com.8825.maestra
```

### Health Check Fails

```bash
# Check if service is running
launchctl list | grep maestra

# Check port
netstat -an | grep 8825

# Check logs
tail -f ~/Library/Logs/maestra_backend_error.log
```

### Conversation Storage Issues

```bash
# Check directory
ls -la ~/.8825/conversations/

# Fix permissions
chmod 700 ~/.8825/conversations/
chmod 600 ~/.8825/conversations/*.json
```

### Cloud Fallback Not Working

```bash
# Check cloud URL
echo $MAESTRA_CLOUD_URL

# Check API key
echo $MAESTRA_API_KEY

# Test connectivity
curl $MAESTRA_CLOUD_URL/health
```

## Success Metrics

**Availability:**
- Local backend uptime > 99.9%
- Cloud fallback latency < 2s
- Health check response time < 100ms

**Performance:**
- Average latency < 500ms
- P95 latency < 1000ms
- Error rate < 1%

**Reliability:**
- Conversation persistence 100%
- Cross-surface continuity 100%
- Auto-start success rate 100%

## Support

**Questions?**
1. Check `MAESTRA_BACKEND_PROTOCOL.md` for architecture
2. Check `TESTING.md` for testing procedures
3. Check `TROUBLESHOOTING` section above
4. Review logs: `~/Library/Logs/maestra_backend.log`

**Issues?**
1. Run smoke tests: `python test_smoke.py`
2. Check metrics: `curl http://localhost:8825/metrics`
3. Review conversation storage: `ls ~/.8825/conversations/`

## Files & Locations

**Backend:**
- `8825_core/maestra_backend/` - Main package
- `~/.maestra/` - Local venv & config
- `~/.8825/conversations/` - Conversation storage
- `~/Library/Logs/maestra_backend.log` - Logs

**Cloud:**
- Replit project: `maestra-backend`
- Cloud URL: `https://maestra.replit.dev`

**Documentation:**
- Protocol: `8825_core/protocols/MAESTRA_BACKEND_PROTOCOL.md`
- README: `8825_core/maestra_backend/README.md`
- All docs: See Documentation Index above

## Status

✅ **Production Ready**
- All 9 sprints completed
- Full test coverage
- Comprehensive documentation
- Ready for immediate deployment

**Next Steps:**
1. Deploy local backend
2. Deploy cloud backend (optional)
3. Register MCP in Windsurf
4. Validate cross-surface integration
5. Broadcast to team
