# Changelog

All notable changes to Axon BBS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- User-uploaded applets (60% complete)
- Universal embed framework (video, PDF, audio)
- Browser history integration (React Router)
- Progressive Web App (PWA) support
- Mobile-responsive UI improvements

---

## [10.27.1] - 2025-10-23

### Added
- **Comprehensive Documentation Overhaul**
  - New `README.md` with complete project overview, quick start, and architecture diagrams
  - New `PROJECT_STATUS.md` with detailed development progress and metrics
  - New `ARCHITECTURE.md` with in-depth technical specifications
  - New `DEVELOPER_HANDBOOK.md` with complete development workflows and best practices
  - New `CHANGELOG.md` for version tracking
  - Updated `docs/AxonBBSAppletDevGuideforAI.txt` with all recent API changes

### Changed
- Reorganized documentation structure
  - Moved 90+ old versioned documents to `docs/archive/`
  - Consolidated scattered `.md` files to `docs/` directory
  - Added `docs/archive/` to `.gitignore`
  - Moved AxonChat and upgrade docs to proper locations

### Fixed
- Documentation accuracy issues
  - Corrected all API signatures (`postEvent`, `readEvents`)
  - Fixed event structure documentation (body vs payload)
  - Updated performance metrics to reflect current production status

---

## [10.27.0] - 2025-10-20

### Added
- **Real-Time Chat System (AxonChat v21)**
  - Client-side polling architecture (2-second interval)
  - Server-side timezone conversion for Tor Browser compatibility
  - User presence sidebar with active users
  - Real-time message updates with 1-3 second latency (100x improvement over v20)
  - Subject-based event filtering for multi-applet support

- **Event Bus API**
  - `postEvent({ subject, body })` - Post real-time events
  - `readEvents()` - Poll for all events with client-side filtering
  - Complete event structure with metadata (author, timestamps, display_time)
  - Support for multiple event types on single MessageBoard

- **Timezone Support**
  - Automatic browser timezone detection via `Intl.DateTimeFormat()`
  - Server-side timestamp conversion to user's local time
  - `display_time` field in event responses (pre-formatted)
  - Works in privacy-hardened browsers (Tor Browser)

### Changed
- **AxonChat Architecture Migration**
  - Migrated from AppletSharedState to MessageBoard architecture
  - Replaced Server-Sent Events (SSE) with client-side polling
  - Consolidated to "Realtime Event Board" with subject filtering
  - Improved scalability for future real-time applets

- **AppletRunner Enhancements**
  - Added timezone detection and passing to backend
  - Improved error handling for integrity check failures
  - Enhanced loading screen with detailed status messages

### Fixed
- Message ordering (chronological instead of reverse)
- Timezone display in Tor Browser (showed UTC instead of local time)
- Code integrity errors from duplicate FileAttachments with different keys
- SSE connection issues (replaced with reliable polling)

### Removed
- **Deprecated Components**
  - `core/agents/chat_agent_service.py` (224 lines)
  - `applets/chat_agent_service.py` (193 lines)
  - Legacy SSE endpoints (now return HTTP 410 Gone with migration instructions)

---

## [10.26.5] - 2025-10-15

### Added
- **Applet Development Tooling**
  - `post_applet_update` management command for automated applet deployment
  - Automatic BitSync manifest creation
  - FileAttachment creation with proper encryption
  - Automatic database updates (code_manifest field)
  - Posted messages to "Applet Library" board with version info

- **Complete Applet Development Guide**
  - 50KB comprehensive guide for AI-assisted applet development
  - Copy-paste ready `window.bbs` API helper
  - Three architecture templates (simple, hybrid, real-time)
  - Utility functions (debug console, crypto, Base64)
  - Production-tested examples from AxonChat, HexGL, FortressOverlord

### Changed
- Applet deployment workflow simplified from 5-10 manual steps to single command
- Documentation updated with corrected API signatures
- Improved developer onboarding materials

---

## [10.26.0] - 2025-10-14

### Added
- **Comprehensive Backup/Restore System**
  - `backup_applets` - Create complete applet backups
  - `restore_applets` - Restore from backups with automatic re-keying
  - `clone_from_bbs` - Clone entire BBS from peer (network + backup hybrid)
  - `download_applet_chunks` - Download missing content chunks
  - `check_applet_manifest` - Verify manifest integrity
  - `sync_applets_from_peer` - Sync applets from trusted peer

- **Admin UI Integration**
  - "Clone full BBS from peer" action in TrustedInstance admin
  - "Clone configuration from peer" (existing, clarified)
  - "Force Refresh and Re-key Peer" action

- **Just-In-Time Rekeying**
  - Automatic manifest re-keying during federation sync
  - Deep copy to prevent database mutation
  - Updates existing manifests instead of skipping

### Changed
- **Federation Sync Improvements**
  - Update existing manifests instead of skipping content
  - Proper chunk hash verification
  - Improved error handling and logging

### Fixed
- **Cloning Issues**
  - "Code integrity check failed" errors after cloning
  - Encryption key mismatches between instances
  - Manifest re-keying during restore operations
  - Chunk download verification

### Performance
- Backup (5 applets): ~2 seconds
- Restore (1 applet): ~1 second
- Network clone: 5-30 minutes (depends on Tor)
- Backup clone: 1-5 minutes

---

## [10.25.0] - 2025-10-02

### Added
- **Client-Side Integrity Verification**
  - SHA-256 checksum verification before applet execution
  - Prevents execution of corrupted or tampered code
  - Shows verification status in loading screen
  - Checksum exposed via `window.BBS_APPLET_CHECKSUM`

- **Hybrid Applet Architecture**
  - Support for separate code and asset packages
  - Dynamic asset loading from ZIP packages
  - On-demand streaming of large files
  - Example: HexGL (17KB code + 5MB assets)

- **Backward Compatibility**
  - Support for both file-based and legacy applet formats
  - Automatic format detection in AppletRunner
  - No need to repackage old applets

- **Shared Library Loading**
  - `required_libraries` parameter in applet config
  - Libraries loaded as separate <script> tags
  - Support for THREE.js, JSZip, and other large dependencies
  - Improves caching and reduces applet size

### Changed
- **AppletRunner Security Enhancements**
  - Added SHA-256 hash verification step
  - Enhanced error messages for integrity failures
  - Improved loading screen with progress indicators

---

## [10.21.2] - 2025-09-27

### Added
- **Dynamic Agent Loading**
  - ServiceManager dynamically loads agents from database
  - `agent_service_path` and `agent_parameters` fields on User model
  - Configure agents entirely through Django admin
  - Enable/disable services without code changes

- **Automated Configuration Cloning**
  - `/api/federation/export_config/` endpoint
  - Exports users, boards, applets (excludes sensitive data)
  - Admin action: "Clone configuration from peer"
  - Automatic generation of unique avatars for imported users
  - Skips superuser accounts during import

### Changed
- Background services now configured via database instead of code
- Improved federation API with better error handling

---

## [10.21.0] - 2025-09-24

### Added
- **Unified Moderation Hub**
  - Single interface for all moderation tasks
  - Ticket-based system (reports, profile approvals, inquiries)
  - Automated PM acknowledgments for closed inquiries
  - Karma rewards for valid reports

- **Backend Modularization Complete**
  - `core/` - Cross-cutting models and services
  - `accounts/` - User management
  - `messaging/` - Message boards and messages
  - `applets/` - Applet framework
  - `federation/` - Inter-server communication

### Changed
- Refactored from 2 large apps to 5 focused apps
- Improved code organization and maintainability
- Service-oriented architecture (thin views, logic in services)

---

## [10.15.0] - 2025-09-21

### Added
- **Private Messaging (E2E Encrypted)**
  - End-to-end encrypted private messages
  - RSA-based encryption with recipient's public key
  - Only recipient can decrypt
  - Message threading and conversation views

### Security
- All private messages encrypted at rest
- Encryption keys never leave user devices
- Server cannot read message contents

---

## [10.10.0] - 2025-09-16

### Added
- **BitSync Protocol v2.0**
  - Content-addressed storage with SHA-256 hashing
  - AES-256-GCM encryption for all content
  - RSA-OAEP key distribution to trusted peers
  - Automatic deduplication (same content = same hash)
  - Chunk-based transfer (512KB default chunk size)

- **Federation Infrastructure**
  - Tor-only communication (.onion addresses)
  - RSA-PSS signed requests
  - Whitelist-based peer trust
  - Automatic content synchronization

### Security
- Multi-layer encryption (transport + content)
- Cryptographic integrity verification
- No single point of failure
- Censorship-resistant design

---

## [10.0.0] - 2025-08-28

### Added
- **Initial Release**
  - Django 4.2+ backend with PostgreSQL
  - React 18 single-page application frontend
  - User authentication with RSA key pairs
  - Message boards and public messaging
  - File attachments with encryption
  - Basic applet framework
  - Sandboxed applet execution

### Security
- Cryptographic user identities (RSA-2048)
- Content encryption at rest
- Sandboxed applet execution
- CSRF and XSS protection

---

## Version Numbering

Axon BBS uses semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Incompatible API changes, database schema changes requiring migration
- **MINOR**: New features, backward-compatible
- **PATCH**: Bug fixes, documentation updates, backward-compatible

**Special Versions:**
- `10.27.0+` indicates unreleased changes on top of 10.27.0

---

## Migration Guide

### Upgrading from 10.26.x to 10.27.x

**Breaking Changes:**
- AxonChat API changed (see docs/AxonChat_Migration_Complete.md)
- Old endpoints return HTTP 410 Gone

**Steps:**
1. Update code: `git pull origin main`
2. Update dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Rebuild frontend: `cd frontend && npm run build`
5. Restart services: `sudo systemctl restart axon-bbs`

**Database Migrations:**
- No breaking changes
- Existing data fully compatible

**Frontend Changes:**
- AxonChat.js updated (automatic via npm build)
- AppletRunner.js updated (automatic)

### Upgrading from 10.21.x to 10.26.x

**Breaking Changes:**
- None (backward compatible)

**New Features:**
- Backup/restore system available
- Integrity verification automatic
- Hybrid applets supported

**Steps:**
1. Standard upgrade process (pull, migrate, build, restart)
2. Optional: Configure applet asset packages
3. Optional: Set up automated backups

---

## Deprecation Notices

### Deprecated in 10.27.0 (Will be removed in 11.0.0)

**AppletSharedState endpoints for chat:**
- `POST /api/applets/{id}/update_state/`
- `GET /api/applets/{id}/events/`

**Replacement:**
- Use MessageBoard with `is_realtime=True`
- Use `/api/chat/post/` and `/api/applets/{id}/read_events/`

**Migration Guide:** See `docs/AxonChat_Migration_Complete.md`

---

## Security Advisories

### None Currently

No security vulnerabilities have been reported.

**To report a security issue:**
- Email: security@axonbbs.example.com (if available)
- Or: Open a private GitHub security advisory

**Do not** open public issues for security vulnerabilities.

---

## Contributors

**Lead Developer:**
- Achduke7 - Original concept and implementation

**Special Thanks:**
- The Tor Project - Anonymity infrastructure
- Django community - Web framework
- React community - Frontend framework

---

## License

This project is licensed under the GNU General Public License v3.0 or later.

See [LICENSE](LICENSE) for details.

---

**Changelog Maintained By:** Achduke7
**Last Updated:** October 23, 2025

---

## Legend

- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements/fixes
- `Performance` - Performance improvements
