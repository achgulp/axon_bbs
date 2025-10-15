# Axon BBS - Backup and Cloning Guide

This guide explains how to backup, restore, and clone Axon BBS instances, including applets and content.

## Table of Contents

1. [Overview](#overview)
2. [Backup Commands](#backup-commands)
3. [Restore Commands](#restore-commands)
4. [Cloning Workflows](#cloning-workflows)
5. [Use Cases](#use-cases)
6. [Technical Details](#technical-details)

## Overview

Axon BBS supports two methods for backing up and cloning instances:

1. **Network-based cloning**: Sync content directly from a peer over Tor
2. **Backup-based cloning**: Create offline backups for transfer via USB, network share, etc.

Both methods handle encryption key management automatically, ensuring that cloned instances can decrypt content.

## Backup Commands

### Create a Full Backup

```bash
# Backup all applets
python manage.py backup_applets

# Backup to a specific directory
python manage.py backup_applets --output /path/to/backup_dir

# Backup a specific applet
python manage.py backup_applets --applet "MimsTris"
```

**What gets backed up:**
- Applet metadata (name, description, parameters, etc.)
- Code chunks (encrypted applet code)
- AppletData instances (user save data)
- Data chunks (encrypted user data)
- HighScores
- SharedState (multiplayer game state)

**Backup structure:**
```
backup_20251014_224121/
├── backup_manifest.json          # Backup metadata
├── Pipe_Dodger/
│   ├── metadata.json              # Applet metadata
│   ├── chunks/                    # Code chunks
│   │   └── 0.chunk
│   ├── applet_data.json           # User data metadata
│   └── data_chunks/               # User data chunks
│       └── username/
│           └── 0.chunk
├── MimsTris/
│   └── ...
└── ...
```

## Restore Commands

### Restore from Backup

```bash
# Restore all applets from a backup
python manage.py restore_applets /path/to/backup_dir

# Restore a specific applet
python manage.py restore_applets /path/to/backup_dir --applet "MimsTris"

# Restore without chunks (will download from peer later)
python manage.py restore_applets /path/to/backup_dir --skip-chunks

# Restore and re-key for current trusted instances
python manage.py restore_applets /path/to/backup_dir --rekey
```

**Important notes:**
- Existing applets are skipped (won't overwrite)
- Use `--rekey` to update encryption keys for current instance
- Use `--skip-chunks` if you want to save disk space and download chunks on-demand

## Cloning Workflows

### Method 1: Single-Command Clone (Recommended)

The simplest way to clone a BBS instance:

```bash
# Clone everything (config + applets) from a peer
python manage.py clone_from_bbs http://example.onion

# Clone using a local backup (faster)
python manage.py clone_from_bbs http://example.onion --backup-dir /path/to/backup

# Clone only applets (skip configuration)
python manage.py clone_from_bbs http://example.onion --skip-config

# Clone only configuration (skip applets)
python manage.py clone_from_bbs http://example.onion --skip-applets
```

**What the clone command does:**
1. Updates peer's public key
2. Clones configuration (users, boards, settings, etc.)
3. Syncs applet manifests with just-in-time rekeying
4. Downloads applet chunks
5. Re-keys all content for local trusted instances

### Method 2: Network-Based Clone (Step-by-Step)

If you prefer manual control:

```bash
# 1. Add peer as trusted instance (via admin UI)
# http://yourinstance.onion/admin/core/trustedinstance/

# 2. Update peer's public key
python manage.py update_peer_key http://peer.onion

# 3. Sync applet manifests
python manage.py sync_applets_from_peer

# 4. Download applet chunks
python manage.py download_applet_chunks

# 5. (Optional) Clone full configuration
# Use admin action: "Clone configuration from peer"
```

### Method 3: Backup-Based Clone (Offline)

For air-gapped or offline scenarios:

```bash
# On SOURCE BBS (host):
# 1. Create backup
python manage.py backup_applets --output /mnt/usb/axon_backup

# 2. Transfer backup to destination (USB drive, network share, etc.)

# On DESTINATION BBS (clone):
# 3. Add source as trusted peer (via admin UI)

# 4. Restore applets from backup
python manage.py restore_applets /mnt/usb/axon_backup --rekey

# 5. (Optional) Clone configuration over network
python manage.py clone_from_bbs http://source.onion --skip-applets
```

## Use Cases

### Use Case 1: Disaster Recovery

**Scenario**: Your BBS instance crashes and you need to restore from backup.

```bash
# Regular backups (run via cron)
0 2 * * * cd /path/to/axon_bbs && python manage.py backup_applets --output /backups

# Restore after disaster
python manage.py restore_applets /backups/latest_backup --rekey
```

### Use Case 2: Development/Testing Instance

**Scenario**: Create a test instance with production data.

```bash
# On production
python manage.py backup_applets --output /tmp/prod_backup

# Transfer to dev machine
scp -r /tmp/prod_backup dev@testserver:/tmp/

# On dev instance
python manage.py restore_applets /tmp/prod_backup --rekey
```

### Use Case 3: Migrating to New Hardware

**Scenario**: Move your BBS to a new server.

```bash
# On old server
python manage.py backup_applets --output /migration/backup

# Transfer database + backup to new server

# On new server
python manage.py migrate
python manage.py restore_applets /migration/backup --rekey
```

### Use Case 4: Creating a Mirror/Backup Node

**Scenario**: Set up a hot standby instance that stays in sync.

```bash
# Initial clone
python manage.py clone_from_bbs http://primary.onion

# Ongoing sync happens automatically via SyncService
# Applets and content will stay up-to-date
```

## Technical Details

### Encryption Key Management

When cloning or restoring:

1. **Manifests contain encryption envelopes**: Each manifest has AES keys encrypted for multiple trusted instances
2. **Just-in-time rekeying**: When syncing, the source BBS adds encryption envelopes for the requesting peer's current keys
3. **Re-keying on restore**: The `--rekey` flag updates all manifests to include encryption keys for your current trusted instances
4. **Chunks are immutable**: Chunks never need to be re-encrypted, only manifests are updated

### Content Verification

All chunks are verified using SHA-256 hashes:

```bash
# Check applet manifest and verify chunks
python manage.py check_applet_manifest <content_hash>
```

### Backup Format

Backups are stored as JSON + raw chunk files:

- **Portable**: Can be transferred between instances
- **Human-readable**: JSON files can be inspected
- **Incremental-friendly**: Chunks are stored by content hash (deduplication)

### Avoiding Data Loss

**Best practices:**
1. Regular automated backups (daily/weekly)
2. Keep backups on separate physical media
3. Test restores periodically
4. Use `--rekey` when restoring to a different instance
5. Verify chunk integrity after restore

### Performance Considerations

**Backup speed:**
- Depends on number of applets and chunk sizes
- Typically < 1 minute for small BBS instances
- Use `--applet` flag to backup specific applets

**Restore speed:**
- Faster with `--skip-chunks` (chunks downloaded on-demand)
- Use `--rekey` to ensure decryption works immediately

**Network clone speed:**
- Depends on Tor network latency
- Can take 5-30 minutes for full clone
- Use backup-based clone for faster results

## Troubleshooting

### "Code integrity check failed" after restore

**Cause**: Chunks don't match manifest hashes.

**Solution**:
```bash
# Delete bad chunks and re-download
rm -rf data/bitsync_chunks/<content_hash>
python manage.py download_applet_chunks
```

### "Invalid padding bytes" when decrypting

**Cause**: Manifest doesn't have encryption key for local instance.

**Solution**:
```bash
# Re-key the applet manifest
python manage.py update_applet_manifests
```

### Applet exists but won't restore

**Cause**: Restore skips existing applets.

**Solution**:
```bash
# Delete existing applet first, then restore
python manage.py shell -c "from applets.models import Applet; Applet.objects.filter(name='AppletName').delete()"
python manage.py restore_applets /path/to/backup --applet "AppletName"
```

### Chunks not downloading

**Cause**: No seeders available or network issues.

**Solution**:
```bash
# Check if peer is reachable
python manage.py reset_peer_sync_time

# Force a sync
python manage.py sync_applets_from_peer

# Download specific applet
python manage.py download_applet_chunks --applet "AppletName"
```

## Advanced Usage

### Scripted Backups

```bash
#!/bin/bash
# backup_script.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/axon_bbs/$DATE"

cd /path/to/axon_bbs
source venv/bin/activate

# Backup applets
python manage.py backup_applets --output "$BACKUP_DIR"

# Keep only last 7 days of backups
find /backups/axon_bbs -type d -mtime +7 -exec rm -rf {} \;
```

### Selective Restore

```bash
# Restore only specific applets
for applet in "MimsTris" "Pipe Dodger" "Video Player"; do
  python manage.py restore_applets /backup/dir --applet "$applet" --rekey
done
```

### Migration Between Instances

```bash
# Export from instance A
python manage.py backup_applets --output /export/applets

# Import to instance B
python manage.py restore_applets /export/applets --skip-chunks --rekey

# Download chunks from instance A
python manage.py sync_applets_from_peer --peer http://instanceA.onion
python manage.py download_applet_chunks
```

## See Also

- [CLONING_FIXES_SUMMARY.md](../CLONING_FIXES_SUMMARY.md) - Technical implementation details
- [Federation Guide](FEDERATION.md) - How federation and syncing works
- [Admin Guide](ADMIN.md) - Administrative tasks and management
