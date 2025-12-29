# Maestra Backend - Observability

## Overview

Comprehensive observability for Maestra Backend with metrics, JSON logging, and Slack alerts.

## 1. Metrics Endpoint

### GET /metrics

Returns system-level metrics for monitoring and observability.

**Response:**
```json
{
  "timestamp": "2025-12-28T15:30:00Z",
  "uptime_seconds": 3600,
  "total_requests": 1234,
  "total_errors": 5,
  "avg_latency_ms": 245,
  "total_cost_usd": 12.34,
  "active_conversations": 42,
  "service": "maestra-backend",
  "version": "2.0.0"
}
```

**Metrics Tracked:**
- `uptime_seconds` - Service uptime since start
- `total_requests` - Total requests processed
- `total_errors` - Total errors (4xx, 5xx)
- `avg_latency_ms` - Average request latency
- `total_cost_usd` - Total API cost
- `active_conversations` - Active conversation count

**Usage:**
```bash
curl http://localhost:8825/metrics
```

## 2. JSON Logging

### Structured Logging

All events logged as JSON for easy parsing and analysis.

**Log Format:**
```json
{
  "timestamp": "2025-12-28T15:30:00Z",
  "logger": "MaestraBackend",
  "level": "INFO",
  "event_type": "request_received",
  "surface_id": "windsurf",
  "user_id": "justinharmon",
  "conversation_id": "conv_2025-12-28_jh_abc12345",
  "message_preview": "What should I do next?"
}
```

### Log Levels

- `DEBUG` - Detailed debugging information
- `INFO` - General informational messages
- `WARNING` - Warning messages (invalid API key, rate limit, etc.)
- `ERROR` - Error messages (exceptions, failures)
- `CRITICAL` - Critical system errors

### Log Locations

**Local:**
```
~/Library/Logs/maestra_backend.log
~/Library/Logs/maestra_backend_error.log
```

**Cloud (Replit):**
```
Replit console output
```

### Viewing Logs

**Local:**
```bash
# View all logs
tail -f ~/Library/Logs/maestra_backend.log

# View errors only
tail -f ~/Library/Logs/maestra_backend_error.log

# Parse JSON logs
cat ~/Library/Logs/maestra_backend.log | jq '.event_type'
```

**Cloud:**
```bash
# View in Replit console
# Or check Replit logs panel
```

## 3. Metrics Logging

### Request Metrics

Every request is logged with detailed metrics.

**Metrics File:**
```
~/.8825/maestra_metrics.jsonl
```

**Entry Format:**
```json
{
  "timestamp": "2025-12-28T15:30:00Z",
  "request_id": "req_abc123",
  "surface_id": "windsurf",
  "user_id": "justinharmon",
  "conversation_id": "conv_2025-12-28_jh_abc12345",
  "mode": "advisor",
  "latency_ms": 234,
  "status_code": 200,
  "tokens": 150,
  "cost_usd": 0.001,
  "error": null
}
```

**Querying Metrics:**
```bash
# View all metrics
cat ~/.8825/maestra_metrics.jsonl | jq '.'

# Count total requests
cat ~/.8825/maestra_metrics.jsonl | wc -l

# Get average latency
cat ~/.8825/maestra_metrics.jsonl | jq '.latency_ms' | awk '{sum+=$1} END {print sum/NR}'

# Find errors
cat ~/.8825/maestra_metrics.jsonl | jq 'select(.error != null)'

# Metrics by surface
cat ~/.8825/maestra_metrics.jsonl | jq -s 'group_by(.surface_id) | map({surface: .[0].surface_id, count: length})'
```

## 4. Slack Alerts

### Configuration

**Set Slack webhook URL:**
```bash
# Get webhook from Slack workspace
# https://api.slack.com/messaging/webhooks

# Set in environment
export MAESTRA_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

**Replit Secrets:**
```
MAESTRA_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Alert Types

**Error Alert:**
```
🔴 Maestra Backend Error
Request failed with status 500
surface_id: windsurf
user_id: justinharmon
error: Connection timeout
```

**Rate Limit Alert:**
```
🟠 Rate Limit Exceeded
IP: 192.168.1.1
Requests: 101/100
Window: 60s
```

**Cost Limit Alert:**
```
🟠 Daily Cost Limit Exceeded
Daily cost: $5.50
Limit: $5.00
Requests: 234
```

### Triggering Alerts

**Manual Alert:**
```python
from observability import get_slack_alerter

alerter = get_slack_alerter()
await alerter.alert(
    title="Manual Alert",
    message="Something important happened",
    severity="warning",
    user_id="justinharmon",
    conversation_id="conv_123"
)
```

**Automatic Alerts:**
- Errors (status >= 500)
- Rate limit violations
- Cost limit violations
- Authentication failures
- Service startup/shutdown

## 5. Monitoring Dashboard

### Metrics Summary

**Check service health:**
```bash
curl http://localhost:8825/health
```

**Check metrics:**
```bash
curl http://localhost:8825/metrics
```

**Monitor logs:**
```bash
tail -f ~/Library/Logs/maestra_backend.log | jq '.'
```

### Key Metrics to Watch

1. **Uptime** - Should be continuous (no restarts)
2. **Error Rate** - Should be < 1%
3. **Average Latency** - Should be < 500ms
4. **Total Cost** - Should stay within limits
5. **Active Conversations** - Should grow over time

### Alerting Thresholds

**Set up alerts for:**
- Error rate > 5%
- Average latency > 1000ms
- Daily cost > limit
- Service down (no /health response)
- Rate limit violations

## 6. Performance Monitoring

### Latency Analysis

```bash
# Get latency percentiles
cat ~/.8825/maestra_metrics.jsonl | jq '.latency_ms' | sort -n | awk '
  BEGIN { count=0 }
  { latencies[count++]=$1 }
  END {
    print "Min:", latencies[0]
    print "P50:", latencies[int(count*0.5)]
    print "P95:", latencies[int(count*0.95)]
    print "P99:", latencies[int(count*0.99)]
    print "Max:", latencies[count-1]
  }
'
```

### Error Analysis

```bash
# Get error breakdown
cat ~/.8825/maestra_metrics.jsonl | jq -s 'group_by(.status_code) | map({status: .[0].status_code, count: length})'

# Get most common errors
cat ~/.8825/maestra_metrics.jsonl | jq -s 'map(select(.error != null)) | group_by(.error) | map({error: .[0].error, count: length}) | sort_by(-.count)'
```

### Cost Analysis

```bash
# Daily cost breakdown
cat ~/.8825/maestra_metrics.jsonl | jq -s 'group_by(.timestamp | split("T")[0]) | map({date: .[0].timestamp | split("T")[0], cost: (map(.cost_usd) | add)})'

# Cost by surface
cat ~/.8825/maestra_metrics.jsonl | jq -s 'group_by(.surface_id) | map({surface: .[0].surface_id, cost: (map(.cost_usd) | add)})'
```

## 7. Troubleshooting

### Metrics Not Appearing

1. Check metrics file exists: `ls -la ~/.8825/maestra_metrics.jsonl`
2. Check permissions: `chmod 644 ~/.8825/maestra_metrics.jsonl`
3. Check logs for errors: `tail -f ~/Library/Logs/maestra_backend.log`

### Slack Alerts Not Working

1. Verify webhook URL: `echo $MAESTRA_SLACK_WEBHOOK_URL`
2. Test webhook: `curl -X POST $MAESTRA_SLACK_WEBHOOK_URL -d '{"text":"test"}'`
3. Check logs for alert errors: `grep -i slack ~/Library/Logs/maestra_backend.log`

### High Latency

1. Check `/metrics` for average latency
2. Review metrics file for slow requests
3. Check system resources (CPU, memory, disk)
4. Review logs for errors or warnings

### High Error Rate

1. Check error breakdown: `cat ~/.8825/maestra_metrics.jsonl | jq 'select(.error != null)'`
2. Review logs for error details
3. Check API key validity (cloud)
4. Check rate limiting status

## 8. Integration with External Tools

### Prometheus Integration

Export metrics in Prometheus format:

```python
@app.get("/metrics/prometheus")
async def prometheus_metrics():
    """Export metrics in Prometheus format"""
    metrics_collector = get_metrics_collector()
    metrics = metrics_collector.get_system_metrics(0)
    
    return f"""
# HELP maestra_uptime_seconds Service uptime in seconds
# TYPE maestra_uptime_seconds gauge
maestra_uptime_seconds {metrics.uptime_seconds}

# HELP maestra_total_requests Total requests processed
# TYPE maestra_total_requests counter
maestra_total_requests {metrics.total_requests}

# HELP maestra_total_errors Total errors
# TYPE maestra_total_errors counter
maestra_total_errors {metrics.total_errors}

# HELP maestra_avg_latency_ms Average latency in milliseconds
# TYPE maestra_avg_latency_ms gauge
maestra_avg_latency_ms {metrics.avg_latency_ms}

# HELP maestra_total_cost_usd Total cost in USD
# TYPE maestra_total_cost_usd counter
maestra_total_cost_usd {metrics.total_cost_usd}

# HELP maestra_active_conversations Active conversations
# TYPE maestra_active_conversations gauge
maestra_active_conversations {metrics.active_conversations}
"""
```

### DataDog Integration

Send metrics to DataDog:

```python
from datadog import initialize, api

options = {
    'api_key': os.getenv('DATADOG_API_KEY'),
    'app_key': os.getenv('DATADOG_APP_KEY')
}

initialize(**options)

# Send metric
api.Metric.send(
    metric='maestra.request.latency',
    points=latency_ms,
    tags=['surface:windsurf', 'user:justinharmon']
)
```

## Files

- `observability.py` - Metrics, logging, and alerts
- `~/.8825/maestra_metrics.jsonl` - Request metrics log
- `~/Library/Logs/maestra_backend.log` - Application logs
- `OBSERVABILITY.md` - This document

## Status

✅ **Sprint 7 Complete**
- `/metrics` endpoint implemented
- JSON logging configured
- Metrics collection working
- Slack alerts ready (webhook configurable)
- Ready for Sprint 8 (Testing)
