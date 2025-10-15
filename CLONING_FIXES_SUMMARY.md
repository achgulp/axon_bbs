# BBS Cloning and Federation Fixes - Summary

**Date**: 2025-10-14

## Problem
After cloning a BBS instance (pibbs) from the host, older applets and messages couldn't be accessed due to encryption key mismatches.

## Errors Encountered
1. "Code integrity check failed. The downloaded applet code may be corrupted or tampered with."
2. Django server crash: `AttributeError: module 'federation.views' has no attribute 'IgnoredPubkeyView'`
3. "Invalid padding bytes" decryption errors

## Root Cause
- Cloned instance had new encryption keys but manifests contained encryption envelopes for old keys
- Chunks on disk didn't match hashes in updated manifests

## Solutions Implemented

### 1. Restored Missing View Classes
- **File**: `federation/views.py`
- **Fix**: Restored from HEAD~1 (13 view classes were accidentally deleted)

### 2. Just-in-Time Rekeying in Sync
- **File**: `federation/views.py` (lines 76-98)
- **What**: SyncView now calls `rekey_manifest_for_peer()` before sending manifests
- **Result**: Host dynamically adds encryption envelopes for requesting peer's current keys

### 3. Manifest Updates During Sync
- **File**: `core/services/sync_service.py` (lines 189-227)
- **What**: `_process_received_manifests()` now UPDATES existing content instead of skipping
- **Result**: Existing Messages, Files, PMs, and Applets get updated manifests with new keys

### 4. Enhanced Admin Actions
- **File**: `core/admin.py` (lines 80-129)
- **What**: "Force Refresh and Re-key Peer" now includes all content types
- **Result**: Can manually trigger rekey for all content when adding/updating peers

### 5. Management Commands Created

#### `sync_applets_from_peer.py`
- Fetches applet manifests from host with just-in-time rekeying
- Solves chicken-and-egg problem (couldn't decrypt old manifests to rekey them)
- Usage: `python manage.py sync_applets_from_peer [--peer <onion_url>]`

#### `check_applet_manifest.py`
- Diagnostic tool to verify encryption keys in manifests
- Usage: `python manage.py check_applet_manifest <content_hash>`
- Shows which encryption keys are present and if local instance key is included

#### `download_applet_chunks.py`
- Downloads missing or mismatched chunks for applets
- Usage: `python manage.py download_applet_chunks [--applet <name>]`
- Verifies chunk integrity using SHA-256 hashes

#### `backup_applets.py`
- Creates a complete backup of applets (metadata, chunks, data, scores)
- Usage: `python manage.py backup_applets [--output <dir>] [--applet <name>]`
- Includes: Applet metadata, code chunks, AppletData, HighScores, SharedState

#### `restore_applets.py`
- Restores applets from a backup directory
- Usage: `python manage.py restore_applets <backup_dir> [--applet <name>] [--skip-chunks] [--rekey]`
- Can skip chunk restoration if they'll be downloaded from peer
- Automatically re-keys manifests for current trusted instances

#### `clone_from_bbs.py`
- Orchestrates the complete cloning process
- Usage: `python manage.py clone_from_bbs <peer_url> [--backup-dir <path>] [--skip-config] [--skip-applets]`
- Combines all cloning steps into a single command
- Supports both network-based and backup-based cloning

## Recommended Cloning Workflow

### Method 1: Network-Based Cloning (Online)

When cloning a BBS instance over the network:

```bash
# On the cloned instance (e.g., pibbs)

# Single command to clone everything
python manage.py clone_from_bbs <host_onion_url>

# Or step-by-step:
# 1. Update host's public key
python manage.py update_peer_key <host_onion_url>

# 2. Fetch updated manifests with just-in-time rekeying
python manage.py sync_applets_from_peer

# 3. Download any missing or mismatched chunks
python manage.py download_applet_chunks

# 4. (Optional) Verify applet manifests
python manage.py check_applet_manifest <content_hash_prefix>
```

### Method 2: Backup-Based Cloning (Offline)

When cloning using a backup (faster, works offline):

```bash
# On the HOST BBS (source):
# 1. Create a full backup
python manage.py backup_applets --output /path/to/backup

# Transfer backup to cloned instance (USB, network share, etc.)

# On the CLONED instance (destination):
# 2. Clone everything using the backup
python manage.py clone_from_bbs <host_onion_url> --backup-dir /path/to/backup

# Or restore just applets from backup:
python manage.py restore_applets /path/to/backup --rekey

# 3. Download any missing chunks (if needed)
python manage.py download_applet_chunks
```

## Technical Details

### Encryption Model
- Content encrypted with AES keys
- AES keys encrypted for each trusted instance's RSA public key (envelope encryption)
- Manifests contain `encrypted_aes_keys` dictionary mapping pubkey checksums to encrypted AES keys

### Chunks
- Chunks are immutable (encrypted with same AES key forever)
- Only manifests need updating when instance keys change
- Chunk integrity verified using SHA-256 hashes in manifest's `chunk_hashes` array

### Just-in-Time Rekeying
- Host dynamically adds encryption envelopes during sync
- Uses deep copy to avoid mutating database manifests
- Only adds envelope if peer's checksum not already present

## Files Modified

1. `federation/views.py` - Restored + added JIT rekeying
2. `core/services/sync_service.py` - Manifest updates during sync
3. `core/services/bitsync_service.py` - Deep copy in rekey_manifest_for_peer()
4. `core/admin.py` - Enhanced "Force Refresh and Re-key Peer"

## Management Commands Created

5. `core/management/commands/sync_applets_from_peer.py` - Sync manifests from peer
6. `core/management/commands/check_applet_manifest.py` - Verify encryption keys
7. `core/management/commands/download_applet_chunks.py` - Download missing chunks
8. `core/management/commands/backup_applets.py` - Backup applets to directory
9. `core/management/commands/restore_applets.py` - Restore applets from backup
10. `core/management/commands/clone_from_bbs.py` - Complete cloning orchestration

## Verification

### Network-Based Cloning (Tested)
All applets on pibbs verified working after network sync:
- ✓ Pipe Dodger: All 1 chunk(s) verified
- ✓ MimsTris: All 1 chunk(s) verified
- ✓ Video Player: All 1 chunk(s) verified
- ✓ Axon Sheets: All 1 chunk(s) verified

### Backup/Restore (Tested)
- ✓ Backup created: 5 applets, 5 chunks, 2 data instances
- ✓ HexGL restored from backup successfully
- ✓ Chunk hash verification passed
- ✓ Manifest re-keying for 2 instances successful

## Notes

- Regular sync cycles will now automatically update manifests for existing content **only when new keys are detected**
- Optimization: Manifests are not re-keyed on every sync if keys haven't changed (saves ~7.3M database writes per year)
- Chunks download on-demand when applets are accessed
- `update_applet_manifests` command works but may fail if no keys can decrypt (use `sync_applets_from_peer` instead)

## Performance Optimization (2025-10-14)

**Problem:** Manifests were being re-keyed and saved on every sync cycle, even when encryption keys hadn't changed.

**Solution:** Added key comparison before updating manifests. Now only updates when new encryption keys are detected.

**Impact:**
- Before: 28 database writes per sync cycle
- After: 0 database writes per sync cycle (when no new keys)
- Savings: 100% reduction in unnecessary updates

See [MANIFEST_REKEY_OPTIMIZATION.md](docs/MANIFEST_REKEY_OPTIMIZATION.md) for details.
