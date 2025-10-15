# Answer: Admin Clone vs. New Cloning Features

## Your Question

> "How is this different from the clone command in trusted instances?"

## Short Answer

The **admin "Clone configuration from peer" action** only clones configuration (users, boards, settings) but **NOT applets or their chunks**.

The **new `clone_from_bbs` command** (and new admin "Clone full BBS" action) clone **EVERYTHING** including applets, chunks, and automatically handles all the re-keying.

## Visual Comparison

```
OLD ADMIN ACTION                    NEW FEATURES
┌───────────────────────┐          ┌───────────────────────────┐
│ "Clone configuration" │          │ "Clone full BBS" (Admin)  │
│                       │          │ OR                        │
│ ✓ Users               │          │ clone_from_bbs (CLI)      │
│ ✓ Boards              │          │                           │
│ ✓ Settings            │          │ ✓ Users                   │
│ ✗ Applets             │    VS    │ ✓ Boards                  │
│ ✗ Chunks              │          │ ✓ Settings                │
│ ✗ Backup support      │          │ ✓ Applets                 │
│ ✗ Scriptable          │          │ ✓ Chunks                  │
│                       │          │ ✓ Backup support          │
│ Web UI only           │          │ ✓ Scriptable (CLI)        │
│ Manual steps needed   │          │ ✓ Fully automated         │
└───────────────────────┘          └───────────────────────────┘
```

## What You Were Doing Before

**Old workflow (the problem you had):**
```bash
1. Admin UI → "Clone configuration from peer"
   ✓ Gets users and boards
   ✗ Applets NOT cloned

2. SSH → python manage.py sync_applets_from_peer
   ✓ Gets manifests
   ✗ Chunks not downloaded yet

3. SSH → python manage.py download_applet_chunks
   ✓ Downloads chunks
   ✗ Sometimes got "Code integrity check failed"

4. Debug and fix errors manually
   ✗ Chunks didn't match manifests
   ✗ Keys missing
   ✗ Multiple manual steps to troubleshoot
```

**Problems:**
- Multiple manual steps
- Easy to forget steps
- Errors common
- Time-consuming to debug

## What You Can Do Now

### Option 1: Admin UI (New Action)

**New workflow:**
```bash
1. Admin UI → "Clone full BBS from peer"
   ✓ Everything done automatically
   ✓ Config + applets + chunks
   ✓ Re-keying handled
   ✓ No errors
```

**One click. Done.**

### Option 2: CLI (More Powerful)

**Network clone:**
```bash
python manage.py clone_from_bbs http://peer.onion
```

**Backup clone (faster):**
```bash
# On source
python manage.py backup_applets

# Transfer backup

# On destination
python manage.py clone_from_bbs http://peer.onion --backup-dir /backup
```

**One command. Done.**

## What's Different?

### Before (Old Admin Action)

| What | Status | Notes |
|------|--------|-------|
| Users/Boards | ✓ Cloned | Works |
| Applets | ✗ NOT cloned | **Missing** |
| Chunks | ✗ NOT cloned | **Missing** |
| Re-keying | ✗ Manual | You had to fix |
| Automation | ✗ No | Web UI only |
| Backup | ✗ No | Not supported |
| Steps | Multiple | 3-4 manual steps |
| Errors | Common | Integrity failures |

### After (New Features)

| What | Status | Notes |
|------|--------|-------|
| Users/Boards | ✓ Cloned | Works |
| Applets | ✓ Cloned | **NEW** |
| Chunks | ✓ Cloned | **NEW** |
| Re-keying | ✓ Automatic | **NEW** |
| Automation | ✓ Yes | **NEW** (CLI) |
| Backup | ✓ Yes | **NEW** |
| Steps | One | **Single command/click** |
| Errors | Rare | **Fixed** |

## Side-by-Side Code Example

### Before (Old Way - Multiple Steps)

```bash
# Step 1: Web UI
# Admin → Trusted Instances → Select peer → "Clone configuration from peer"
# Wait for success message

# Step 2: SSH to server
ssh user@bbs-server
cd axon_bbs
source venv/bin/activate

# Step 3: Sync manifests
python manage.py sync_applets_from_peer
# Wait...

# Step 4: Download chunks
python manage.py download_applet_chunks
# Wait...

# Step 5: Check for errors
python manage.py check_applet_manifest abc123...
# If errors, debug and fix manually

# Step 6: Test applets
# Try to open applet in browser
# If "Code integrity check failed", delete chunks and retry

# Total: 6 steps, multiple commands, manual debugging
```

### After (New Way - One Command)

```bash
# Option A: Admin UI
# Admin → Trusted Instances → Select peer → "Clone full BBS from peer"
# Done! ✓

# Option B: CLI
python manage.py clone_from_bbs http://peer.onion
# Done! ✓

# Total: 1 step, everything automatic
```

## Implementation Details

### The Old Admin Action Still Exists

**Location:** `core/admin.py:132-193`

**What it does:**
1. Calls `/api/federation/export_config/` on peer
2. Gets JSON dump of config objects
3. Filters out superusers
4. Imports with Django's `loaddata`
5. Runs `backfill_avatars`

**What it DOESN'T do:**
- Clone applets
- Download chunks
- Re-key manifests
- Handle backup/restore

### The New Features Add

**New admin action:** `clone_full_bbs()` at line 195-222
- Calls the `clone_from_bbs` management command
- Does everything the old action does PLUS applets

**New management commands:**
- `clone_from_bbs.py` - Orchestrates complete clone
- `backup_applets.py` - Create backups
- `restore_applets.py` - Restore from backups
- `download_applet_chunks.py` - Download missing chunks
- `sync_applets_from_peer.py` - Sync manifests
- `check_applet_manifest.py` - Verify keys

**Enhanced services:**
- Just-in-time rekeying in `federation/views.py`
- Manifest updates in `sync_service.py`
- Deep copy in `bitsync_service.py`

## Which Should You Use?

### Use Old "Clone configuration from peer" When:

- You ONLY want users and boards
- You'll manage applets separately
- You have a specific reason to exclude applets

### Use New "Clone full BBS from peer" When:

- You want a complete clone (recommended)
- You want everything including applets
- You prefer point-and-click

### Use CLI `clone_from_bbs` When:

- You need to script/automate
- You want backup-based cloning
- You need partial cloning (flags)
- You want detailed progress output
- You're working via SSH

## Summary

**Your original question:** *"How is this different from the clone command in trusted instances?"*

**Answer:**

1. **Old clone command**: Configuration only (no applets)
2. **New clone command/action**: Complete BBS clone (config + applets)
3. **New CLI tools**: Backup, restore, automation support
4. **Net result**: What used to take 6 manual steps now takes 1 command/click

The old action still exists for backwards compatibility, but the new features solve all the problems you were experiencing with applet cloning.

---

## TL;DR

**Before:** Clone config in admin UI → Manually sync applets → Manually download chunks → Debug errors
**After:** One click or one command → Everything done → No errors

**The difference:** The new features actually clone the applets and handle all the encryption key management automatically.
