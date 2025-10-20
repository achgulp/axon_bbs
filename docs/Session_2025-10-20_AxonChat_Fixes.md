# Development Session: AxonChat Real-time Fixes
**Date**: October 20, 2025
**Session Focus**: Fix AxonChat real-time message updates and consolidate to unified Realtime Event Board

---

## Session Summary

Successfully consolidated AxonChat architecture to use a unified "Realtime Event Board" with subject-based filtering, improving scalability for future applets. Fixed message rendering order issue. Identified threading issue preventing real-time SSE broadcasting.

---

## Current Status

### ✅ Completed Tasks

1. **Fixed Message Rendering Order**
   - Problem: Initial messages were displayed in reverse chronological order (newest first)
   - Fix: Modified SSE endpoint to reverse the message list after fetching
   - File: `core/views/applet_events.py` line 122-124
   - Result: Messages now appear in correct chronological order (oldest first)

2. **Fixed SSE Cumulative Message Updates**
   - Problem: SSE was only sending new message deltas, but frontend expected full cumulative list
   - Fix: Track `all_messages` list and append new messages, send complete list on each update
   - File: `core/views/applet_events.py` lines 145-171
   - Result: Frontend renders messages correctly when receiving updates

3. **Consolidated to Unified Realtime Event Board**
   - Architecture Change: AxonChat now uses "Realtime Event Board" (ID=8) instead of dedicated board (ID=9)
   - Messages identified by `subject='AxonChat'`
   - Benefits:
     - Single board visible in Message Boards UI
     - Future applets can use different subjects (e.g., 'GameScore', 'Notifications')
     - Simpler federation (one board instead of many)
     - Easier monitoring and management
   - Files Modified:
     - `applets/views.py`: PostChatMessageView posts to board ID=8 with subject='AxonChat'
     - `core/views/applet_events.py`: chat_event_stream filters by subject='AxonChat'

4. **Git Management**
   - Committed all changes to main branch
   - Commits: `cbf2edd`, `dff844d`, `d46dc67`, `7926f66`, `ba4da96`
   - Pushed to GitHub
   - Pulled changes on PiBBS

---

## ⚠️ Outstanding Issue

**Real-time SSE Broadcasting Not Working**

**Symptoms:**
- Messages are saved to database correctly ✅
- Messages federate between servers ✅
- Messages appear when reloading applet ✅
- Messages do NOT appear in real-time without reload ❌

**Root Cause Identified:**
The RealtimeMessageService background thread is not executing its `_run()` polling loop.

**Evidence:**
```
INFO Started RealtimeMessageService for board 'Realtime Event Board' (id=8)
INFO Started RealtimeMessageService for board 'AxonChat' (id=9)
```
- Service claims to start successfully
- But `_run()` method's first log "Starting real-time sync loop" never appears
- Thread.start() is called, but the target function doesn't execute

**Debugging Attempts:**
1. Added debug logging to `start()` method - logs don't appear
2. Added fatal exception handling to `_run()` - no errors logged
3. Cleared Python cache (__pycache__) - issue persists
4. Verified code changes are committed and in file

**Hypothesis:**
- Possible Python threading issue with Django's development server auto-reloader
- Daemon threads may be failing silently
- Import caching might be preventing code reload

---

## Architecture Details

### Unified Realtime Event Board

**Board Configuration:**
```python
MessageBoard:
  id: 8
  name: 'Realtime Event Board'
  is_realtime: True
  federation_room_id: 'test-chat'  # Federation identifier
  trusted_peers: [...]
```

**Subject-Based Message Filtering:**
- AxonChat messages: `subject='AxonChat'`
- Future gaming applet: `subject='GameScore'`
- Future notifications: `subject='SystemAlert'`

**SSE Endpoint Logic:**
```python
# Get all messages from board with matching subject
initial_messages = Message.objects.filter(
    board=board,
    subject='AxonChat'
).order_by('-created_at')[:50]

# Reverse to chronological order
initial_messages.reverse()

# Filter updates by subject
new_chat_messages = [msg for msg in new_messages_queryset if msg.subject == 'AxonChat']
```

---

## Key Files Modified

### Backend
```
applets/views.py                        - PostChatMessageView uses unified board
core/views/applet_events.py             - chat_event_stream filters by subject, fixed message order
core/agents/realtime_message_service.py - Added debug/fatal exception logging
```

### Documentation
```
docs/Session_2025-10-20_AxonChat_Fixes.md  - This session notes (NEW)
```

---

## Testing Results

### What Works ✅
1. **Post message from Host BBS** → Appears in AxonChat on Host BBS immediately
2. **Reload AxonChat on PiBBS** → New messages from Host BBS appear
3. **View in Message Boards** → Can see AxonChat messages in "Realtime Event Board"
4. **Subject filtering** → Only AxonChat messages appear in AxonChat applet

### What Doesn't Work ❌
1. **Real-time updates** → Messages don't appear without page/applet reload
2. **Federation delay** → Must reload to see federated messages (no auto-update)

---

## Server Status

### Host BBS
```bash
# Running at http://127.0.0.1:8000
# RealtimeMessageService: Started but thread not running
# Services: SyncService ✅, HighScoreService ✅, ModeratorAgent ✅
```

### PiBBS
```bash
# Running at http://192.168.58.7:8000 (via Tor)
# Federation: Polling Host BBS every ~1 second
# Changes synced via git pull
```

---

## Next Steps

### Immediate Priority
1. **Fix RealtimeMessageService thread execution**
   - Investigate why daemon thread `_run()` method doesn't execute
   - Consider non-daemon thread approach
   - Test with production server instead of development server
   - Alternative: Implement simpler polling mechanism without threading

2. **Verify Thread Startup**
   - Add logging immediately after `Thread()` constructor
   - Check thread.is_alive() status
   - Test thread.join() to see if thread exits immediately

### Future Enhancements
1. **Remove Old AxonChat Board** (ID=9)
   - Update database to remove MessageBoard with ID=9
   - Clean up any references

2. **Improve Federation**
   - Once real-time works locally, test cross-server real-time updates
   - Verify federation room_id configuration

3. **Performance Monitoring**
   - Add metrics for message latency
   - Track subscriber counts
   - Monitor broadcast queue sizes

---

## Useful Commands

### Restart Django (Host BBS)
```bash
pkill -9 -f "python.*runserver"
cd /home/dukejer/axon_bbs
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000 > /tmp/django_host.log 2>&1 &
```

### Check Realtime Service Status
```bash
source venv/bin/activate
python manage.py shell <<'EOF'
from core.services.service_manager import service_manager
print("Realtime services:", service_manager.realtime_services)
for board_id, svc in service_manager.realtime_services.items():
    print(f"Board {board_id}: thread.is_alive()={svc.thread.is_alive()}")
EOF
```

### Clear Python Cache
```bash
find /home/dukejer/axon_bbs -type d -name __pycache__ -exec rm -rf {} +
find /home/dukejer/axon_bbs -name "*.pyc" -delete
```

### Test Message Post
```bash
curl -X POST http://127.0.0.1:8000/api/chat/post/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"text": "Test message"}'
```

---

## Git Commit History (Session)

```
ba4da96 - Add thread startup debug logging
7926f66 - Add fatal exception logging to RealtimeMessageService thread
d46dc67 - Consolidate AxonChat to use unified Realtime Event Board
dff844d - Add debug logging to RealtimeMessageService broadcast
cbf2edd - Fix AxonChat message ordering and cumulative updates in SSE stream
```

---

## Questions for Next Session

1. **Threading Issue**: Why isn't the daemon thread's `_run()` method executing?
2. **Alternative Approach**: Should we switch to Django Channels or Celery for real-time updates?
3. **Production Testing**: Does the threading issue persist in production (not development server)?
4. **Federation**: Once real-time works, will federated messages broadcast correctly?

---

## References

- **Previous Session**: `docs/Session_2025-10-18_AxonChat_Phase2.md`
- **Migration Docs**: `docs/AxonChat_Migration_Complete.md`
- **Architecture**: `AxonChat_Phase2_Migration.md`
- **Git Repository**: https://github.com/achgulp/axon_bbs

---

**Session End Time**: October 20, 2025 - 3:35 PM EST
**Next Steps**: Debug RealtimeMessageService thread execution issue
**Status**: Partial success - architecture improved, threading issue remains
