# AxonChat Migration to MessageBoard Architecture

## Overview

AxonChat has been successfully migrated from the legacy AppletSharedState/ChatAgentService architecture to the new MessageBoard/RealtimeMessageService architecture.

**Migration Date**: October 2025
**Status**: ✅ COMPLETE

## Performance Improvements

| Metric | Before (Legacy) | After (MessageBoard) | Improvement |
|--------|----------------|---------------------|-------------|
| **Latency** | 2-4 minutes | 1-3 seconds | ~100x faster |
| **Federation** | Manual polling | Automatic sync | Real-time |
| **Persistence** | JSON blob | Database rows | Queryable |
| **Scalability** | Single service | Broadcast queues | Multi-subscriber |

## Architecture Changes

### Before: AppletSharedState (Deprecated)
```
AxonChat.js → /api/applets/{id}/update_state/ → ChatAgentService
                                                      ↓
                                               AppletSharedState.state_data (JSON)
                                                      ↓
AxonChat.js ← /api/applets/{id}/events/ ← SSE ← ChatAgentService (2-4 min polling)
```

### After: MessageBoard
```
AxonChat.js → /api/chat/post/ → Message.objects.create()
                                       ↓
                                 MessageBoard (id=9, is_realtime=True)
                                       ↓
                                 RealtimeMessageService (1s poll interval)
                                       ↓
AxonChat.js ← /api/chat/events/ ← SSE ← Broadcast Queue (1-3s latency)
```

## API Changes

### Message Posting

**OLD (Deprecated)**:
```javascript
POST /api/applets/03e39b0a-df3f-4879-9b63-b5bc930a2d88/update_state/
Body: { "action": "post_message", "text": "Hello world!" }
```

**NEW**:
```javascript
POST /api/chat/post/
Body: { "text": "Hello world!" }
```

### SSE Stream

**OLD (Deprecated)**:
```javascript
GET /api/applets/03e39b0a-df3f-4879-9b63-b5bc930a2d88/events/?token=...&tz=...
```

**NEW**:
```javascript
GET /api/chat/events/?token=...&tz=...
```

### Message Format (Unchanged!)

Both old and new implementations use the same message format:
```json
{
  "messages": [
    {
      "id": "uuid",
      "timestamp": "2025-10-17T20:56:39.457956+00:00",
      "display_time": "8:56:39 PM",
      "user": "username",
      "user_pubkey": "-----BEGIN PUBLIC KEY-----...",
      "text": "Hello world!"
    }
  ]
}
```

## Database Schema

### MessageBoard (AxonChat)
```sql
id: 9
name: 'AxonChat'
is_realtime: true
federation_room_id: 'axonchat-global'
trusted_peers: ['http://ak7r7fuax7e2ow5o4gx4nqeuk2ewoao5ovpsca...']
message_retention_days: 30
```

### Message (Chat Messages)
```sql
board_id: 9 (AxonChat)
subject: 'Chat'
body: 'Hello world!'
author_id: user.id
pubkey: user.pubkey
created_at: UTC timestamp
```

## Deprecated Components

### Removed Files
- ✅ `core/agents/chat_agent_service.py` (17KB, 224 lines)
- ✅ `applets/chat_agent_service.py` (4.1KB, 193 lines)

### Deprecated Endpoints (Backward Compatible)

**Still functional but return deprecation warnings**:

1. **`/api/applets/{id}/events/`** (SSE)
   - Returns: HTTP 410 Gone with error message
   - Use instead: `/api/chat/events/`

2. **`/api/applets/{id}/update_state/`** (POST)
   - Returns: HTTP 410 Gone with error message
   - Use instead: `/api/chat/post/`

### Kept for Compatibility

**AppletSharedState model and views remain** for:
- Future applets that may need shared state
- Backup/restore functionality
- Admin interface
- Generic room-based state API

**Recommendation**: New chat-like applets should use MessageBoard + RealtimeMessageService instead.

## Federation Details

### Room ID
```
axonchat-global
```

### Trusted Peers
- **Host BBS**: `http://xnjzv3k7gd2yw5l3u6mxqqr6jkq7flxvj4j5ljopoxf2bglwdcpqmhid.onion`
- **PiBBS**: `http://ak7r7fuax7e2ow5o4gx4nqeuk2ewoao5ovpsca3m3bmf2or7fyd.onion`

### Synchronization
- **Poll Interval**: 1 second
- **Deduplication**: UUID-based message IDs
- **Transport**: Tor (SOCKS5 proxy at 127.0.0.1:9050)
- **Protocol**: HTTP POST with JWT authentication

## Timezone Handling

### Storage
- All timestamps stored in **UTC** in database
- `Message.created_at` field uses Django's `DateTimeField(auto_now_add=True)`

### Conversion
- Conversion happens at **display time** in SSE stream
- Sources (priority order):
  1. Query parameter `?tz=America/New_York`
  2. Authenticated user's `user.timezone` setting
  3. Default: UTC

### Display Format
```javascript
"8:56:39 PM"  // Hour (no leading zero):Minutes:Seconds AM/PM
```

## Testing Checklist

- [x] Message posting works on Host BBS
- [x] Message posting works on PiBBS
- [x] Messages federate Host → PiBBS (1-3s latency)
- [x] Messages federate PiBBS → Host (1-3s latency)
- [x] Timezone conversion works correctly
- [x] User sidebar updates properly
- [x] SSE reconnection works after network interruption
- [x] Old endpoints return deprecation warnings

## Rollback Plan

If critical issues are discovered:

1. **Revert frontend** to old endpoints (5 min rebuild)
2. **No database changes needed** - both systems can coexist
3. **ChatAgentService code** is in git history and can be restored
4. **Zero downtime** - old AppletSharedState views still exist

## Migration for Future Applets

If you're building a new applet that needs real-time shared state:

### Use MessageBoard if:
- ✅ You need real-time updates (<3s latency)
- ✅ You want automatic federation
- ✅ You need message persistence and queries
- ✅ Multiple users interact in real-time
- ✅ Chat-like or collaborative features

### Use AppletSharedState if:
- 📝 You need simple JSON blob storage
- 📝 Updates are infrequent (>1 minute)
- 📝 State is private to single user/applet instance
- 📝 No federation needed

**Example**: New "Collaborative Whiteboard" applet → Use MessageBoard with `is_realtime=True`

## Related Documentation

- `AxonChat_Phase2_Migration.md` - Original migration plan
- `AxonChat_DeveloperHandoff_10.27.0.txt` - Original implementation guide (legacy)
- `RealtimeMessageService_Architecture.md` - Real-time federation design

## Questions?

Contact the Axon BBS development team or open an issue in the repository.

---

**Generated**: October 17, 2025
**Axon BBS Version**: 10.27.0+
