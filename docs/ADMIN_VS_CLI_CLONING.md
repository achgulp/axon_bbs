# Admin UI vs CLI Cloning - Comparison Guide

## Overview

Axon BBS provides two ways to clone instances:

1. **Admin UI Actions** - Point-and-click cloning from the admin interface
2. **CLI Commands** - Command-line tools for scripting and automation

This guide explains the differences and when to use each.

## Admin UI Cloning

### Access
Navigate to: **Admin → Core → Trusted Instances → Select peer → Actions**

### Available Actions

#### 1. "Clone configuration from peer (config only, no applets)"

**What it clones:**
- ✓ Users (excluding superusers)
- ✓ Message boards
- ✓ Settings and configurations
- ✓ Ignored pubkeys
- ✓ Valid file types
- ✓ Shared libraries
- ✗ Applets (metadata only, no chunks)

**When to use:**
- You only want user accounts and boards
- You'll manage applets separately
- Quick setup of basic BBS structure

**How it works:**
```
Admin UI → Select peer → Actions → "Clone configuration from peer"
```

#### 2. "Clone full BBS from peer (config + applets)" ⭐ NEW

**What it clones:**
- ✓ Everything from config clone (above)
- ✓ Applet metadata and manifests
- ✓ Applet code chunks
- ✓ User data for applets
- ✓ High scores
- ✓ Re-keys all content

**When to use:**
- You want a complete clone
- You prefer point-and-click over CLI
- You have admin UI access

**How it works:**
```
Admin UI → Select peer → Actions → "Clone full BBS from peer"
```

**Note:** This action calls `clone_from_bbs` management command internally.

## CLI Cloning

### Access
SSH into the server or run from the command line:

```bash
cd /path/to/axon_bbs
source venv/bin/activate
python manage.py <command>
```

### Available Commands

#### 1. `clone_from_bbs` - Complete BBS cloning

**Full syntax:**
```bash
python manage.py clone_from_bbs <peer_url> [options]

Options:
  --backup-dir <path>    Use local backup instead of network sync
  --skip-config          Only clone applets (skip configuration)
  --skip-applets         Only clone config (skip applets)
```

**Examples:**

```bash
# Clone everything (same as admin "Clone full BBS")
python manage.py clone_from_bbs http://peer.onion

# Clone using local backup (faster, offline-friendly)
python manage.py clone_from_bbs http://peer.onion --backup-dir /backup

# Clone only configuration (same as admin "Clone configuration")
python manage.py clone_from_bbs http://peer.onion --skip-applets

# Clone only applets (assume config already cloned)
python manage.py clone_from_bbs http://peer.onion --skip-config
```

#### 2. `backup_applets` - Create backups

**Not available in admin UI** - CLI only

```bash
# Backup all applets
python manage.py backup_applets

# Backup to specific directory
python manage.py backup_applets --output /backups/daily

# Backup specific applet
python manage.py backup_applets --applet "MimsTris"
```

#### 3. `restore_applets` - Restore from backups

**Not available in admin UI** - CLI only

```bash
# Restore all applets from backup
python manage.py restore_applets /path/to/backup --rekey

# Restore specific applet
python manage.py restore_applets /path/to/backup --applet "MimsTris" --rekey

# Restore without chunks (download from network later)
python manage.py restore_applets /path/to/backup --skip-chunks --rekey
```

## Comparison Table

| Feature | Admin "Clone Config" | Admin "Clone Full BBS" | CLI `clone_from_bbs` |
|---------|---------------------|------------------------|---------------------|
| **Interface** | Web UI | Web UI | Command line |
| **Scriptable** | ✗ No | ✗ No | ✓ Yes |
| **Users/Boards** | ✓ Yes | ✓ Yes | ✓ Yes |
| **Applets** | ✗ No | ✓ Yes | ✓ Yes |
| **Chunks** | ✗ No | ✓ Yes | ✓ Yes |
| **Backup Support** | ✗ No | ✗ No | ✓ Yes |
| **Partial Clone** | ✗ No | ✗ No | ✓ Yes (flags) |
| **Progress Visible** | ✗ Admin message | ✗ Admin message | ✓ Detailed output |
| **Remote Execution** | ✗ Requires UI | ✗ Requires UI | ✓ Via SSH |
| **Automation** | ✗ Manual only | ✗ Manual only | ✓ Cron/scripts |

## When to Use Each Method

### Use Admin UI When:

✓ You prefer graphical interfaces
✓ You have admin access to the web UI
✓ You're doing a one-time manual clone
✓ You don't need scripting/automation
✓ You're comfortable with web admin tools

### Use CLI When:

✓ You need to script/automate cloning
✓ You're cloning multiple times (e.g., dev/test/staging)
✓ You want detailed progress output
✓ You need partial cloning (config OR applets)
✓ You want to use backup-based cloning
✓ You're working via SSH without GUI
✓ You're setting up automated backups

## Workflow Examples

### Example 1: Quick One-Time Clone (Admin UI)

**Scenario:** You're setting up a test instance and want to clone production.

**Steps:**
1. Log into admin UI on test instance
2. Go to Trusted Instances
3. Select production peer
4. Actions → "Clone full BBS from peer"
5. Wait for success message
6. Done!

**Time:** ~2 minutes of clicking + network sync time

---

### Example 2: Automated Nightly Backups (CLI)

**Scenario:** You want automated backups every night.

**Setup script (`/usr/local/bin/backup_bbs.sh`):**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/axon_bbs/$DATE"

cd /home/axon/axon_bbs
source venv/bin/activate
python manage.py backup_applets --output "$BACKUP_DIR"

# Keep only last 7 days
find /backups/axon_bbs -type d -mtime +7 -exec rm -rf {} \;
```

**Crontab:**
```cron
0 2 * * * /usr/local/bin/backup_bbs.sh
```

**Result:** Automatic daily backups with 7-day retention

---

### Example 3: Dev/Test Instance Refresh (CLI)

**Scenario:** Weekly refresh of test instance from production.

**Script:**
```bash
#!/bin/bash
# refresh_test_instance.sh

# Clone from production
python manage.py clone_from_bbs http://production.onion

# Restart services
sudo systemctl restart axon_bbs
```

**Crontab:**
```cron
0 6 * * 1 /home/axon/refresh_test_instance.sh
```

**Result:** Test instance synced with production every Monday at 6 AM

---

### Example 4: Migration to New Hardware (CLI + Backup)

**Scenario:** Moving BBS to new server.

**On old server:**
```bash
# Create full backup
python manage.py backup_applets --output /migration/backup

# Backup database
pg_dump axon_bbs > /migration/database.sql

# Transfer to new server
scp -r /migration newserver:/tmp/
```

**On new server:**
```bash
# Restore database
psql axon_bbs < /tmp/migration/database.sql

# Run migrations
python manage.py migrate

# Restore applets
python manage.py restore_applets /tmp/migration/backup --rekey

# Start services
sudo systemctl start axon_bbs
```

**Result:** Complete migration with minimal downtime

---

### Example 5: Disaster Recovery (Hybrid)

**Scenario:** Production server crashed, restore from backup.

**Using CLI (fastest):**
```bash
# On new server
python manage.py restore_applets /backups/latest --rekey
python manage.py clone_from_bbs http://backup_node.onion --skip-applets
```

**Using Admin UI (if CLI unavailable):**
1. Manually copy backup to new server
2. Use admin to clone configuration from backup node
3. Manually restore applet files
4. Use "Force Refresh and Re-key Peer" action

**Result:** Production restored

## Technical Differences

### Admin Actions

**Implementation:**
- Defined in `core/admin.py`
- Uses Django admin framework
- Runs synchronously in web request
- Limited error reporting (just success/error message)
- Can timeout on slow networks

**Code flow:**
```python
def clone_full_bbs(self, request, queryset):
    # Calls management command internally
    call_command('clone_from_bbs', peer.web_ui_onion_url)
```

### CLI Commands

**Implementation:**
- Defined in `core/management/commands/`
- Standalone Python scripts
- Detailed console output
- Better error messages and logging
- Can run with custom timeouts
- Supports pipes and redirection

**Code flow:**
```python
class Command(BaseCommand):
    def handle(self, *args, **options):
        # Full implementation with detailed steps
        # Better error handling
        # Configurable options
```

## Best Practices

### For Production:

1. **Use CLI for backups** - Automate with cron
2. **Use Admin UI for quick fixes** - Manual one-time operations
3. **Test restores regularly** - Verify backups work
4. **Keep multiple backup locations** - Different physical media
5. **Document your workflow** - Script everything

### For Development:

1. **Use CLI for refreshes** - Automate test instance updates
2. **Use backup-based cloning** - Faster than network sync
3. **Script your setup** - Infrastructure as code
4. **Use partial cloning** - Only clone what you need

### For Disaster Recovery:

1. **Have both methods ready** - Admin UI as fallback
2. **Practice recovery** - Test your procedures
3. **Keep offline backups** - Not just on the same server
4. **Document steps** - Written procedures

## Troubleshooting

### Admin UI Issues

**Problem:** Action times out
**Solution:** Use CLI with custom timeout

**Problem:** Can't see progress
**Solution:** Check server logs or use CLI

**Problem:** Error message not helpful
**Solution:** Use CLI for detailed error output

### CLI Issues

**Problem:** Command not found
**Solution:** Ensure virtual environment activated

**Problem:** Permission denied
**Solution:** Run as correct user (usually not root)

**Problem:** Import errors
**Solution:** Check Django settings and database connection

## Migration Path

If you're currently using the old admin clone action:

### Before (Old Way)
```
1. Admin → Clone configuration from peer
2. SSH → python manage.py sync_applets_from_peer
3. SSH → python manage.py download_applet_chunks
4. Debug errors manually
```

### After (New Way - Admin)
```
1. Admin → Clone full BBS from peer
   (Everything done automatically)
```

### After (New Way - CLI)
```
1. SSH → python manage.py clone_from_bbs http://peer.onion
   (Everything done automatically)
```

## Summary

- **Admin UI**: Best for occasional manual operations
- **CLI Commands**: Best for automation, scripting, and power users
- **New "Clone full BBS" action**: Combines benefits of both (UI + completeness)
- **Backup commands**: CLI-only, essential for disaster recovery

Choose based on your needs, but having both available gives you maximum flexibility!
