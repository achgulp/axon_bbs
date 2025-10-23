# Axon BBS - Technical Architecture

**Version**: 10.27.0+
**Last Updated**: October 23, 2025

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture](#core-architecture)
3. [BitSync Protocol](#bitsync-protocol)
4. [Real-Time Communication](#real-time-communication)
5. [Applet Framework](#applet-framework)
6. [Federation](#federation)
7. [Security Architecture](#security-architecture)
8. [Data Model](#data-model)
9. [API Design](#api-design)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

Axon BBS is a federated, anonymous bulletin board system built on a foundation of cryptographic security and peer-to-peer data synchronization. The architecture is designed around three core principles:

1. **Security by Default**: All data encrypted, all code sandboxed, all requests authenticated
2. **Decentralization**: No single point of failure, peer-to-peer federation
3. **Extensibility**: Sandboxed applet framework for unlimited functionality

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                            │
│  ┌────────────────────┐         ┌─────────────────────────┐ │
│  │   React SPA        │         │   Tor Browser           │ │
│  │   - Message UI     │         │   - Anonymity          │ │
│  │   - Chat UI        │         │   - .onion Access      │ │
│  │   - AppletRunner   │         │                         │ │
│  └────────────────────┘         └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ HTTPS
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Django REST │  │  Services    │  │  Background      │  │
│  │  API         │  │  Layer       │  │  Services        │  │
│  │              │  │              │  │  - RealtimeMsg   │  │
│  │  - Auth      │  │  - BitSync   │  │  - Federation    │  │
│  │  - Messages  │  │  - Sync      │  │  - Cleanup       │  │
│  │  - Chat      │  │  - Crypto    │  │                  │  │
│  │  - Applets   │  │              │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↕
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ PostgreSQL   │  │  Filesystem  │  │  Tor Network     │  │
│  │  - Users     │  │  - Chunks    │  │  - Peers         │  │
│  │  - Messages  │  │  - Media     │  │  - Federation    │  │
│  │  - Manifests │  │  - Avatars   │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Architecture

### Technology Stack

**Backend:**
```
Django 4.2+
├── Python 3.8+
├── PostgreSQL 12+
├── Cryptography (RSA, AES-256-GCM)
├── Requests + PySocks (Tor)
└── PyJWT (Authentication)
```

**Frontend:**
```
React 18
├── Axios (API Client)
├── Tailwind CSS
├── Create React App
└── Modern ES6+ JavaScript
```

**Infrastructure:**
```
Tor
├── Hidden Services (.onion)
├── SOCKS5 Proxy
└── Anonymous Routing

PostgreSQL
├── JSONB for manifests
├── Full-text search
└── Cryptographic key storage
```

### Backend Module Structure

The backend is organized into feature-specific Django apps:

```
axon_bbs/
├── core/                     # Core cross-cutting concerns
│   ├── models.py            # User, TrustedInstance, FileAttachment
│   ├── services/
│   │   ├── bitsync_service.py      # Content-addressed storage
│   │   ├── sync_service.py         # Federation sync logic
│   │   └── crypto_service.py       # Encryption utilities
│   ├── views/
│   │   ├── applet_events.py        # Event bus API
│   │   └── content_stream.py       # Chunk downloads
│   └── management/commands/         # CLI tools
│
├── accounts/                 # User management
│   ├── models.py            # IgnoredPubkey, BannedPubkey
│   └── views.py             # Profile, authentication
│
├── messaging/                # Message boards
│   ├── models.py            # MessageBoard, Message, PrivateMessage
│   ├── services/
│   │   └── realtime_message_service.py  # Chat federation
│   └── views.py             # Board and message APIs
│
├── applets/                  # Applet framework
│   ├── models.py            # Applet, AppletData, HighScore
│   └── views.py             # Applet APIs (data, events)
│
├── federation/               # Inter-server communication
│   ├── models.py            # FederatedAction
│   ├── views.py             # Federation endpoints
│   └── services/
│       └── federation_service.py    # Peer sync logic
│
└── axon_project/             # Django project settings
    ├── settings.py
    ├── urls.py
    └── wsgi.py
```

### Service-Oriented Architecture

Business logic is encapsulated in service classes, keeping views "thin":

```python
# Example: Message creation flow

# 1. View receives HTTP request
class CreateMessageView(APIView):
    def post(self, request):
        # Minimal validation
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Delegate to service
        message = MessageService.create_message(
            author=request.user,
            board_id=serializer.data['board_id'],
            body=serializer.data['body'],
            attachments=request.FILES.getlist('attachments')
        )

        return Response(MessageSerializer(message).data)

# 2. Service handles business logic
class MessageService:
    @staticmethod
    def create_message(author, board_id, body, attachments=None):
        # Create message
        message = Message.objects.create(...)

        # Process attachments
        if attachments:
            for file in attachments:
                # BitSync handles encryption & chunking
                manifest = BitSyncService.create_encrypted_content(
                    file, author.pubkey
                )
                FileAttachment.objects.create(
                    content_hash=manifest['content_hash'],
                    manifest=manifest,
                    message=message
                )

        # Trigger federation
        FederationService.broadcast_message(message)

        return message
```

**Benefits:**
- Thin views (HTTP-only concerns)
- Testable business logic
- Reusable services
- Clear separation of concerns

---

## BitSync Protocol

BitSync is Axon BBS's content-addressed P2P synchronization protocol. All content is identified, encrypted, and verified by cryptographic hashes.

### Content Addressing

Every piece of content (message, file, applet code) is:
1. **Chunked** into 512KB pieces
2. **Encrypted** with AES-256-GCM (unique key per content)
3. **Hashed** with SHA-256 (becomes the content_hash)
4. **Manifested** with chunk list and encrypted AES keys

```
┌─────────────────────────────────────────────────────────┐
│             BitSync Content Creation                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Original File: applet.js (2MB)                        │
│         ↓                                               │
│  ┌──────────────────────────────────────┐              │
│  │  1. Chunking (512KB each)            │              │
│  │     ├─ Chunk 0: bytes 0-524287       │              │
│  │     ├─ Chunk 1: bytes 524288-1048575 │              │
│  │     ├─ Chunk 2: bytes 1048576-1572863│              │
│  │     └─ Chunk 3: bytes 1572864-2097151│              │
│  └──────────────────────────────────────┘              │
│         ↓                                               │
│  ┌──────────────────────────────────────┐              │
│  │  2. Generate Random AES-256 Key      │              │
│  │     aes_key = os.urandom(32)         │              │
│  └──────────────────────────────────────┘              │
│         ↓                                               │
│  ┌──────────────────────────────────────┐              │
│  │  3. Encrypt Each Chunk               │              │
│  │     for chunk in chunks:             │              │
│  │       nonce = os.urandom(12)         │              │
│  │       encrypted = AES256GCM.encrypt( │              │
│  │         chunk, aes_key, nonce        │              │
│  │       )                               │              │
│  │       store(encrypted + nonce + tag) │              │
│  └──────────────────────────────────────┘              │
│         ↓                                               │
│  ┌──────────────────────────────────────┐              │
│  │  4. Hash Encrypted Chunks            │              │
│  │     chunk_hashes = [                 │              │
│  │       sha256(enc_chunk_0),           │              │
│  │       sha256(enc_chunk_1),           │              │
│  │       ...                             │              │
│  │     ]                                 │              │
│  └──────────────────────────────────────┘              │
│         ↓                                               │
│  ┌──────────────────────────────────────┐              │
│  │  5. Encrypt AES Key for Each Peer   │              │
│  │     encrypted_aes_keys = {           │              │
│  │       "local": RSA_encrypt(          │              │
│  │         aes_key, local_pubkey        │              │
│  │       ),                              │              │
│  │       "peer1.onion": RSA_encrypt(    │              │
│  │         aes_key, peer1_pubkey        │              │
│  │       )                               │              │
│  │     }                                 │              │
│  └──────────────────────────────────────┘              │
│         ↓                                               │
│  ┌──────────────────────────────────────┐              │
│  │  6. Create Manifest                  │              │
│  │     {                                 │              │
│  │       "content_hash": sha256(all),   │              │
│  │       "encrypted_aes_keys": {...},   │              │
│  │       "chunks": chunk_hashes,        │              │
│  │       "size": 2097152,               │              │
│  │       "created_at": "2025-10-23..."  │              │
│  │     }                                 │              │
│  └──────────────────────────────────────┘              │
│         ↓                                               │
│  FileAttachment(                                       │
│    content_hash="abc123...",                           │
│    manifest={...}                                      │
│  )                                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Manifest Structure

```json
{
  "content_hash": "a1b2c3d4e5f6...",
  "encrypted_aes_keys": {
    "local_instance": "RSA-encrypted-base64...",
    "http://peer1.onion": "RSA-encrypted-base64...",
    "http://peer2.onion": "RSA-encrypted-base64..."
  },
  "chunks": [
    "chunk0_hash_sha256",
    "chunk1_hash_sha256",
    "chunk2_hash_sha256"
  ],
  "size": 2097152,
  "chunk_size": 524288,
  "created_at": "2025-10-23T15:30:00Z",
  "metadata": {
    "filename": "applet.js",
    "mime_type": "application/javascript"
  }
}
```

### Content Retrieval

```python
# Client requests content
GET /api/content/stream/a1b2c3d4e5f6/?for_verification

# Backend flow:
1. Find FileAttachment by content_hash
2. Load manifest from database
3. Decrypt AES key using instance's private RSA key
4. For each chunk:
   a. Read encrypted chunk from filesystem
   b. Verify SHA-256 hash
   c. Decrypt using AES key
   d. Append to output buffer
5. Return complete decrypted content
```

### Re-keying

When restoring content to a different instance, AES keys must be re-encrypted for the new instance's public key:

```python
def rekey_manifest(manifest, new_pubkey):
    """Re-key manifest for new instance"""
    # 1. Decrypt AES key using current instance's private key
    encrypted_key = manifest['encrypted_aes_keys']['local_instance']
    aes_key = decrypt_with_private_key(encrypted_key)

    # 2. Re-encrypt AES key for new instance
    new_encrypted_key = encrypt_with_public_key(aes_key, new_pubkey)

    # 3. Add new key to manifest (keep old keys!)
    manifest['encrypted_aes_keys'][new_pubkey] = new_encrypted_key

    return manifest
```

### Deduplication

Content with identical data shares the same content_hash:

```python
# User A uploads cat.jpg
manifest_a = BitSyncService.create_encrypted_content(cat.jpg)
# content_hash: "abc123..."

# User B uploads same cat.jpg
manifest_b = BitSyncService.create_encrypted_content(cat.jpg)
# content_hash: "abc123..." (same!)

# Storage: Only one copy of chunks on disk
# Database: Two FileAttachment records, same content_hash
# Benefits: Saves disk space, faster federation sync
```

---

## Real-Time Communication

### AxonChat Architecture

AxonChat provides sub-second real-time messaging using a polling-based architecture:

```
┌──────────────────────────────────────────────────────────┐
│              AxonChat Real-Time Flow                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  User types message in AxonChat UI                      │
│    ↓                                                     │
│  POST /api/chat/post/                                   │
│    { "text": "Hello, world!" }                          │
│    ↓                                                     │
│  Message.objects.create(                                │
│    board_id=9,  # AxonChat board                       │
│    subject='AxonChat',                                  │
│    body='Hello, world!',                                │
│    author=user                                          │
│  )                                                       │
│    ↓                                                     │
│  [Message stored in database]                           │
│    ↓                                                     │
│  RealtimeMessageService detects new message             │
│    (polls database every 1 second)                      │
│    ↓                                                     │
│  Broadcasts to federation peers:                        │
│    POST http://peer1.onion/api/rooms/axonchat/state/   │
│    {                                                     │
│      "messages": [{...}],                               │
│      "version": 123                                     │
│    }                                                     │
│    ↓                                                     │
│  [Peer receives and stores message]                    │
│    ↓                                                     │
│  AxonChat.js polls for updates                          │
│    (every 2 seconds)                                    │
│    GET /api/applets/{id}/read_events/                  │
│    ↓                                                     │
│  Returns new messages:                                  │
│    {                                                     │
│      "events": [                                        │
│        {                                                 │
│          "id": 123,                                     │
│          "subject": "AxonChat",                         │
│          "body": "{\"text\":\"Hello, world!\"}",       │
│          "author_nickname": "Alice",                    │
│          "display_time": "3:45 PM"                      │
│        }                                                 │
│      ]                                                   │
│    }                                                     │
│    ↓                                                     │
│  AxonChat.js renders new message                        │
│  User sees message (total time: 1-3 seconds)           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### MessageBoard Event Bus

The `MessageBoard` model serves as an event bus for real-time applications:

```python
class MessageBoard(models.Model):
    name = models.CharField(max_length=255)
    is_realtime = models.BooleanField(default=False)
    federation_room_id = models.CharField(max_length=100, null=True)
    trusted_peers = models.JSONField(default=list)
    message_retention_days = models.IntegerField(default=90)

    # Messages on this board
    messages = Message.objects.filter(board=self)
```

**Key Fields:**
- `is_realtime`: Enables real-time polling/federation
- `federation_room_id`: Unique identifier across federated instances
- `trusted_peers`: List of .onion URLs to federate with
- `message_retention_days`: Auto-delete old messages

### RealtimeMessageService

Background service that federates chat messages:

```python
class RealtimeMessageService:
    """
    Polls realtime boards every 1 second.
    Syncs new messages to trusted peers.
    """

    def run(self):
        while True:
            # Find boards with realtime enabled
            realtime_boards = MessageBoard.objects.filter(
                is_realtime=True
            )

            for board in realtime_boards:
                # Get messages since last sync
                new_messages = board.messages.filter(
                    created_at__gt=board.last_sync_time
                )

                if new_messages.exists():
                    # Broadcast to peers
                    for peer_url in board.trusted_peers:
                        self.sync_to_peer(peer_url, board, new_messages)

                    # Update sync time
                    board.last_sync_time = timezone.now()
                    board.save()

            time.sleep(1)  # Poll interval

    def sync_to_peer(self, peer_url, board, messages):
        """Sync messages to peer via authenticated request"""
        payload = {
            'messages': [serialize(m) for m in messages],
            'room_id': board.federation_room_id,
            'version': board.version
        }

        # Sign request with instance private key
        signature = sign_request(payload)

        # Send to peer
        requests.post(
            f'{peer_url}/api/rooms/{board.federation_room_id}/state/',
            json=payload,
            headers={
                'X-Pubkey': instance_pubkey,
                'X-Signature': signature,
                'X-Timestamp': str(time.time())
            },
            proxies={'http': 'socks5h://127.0.0.1:9050'}  # Tor
        )
```

### Client-Side Polling

AxonChat uses client-side polling instead of WebSockets/SSE for reliability:

```javascript
// AxonChat.js

let processedMessageIds = new Set();

async function pollForMessages() {
    try {
        // Get all events for this applet
        const events = await window.bbs.readEvents();

        // Filter by subject and dedup
        const newMessages = events.filter(e =>
            e.subject === 'AxonChat' &&
            !processedMessageIds.has(e.id)
        );

        if (newMessages.length > 0) {
            // Sort chronologically
            newMessages.sort((a, b) =>
                new Date(a.created_at) - new Date(b.created_at)
            );

            // Mark as processed
            newMessages.forEach(e => processedMessageIds.add(e.id));

            // Render
            newMessages.forEach(renderMessage);
        }
    } catch (err) {
        console.error('Poll error:', err);
    }
}

// Poll every 2 seconds
setInterval(pollForMessages, 2000);
```

**Why Polling Instead of SSE/WebSockets?**
1. **Simplicity**: No complex connection management
2. **Reliability**: Works through Tor, proxies, firewalls
3. **Debugging**: Easy to inspect requests in DevTools
4. **Stateless**: No server-side connection state
5. **Tor-friendly**: Tor doesn't handle persistent connections well

---

## Applet Framework

### Security Model

Applets run in sandboxed iframes with strict security:

```html
<iframe
  title="Applet Name"
  srcDoc="<!DOCTYPE html>..."
  sandbox="allow-scripts allow-same-origin"
/>
```

**Sandbox Restrictions:**
- ❌ No `fetch()` or `XMLHttpRequest` to external domains
- ❌ No access to `parent.document` or `window.top`
- ❌ No `localStorage` or cookies outside iframe
- ❌ No form submission to external URLs
- ❌ No plugin execution
- ✅ JavaScript execution allowed
- ✅ Same-origin communication via `postMessage`

### postMessage API Bridge

Applets communicate with the BBS via a `window.bbs` API implemented using `postMessage`:

```javascript
// AppletRunner.js (parent window)
window.addEventListener('message', (event) => {
    if (event.source !== iframeRef.current.contentWindow) return;

    const { command, payload, requestId } = event.data;

    // Route command to backend
    let response;
    switch (command) {
        case 'getUserInfo':
            response = await apiClient.get('/api/user/profile/');
            break;
        case 'saveData':
            response = await apiClient.post(`/api/applets/${appletId}/data/`, payload);
            break;
        // ... other commands
    }

    // Send response back to iframe
    iframeRef.current.contentWindow.postMessage({
        command: `response_${command}`,
        requestId,
        payload: response.data
    }, '*');
});
```

```javascript
// window.bbs helper (inside applet iframe)
window.bbs = {
    _callbacks: {},
    _requestId: 0,

    _postMessage: function(command, payload = {}) {
        return new Promise((resolve, reject) => {
            const requestId = this._requestId++;
            this._callbacks[requestId] = { resolve, reject };
            window.parent.postMessage({ command, payload, requestId }, '*');
        });
    },

    getUserInfo: function() {
        return this._postMessage('getUserInfo');
    },

    saveData: function(data) {
        return this._postMessage('saveData', data);
    }
};

window.addEventListener('message', (event) => {
    const { command, requestId, payload, error } = event.data;
    if (command && command.startsWith('response_')) {
        const { resolve, reject } = window.bbs._callbacks[requestId];
        if (error) reject(new Error(error));
        else resolve(payload);
        delete window.bbs._callbacks[requestId];
    }
});
```

### Integrity Verification

Before executing applet code, AppletRunner verifies its SHA-256 hash:

```javascript
// AppletRunner.js

const codeUrl = `/api/content/stream/${applet.code_manifest.content_hash}/?for_verification`;
const receivedPayloadString = await fetch(codeUrl).then(r => r.text());

// Compute SHA-256 in browser
const calculatedHash = await sha256(receivedPayloadString);

// Verify against manifest
if (calculatedHash !== applet.code_manifest.content_hash) {
    throw new Error(`
        Code integrity check failed.
        Expected: ${applet.code_manifest.content_hash}
        Calculated: ${calculatedHash}
        The downloaded applet code may be corrupted or tampered with.
    `);
}

// Hash matches - safe to execute
```

### Hybrid Architecture

Large applets (games, 3D apps) use a hybrid architecture:

**Applet Code** (10-50KB JavaScript):
- Small loader that initializes the app
- Requests asset package from BBS
- Unpacks assets in memory
- Bootstraps main application

**Asset Package** (1-50MB ZIP):
- Models, textures, audio, fonts
- Stored as separate FileAttachment
- Referenced in applet `parameters.asset_package_hash`
- Loaded on-demand via `bbs.getAttachmentBlob()`

**Example: HexGL Loading Flow**

```javascript
// hexgl.js (17KB loader)

(async function() {
    const root = document.getElementById('applet-root');

    // Show progress indicator
    function showProgress(message, percent) {
        root.innerHTML = `
            <div class="loader">
                <p>${message}</p>
                <div class="progress-bar" style="width: ${percent}%"></div>
            </div>
        `;
    }

    showProgress('Fetching configuration...', 5);

    // 1. Get asset package hash from applet config
    const info = await window.bbs.getAppletInfo();
    const assetHash = info.parameters.asset_package_hash;

    if (!assetHash) {
        throw new Error('No asset package configured');
    }

    showProgress(`Downloading assets (${assetHash.substr(0, 8)}...)`, 15);

    // 2. Download asset package (5MB ZIP)
    const assetBlob = await window.bbs.getAttachmentBlob(assetHash);

    showProgress('Decompressing assets...', 40);

    // 3. Unzip in memory using JSZip
    const zip = await JSZip.loadAsync(assetBlob);
    const assets = {};

    for (const filename in zip.files) {
        if (zip.files[filename].dir) continue;
        const fileBlob = await zip.files[filename].async("blob");
        assets[filename] = URL.createObjectURL(fileBlob);
    }

    showProgress('Starting game...', 95);

    // 4. Initialize THREE.js game with asset URLs
    initializeGame(assets);
})();

function initializeGame(assets) {
    // Load models
    const loader = new THREE.GLTFLoader();
    loader.load(assets['ship.gltf'], (gltf) => {
        scene.add(gltf.scene);
    });

    // Load textures
    const texture = new THREE.TextureLoader().load(assets['track.png']);

    // Start game loop
    animate();
}
```

**Benefits:**
- Small initial load (17KB vs 5MB)
- Progress indicator during asset download
- Assets cached as blob URLs
- Works with large games and apps

---

## Federation

### Peer Discovery & Trust

Federation in Axon BBS is whitelist-based. Only explicitly trusted peers can sync:

```python
class TrustedInstance(models.Model):
    base_url = models.CharField(max_length=255)  # http://peer.onion
    is_trusted_peer = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True)
    pubkey = models.TextField()  # Peer's public key
    nickname = models.CharField(max_length=50)

    # Federation status
    is_syncing = models.BooleanField(default=False)
    last_sync_time = models.DateTimeField(null=True)
    sync_errors = models.IntegerField(default=0)
```

**Adding a Peer:**
1. Admin enters peer's .onion URL
2. System fetches peer's public key via `/api/federation/identity/`
3. Admin marks as "Trusted Peer"
4. Federation begins automatically

### Request Signing

All federation requests are signed with RSA-PSS:

```python
def sign_request(payload, private_key):
    """Sign request payload with instance private key"""
    message = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def verify_signature(payload, signature, public_key):
    """Verify request came from claimed peer"""
    message = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature_bytes = base64.b64decode(signature)

    try:
        public_key.verify(
            signature_bytes,
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return True
    except:
        return False
```

**Request Headers:**
```http
POST /api/rooms/global-chat/state/
Host: peer.onion
X-Pubkey: -----BEGIN PUBLIC KEY-----...
X-Timestamp: 1697895432.123
X-Signature: base64-encoded-signature...
Content-Type: application/json

{
  "messages": [...],
  "room_id": "global-chat",
  "version": 123
}
```

**Verification on Receiving End:**
```python
def federation_endpoint(request):
    # Extract headers
    pubkey = request.headers.get('X-Pubkey')
    timestamp = request.headers.get('X-Timestamp')
    signature = request.headers.get('X-Signature')

    # Verify timestamp (prevent replay attacks)
    if abs(time.time() - float(timestamp)) > 300:  # 5 minutes
        return JsonResponse({'error': 'Timestamp too old'}, status=400)

    # Verify signature
    payload = json.loads(request.body)
    if not verify_signature(payload, signature, load_public_key(pubkey)):
        return JsonResponse({'error': 'Invalid signature'}, status=403)

    # Verify peer is trusted
    if not TrustedInstance.objects.filter(pubkey=pubkey, is_trusted_peer=True).exists():
        return JsonResponse({'error': 'Untrusted peer'}, status=403)

    # Process request
    ...
```

### Content Synchronization

When a peer syncs content (applets, messages, etc.), the flow is:

```
┌──────────────────────────────────────────────────────────┐
│           Federation Content Sync Flow                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  PEER A (Source)                 PEER B (Destination)   │
│                                                          │
│  1. Applet published                                    │
│     ├─ Code uploaded                                    │
│     ├─ Manifest created                                 │
│     └─ Message posted to board                          │
│         ↓                                                │
│  2. RealtimeMessageService detects new post             │
│         ↓                                                │
│  3. Broadcast to Peer B                                 │
│     POST /api/boards/sync/                              │
│     {                                                    │
│       "messages": [{                                    │
│         "id": "uuid",                                   │
│         "body": "New applet!",                          │
│         "attachments": [{                               │
│           "content_hash": "abc123",                     │
│           "manifest": {...}                             │
│         }]                                               │
│       }]                                                 │
│     }                                                    │
│                              ↓                           │
│                       4. Peer B receives message        │
│                          ├─ Verifies signature          │
│                          ├─ Creates Message record      │
│                          └─ Notes missing chunk abc123  │
│                              ↓                           │
│                       5. Download chunks                │
│                          GET /api/content/stream/abc123 │
│                          ←─────────────────────         │
│  6. Return encrypted chunks                             │
│     [chunk0][chunk1][chunk2]                            │
│     ─────────────────────→                              │
│                              ↓                           │
│                       7. Peer B processes               │
│                          ├─ Verifies chunk hashes       │
│                          ├─ Re-keys manifest            │
│                          │  (adds own pubkey)           │
│                          ├─ Stores chunks locally       │
│                          └─ Content now available       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Tor Integration

All federation traffic routes through Tor:

```python
import requests

TOR_PROXY = 'socks5h://127.0.0.1:9050'

def fetch_from_peer(peer_url, endpoint):
    """Fetch data from peer via Tor"""
    response = requests.get(
        f'{peer_url}{endpoint}',
        proxies={
            'http': TOR_PROXY,
            'https': TOR_PROXY
        },
        timeout=60
    )
    return response.json()
```

**Tor Configuration:**
```bash
# /etc/tor/torrc

HiddenServiceDir /var/lib/tor/axon_bbs/
HiddenServicePort 80 127.0.0.1:8000

# Result: BBS accessible at http://xnjzv3k7gd2yw5l3...mhid.onion
```

---

## Security Architecture

### Encryption Layers

Axon BBS uses multiple layers of encryption:

```
┌─────────────────────────────────────────────────────────┐
│                 Encryption Layers                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 4: Transport (Tor)                              │
│  ├─ Onion routing (3 hops)                             │
│  ├─ End-to-end encryption                              │
│  └─ IP anonymity                                        │
│      ↓                                                  │
│  Layer 3: HTTPS (Optional, for clearnet)               │
│  ├─ TLS 1.3                                            │
│  └─ Certificate validation                             │
│      ↓                                                  │
│  Layer 2: BitSync Content Encryption                   │
│  ├─ AES-256-GCM (content)                              │
│  ├─ RSA-OAEP (key distribution)                        │
│  └─ Per-content unique keys                            │
│      ↓                                                  │
│  Layer 1: Database Encryption (Django Field Encryption)│
│  ├─ Private keys encrypted at rest                     │
│  ├─ Session tokens hashed                              │
│  └─ Passwords hashed (Argon2)                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌──────────────────────────────────────────────────────────┐
│              User Authentication Flow                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. User submits username + password                    │
│     POST /api/auth/login/                               │
│     { "username": "alice", "password": "..." }          │
│         ↓                                                │
│  2. Backend validates credentials                       │
│     ├─ Load user from database                          │
│     ├─ Verify password hash (Argon2)                    │
│     └─ Check account status (active, banned, etc.)      │
│         ↓                                                │
│  3. Generate JWT token                                  │
│     token = jwt.encode({                                │
│       'user_id': user.id,                               │
│       'username': user.username,                        │
│       'exp': datetime.now() + timedelta(days=7)         │
│     }, SECRET_KEY)                                       │
│         ↓                                                │
│  4. Return token + user data                            │
│     {                                                    │
│       "token": "eyJhbGciOiJIUzI1NiIs...",               │
│       "user": {                                          │
│         "id": 1,                                         │
│         "username": "alice",                            │
│         "pubkey": "-----BEGIN PUBLIC KEY-----..."       │
│       }                                                  │
│     }                                                    │
│         ↓                                                │
│  5. Client stores token                                 │
│     localStorage.setItem('authToken', token)            │
│         ↓                                                │
│  6. Client includes token in all requests               │
│     axios.get('/api/messages/', {                       │
│       headers: {                                         │
│         'Authorization': `Bearer ${token}`              │
│       }                                                  │
│     })                                                   │
│         ↓                                                │
│  7. Backend validates token on each request             │
│     decoded = jwt.decode(token, SECRET_KEY)             │
│     user = User.objects.get(id=decoded['user_id'])      │
│     request.user = user                                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Permission System

```python
class User(AbstractBaseUser):
    """Custom user model with role-based permissions"""

    # Roles
    is_sysop = models.BooleanField(default=False)     # Full admin
    is_moderator = models.BooleanField(default=False)  # Moderation powers
    is_agent = models.BooleanField(default=False)      # Backend service

    # Restrictions
    is_banned = models.BooleanField(default=False)
    can_post = models.BooleanField(default=True)
    can_upload = models.BooleanField(default=True)

    # Karma (reputation)
    karma = models.IntegerField(default=0)

    def has_permission(self, action):
        """Check if user can perform action"""
        if self.is_banned:
            return False

        if action == 'moderate':
            return self.is_moderator or self.is_sysop

        if action == 'admin':
            return self.is_sysop

        if action == 'post':
            return self.can_post

        if action == 'upload':
            return self.can_upload and self.karma >= 10

        return True
```

---

## Data Model

### Core Models

**User**
```python
class User(AbstractBaseUser):
    username = CharField(unique=True)
    nickname = CharField(max_length=50)
    pubkey = TextField()  # RSA public key
    encrypted_private_key = TextField()  # AES-encrypted RSA private key
    avatar_url = CharField()
    karma = IntegerField(default=0)
    timezone = CharField(default='UTC')

    # Permissions
    is_sysop = BooleanField(default=False)
    is_moderator = BooleanField(default=False)
    is_agent = BooleanField(default=False)
    is_banned = BooleanField(default=False)
```

**Message**
```python
class Message(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    board = ForeignKey(MessageBoard, on_delete=CASCADE)
    author = ForeignKey(User, on_delete=SET_NULL, null=True)
    subject = CharField(max_length=255)
    body = TextField()
    pubkey = TextField()  # Author's pubkey at time of posting
    created_at = DateTimeField(auto_now_add=True)

    # Real-time event bus fields
    is_event = BooleanField(default=False)
    event_subject = CharField(max_length=100, null=True)
```

**MessageBoard**
```python
class MessageBoard(models.Model):
    name = CharField(max_length=255)
    description = TextField()
    is_realtime = BooleanField(default=False)
    federation_room_id = CharField(max_length=100, null=True, unique=True)
    trusted_peers = JSONField(default=list)
    message_retention_days = IntegerField(default=90)
```

**Applet**
```python
class Applet(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(max_length=255)
    description = TextField()
    code_manifest = JSONField()  # BitSync manifest
    parameters = JSONField(default=dict)  # Custom config
    is_debug_mode = BooleanField(default=False)

    # For user-uploaded applets
    owner = ForeignKey(User, null=True)
    is_active = BooleanField(default=True)
```

**FileAttachment**
```python
class FileAttachment(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    content_hash = CharField(max_length=64, db_index=True)
    manifest = JSONField()  # BitSync manifest
    filename = CharField(max_length=255)
    size = IntegerField()
    mime_type = CharField(max_length=100)
    author = ForeignKey(User, null=True)
    created_at = DateTimeField(auto_now_add=True)
```

**TrustedInstance**
```python
class TrustedInstance(models.Model):
    base_url = CharField(max_length=255, unique=True)
    pubkey = TextField()
    nickname = CharField(max_length=50)
    is_trusted_peer = BooleanField(default=False)
    last_seen = DateTimeField(null=True)
    last_sync_time = DateTimeField(null=True)
```

### Database Schema Diagram

```
┌─────────────┐         ┌──────────────┐
│    User     │────────>│   Message    │
│             │ 1     * │              │
│ - username  │         │ - subject    │
│ - pubkey    │         │ - body       │
│ - karma     │         │ - created_at │
└─────────────┘         └──────────────┘
      │                        │
      │ 1                      │ *
      │                        │
      ↓ *                      ↓ 1
┌─────────────┐         ┌──────────────┐
│   Applet    │         │ MessageBoard │
│             │         │              │
│ - name      │         │ - name       │
│ - manifest  │         │ - is_realtime│
│ - parameters│         │ - room_id    │
└─────────────┘         └──────────────┘
      │
      │ 1
      │
      ↓ *
┌──────────────┐
│ AppletData   │
│              │
│ - user       │
│ - applet     │
│ - data (JSON)│
└──────────────┘

┌──────────────────┐
│ FileAttachment   │
│                  │
│ - content_hash   │
│ - manifest (JSON)│
│ - filename       │
└──────────────────┘
```

---

## API Design

### RESTful Endpoints

**Authentication:**
```
POST   /api/auth/login/           # Login
POST   /api/auth/logout/          # Logout
POST   /api/auth/register/        # Create account
GET    /api/user/profile/         # Current user profile
PATCH  /api/user/profile/         # Update profile
```

**Message Boards:**
```
GET    /api/boards/               # List boards
GET    /api/boards/{id}/          # Board details
GET    /api/boards/{id}/messages/ # List messages
POST   /api/messages/             # Create message
GET    /api/messages/{id}/        # Message details
DELETE /api/messages/{id}/        # Delete message (if owner)
```

**Real-Time Chat:**
```
POST   /api/chat/post/                      # Post chat message
GET    /api/applets/{id}/read_events/       # Poll for events
POST   /api/applets/{id}/post_event/        # Post event
GET    /api/rooms/{room_id}/shared_state/   # Federation sync
POST   /api/rooms/{room_id}/shared_state/   # Receive federated state
```

**Applets:**
```
GET    /api/applets/                 # List applets
GET    /api/applets/{id}/            # Applet details
GET    /api/applets/{id}/data/       # Get user's saved data
POST   /api/applets/{id}/data/       # Save user data
POST   /api/applets/upload/          # Upload new applet (pending approval)
```

**Content:**
```
GET    /api/content/stream/{hash}/   # Stream content chunks
GET    /api/content/metadata/{hash}/ # Get manifest metadata
```

**Federation:**
```
GET    /api/federation/identity/     # Get instance public key
GET    /api/federation/export_config/ # Export BBS config
POST   /api/federation/import_config/ # Import config from peer
POST   /api/rooms/{room_id}/state/   # Receive federated events
```

### Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "timestamp": "2025-10-23T15:30:00Z"
}
```

Error responses:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field 'body'",
    "details": { ... }
  },
  "timestamp": "2025-10-23T15:30:00Z"
}
```

---

## Deployment Architecture

### Production Setup

```
                    ┌─────────────────┐
                    │   Tor Network   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Hidden Service  │
                    │ xnjzv...mhid    │
                    │ .onion:80       │
                    └────────┬────────┘
                             │
┌─────────────────────────────▼──────────────────────────────┐
│                    Nginx Reverse Proxy                     │
│  - SSL termination (if clearnet)                           │
│  - Static file serving                                     │
│  - Request routing                                         │
└────────────────────────────┬───────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐          ┌────────▼────────┐
     │  Gunicorn        │          │  Static Files   │
     │  (WSGI Server)   │          │  /static/       │
     │  - 4 workers     │          │  /media/        │
     │  - Django app    │          │                 │
     └────────┬─────────┘          └─────────────────┘
              │
     ┌────────▼─────────┐
     │   PostgreSQL     │
     │   Database       │
     │   - Messages     │
     │   - Users        │
     │   - Manifests    │
     └──────────────────┘
```

### Service Configuration

**systemd unit file** (`/etc/systemd/system/axon-bbs.service`):
```ini
[Unit]
Description=Axon BBS Django Application
After=network.target postgresql.service tor.service

[Service]
User=axonbbs
Group=axonbbs
WorkingDirectory=/opt/axon_bbs
Environment="PATH=/opt/axon_bbs/venv/bin"
ExecStart=/opt/axon_bbs/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    axon_project.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Nginx configuration**:
```nginx
server {
    listen 80;
    server_name xnjzv3k7gd2yw5l3u6mxqqr6jkq7flxvj4j5ljopoxf2bglwdcpqmhid.onion;

    location /static/ {
        alias /opt/axon_bbs/staticfiles/;
    }

    location /media/ {
        alias /opt/axon_bbs/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Scaling Strategy

**Horizontal Scaling:**
```
                   Load Balancer
                         │
          ┌──────────────┼──────────────┐
          │              │              │
    ┌─────▼─────┐  ┌─────▼─────┐  ┌────▼──────┐
    │ Django    │  │ Django    │  │ Django    │
    │ Instance 1│  │ Instance 2│  │ Instance 3│
    └─────┬─────┘  └─────┬─────┘  └────┬──────┘
          │              │              │
          └──────────────┼──────────────┘
                         │
                   ┌─────▼─────┐
                   │ PostgreSQL│
                   │ Primary   │
                   └─────┬─────┘
                         │
                   ┌─────▼─────┐
                   │ PostgreSQL│
                   │ Replica   │
                   └───────────┘
```

### Monitoring

**Prometheus Metrics:**
```python
# Custom metrics
from prometheus_client import Counter, Histogram

chat_messages_total = Counter(
    'axon_chat_messages_total',
    'Total chat messages sent'
)

federation_sync_duration = Histogram(
    'axon_federation_sync_duration_seconds',
    'Time spent syncing with peers'
)

# In code:
chat_messages_total.inc()
with federation_sync_duration.time():
    sync_to_peer(peer)
```

**Health Check Endpoint:**
```python
# /api/health/
{
  "status": "healthy",
  "database": "connected",
  "tor": "connected",
  "peers": {
    "total": 2,
    "reachable": 2
  },
  "services": {
    "RealtimeMessageService": "running"
  }
}
```

---

## Conclusion

Axon BBS's architecture balances security, performance, and extensibility through:

1. **Content-addressed storage** (BitSync) for integrity and deduplication
2. **Sandboxed applets** for safe extensibility
3. **Real-time polling** for reliable low-latency communication
4. **Tor-only federation** for anonymity and censorship resistance
5. **Multi-layer encryption** for defense in depth
6. **Service-oriented backend** for maintainability

The system is designed to be:
- **Secure by default**: Multiple layers of encryption and sandboxing
- **Scalable**: Stateless federation, horizontal scaling capability
- **Resilient**: No single point of failure, backup/restore infrastructure
- **Extensible**: Applet framework allows unlimited functionality

---

**Last Updated**: October 23, 2025 by Achduke7
