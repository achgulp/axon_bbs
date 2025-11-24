# Applet Publishing Guide for Axon BBS

**Last Updated:** October 23, 2025
**Document Version:** 1.0

---

## Recent Work Summary

### AxonChat v20 - Version Logging Fix

**Problem:** Version number wasn't showing in debug console
**Root Cause:** `debugLog()` was called before the HTML debug console element was created

**Solution:**
- Moved version log from line 80 (before HTML render) to line 327 (after UI rendered)
- Changed version from v19.0 to v20
- Updated and posted applet manifest
- Deployed to both HostBBS and PiBBS

**Files Changed:**
- `frontend/src/applets/AxonChat.js`

**Git Commit:** `6663390` - "Update AxonChat to v20 with fixed version logging"

---

### AxonChat v21 - Critical Bug Fixes

**Three Major Issues Fixed:**

#### 1. Duplicate Users in Sidebar
**Problem:** Users appearing twice (e.g., JakeFarm showed up twice on PiBBS)
**Root Cause:** Line 379 was comparing both pubkey AND nickname, creating false matches

**Solution:**
```javascript
// Before (v20):
const isCurrentUser = (userId === currentUserShortId || nickname === userInfo.nickname);

// After (v21):
const isCurrentUser = (userId === currentUserShortId);
```

#### 2. Users Showing as "Anonymous"
**Problem:** JakeFarm showing as "Anonymous" instead of username on HostBBS
**Root Cause:** Line 560 checking for non-existent `author_display` field

**Solution:**
```javascript
// Before (v20):
user: event.author_display || event.author || event.author_nickname || 'Anonymous',

// After (v21):
user: event.author_nickname || event.author || 'Anonymous',
avatar_url: event.avatar_url,  // Also added avatar
```

#### 3. Timezone Debug Logging
**Problem:** Timestamps 4 hours off on PiBBS using Tor Browser

**Solution:** Added comprehensive debug logging:
- Line 87-88: Shows detected timezone at startup
- Line 548-550: Shows UTC vs converted time for each message

**Files Changed:**
- `frontend/src/applets/AxonChat.js`

**Git Commit:** `30b2da7` - "Update AxonChat to v21 with critical bug fixes"

---

## Deployment Summary

**Both v20 and v21 were:**
1. ✅ Committed to git
2. ✅ Pushed to GitHub origin/main
3. ✅ Manifest updated on HostBBS
4. ✅ Posted to "Applet Library" board (BitSync federation)
5. ✅ Deployed to PiBBS (git pull + manifest update)

---

# Complete Applet Publishing Guide

## Overview

Axon BBS applets are JavaScript files that run in sandboxed iframes. The publishing process involves:
1. Writing the applet code
2. Updating the applet manifest
3. Posting to the Applet Library board
4. Deploying to federated instances

---

## Step-by-Step Publishing Process

### Step 1: Create or Update Applet Code

**Location:** `/path/to/axon_bbs/frontend/src/applets/YourApplet.js`

**Required Structure:**
```javascript
// --- Start of Applet API Helper (MANDATORY) ---
window.bbs = {
  _callbacks: {},
  _requestId: 0,
  _handleMessage: function(event) {
    const { command, payload, requestId, error } = event.data;
    if (command && command.startsWith('response_') && this._callbacks[requestId]) {
      const { resolve, reject } = this._callbacks[requestId];
      if (error) { reject(new Error(error)); } else { resolve(payload); }
      delete this._callbacks[requestId];
    }
  },
  _postMessage: function(command, payload = {}) {
    return new Promise((resolve, reject) => {
      const requestId = this._requestId++;
      this._callbacks[requestId] = { resolve, reject };
      if (window.parent !== window) {
        window.parent.postMessage({ command, payload, requestId }, '*');
      } else {
        console.warn("BBS API: Not running in a frame.");
        resolve({});
      }
    });
  },
  // Standard API
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); },
  // Advanced API
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); },
  postEvent: function(eventData) { return this._postMessage('postEvent', eventData); },
  readEvents: function() { return this._postMessage('readEvents'); },
  fetch: function(url, options = {}) {
    return this._postMessage('fetch', { url, options }).then(response => response);
  }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---

// --- Main Applet Execution ---
(async function() {
    const APPLET_VERSION = "v1.0";
    const appletContainer = document.getElementById('applet-root');

    // Your applet code here
    const userInfo = await window.bbs.getUserInfo();
    const appletInfo = await window.bbs.getAppletInfo();

    // Render UI
    appletContainer.innerHTML = `<h1>Hello ${userInfo.nickname}!</h1>`;
})();
```

**Key Points:**
- Always include the BBS API Helper (unchanged boilerplate)
- Use `applet-root` as the main container ID
- Version your applet with `APPLET_VERSION` constant
- Use async/await for API calls
- All code runs in sandboxed iframe

---

### Step 2: Update Applet Manifests

**Command:**
```bash
cd /path/to/axon_bbs
source venv/bin/activate
python manage.py update_applet_manifests
```

**What This Does:**
- Reads all applets from `frontend/src/applets/`
- Creates BitSync encrypted manifests (chunks + hashes)
- Saves encrypted chunks to `data/bitsync_chunks/{content_hash}/`
- Updates `Applet.code_manifest` field in database
- Re-keys manifests for all trusted instances (federation)

**Expected Output:**
```
--- Axon BBS Management Utility v10.5.0 ---
Updated applet: Video Player
Updated applet: Axon Sheets
Updated applet: Pipe Dodger
Updated applet: MimsTris
Updated applet: HexGL
Updated applet: AxonChat

Completed! Updated 6 applets, 0 failed.
INFO Manifest re-keyed for 2 total instance(s).
INFO Manifest re-keyed for 2 total instance(s).
...
```

---

### Step 3: Post Applet Update to Applet Library

**Command (Recommended Method):**
```bash
python manage.py post_applet_update <path_to_applet.js> \
  --name "AppletName" \
  --description "Version X.X: Description of changes"
```

**Example:**
```bash
python manage.py post_applet_update frontend/src/applets/AxonChat.js \
  --name "AxonChat" \
  --description "AxonChat v21 - Fixed duplicate users, Anonymous display, added timezone logging"
```

**What This Command Does (Automated):**
1. ✅ Creates BitSync manifest with encrypted chunks for the applet file
2. ✅ Creates `FileAttachment` record in database
3. ✅ Creates BitSync manifest for the message content (enables federation sync)
4. ✅ Posts message to "Applet Library" board with file attachment
5. ✅ **Updates the Applet's `code_manifest`** to point to the new FileAttachment
6. ✅ Prints FileAttachment ID and content hash for reference
7. ✅ **Message auto-syncs to federated peers** via BitSync protocol

**Expected Output:**
```
--- Axon BBS Management Utility v10.5.0 ---
Initialized BitSyncService
Created BitSync manifest with content_hash: ce9b91d40f888c8d...
Created FileAttachment ID: 81f92070-d3b9-49b0-ae9e-518e6b4f45fa
Created message BitSync manifest: 9c11a38a715c1ff4...

✓ Posted applet update to "Applet Library" board
  Message ID: 3b769f6f-9e60-4fb9-95f2-47b9bffee279
  Subject: AxonChat [ce9b91d4]
  Attachment Hash: 8656d1f195f4d5262859d8c06f1c548791768793d4d050264a7eedcfc98aaacd
  FileAttachment ID: 81f92070-d3b9-49b0-ae9e-518e6b4f45fa

✓ Updated AxonChat applet code manifest
  Applet ID: 03e39b0a-df3f-4879-9b63-b5bc930a2d88
INFO Creating manifest for 2 total instance(s).
```

---

### Step 4: Commit to Git

```bash
git add frontend/src/applets/YourApplet.js
git commit -m "Update YourApplet to vX.X - Description of changes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

---

### Step 5: Deploy to Remote Instances (e.g., PiBBS)

**Single Command (Recommended):**
```bash
ssh -p 2222 pibbs@192.168.58.7 "cd axon_bbs && git pull && source venv/bin/activate && python manage.py update_applet_manifests"
```

**What This Does:**
1. SSH into remote instance
2. Pull latest code from GitHub
3. Activate Python virtual environment
4. Update applet manifests on remote instance

**For Multiple Remotes:**
```bash
# HostBBS (local)
cd /path/to/axon_bbs
git pull
source venv/bin/activate
python manage.py update_applet_manifests

# PiBBS (remote)
ssh -p 2222 pibbs@192.168.58.7 "cd axon_bbs && git pull && source venv/bin/activate && python manage.py update_applet_manifests"
```

---

## Complete Workflow Example

Here's a full example of publishing AxonChat v21:

```bash
# 1. Edit applet
nano frontend/src/applets/AxonChat.js
# (Make changes, update APPLET_VERSION to "v21")

# 2. Update manifests on HostBBS
cd /path/to/axon_bbs
source venv/bin/activate
python manage.py update_applet_manifests

# 3. Post to Applet Library (creates message + federation sync)
python manage.py post_applet_update frontend/src/applets/AxonChat.js \
  --name "AxonChat" \
  --description "v21: Fixed duplicate users, Anonymous display, added timezone logging"

# 4. Commit to git
git add frontend/src/applets/AxonChat.js
git commit -m "Update AxonChat to v21 with critical bug fixes

Fixed three major issues:
1. Duplicate users in sidebar
2. Anonymous display issue
3. Added timezone debug logging

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push

# 5. Deploy to PiBBS
ssh -p 2222 pibbs@192.168.58.7 "cd axon_bbs && git pull && source venv/bin/activate && python manage.py update_applet_manifests"
```

---

## Applet API Reference

### Standard API Methods

#### `getUserInfo()`
Returns current user information.

**Returns:**
```javascript
{
  nickname: "JakeFarm",
  pubkey: "214467155aac6beeb17ed5819cc45a0b",  // 16-char SHA256 hash
  avatar_url: "/media/avatars/user_avatar.png"
}
```

**Example:**
```javascript
const userInfo = await window.bbs.getUserInfo();
console.log(`Hello ${userInfo.nickname}`);
```

---

#### `getData()`
Get applet-specific persistent data (stored per user, per applet).

**Returns:** Any JSON-serializable object

**Example:**
```javascript
const data = await window.bbs.getData();
const score = data.highScore || 0;
```

---

#### `saveData(newData)`
Save applet-specific persistent data.

**Parameters:**
- `newData` (Object): Any JSON-serializable object

**Example:**
```javascript
await window.bbs.saveData({ highScore: 1000, level: 5 });
```

---

#### `getAppletInfo()`
Get information about the current applet instance.

**Returns:**
```javascript
{
  id: "03e39b0a-df3f-4879-9b63-b5bc930a2d88",  // UUID
  name: "AxonChat",
  description: "Federated chat applet",
  parameters: {}  // Custom applet parameters
}
```

---

### Advanced API Methods

#### `postEvent(eventData)`
Post an event to the applet's event board (for multi-user interaction).

**Parameters:**
- `eventData` (Object): Event data to post
  - `subject` (String): Event subject/type
  - `body` (String): Event content/message
  - Additional custom fields allowed

**Example:**
```javascript
await window.bbs.postEvent({
  subject: 'AxonChat',
  body: 'Hello federation!'
});
```

**Note:** Events are stored in the applet's `event_board` (MessageBoard) and sync across federation.

---

#### `readEvents()`
Read events from the applet's event board (with automatic timezone conversion).

**Returns:** Array of event objects

**Example Response:**
```javascript
[
  {
    id: "9619980c-6a99-4514-88a1-1e123784f73c",
    subject: "AxonChat",
    body: "Hello from PiBBS!",
    author: "Achduke7",
    author_nickname: "JakeFarm",
    avatar_url: "/media/avatars/jakefarm.png",
    pubkey: "214467155aac6beeb17ed5819cc45a0b",
    created_at: "2025-10-23T21:04:02Z",  // UTC timestamp
    display_time: "5:04:02 PM"  // User's local timezone
  }
]
```

**Important:**
- Timestamps are automatically converted to user's timezone
- `display_time` field is ready for display
- Backend detects timezone from browser: `Intl.DateTimeFormat().resolvedOptions().timeZone`

---

#### `fetch(url, options)`
Proxied HTTP fetch through backend (handles CORS and Tor routing).

**Parameters:**
- `url` (String): URL to fetch
- `options` (Object): Standard fetch options (method, headers, body, etc.)

**Returns:** Response object (same as standard fetch)

**Example:**
```javascript
const response = await window.bbs.fetch('/api/chat/post/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Hello world' })
});
const data = await response.json();
```

**Use Cases:**
- Accessing Axon BBS API endpoints
- External API calls (proxied through backend)
- Tor-routed requests (if configured)

---

## Timezone Handling

### How It Works

The backend automatically converts all timestamps from UTC to the user's local timezone:

1. **Browser Detection:** Frontend detects timezone using:
   ```javascript
   const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
   // Example: "America/New_York"
   ```

2. **API Calls:** Timezone is passed as `tz` query parameter:
   ```
   GET /api/applets/{id}/read_events/?tz=America/New_York
   ```

3. **Backend Conversion:** `convert_message_timestamps()` converts UTC to user timezone:
   ```python
   tz = pytz.timezone(user_timezone)  # e.g., America/New_York
   local_time = utc_time.astimezone(tz)
   display_time = f"{hour}:{local_time.strftime('%M:%S %p')}"  # "5:04:02 PM"
   ```

4. **Frontend Display:** Use the `display_time` field directly:
   ```javascript
   timestamp.textContent = msg.display_time;  // "5:04:02 PM"
   ```

### Tor Browser Caveat

**Problem:** Tor Browser spoofs timezone to UTC for privacy/anonymity
**Result:** Users on Tor see UTC times instead of their local timezone
**Solution:** Consider adding a user preference setting for manual timezone selection

---

## BitSync Manifest Structure

When applets are published, they're encrypted using BitSync for secure federation distribution.

**Manifest Example:**
```json
{
  "content_hash": "d0d53a198b6629a2eb8f4c6a7d1234567890abcdef",
  "chunk_size": 262144,
  "chunk_hashes": [
    "85d96cdb50a43d593817ccc19b8ec3ae10c59849432740eb0b3b27b94a0c7455"
  ],
  "encryption_iv": "/EZOlQ1FHXQTi+2FSHVQWA==",
  "encrypted_aes_keys": {
    "214467155aac6beeb17ed5819cc45a0b": "asCBJom4wCzJelOpLHukB08Uj6XJL..."
  }
}
```

**Fields:**
- `content_hash`: SHA256 hash of entire file (unique identifier)
- `chunk_size`: Size of each chunk in bytes (default: 256KB)
- `chunk_hashes`: Array of SHA256 hashes for each chunk
- `encryption_iv`: AES initialization vector (base64)
- `encrypted_aes_keys`: Per-instance encrypted AES keys
  - Key: Instance's short pubkey (16-char hash)
  - Value: AES key encrypted with instance's RSA public key

**File Storage:**
```
data/bitsync_chunks/
├── {chunk_hash}/
│   └── {chunk_hash}.enc  # Encrypted chunk file
```

**How Federation Works:**
1. Publisher creates BitSync manifest with encrypted chunks
2. Manifest is posted to "Applet Library" message board
3. Message syncs to all trusted federation peers
4. Peers download chunks using their instance-specific decryption keys
5. Peers decrypt and verify chunks using SHA256 hashes

---

## Database Models Reference

### Applet Model

**Location:** `applets/models.py`

**Key Fields:**
- `id` (UUID): Primary key
- `name` (String): Applet display name
- `description` (Text): Applet description
- `code_manifest` (JSON): BitSync manifest for applet JavaScript code
- `event_board` (ForeignKey → MessageBoard): Board for applet events
- `is_debug_mode` (Boolean): Enable debug console
- `owner` (ForeignKey → User): Applet owner
- `author_pubkey` (String): Original author's public key
- `parameters` (JSON): Custom applet parameters
- `created_at` (DateTime): Creation timestamp

**Example Query:**
```python
from applets.models import Applet
applet = Applet.objects.get(name='AxonChat')
print(applet.code_manifest['content_hash'])
```

---

### FileAttachment Model

**Location:** `core/models.py`

**Key Fields:**
- `id` (UUID): Primary key
- `filename` (String): Original filename
- `content_type` (String): MIME type (e.g., "application/javascript")
- `size` (Integer): File size in bytes
- `metadata_manifest` (JSON): BitSync manifest for file content
- `author` (ForeignKey → User): File uploader
- `created_at` (DateTime): Upload timestamp

**Example Query:**
```python
from core.models import FileAttachment
attachment = FileAttachment.objects.get(id='81f92070-d3b9-49b0-ae9e-518e6b4f45fa')
print(f"Hash: {attachment.metadata_manifest['content_hash']}")
```

---

### Message Model

**Location:** `messaging/models.py`

**Key Fields:**
- `id` (UUID): Primary key
- `board` (ForeignKey → MessageBoard): Parent board
- `subject` (String): Message subject
- `body` (Text): Message content
- `author` (ForeignKey → User): Message author
- `pubkey` (String): Author's public key hash (16 chars)
- `metadata_manifest` (JSON): BitSync manifest (required for federation sync)
- `attachments` (ManyToMany → FileAttachment): Attached files
- `created_at` (DateTime): Creation timestamp

**Important:** Only messages with `metadata_manifest` sync via federation!

---

## Troubleshooting Guide

### Applet Not Loading

**Symptom:** Applet shows blank screen or error

**Diagnosis:**
```bash
cd /path/to/axon_bbs
source venv/bin/activate
python manage.py shell <<'EOF'
from applets.models import Applet
applet = Applet.objects.get(name='YourApplet')
print("Code manifest:", applet.code_manifest)
print("Content hash:", applet.code_manifest.get('content_hash', 'MISSING'))
EOF
```

**Solutions:**
1. Run `python manage.py update_applet_manifests`
2. Check browser console for JavaScript errors
3. Verify applet file exists: `ls -la frontend/src/applets/YourApplet.js`
4. Check chunks exist: `ls -la data/bitsync_chunks/{content_hash}/`

---

### Messages Not Syncing to Peers

**Symptom:** Applet Library posts not appearing on federated instances

**Cause:** Only messages with `metadata_manifest` field are synced via federation.

**Diagnosis:**
```bash
python manage.py shell <<'EOF'
from messaging.models import Message
msg = Message.objects.filter(subject__contains='AxonChat').first()
if msg.metadata_manifest:
    print(f"✓ Message WILL sync")
    print(f"  Content hash: {msg.metadata_manifest.get('content_hash', 'N/A')[:16]}...")
else:
    print(f"✗ Message will NOT sync (no metadata_manifest)")
EOF
```

**Solution:**
- Always use `post_applet_update` command (creates manifest automatically)
- For manual posts, use `BitSyncService.create_encrypted_content()`

---

### Duplicate Users in Sidebar

**Symptom:** Same user appears multiple times in user list

**Cause:** Incorrect pubkey comparison logic

**Solution:**
```javascript
// WRONG - compares both pubkey and nickname
const isCurrentUser = (userId === currentUserShortId || nickname === userInfo.nickname);

// CORRECT - only compare pubkey (unique identifier)
const isCurrentUser = (userId === currentUserShortId);
```

---

### Users Showing as "Anonymous"

**Symptom:** Usernames not displaying correctly

**Cause:** Checking for wrong field name from backend

**Solution:**
```javascript
// WRONG - author_display doesn't exist
user: event.author_display || event.author || 'Anonymous'

// CORRECT - use author_nickname from backend
user: event.author_nickname || event.author || 'Anonymous'
```

Also ensure avatar is included:
```javascript
avatar_url: event.avatar_url
```

---

### Timezone Issues

**Symptom:** Times shown are wrong by several hours

**Diagnosis:** Add debug logging:
```javascript
const detectedTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
debugLog(`Detected timezone: ${detectedTimezone}`);
debugLog(`UTC: ${msg.created_at}, Display: ${msg.display_time}`);
```

**Common Causes:**
1. **Tor Browser:** Spoofs timezone to UTC for privacy
   - Solution: Add user preference for manual timezone selection
2. **Backend not converting:** Check `convert_message_timestamps()` is called
3. **Missing `tz` parameter:** Verify `readEvents()` passes timezone

**Backend Check:**
```bash
tail -f /tmp/django_host.log | grep -i timezone
```

---

### Clear Python Cache

**When:** After updating models or encountering import errors

```bash
find /path/to/axon_bbs -type d -name __pycache__ -exec rm -rf {} +
find /path/to/axon_bbs -name "*.pyc" -delete
```

---

### Restart Servers

**HostBBS:**
```bash
pkill -9 -f "python.*runserver"
cd /path/to/axon_bbs
source venv/bin/activate
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_host.log 2>&1 &
```

**PiBBS:**
```bash
ssh -p 2222 pibbs@192.168.58.7 'pkill -9 -f "python.*runserver"; cd axon_bbs && source venv/bin/activate && nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_pibbs.log 2>&1 < /dev/null &'
```

---

## File Locations Reference

```
axon_bbs/
├── frontend/src/applets/              # Applet source code (JavaScript)
│   ├── AxonChat.js                    # Chat applet
│   ├── HexGL.js                       # Racing game
│   ├── VideoPlayer.js                 # Video player
│   └── ...
├── data/bitsync_chunks/               # Encrypted applet chunks
│   └── {chunk_hash}/
│       └── {chunk_hash}.enc
├── core/
│   ├── services/
│   │   ├── bitsync_service.py         # BitSync encryption/decryption
│   │   └── sync_service.py            # Federation sync
│   ├── views/
│   │   ├── applet_events.py           # SSE event streaming (deprecated)
│   │   └── realtime_board_events.py   # Realtime board SSE
│   └── management/commands/
│       ├── update_applet_manifests.py # Update all applet manifests
│       └── post_applet_update.py      # Post applet to Applet Library
├── applets/
│   ├── models.py                      # Applet model definition
│   ├── views.py                       # ReadAppletEventsView API
│   └── admin.py                       # Django admin interface
├── messaging/
│   ├── models.py                      # Message, MessageBoard models
│   └── admin.py                       # Message admin (Rekey action)
├── frontend/src/components/
│   └── AppletRunner.js                # Applet iframe container & API bridge
└── docs/
    ├── Server_Management_Guide.md     # Server operations
    └── Applet_Publishing_Guide.md     # This document
```

---

## Management Commands Reference

**Location:** `core/management/commands/`

### update_applet_manifests

**Purpose:** Update BitSync manifests for all applets

**Usage:**
```bash
python manage.py update_applet_manifests
```

**What it does:**
- Scans `frontend/src/applets/` directory
- Reads each `.js` file
- Creates/updates BitSync manifest (encryption, chunking, hashing)
- Saves chunks to `data/bitsync_chunks/`
- Updates `Applet.code_manifest` in database
- Re-keys manifests for all trusted instances

---

### post_applet_update

**Purpose:** Post applet update to Applet Library board

**Usage:**
```bash
python manage.py post_applet_update <applet_path> --name <name> --description <desc>
```

**Parameters:**
- `applet_path`: Path to applet JS file (required)
- `--name`: Applet name (required)
- `--description`: Update description (optional)
- `--username`: Post as specific user (optional, default: current admin)
- `--board`: Target board (optional, default: "Applet Library")

**Example:**
```bash
python manage.py post_applet_update frontend/src/applets/AxonChat.js \
  --name "AxonChat" \
  --description "v21: Bug fixes"
```

**What it does:**
1. Creates BitSync manifest for applet file
2. Creates FileAttachment record
3. Creates BitSync manifest for message (enables federation)
4. Posts message to Applet Library board
5. Updates applet's `code_manifest`
6. Message auto-syncs to federated peers

---

### check_applet_manifest

**Purpose:** Verify applet manifest integrity

**Usage:**
```bash
python manage.py check_applet_manifest <applet_name>
```

---

### backup_applets

**Purpose:** Backup all applet code and manifests

**Usage:**
```bash
python manage.py backup_applets
```

---

### sync_applets_from_peer

**Purpose:** Sync applets from federated peer

**Usage:**
```bash
python manage.py sync_applets_from_peer --peer-url http://192.168.58.7:8000
```

---

## Best Practices for AI

### When Creating Applets

1. **Always include the API helper** - Use the exact boilerplate from Step 1
2. **Use semantic versioning** - `APPLET_VERSION = "v1.0"`, `v1.1`, `v2.0`
3. **Add debug logging** - Help troubleshoot issues in production
4. **Handle errors gracefully** - Wrap API calls in try/catch
5. **Use async/await** - All BBS API methods are async
6. **Test locally first** - Use HostBBS before deploying to PiBBS

### When Publishing Applets

1. **Update version number** - Increment `APPLET_VERSION` before publishing
2. **Write descriptive commit messages** - Explain what changed and why
3. **Use post_applet_update command** - Don't manually create manifests
4. **Test on both instances** - HostBBS and PiBBS
5. **Check federation sync** - Verify message has `metadata_manifest`

### Security Considerations

1. **Never trust user input** - Sanitize before rendering
2. **Use textContent, not innerHTML** - Prevents XSS
3. **Validate API responses** - Backend can return errors
4. **Don't store secrets in applet code** - Code is public/federated
5. **Respect user privacy** - Especially with Tor Browser users

---

## Federation Architecture

### How Applets Sync Across Instances

1. **Developer** publishes applet on HostBBS using `post_applet_update`
2. **Message created** on "Applet Library" board with BitSync manifest
3. **Message syncs** to all trusted federation peers automatically
4. **Peers download** encrypted chunks using their instance keys
5. **Peers decrypt** chunks and verify integrity with SHA256 hashes
6. **Peers update** their local applet manifest

### Instance Trust Model

**TrustedInstance Model:**
- Each instance has RSA keypair (public/private)
- Manifests encrypted with AES-256
- AES key encrypted with each instance's RSA public key
- Only trusted instances can decrypt content

**Security:**
- Content is encrypted at rest
- Chunks stored separately from keys
- Each instance has unique decryption key
- SHA256 hashing ensures integrity

---

## Example Applet: AxonChat

See `frontend/src/applets/AxonChat.js` for a complete, production-ready example.

**Features:**
- Real-time federated chat
- User sidebar with avatars
- Timezone-aware timestamps
- Polling-based updates (2 second interval)
- Debug console (when `is_debug_mode=True`)

**Key Techniques:**
- Uses `postEvent()` to send messages
- Uses `readEvents()` to fetch messages
- Filters events by `subject === 'AxonChat'`
- Tracks processed message IDs to avoid duplicates
- Updates active users based on recent messages
- Renders messages incrementally for performance

---

## Changelog

**Version 1.0 (October 23, 2025):**
- Initial guide created
- Documented v20 and v21 AxonChat updates
- Complete publishing workflow
- API reference
- Troubleshooting guide
- File locations and architecture

---

**Document Author:** Claude Code
**Project:** Axon BBS
**Repository:** https://github.com/achgulp/axon_bbs
