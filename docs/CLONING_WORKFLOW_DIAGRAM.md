# Axon BBS Cloning Workflow Diagram

## Network-Based Cloning Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCE BBS (Host)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Applets    │  │ Configuration│  │   Content    │         │
│  │  - Metadata  │  │  - Users     │  │  - Messages  │         │
│  │  - Manifests │  │  - Boards    │  │  - Files     │         │
│  │  - Chunks    │  │  - Settings  │  │  - PMs       │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Tor Network
                              │ (Encrypted + Just-in-Time Rekeying)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           DESTINATION BBS (Clone) - Running:                    │
│           python manage.py clone_from_bbs http://host.onion     │
│                                                                 │
│  Step 1: Update Peer Key                                       │
│  ┌────────────────────────────────────────────┐                │
│  │  update_peer_key http://host.onion         │                │
│  │  ✓ Fetches host's public key               │                │
│  │  ✓ Stores in TrustedInstance table         │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 2: Clone Configuration                                   │
│  ┌────────────────────────────────────────────┐                │
│  │  Fetches /api/federation/export_config/    │                │
│  │  ✓ Users (excluding superusers)            │                │
│  │  ✓ Message boards                          │                │
│  │  ✓ Settings and configurations             │                │
│  │  ✓ Filters out superuser content           │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 3: Sync Applet Manifests                                 │
│  ┌────────────────────────────────────────────┐                │
│  │  sync_applets_from_peer                    │                │
│  │  ✓ Fetches manifests with JIT rekeying     │                │
│  │  ✓ Updates existing applet records         │                │
│  │  ✓ Adds encryption keys for local instance │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 4: Download Chunks                                       │
│  ┌────────────────────────────────────────────┐                │
│  │  download_applet_chunks                    │                │
│  │  ✓ Downloads missing code chunks           │                │
│  │  ✓ Verifies SHA-256 hashes                 │                │
│  │  ✓ Stores in bitsync_chunks/               │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 5: Re-key All Content                                    │
│  ┌────────────────────────────────────────────┐                │
│  │  Iterates through all content:             │                │
│  │  ✓ Messages                                │                │
│  │  ✓ Files                                   │                │
│  │  ✓ Private messages                        │                │
│  │  ✓ Applets                                 │                │
│  │  Updates manifests for local instance      │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  ✓ Clone Complete!                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Backup-Based Cloning Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOURCE BBS (Host)                            │
│           python manage.py backup_applets                       │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Applets    │  │  AppletData  │  │  HighScores  │         │
│  │  - Metadata  │  │  - User data │  │  - Scores    │         │
│  │  - Manifests │  │  - Manifests │  │  - Stats     │         │
│  │  - Chunks    │  │  - Chunks    │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           ▼                                     │
│                ┌──────────────────┐                            │
│                │  Backup Archive  │                            │
│                │  - JSON metadata │                            │
│                │  - Chunk files   │                            │
│                │  - Manifest      │                            │
│                └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Physical Transfer
                              │ (USB, Network Share, SCP, etc.)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           DESTINATION BBS (Clone)                               │
│           python manage.py restore_applets /backup --rekey      │
│                                                                 │
│  Step 1: Read Backup Manifest                                  │
│  ┌────────────────────────────────────────────┐                │
│  │  Reads backup_manifest.json                │                │
│  │  ✓ Lists all applets in backup             │                │
│  │  ✓ Verifies backup integrity               │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 2: Restore Metadata                                      │
│  ┌────────────────────────────────────────────┐                │
│  │  For each applet:                          │                │
│  │  ✓ Reads metadata.json                     │                │
│  │  ✓ Creates Applet record                   │                │
│  │  ✓ Creates AppletData records              │                │
│  │  ✓ Creates HighScore records               │                │
│  │  ✓ Creates SharedState record              │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 3: Restore Chunks                                        │
│  ┌────────────────────────────────────────────┐                │
│  │  Copies chunk files:                       │                │
│  │  ✓ Code chunks → bitsync_chunks/           │                │
│  │  ✓ Data chunks → bitsync_chunks/           │                │
│  │  ✓ Preserves directory structure           │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  Step 4: Re-key Manifests (--rekey flag)                       │
│  ┌────────────────────────────────────────────┐                │
│  │  For each restored applet:                 │                │
│  │  ✓ Gets AES key from old manifest          │                │
│  │  ✓ Encrypts for current instance keys      │                │
│  │  ✓ Updates manifest in database            │                │
│  └────────────────────────────────────────────┘                │
│                                                                 │
│  ✓ Restore Complete!                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Single-Command Clone Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  USER RUNS: python manage.py clone_from_bbs http://host.onion   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  Is --backup-dir specified?             │
        └─────────────────────────────────────────┘
                    │                   │
                    │ No                │ Yes
                    │                   │
                    ▼                   ▼
    ┌───────────────────────┐   ┌──────────────────────┐
    │  Network Clone Path   │   │  Backup Clone Path   │
    │  (See diagram above)  │   │  (See diagram above) │
    └───────────────────────┘   └──────────────────────┘
                    │                   │
                    └───────┬───────────┘
                            ▼
                ┌───────────────────────┐
                │  --skip-config?       │
                └───────────────────────┘
                        │       │
                        │ No    │ Yes
                        │       │
                        ▼       ▼
                ┌────────┐   ┌────────┐
                │ Clone  │   │  Skip  │
                │ Config │   │        │
                └────────┘   └────────┘
                        │
                        ▼
                ┌───────────────────────┐
                │  --skip-applets?      │
                └───────────────────────┘
                        │       │
                        │ No    │ Yes
                        │       │
                        ▼       ▼
                ┌────────┐   ┌────────┐
                │ Clone  │   │  Skip  │
                │Applets │   │        │
                └────────┘   └────────┘
                        │
                        ▼
                ┌───────────────────────┐
                │  Force Re-key All     │
                │  Content              │
                └───────────────────────┘
                        │
                        ▼
                ┌───────────────────────┐
                │  ✓ Clone Complete!    │
                └───────────────────────┘
```

## Encryption Key Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     MANIFEST STRUCTURE                          │
│                                                                 │
│  {                                                              │
│    "content_hash": "abc123...",                                 │
│    "chunk_hashes": ["hash1", "hash2", ...],                     │
│    "encryption_iv": "base64_iv",                                │
│    "encrypted_aes_keys": {                                      │
│      "instance1_checksum": "encrypted_key1",  ← Host instance   │
│      "instance2_checksum": "encrypted_key2"   ← Clone instance  │
│    }                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  JUST-IN-TIME REKEYING                          │
│                                                                 │
│  1. Clone requests manifest from host                          │
│  2. Host checks: Does manifest have clone's key?               │
│     ├─ Yes: Return manifest as-is                              │
│     └─ No:  Decrypt AES key with host's private key            │
│             Encrypt AES key with clone's public key            │
│             Add to encrypted_aes_keys                          │
│             Return updated manifest                            │
│                                                                 │
│  3. Clone receives manifest and saves to database              │
│  4. Clone can now decrypt content using its private key        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DECRYPTION PROCESS                             │
│                                                                 │
│  1. Get manifest from database                                 │
│  2. Calculate local instance checksum                          │
│  3. Get encrypted AES key for local checksum                   │
│  4. Decrypt AES key using local private key                    │
│  5. Decrypt content using AES key + IV                         │
│  6. Verify decrypted content hash matches content_hash         │
│  7. Return decrypted content                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Decision Tree: Which Clone Method?

```
                    START
                      │
                      ▼
        ┌─────────────────────────────┐
        │ Do you have network access  │
        │ to the source BBS?          │
        └─────────────────────────────┘
                │              │
                │ Yes          │ No
                │              │
                ▼              ▼
    ┌────────────────┐   ┌────────────────┐
    │ Is the source  │   │  Must use      │
    │ BBS online and │   │  backup-based  │
    │ accessible?    │   │  clone         │
    └────────────────┘   └────────────────┘
            │   │              │
            │   └──────────────┘
            │ Yes
            ▼
    ┌────────────────────────────┐
    │ Do you need to clone       │
    │ multiple times or want     │
    │ faster clones?             │
    └────────────────────────────┘
            │              │
            │ Yes          │ No
            │              │
            ▼              ▼
    ┌────────────┐   ┌──────────────┐
    │ Create     │   │ Use network  │
    │ backup on  │   │ clone for    │
    │ source,    │   │ one-time     │
    │ then use   │   │ clone        │
    │ backup-    │   │              │
    │ based      │   │ Faster setup │
    │ clone      │   │ Less storage │
    │            │   │              │
    │ Faster for │   └──────────────┘
    │ multiple   │
    │ clones     │
    └────────────┘
```

## Chunk Verification Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHUNK VERIFICATION                           │
│                                                                 │
│  After restore or download:                                    │
│                                                                 │
│  For each chunk in manifest.chunk_hashes:                      │
│    1. Read chunk file from disk                                │
│    2. Calculate SHA-256 hash                                   │
│    3. Compare with expected hash from manifest                 │
│    4. If match: ✓ Chunk verified                               │
│       If mismatch: ✗ Chunk corrupted                           │
│                                                                 │
│  If any chunk fails:                                           │
│    - Delete corrupted chunk                                    │
│    - Re-download from peer                                     │
│    - Verify again                                              │
│                                                                 │
│  After all chunks verified:                                    │
│    - Reassemble chunks                                         │
│    - Decrypt using AES key                                     │
│    - Calculate content hash                                    │
│    - Verify matches manifest.content_hash                      │
│    - If match: ✓ Content ready                                 │
│      If mismatch: ✗ Content corrupted                          │
└─────────────────────────────────────────────────────────────────┘
```
