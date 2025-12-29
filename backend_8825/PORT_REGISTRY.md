# 8825 Port Registry

## Reserved Ports

| Port | Service | Status | Notes |
|------|---------|--------|-------|
| 5000 | macOS AirTunes | Reserved | Do not use - system reserved |
| 5001 | Integration Server | Active | Flask integration server |
| 5002 | Capsules | Active | Flask capsules UI |
| 5050 | Export Console | Active | Export service |
| 5170 | Project Planning MCP | Active | Brain-first planning |
| 8825 | Maestra Backend | Active | Primary Maestra service |
| 8826-8829 | Maestra Fallback | Available | Used if 8825 occupied |

## Maestra Port Allocation

**Primary:** 8825 (localhost:8825)

**Fallback sequence (if 8825 occupied):**
1. 8826
2. 8827
3. 8828
4. 8829

**Port detection:** `install_maestra_local.sh` checks availability and writes chosen port to `~/.maestra/port`

**Health endpoint advertises actual port:**
```json
{
  "status": "healthy",
  "port": 8825,
  "uptime_seconds": 1234
}
```

## Adding New Services

When adding a new service:
1. Choose port from available range
2. Add entry to this registry
3. Update `install_maestra_local.sh` if port fallback needed
4. Document in service README
