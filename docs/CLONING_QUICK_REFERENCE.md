# Axon BBS Cloning - Quick Reference

## One-Line Commands

### Clone Everything (Network)
```bash
python manage.py clone_from_bbs http://peer.onion
```

### Clone Everything (Backup)
```bash
python manage.py clone_from_bbs http://peer.onion --backup-dir /path/to/backup
```

### Create Backup
```bash
python manage.py backup_applets
```

### Restore from Backup
```bash
python manage.py restore_applets /path/to/backup --rekey
```

## Common Operations

| Task | Command |
|------|---------|
| **Backup all applets** | `python manage.py backup_applets` |
| **Backup one applet** | `python manage.py backup_applets --applet "Name"` |
| **Restore all applets** | `python manage.py restore_applets /backup/dir --rekey` |
| **Restore one applet** | `python manage.py restore_applets /backup/dir --applet "Name"` |
| **Clone from peer** | `python manage.py clone_from_bbs http://peer.onion` |
| **Sync manifests** | `python manage.py sync_applets_from_peer` |
| **Download chunks** | `python manage.py download_applet_chunks` |
| **Check manifest** | `python manage.py check_applet_manifest <hash>` |
| **Update peer key** | `python manage.py update_peer_key http://peer.onion` |

## Step-by-Step Workflows

### Network Clone (Manual Steps)
```bash
# 1. Add peer in admin UI
# 2. Update peer key
python manage.py update_peer_key http://peer.onion

# 3. Sync manifests
python manage.py sync_applets_from_peer

# 4. Download chunks
python manage.py download_applet_chunks
```

### Backup Clone (Manual Steps)
```bash
# On source:
python manage.py backup_applets --output /backup

# Transfer /backup to destination

# On destination:
python manage.py restore_applets /backup --rekey
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Integrity check failed** | `rm -rf data/bitsync_chunks/<hash>` then `download_applet_chunks` |
| **Invalid padding bytes** | `python manage.py update_applet_manifests` |
| **Chunks not downloading** | `python manage.py sync_applets_from_peer` |
| **Applet won't restore** | Delete it first, then restore |

## Flags and Options

### backup_applets
- `--output <dir>` - Backup directory (default: applet_backups)
- `--applet <name>` - Backup specific applet only

### restore_applets
- `--applet <name>` - Restore specific applet only
- `--skip-chunks` - Don't restore chunks (download later)
- `--rekey` - Re-key manifests for current instance

### clone_from_bbs
- `--backup-dir <path>` - Use local backup instead of network sync
- `--skip-config` - Only clone applets
- `--skip-applets` - Only clone configuration

### download_applet_chunks
- `--applet <name>` - Download chunks for specific applet only

## What Gets Backed Up

✓ Applet metadata (name, description, etc.)
✓ Code chunks (encrypted applet code)
✓ AppletData (user save files)
✓ Data chunks (encrypted user data)
✓ HighScores
✓ SharedState (multiplayer state)

## What Gets Cloned

✓ All backed up items (above)
✓ User accounts (excluding superusers)
✓ Message boards
✓ Messages and attachments
✓ Trusted instances
✓ Federation settings
✓ Valid file types
✓ Shared libraries

## Performance Tips

- Use backup-based clone for faster transfers
- Use `--skip-chunks` to defer chunk downloads
- Use `--applet` flag to backup/restore specific applets
- Schedule backups during low-traffic periods
- Keep backups on separate physical media

## Security Notes

- Chunks are encrypted and verified with SHA-256
- Manifests contain encryption keys for trusted instances
- Re-keying happens automatically during restore/clone
- Superuser accounts are never cloned
- Content owned by superusers is excluded from clones
