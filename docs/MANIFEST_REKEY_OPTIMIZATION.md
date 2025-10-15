# Manifest Re-key Optimization

**Date:** 2025-10-14
**Issue:** Manifests being re-keyed on every sync cycle
**Solution:** Skip update if no new encryption keys

## Problem

After implementing the cloning and manifest update functionality, pibbs was constantly re-keying and saving manifests on every sync cycle, even when nothing had changed:

```
INFO Received 28 new manifest(s) from peer
INFO Manifest re-keyed for 2 total instance(s).
INFO Updated manifest for existing message 5e870efb83
INFO Manifest re-keyed for 2 total instance(s).
INFO Updated manifest for existing file 2c81773ecf
... (repeated 28 times every 2 minutes)
```

This caused:
- Unnecessary database writes
- Excessive logging
- Wasted CPU cycles
- Repeated "Manifest re-keyed" messages

## Root Cause

In `sync_service.py`, the `_process_received_manifests()` function was **unconditionally** updating existing content:

```python
# OLD CODE (problematic)
if existing_message or existing_file or existing_pm or existing_applet:
    # Always rekey and save, even if keys haven't changed
    updated_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(manifest)
    existing_message.metadata_manifest = updated_manifest
    existing_message.save()  # ← Saves EVERY time
```

Even though `rekey_manifest_for_new_peers()` returns a new copy (deep copy), it was being saved to the database every sync cycle, regardless of whether any new keys were actually added.

## Solution

Added a check to compare encryption keys before updating:

```python
# NEW CODE (optimized)
if existing_message or existing_file or existing_pm or existing_applet:
    # Get the current manifest from the database
    if existing_message:
        current_manifest = existing_message.metadata_manifest
    elif existing_file:
        current_manifest = existing_file.metadata_manifest
    elif existing_pm:
        current_manifest = existing_pm.metadata_manifest
    else:  # existing_applet
        current_manifest = existing_applet.code_manifest

    # Check if the incoming manifest has any new encryption keys
    current_keys = set(current_manifest.get('encrypted_aes_keys', {}).keys())
    incoming_keys = set(manifest.get('encrypted_aes_keys', {}).keys())

    # Only update if there are new keys we don't have
    if not incoming_keys.issubset(current_keys):
        # New keys detected - merge them in
        updated_manifest = service_manager.bitsync_service.rekey_manifest_for_new_peers(manifest)
        existing_message.metadata_manifest = updated_manifest
        existing_message.save()  # ← Only saves when needed
        logger.info(f"Updated manifest for existing message {content_hash[:10]} (added {len(incoming_keys - current_keys)} new key(s))")
    # else: No new keys, skip update
```

## How It Works

### Key Comparison Logic

1. **Extract current keys**: Get the set of instance checksums from the database manifest
2. **Extract incoming keys**: Get the set of instance checksums from the peer's manifest
3. **Check subset**: If all incoming keys are already in current keys, skip update
4. **Update if needed**: Only when new keys are detected, merge and save

### Example Scenario

**Scenario 1: No new keys (common case)**
```
Current keys:  {checksum_host, checksum_pibbs}
Incoming keys: {checksum_host, checksum_pibbs}
Result: Skip update (subset check passes)
```

**Scenario 2: New peer added (rare case)**
```
Current keys:  {checksum_host, checksum_pibbs}
Incoming keys: {checksum_host, checksum_pibbs, checksum_newpeer}
Result: Update manifest (added 1 new key)
```

**Scenario 3: Fresh clone (initial sync)**
```
Current keys:  {checksum_host}
Incoming keys: {checksum_host, checksum_pibbs}
Result: Update manifest (added 1 new key)
```

## Results

### Before Optimization

```
INFO 2025-10-14 23:02:04,384 <-- Received 28 new manifest(s)
INFO 2025-10-14 23:02:04,488 Manifest re-keyed for 2 total instance(s).
INFO 2025-10-14 23:02:04,574 Updated manifest for existing message 5e870efb83
INFO 2025-10-14 23:02:04,629 Manifest re-keyed for 2 total instance(s).
INFO 2025-10-14 23:02:04,732 Updated manifest for existing PM c2cba6bf24
... (28 updates total)
```

**Impact:**
- 28 database writes
- 28 re-key operations
- 56 log messages (2 per manifest)

### After Optimization

```
INFO 2025-10-14 23:04:10,291 <-- Received 28 new manifest(s)
INFO 2025-10-14 23:04:10,780 Timestamp for peer updated
```

**Impact:**
- 0 database writes
- 0 re-key operations
- 2 log messages (receive + timestamp)

**Improvement:** 100% reduction in unnecessary updates

## When Manifests ARE Updated

Manifests will still be updated when:

1. **New peer added to federation**
   - A new BBS instance is added as a trusted peer
   - Host re-keys content for the new peer
   - Next sync brings manifest with new encryption key

2. **Fresh clone/restore**
   - Instance is cloned from backup
   - Has new instance keys
   - First sync after clone updates manifests

3. **Manual re-key operation**
   - Admin runs "Force Refresh and Re-key Peer"
   - Updates all manifests with new keys

## Performance Impact

### Network Traffic
- **No change**: Same number of manifests received
- Optimization is on the *receiving* end

### Database Operations

**Per sync cycle (28 manifests):**

| Operation | Before | After | Savings |
|-----------|--------|-------|---------|
| SELECT queries | 28 | 28 | 0 |
| UPDATE queries | 28 | 0 | 100% |
| Re-key operations | 28 | 0 | 100% |
| Log writes | 56 | 2 | 96% |

**Yearly savings (assuming 2-minute sync interval):**

- Database writes saved: ~7.3 million
- Log messages saved: ~14.6 million

### CPU Usage

- Reduced CPU for:
  - JSON serialization (28 fewer per cycle)
  - Database transaction overhead
  - Log formatting and writing

## Code Location

**File:** `core/services/sync_service.py`
**Function:** `_process_received_manifests()`
**Lines:** 202-242

## Testing

Verified on pibbs instance:

1. **Before fix:**
   - Every sync: 28 "Updated manifest" messages
   - Every sync: 28 "Manifest re-keyed" messages

2. **After fix:**
   - Sync cycles: No update messages
   - Manifests still have correct keys
   - Content still decrypts properly

3. **Tested scenarios:**
   - Normal sync (no new keys): No updates ✓
   - New content: Downloads correctly ✓
   - Existing content: Decrypts correctly ✓

## Future Improvements

### Potential Optimizations

1. **Batch key comparison**
   - Compare all manifests at once
   - Single database query instead of one per manifest

2. **Key version tracking**
   - Add manifest version number
   - Skip comparison if versions match

3. **Checksum caching**
   - Cache local instance checksums
   - Avoid recalculating every manifest

### Monitoring

Consider adding metrics:
- Number of manifests updated per sync
- Number of new keys added
- Average re-key time

## Related Documentation

- [CLONING_FIXES_SUMMARY.md](../CLONING_FIXES_SUMMARY.md) - Overview of cloning fixes
- [BACKUP_AND_CLONING.md](BACKUP_AND_CLONING.md) - Complete cloning guide
- [Just-in-Time Rekeying](CLONING_WORKFLOW_DIAGRAM.md) - How rekeying works
