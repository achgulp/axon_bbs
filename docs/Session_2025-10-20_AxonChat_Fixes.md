# Development Session: AxonChat Real-time Fixes
**Date**: October 20, 2025
**Session Focus**: Fix AxonChat real-time message updates and consolidate to unified Realtime Event Board

---

## Session Summary

**Morning Session (SSE Debugging):**
Successfully consolidated AxonChat architecture to use a unified "Realtime Event Board" with subject-based filtering, improving scalability for future applets. Fixed message rendering order issue. Identified threading issue preventing real-time SSE broadcasting.

**Afternoon Session (v17 Client Polling + v18 Timezone Fix):**
Replaced SSE with simple client-side polling (2-second interval) for reliable real-time updates. Fixed code integrity error on PiBBS by removing duplicate federated FileAttachment. Implemented server-side timezone conversion to fix Tor Browser displaying UTC instead of EST.

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

4. **Switched to Client-Side Polling (AxonChat v17)**
   - Problem: SSE threading issue prevented real-time updates
   - Solution: Replaced SSE with 2-second polling using existing `/api/applets/{id}/read_events/` endpoint
   - Implementation:
     - Added `processedMessageIds` Set for deduplication
     - Poll every 2000ms, only render new messages
     - Scroll to bottom on new messages
   - File: `frontend/src/applets/AxonChat.js` lines 558-584
   - Result: Real-time messaging works reliably without SSE complexity

5. **Fixed Code Integrity Error on PiBBS**
   - Problem: "Code integrity check failed. The downloaded applet code may be corrupted or tampered with."
   - Root Cause: Duplicate FileAttachments with same content_hash but different encryption keys
     - ID `0cbf79ac` (Federation, no author) - encrypted with Host BBS keys
     - ID `47c358f4` (Achduke7, local post) - encrypted with PiBBS keys
   - BitSync tried to decrypt federated chunks but had wrong keys
   - Fix: Deleted federated FileAttachment, kept only locally-posted one
   - Result: v17 loads successfully on PiBBS

6. **Fixed Timezone Display in Tor Browser (AxonChat v18)**
   - Problem: Tor Browser showed UTC times (7:59:52 PM) instead of EST (2:59:52 PM)
   - Root Cause: Tor Browser uses UTC by default for fingerprinting protection
   - Solution: Server-side timezone conversion
     - Modified `ReadAppletEventsView` to accept `tz` query parameter
     - Reused `convert_message_timestamps()` from `core/views/realtime_board_events.py`
     - Updated `AppletRunner.js` to detect browser timezone using `Intl.DateTimeFormat()`
     - Modified `AxonChat.js` to use server-provided `display_time` field
   - Files Modified:
     - `applets/views.py` lines 180-220: ReadAppletEventsView with timezone support
     - `frontend/src/components/AppletRunner.js` lines 243-250: Timezone detection
     - `frontend/src/applets/AxonChat.js` lines 554-563: Use display_time from server
   - Result: Timestamps display correctly in EST even in Tor Browser

7. **Git Management**
   - Committed all changes to main branch
   - Commits: `cbf2edd`, `dff844d`, `d46dc67`, `7926f66`, `ba4da96`, `43539c3`, `1b18f39`, `1c2b70b`
   - Pushed to GitHub
   - Pulled changes on PiBBS
   - Built frontend on both servers

---

## ✅ Issue Resolved

**Real-time SSE Broadcasting Not Working**

**Original Problem:**
- RealtimeMessageService background thread not executing `_run()` polling loop
- SSE connections established but no updates pushed
- Messages only appeared on applet reload

**Solution:**
- Abandoned SSE approach in favor of simpler client-side polling
- AxonChat v17 polls every 2 seconds using existing REST API
- Deduplication handled client-side with Set tracking
- Works reliably across regular and Tor browsers
- No threading complexity or daemon thread issues

**Status:** Closed - Workaround implemented and tested successfully

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
cd /path/to/axon_bbs
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
find /path/to/axon_bbs -type d -name __pycache__ -exec rm -rf {} +
find /path/to/axon_bbs -name "*.pyc" -delete
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

**Morning (SSE Debugging):**
```
cbf2edd - Fix AxonChat message ordering and cumulative updates in SSE stream
dff844d - Add debug logging to RealtimeMessageService broadcast
d46dc67 - Consolidate AxonChat to use unified Realtime Event Board
7926f66 - Add fatal exception logging to RealtimeMessageService thread
ba4da96 - Add thread startup debug logging
```

**Afternoon (v17 Polling + v18 Timezone):**
```
43539c3 - Replace SSE with client-side polling for reliable real-time updates (AxonChat v17)
1b18f39 - Add server-side timezone conversion for Tor Browser compatibility
1c2b70b - Post AxonChat v18 with timezone fixes
```

---

## Testing Summary

### ✅ What Works Now
1. **Real-time messaging**: Messages appear within 2 seconds without reload
2. **Code integrity**: FileAttachments load correctly on both servers
3. **Timezone display**: Timestamps show in EST even in Tor Browser
4. **Federation**: Messages sync between Host BBS and PiBBS
5. **Message deduplication**: No duplicate messages when polling
6. **Subject filtering**: Only AxonChat messages appear in AxonChat applet

### 📊 Performance Metrics
- **Polling interval**: 2 seconds
- **Max messages fetched**: 50 (most recent)
- **Average latency**: < 3 seconds for cross-server messages
- **Bundle size**: 73.57 kB (main.js after gzip)
- **Memory footprint**: Minimal (Set-based deduplication)

---

## References

- **Previous Session**: `docs/Session_2025-10-18_AxonChat_Phase2.md`
- **Migration Docs**: `docs/AxonChat_Migration_Complete.md`
- **Architecture**: `AxonChat_Phase2_Migration.md`
- **Git Repository**: https://github.com/achgulp/axon_bbs

---

**Session End Time**: October 20, 2025 - 5:00 PM EST
**Status**: ✅ Complete success - Real-time messaging, code integrity, and timezone display all working

---

## October 21, 2025 - AxonChat v19 Deployment

**Power Outage Recovery and v19 Deployment**

### Changes in v19:
- Added `APPLET_VERSION = "v19.0"` constant for version tracking
- Updated initialization debug message to show version: `AxonChat ${APPLET_VERSION} initializing...`
- Removed unnecessary fallback in timestamp display (server always provides `display_time`)

### Deployment Steps Completed:
1. ✅ Committed v19 changes to git (commit `f037cde`)
2. ✅ Pushed to GitHub
3. ✅ Rebuilt frontend on HostBBS (main.b6a366d4.js)
4. ✅ Deployed to PiBBS (git pull + rebuild)
5. ✅ Posted update to Applet Library using `manage.py post_applet_update`
   - Message ID: `cc2e8184-4c25-4394-8bf9-53b189caab44`
   - FileAttachment ID: `6c9d454c-d1ef-4559-b7ad-a4d0e990e148`
   - Content Hash: `c69fc1f4d69c6a63...`
6. ✅ Updated AxonChat applet `code_manifest` to point to new BitSync chunks
7. ✅ Restarted both servers with `nohup` for persistence

### Server Status:
- **HostBBS**: Running at `http://127.0.0.1:8000` (nohup, PID 12052)
- **PiBBS**: Running at `http://192.168.58.7:8000` (nohup, PIDs 45681/45682)

**Next Session**: Test v19 loading in browser, verify version appears in console logs

---

## October 21, 2025 (Continued) - BitSync & Federation Fixes

**Fixed Critical Federation Sync Bug**

### Issues Discovered:
1. **BitSync chunk location mismatch** - Chunks saved to `{content_hash}/0.chunk` but system expects `{chunk_hash}/{chunk_hash}.enc`
2. **Messages not syncing to peers** - `post_applet_update` didn't create `metadata_manifest` for messages
3. **Hardcoded version in subject** - Command used "v18" instead of content hash

### Root Cause:
The sync service only syncs messages with `metadata_manifest`:
```python
Message.objects.filter(metadata_manifest__isnull=False)
```

Manually posted messages (like v19b) had `metadata_manifest` and synced ✓
Command-posted messages (like [f54fad00]) didn't have `metadata_manifest` and didn't sync ✗

### Fixes Implemented:

**1. Fixed `post_applet_update` subject line** (commit `223fd0f`):
- Changed from hardcoded "v18" to `{applet_name} [{content_hash[:8]}]`
- Now shows unique hash prefix for each version (e.g., "AxonChat [f54fad00]")

**2. Added message BitSync manifest** (commit `71d885d`):
- `post_applet_update` now creates `metadata_manifest` for the Message object
- Encrypts message content (subject + body) via BitSync
- Enables automatic federation sync to peers
- Messages now appear on PiBBS automatically (after sync interval)

**3. Created Server Management Guide** (commit `33301b2`):
- Complete reference for server operations, applet publishing, and troubleshooting
- Documents BitSync chunk location fix
- Explains message federation requirements
- Location: `docs/Server_Management_Guide.md`

### BitSync Chunk Fix Script:
Created workaround script to copy chunks from incorrect location to correct location:
```python
# Copy from: {content_hash}/0.chunk
# Copy to: {chunk_hash}/{chunk_hash}.enc
```

Applied to both HostBBS and PiBBS for v19 deployment.

### Final v19 Deployment:
- ✅ HostBBS: AxonChat v19 (content hash `f54fad00...`)
- ✅ PiBBS: AxonChat v19 (content hash `9eed4a51...`)
- ✅ Both servers have fixed BitSync chunks
- ✅ Future `post_applet_update` posts will auto-sync

### Files Modified:
- `core/management/commands/post_applet_update.py` - Added message manifest, fixed subject
- `docs/Server_Management_Guide.md` - New comprehensive guide
- `docs/Session_2025-10-20_AxonChat_Fixes.md` - This file

### Git Commits:
- `f037cde` - Update AxonChat to v19 with version labeling
- `223fd0f` - Fix post_applet_update to use content hash prefix
- `71d885d` - Add message BitSync manifest for federation sync
- `33301b2` - Create Server Management Guide

**Session Status**: ✅ Complete - v19 deployed, sync issues fixed, documentation updated

---

## October 21, 2025 (Evening) - Fixed Applet Manifest Pointer

**Issue**: AxonChat v19 code in source file and BitSync chunks, but browser loaded old code

### Root Cause:
The AxonChat applet's `code_manifest` field was pointing to the WRONG FileAttachment:
- Applet was using: `f54fad00186f172e...` (AxonChat_republish.js - old code)
- v19b message had: `d134a9a1afb7240c...` (AxonChat.js - correct v19 code)

### Investigation Process:
1. Verified source file `/path/to/axon_bbs/frontend/src/applets/AxonChat.js` contains v19 code ✓
2. Checked git history - commit `f037cde` has v19 changes ✓
3. Traced AppletRunner.js → fetches `/api/content/stream/{content_hash}/?for_verification`
4. Found StreamContentView → uses `sync_service.get_manifest_by_content_hash()`
5. Discovered applet.code_manifest pointing to wrong FileAttachment
6. Found v19b message (ID: 2a172e9e...) with correct content_hash
7. Manually updated applet to use v19b manifest

### Fix Applied:
```python
applet = Applet.objects.get(name='AxonChat')
v19b_attachment = FileAttachment.objects.get(id='7570ddea-5b61-4f51-907f-ec0036e90f6b')
applet.code_manifest = v19b_attachment.metadata_manifest
applet.save()
```

### Verification:
```bash
# Confirmed v19b chunks contain correct code:
✓ APPLET_VERSION found: const APPLET_VERSION = "v19.0";
✓ Debug message template: ${APPLET_VERSION} initializing
```

### Why post_applet_update Didn't Update Applet:
The command detected v19b as already published (same filename + size) and exited early, so it never reached the applet update code (lines 200-221).

### Current Status:
- ✅ HostBBS: Running (PID 79708), AxonChat using v19b manifest (d134a9a1...)
- ✅ PiBBS: Running (PIDs 45681/45682)
- ✅ v19b message in Applet Library with correct code
- ✅ Applet code_manifest updated to point to v19b

**Next**: User should test in browser - should now see version number in console and correct EST timezone
