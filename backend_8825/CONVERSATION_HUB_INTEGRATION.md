# Conversation Hub Integration - Sprint 4 Complete

## Overview

Maestra Backend now integrates with Conversation Hub for durable state persistence and cross-surface continuity.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Maestra Request                          │
│  (user_id, surface_id, conversation_id, message)           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Maestra Backend (/api/maestra/core)            │
│                                                              │
│  1. Get or create conversation via Conversation Hub         │
│  2. Log user message to Conversation Hub                    │
│  3. Execute Maestra Core logic (TODO)                       │
│  4. Log assistant response to Conversation Hub              │
│  5. Return MaestraEnvelope with conversation_id             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│           Conversation Hub (~/.8825/conversations/)         │
│                                                              │
│  ├─ index.json (conversation index)                         │
│  ├─ conv_2025-12-28_jh_abc12345.json (conversation 1)      │
│  ├─ conv_2025-12-28_jh_def67890.json (conversation 2)      │
│  └─ ...                                                     │
│                                                              │
│  Each conversation stores:                                  │
│  - Messages (user/assistant)                                │
│  - Metadata (created_at, updated_at, status)                │
│  - Surfaces (windsurf, browser_ext, goose, mobile)          │
│  - Artifacts (linked Library entries)                       │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Conversation Creation
- Auto-create conversation if conversation_id doesn't exist
- Conversation ID format: `conv_YYYY-MM-DD_user_id_random_suffix`
- Topic extracted from first message (first 100 chars)

### 2. Message Logging
- Every user message logged with role, content, surface, mode, metadata
- Every assistant response logged with latency, model, tokens, cost
- Metadata includes file_path, workspace context

### 3. Cross-Surface Continuity
- Conversation tracks all surfaces that have participated
- User can switch surfaces and resume conversation
- Conversation history available across all surfaces

### 4. Durable Storage
- Conversations stored as JSON files in `~/.8825/conversations/`
- Index file tracks all conversations for quick lookup
- Atomic writes prevent corruption

## Implementation Details

### ConversationHubClient

**Location:** `8825_core/maestra_backend/conversation_hub_client.py`

**Methods:**
- `create_conversation()` - Create new conversation
- `get_conversation()` - Retrieve conversation by ID
- `append_message()` - Log message to conversation
- `link_artifact()` - Link Library artifact to conversation
- `get_messages()` - Get conversation messages
- `close_conversation()` - Mark conversation as closed
- `list_conversations()` - List conversations with filtering

**Global Instance:**
```python
from conversation_hub_client import get_client
hub = get_client()  # Singleton instance
```

### Maestra Backend Integration

**Location:** `8825_core/maestra_backend/server.py`

**Changes:**
1. Import Conversation Hub client
2. In `/api/maestra/core` endpoint:
   - Get or create conversation
   - Log user message
   - Execute logic (placeholder)
   - Log assistant response
   - Return response with conversation_id

### Conversation Storage

**Location:** `~/.8825/conversations/`

**Index file:** `index.json`
```json
{
  "conversations": [
    {
      "id": "conv_2025-12-28_jh_abc12345",
      "topic": "What should I do next?",
      "owner": "justinharmon",
      "surfaces": ["windsurf", "browser_ext"],
      "created_at": "2025-12-28T14:50:00Z",
      "updated_at": "2025-12-28T14:55:00Z",
      "message_count": 5,
      "status": "active"
    }
  ],
  "last_updated": "2025-12-28T14:55:00Z"
}
```

**Conversation file:** `conv_2025-12-28_jh_abc12345.json`
```json
{
  "id": "conv_2025-12-28_jh_abc12345",
  "topic": "What should I do next?",
  "owner": "justinharmon",
  "surfaces": ["windsurf", "browser_ext"],
  "tags": [],
  "messages": [
    {
      "id": "msg_uuid",
      "role": "user",
      "content": "What should I do next?",
      "surface": "windsurf",
      "mode": "advisor",
      "timestamp": "2025-12-28T14:50:00Z",
      "meta": {
        "file_path": "/path/to/file.py",
        "workspace": "/path/to/workspace"
      }
    },
    {
      "id": "msg_uuid",
      "role": "assistant",
      "content": "Based on your context...",
      "surface": "windsurf",
      "mode": "advisor",
      "timestamp": "2025-12-28T14:50:05Z",
      "meta": {
        "latency_ms": 234,
        "model": "placeholder",
        "tokens": 150,
        "cost_usd": 0.001
      }
    }
  ],
  "artifacts": [
    {
      "type": "knowledge",
      "id": "K-001",
      "title": "Relevant Knowledge",
      "confidence": 0.95,
      "linked_at": "2025-12-28T14:50:05Z"
    }
  ],
  "meta": {
    "created_at": "2025-12-28T14:50:00Z",
    "updated_at": "2025-12-28T14:50:05Z",
    "status": "active",
    "message_count": 2
  }
}
```

## Usage Examples

### Create/Resume Conversation

```python
from conversation_hub_client import get_client

hub = get_client()

# First request - creates conversation
response = await maestra_core(MaestraRequest(
    user_id="justinharmon",
    surface_id="windsurf",
    conversation_id="conv_2025-12-28_jh_abc12345",
    message="What should I do next?"
))

# Second request - resumes same conversation
response = await maestra_core(MaestraRequest(
    user_id="justinharmon",
    surface_id="browser_ext",  # Different surface!
    conversation_id="conv_2025-12-28_jh_abc12345",
    message="Tell me more about that"
))
```

### Query Conversation History

```python
hub = get_client()

# Get all messages
messages = hub.get_messages("conv_2025-12-28_jh_abc12345")

# Get last 5 messages
recent = hub.get_messages("conv_2025-12-28_jh_abc12345", limit=5)

# List user's conversations
convs = hub.list_conversations(user_id="justinharmon")

# List conversations from specific surface
windsurf_convs = hub.list_conversations(surface_id="windsurf")
```

### Link Artifacts

```python
hub = get_client()

# Link Library entry to conversation
hub.link_artifact(
    conversation_id="conv_2025-12-28_jh_abc12345",
    artifact_type="knowledge",
    artifact_id="K-001",
    title="Relevant Knowledge",
    confidence=0.95
)
```

## Testing

### Manual Test

```bash
# Start Maestra Backend
python -m maestra_backend --mode local --port 8825

# Test canonical endpoint
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "jh",
    "surface_id": "windsurf",
    "conversation_id": "conv_2025-12-28_jh_test",
    "message": "hello"
  }'

# Check conversation storage
ls -la ~/.8825/conversations/
cat ~/.8825/conversations/index.json
cat ~/.8825/conversations/conv_2025-12-28_jh_test.json
```

### Verify Cross-Surface Continuity

```bash
# Request 1: Windsurf
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "jh",
    "surface_id": "windsurf",
    "conversation_id": "conv_test_123",
    "message": "First message from Windsurf"
  }'

# Request 2: Browser Extension (same conversation_id)
curl -X POST http://localhost:8825/api/maestra/core \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "jh",
    "surface_id": "browser_ext",
    "conversation_id": "conv_test_123",
    "message": "Second message from Browser"
  }'

# Verify both surfaces in conversation
cat ~/.8825/conversations/conv_test_123.json | jq '.surfaces'
# Output: ["windsurf", "browser_ext"]
```

## Next Steps

1. **Sprint 5:** Cloud Deploy - Deploy to Replit with same Conversation Hub integration
2. **Sprint 6:** Security & Privacy - Add cost guardrails, data residency policy
3. **Sprint 7:** Observability - Add /metrics endpoint, JSON logging, Slack alerts
4. **Sprint 8:** Testing - Smoke tests for local/cloud/mixed scenarios
5. **Sprint 9:** Formalization - Agent factory integration, generate protocol/README

## Files Created/Modified

**New Files:**
- `8825_core/maestra_backend/conversation_hub_client.py` - Conversation Hub client
- `8825_core/maestra_backend/CONVERSATION_HUB_INTEGRATION.md` - This document

**Modified Files:**
- `8825_core/maestra_backend/server.py` - Integrated Conversation Hub into `/api/maestra/core`
- `8825_core/brain/capability_map.json` - Updated maestra-backend integration notes

## Status

✅ **Sprint 4 Complete**
- Conversation Hub client implemented
- Maestra Backend integrated with Conversation Hub
- Durable state persistence working
- Cross-surface continuity enabled
- Ready for Sprint 5 (Cloud Deploy)
