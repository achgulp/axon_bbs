# Axon BBS NetCode Development Roadmap

**Created**: November 22, 2025
**Purpose**: Development plan for building reusable netcode library on top of 60fps real-time infrastructure

---

## Overview

This roadmap outlines the development of **AxonNetcode** - a reusable multiplayer networking library that sits on top of the existing 60fps real-time infrastructure. The library will provide game developers with high-level abstractions for common networking patterns while remaining flexible for game-specific customization.

### Target Games

- **Bee Adventure** (FPS - in development): Primary driver for FPSNetcode preset
- **Avenger Bee** (FPS - existing): Will benefit from FPSNetcode preset
- **Warzone Lite** (RTS - existing): Needs RTSNetcode preset
- **HexGL** (Racing - existing): Needs RacingNetcode preset

---

## Development Phases

### Phase 1: Core Library Design

- [ ] **Design AxonNetcode core library architecture and API**
  - Define base class structure
  - Plan event system and callbacks
  - Design state synchronization patterns
  - Specify message format standards
  - Document core API methods

### Phase 2: Core Implementation

- [ ] **Implement AxonNetcode.js core library**
  - Player state synchronization
  - Client-side prediction framework
  - Server reconciliation logic
  - Remote player interpolation
  - Input history buffering
  - Tick management system

### Phase 3: Game-Specific Presets

- [ ] **Build FPSNetcode preset for Bee Adventure and Avenger Bee**
  - Client prediction for player movement
  - Lag compensation for shooting/hit detection
  - Server-authoritative resource collection
  - Health/damage synchronization
  - Respawn handling

- [ ] **Build RTSNetcode preset for Warzone Lite**
  - Unit selection synchronization
  - Command buffering and validation
  - Deterministic simulation support
  - Fog of war handling
  - Building/construction state sync

- [ ] **Build RacingNetcode preset for HexGL**
  - Vehicle physics prediction
  - Track position synchronization
  - Checkpoint validation
  - Lap timing coordination
  - Starting grid positioning

### Phase 4: Utility Modules

- [ ] **Create netcode utilities**
  - `interpolation.js`: Lerp, slerp, and smoothing functions
  - `serialization.js`: Compact binary message formats
  - `lagCompensation.js`: Rewind/replay helpers for hit detection
  - `prediction.js`: Physics prediction helpers
  - `reconciliation.js`: State correction algorithms

### Phase 5: Bee Adventure Integration

- [ ] **Port Bee Adventure to Axon BBS as single-player applet**
  - Package game code and assets via BitSync
  - Integrate with `window.bbs` API
  - Implement data persistence (scores, progress)
  - Test single-player functionality
  - Optimize asset loading

- [ ] **Integrate FPSNetcode into Bee Adventure for multiplayer**
  - Replace local-only logic with netcode calls
  - Implement server-side validation
  - Add multiplayer UI (player list, scoreboard)
  - Handle player join/leave events
  - Test with multiple clients

### Phase 6: Documentation

- [ ] **Write netcode library documentation and usage examples**
  - API reference for core AxonNetcode class
  - Usage guides for each preset (FPS, RTS, Racing)
  - Code examples for common patterns
  - Migration guide for existing games
  - Best practices and performance tips
  - Troubleshooting guide

### Phase 7: Testing & Optimization

- [ ] **Test multiplayer with 4-8 players on single/dual Pi4 setup**
  - Single Pi4: 4 players @ 60fps local
  - Dual Pi4 LAN: 8 players (4 per Pi4) @ 60fps local + federation
  - Measure latency and CPU usage
  - Profile network bandwidth
  - Optimize message size and frequency
  - Test edge cases (disconnect, lag spikes, etc.)

---

## File Structure

```
frontend/src/lib/netcode/
├── AxonNetcode.js              # Core library
├── presets/
│   ├── FPSNetcode.js          # For Bee Adventure, Avenger Bee
│   ├── RTSNetcode.js          # For Warzone Lite
│   └── RacingNetcode.js       # For HexGL
├── utils/
│   ├── interpolation.js       # Smoothing and lerp utilities
│   ├── serialization.js       # Binary message packing
│   ├── lagCompensation.js     # Hit detection rewinding
│   ├── prediction.js          # Physics prediction helpers
│   └── reconciliation.js      # State correction algorithms
├── examples/
│   ├── fps-example.js         # FPS netcode usage
│   ├── rts-example.js         # RTS netcode usage
│   └── racing-example.js      # Racing netcode usage
└── README.md                   # Library documentation
```

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Game Layer                          │
│  (Bee Adventure, Warzone Lite, HexGL, etc.)        │
│  - Game-specific logic                              │
│  - Rendering & input handling                       │
└──────────────┬──────────────────────────────────────┘
               │ uses
┌──────────────▼──────────────────────────────────────┐
│          AxonNetcode Library (NEW)                   │
│  - PlayerStateSync, EntityStateSync                 │
│  - ClientPredictor, Interpolator                    │
│  - LagCompensator, MessageSerializer                │
│  - Presets: FPSNetcode, RTSNetcode, RacingNetcode  │
└──────────────┬──────────────────────────────────────┘
               │ uses
┌──────────────▼──────────────────────────────────────┐
│     60fps Real-Time Infrastructure                   │
│  - Dual-loop polling (local 60fps + federation)     │
│  - MessageBoard event bus                            │
│  - LAN/Tor federation modes                          │
└─────────────────────────────────────────────────────┘
```

---

## Success Criteria

- [ ] Bee Adventure runs multiplayer with 4 players @ 60fps on single Pi4
- [ ] Perceived latency < 50ms for local players
- [ ] No code duplication between games for common patterns
- [ ] Clear documentation enables new developers to add multiplayer easily
- [ ] Library remains optional - advanced users can still go direct to 60fps API

---

## Notes

- **Start with Bee Adventure**: Build netcode as needed for one game, then extract patterns
- **Keep it modular**: Each preset and utility should be independently usable
- **Prioritize FPS first**: Bee Adventure is the primary driver, other presets can follow
- **Document as you go**: Write examples while building, not after

---

**Next Steps**: Complete Bee Adventure single-player (AI bees, NPCs) before starting Phase 5
