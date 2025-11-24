# Axon BBS Server Management Guide

Quick reference for common server management tasks.

---

## Server Information

### HostBBS (Development Server)
- **Location**: `/path/to/axon_bbs`
- **URL**: `http://127.0.0.1:8000`
- **User**: [username]

### PiBBS (Remote Server)
- **Location**: `/home/pibbs/axon_bbs`
- **URL**: `http://192.168.58.7:8000`
- **SSH Access**: `ssh -p 2222 pibbs@192.168.58.7`

---

## Starting/Restarting Servers

### HostBBS

```bash
# Kill any existing Django processes
pkill -9 -f "python.*runserver"

# Start server with nohup (persists after logout)
cd /path/to/axon_bbs
source venv/bin/activate
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_host.log 2>&1 &

# Verify server is running
curl -s http://127.0.0.1:8000/ | grep -o 'main\.[a-z0-9]*\.js' | head -1
ps aux | grep 'python.*runserver' | grep -v grep
```

### PiBBS

```bash
# SSH into PiBBS
ssh -p 2222 pibbs@192.168.58.7

# Kill any existing Django processes
pkill -9 -f "python.*runserver"

# Start server with nohup
cd axon_bbs
source venv/bin/activate
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_pibbs.log 2>&1 &

# Verify server is running
curl -s http://127.0.0.1:8000/ | grep -o 'main\.[a-z0-9]*\.js' | head -1
ps aux | grep 'python.*runserver' | grep -v grep

# Exit SSH
exit
```

### Alternative: Remote PiBBS Restart (from HostBBS)

```bash
# One-liner to restart PiBBS remotely
ssh -p 2222 pibbs@192.168.58.7 'bash -c "cd axon_bbs && source venv/bin/activate && nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_pibbs.log 2>&1 < /dev/null &"'

# Verify it's running
ssh -p 2222 pibbs@192.168.58.7 "ps aux | grep 'python.*runserver' | grep -v grep"
```

---

## Checking Server Status

### Check Logs

```bash
# HostBBS logs
tail -f /tmp/django_host.log

# PiBBS logs
ssh -p 2222 pibbs@192.168.58.7 "tail -f /tmp/django_pibbs.log"
```

### Check Process Status

```bash
# HostBBS
ps aux | grep 'python.*runserver' | grep -v grep

# PiBBS
ssh -p 2222 pibbs@192.168.58.7 "ps aux | grep 'python.*runserver' | grep -v grep"
```

### Check Server Health

```bash
# HostBBS
curl -s http://127.0.0.1:8000/health/

# PiBBS (from remote)
ssh -p 2222 pibbs@192.168.58.7 "curl -s http://127.0.0.1:8000/health/"
```

---

## Publishing Applets

### Method 1: Using Management Command (Recommended)

This is the **preferred method** - it handles everything automatically:

```bash
cd /path/to/axon_bbs
source venv/bin/activate

# Post applet update to Applet Library
python manage.py post_applet_update <path_to_applet.js> \
  --name "AppletName" \
  --description "Version X.X: Description of changes"
```

**What this does automatically:**
1. Creates BitSync manifest with encrypted chunks for the applet file
2. Creates FileAttachment in database
3. Creates BitSync manifest for the message content (for federation sync)
4. Posts message to "Applet Library" board with attachment
5. **Updates the Applet's `code_manifest`** to point to the new FileAttachment
6. Prints FileAttachment ID and content hash
7. **Message will auto-sync to federated peers** (via BitSync message manifest)

**Example:**
```bash
python manage.py post_applet_update frontend/src/applets/AxonChat.js \
  --name "AxonChat" \
  --description "v19: Version labeling and code cleanup"
```

### Method 2: Manual Publication (If Command Fails)

If the command detects a duplicate (same filename + size), manually create the post:

```bash
source venv/bin/activate
python manage.py shell <<'EOF'
from messaging.models import Message, MessageBoard
from core.models import FileAttachment
from core.services.bitsync_service import BitSyncService
from django.contrib.auth import get_user_model
import base64
import hashlib

User = get_user_model()
admin = User.objects.get(username='Achduke7')
bitsync_service = BitSyncService()

# Read applet file
with open('/path/to/applet.js', 'rb') as f:
    file_data = f.read()

file_hash = hashlib.sha256(file_data).hexdigest()

# Create BitSync manifest
file_content_payload = {
    "type": "file",
    "filename": "AppletName.js",
    "content_type": "application/javascript",
    "size": len(file_data),
    "data": base64.b64encode(file_data).decode('ascii'),
    "applet_name": "AppletName",
    "description": "Version description"
}

content_hash, manifest = bitsync_service.create_encrypted_content(file_content_payload)

# Create FileAttachment
file_attachment = FileAttachment.objects.create(
    author=admin,
    filename='AppletName.js',
    content_type='application/javascript',
    size=len(file_data),
    metadata_manifest=manifest
)

# Post to Applet Library
applet_board = MessageBoard.objects.get(name='Applet Library')
message = Message.objects.create(
    board=applet_board,
    author=admin,
    subject='AppletName vX',
    body=f'''Description of changes

**FileAttachment ID:** {file_attachment.id}
**File Hash:** {file_hash}
'''
)
message.attachments.add(file_attachment)

print(f"Message ID: {message.id}")
print(f"FileAttachment ID: {file_attachment.id}")
print(f"Content Hash: {content_hash}")
EOF
```

### Step 3: Update Applet to Use New FileAttachment

**IMPORTANT:** After posting to Applet Library, update the applet's code_manifest:

```bash
source venv/bin/activate
python manage.py shell <<'EOF'
from applets.models import Applet
from core.models import FileAttachment

applet = Applet.objects.get(name='AppletName')
file_attachment = FileAttachment.objects.get(id='<FileAttachment-ID-from-above>')

# Update applet to use new manifest
applet.code_manifest = file_attachment.metadata_manifest
applet.save()

print(f"✓ Updated {applet.name} applet")
print(f"  Content Hash: {applet.code_manifest.get('content_hash', 'N/A')[:16]}...")
EOF
```

---

## Deploying Code Changes

### Full Deployment Workflow

```bash
# 1. Make code changes to frontend/src/applets/YourApplet.js

# 2. Commit to git
git add frontend/src/applets/YourApplet.js
git commit -m "Update YourApplet to vX"
git push

# 3. Build frontend on HostBBS
cd /path/to/axon_bbs/frontend
npm run build

# 4. Deploy to PiBBS
ssh -p 2222 pibbs@192.168.58.7 "cd axon_bbs && git pull"
ssh -p 2222 pibbs@192.168.58.7 "cd axon_bbs/frontend && npm run build"

# 5. Publish applet to Applet Library
cd /path/to/axon_bbs
source venv/bin/activate
python manage.py post_applet_update frontend/src/applets/YourApplet.js \
  --name "YourApplet" \
  --description "vX: Description of changes"

# 6. Restart servers (if needed)
# HostBBS
pkill -9 -f "python.*runserver"
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_host.log 2>&1 &

# PiBBS
ssh -p 2222 pibbs@192.168.58.7 'bash -c "cd axon_bbs && source venv/bin/activate && nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_pibbs.log 2>&1 < /dev/null &"'
```

---

## Useful Management Commands

```bash
cd /path/to/axon_bbs
source venv/bin/activate

# Check applet manifest
python manage.py check_applet_manifest AxonChat

# Sync applets from peer
python manage.py sync_applets_from_peer --peer-url http://192.168.58.7:8000

# Backup applets
python manage.py backup_applets

# Download applet chunks
python manage.py download_applet_chunks --applet-id <applet-id>

# Django shell
python manage.py shell

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Check for errors
python manage.py check
```

---

## Troubleshooting

### Server won't start

```bash
# Check if port is already in use
lsof -i :8000

# Check for Python errors
tail -100 /tmp/django_host.log

# Clear Python cache
find /path/to/axon_bbs -type d -name __pycache__ -exec rm -rf {} +
find /path/to/axon_bbs -name "*.pyc" -delete
```

### Applet not loading

```bash
# Check applet code_manifest
python manage.py shell <<'EOF'
from applets.models import Applet
applet = Applet.objects.get(name='AppletName')
print(applet.code_manifest)
EOF

# Check if BitSync chunks exist
ls -la /path/to/axon_bbs/data/bitsync_chunks/
```

### BitSync chunk location mismatch

**Known Issue:** BitSync saves chunks to `{content_hash}/0.chunk` but the download system expects `{chunk_hash}/{chunk_hash}.enc`.

**Fix chunks for a FileAttachment:**
```bash
source venv/bin/activate
python manage.py shell <<'EOF'
from core.models import FileAttachment
import os
import shutil

# Replace with your FileAttachment ID
fa = FileAttachment.objects.get(id='YOUR-FILE-ATTACHMENT-ID')
manifest = fa.metadata_manifest

content_hash = manifest['content_hash']
chunk_hashes = manifest['chunk_hashes']

print(f"Fixing {len(chunk_hashes)} chunks...")

for i, chunk_hash in enumerate(chunk_hashes):
    src_file = f"/path/to/axon_bbs/data/bitsync_chunks/{content_hash}/{i}.chunk"
    dest_dir = f"/path/to/axon_bbs/data/bitsync_chunks/{chunk_hash}"
    dest_file = f"{dest_dir}/{chunk_hash}.enc"

    if not os.path.exists(src_file):
        print(f"  ✗ Source missing: {src_file}")
        continue

    if os.path.exists(dest_file):
        print(f"  ✓ Chunk {i}: already exists")
        continue

    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src_file, dest_file)

    size = os.path.getsize(dest_file)
    print(f"  ✓ Chunk {i}: {chunk_hash[:16]}... ({size} bytes) FIXED")

print(f"✓ All chunks fixed")
EOF
```

### Messages not syncing to peers

**Cause:** Only messages with a `metadata_manifest` are synced via federation.

**Check if a message will sync:**
```bash
source venv/bin/activate
python manage.py shell <<'EOF'
from messaging.models import Message

msg = Message.objects.get(subject='Your Subject')
if msg.metadata_manifest:
    print(f"✓ Message WILL sync (has metadata_manifest)")
    print(f"  content_hash: {msg.metadata_manifest.get('content_hash', 'N/A')[:16]}...")
else:
    print(f"✗ Message will NOT sync (no metadata_manifest)")
    print(f"  Messages need BitSync manifest to federate")
EOF
```

**Note:** The `post_applet_update` command (as of commit 71d885d) automatically creates `metadata_manifest` for messages. Older messages posted without this may not sync.

### Federation issues

```bash
# Check sync status
python manage.py shell <<'EOF'
from core.models import TrustedInstance
for instance in TrustedInstance.objects.all():
    print(f"{instance.web_ui_onion_url}: {instance.last_synced_at}")
EOF
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start HostBBS | `nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_host.log 2>&1 &` |
| Start PiBBS | `ssh -p 2222 pibbs@192.168.58.7 'nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django_pibbs.log 2>&1 < /dev/null &'` |
| Publish Applet | `python manage.py post_applet_update <path> --name "Name" --description "Desc"` |
| Build Frontend | `cd frontend && npm run build` |
| Check Logs | `tail -f /tmp/django_host.log` |
| Git Push | `git add . && git commit -m "msg" && git push` |
| Pull on PiBBS | `ssh -p 2222 pibbs@192.168.58.7 "cd axon_bbs && git pull"` |

---

## Changelog

**October 21, 2025 - v2:**
- Added BitSync chunk location mismatch troubleshooting
- Added message federation sync requirements
- Updated `post_applet_update` to create message metadata_manifest for federation
- Fixed subject line to use content hash prefix instead of hardcoded version

**October 21, 2025 - v1:**
- Initial creation

---

**Last Updated**: October 21, 2025 (v2)
