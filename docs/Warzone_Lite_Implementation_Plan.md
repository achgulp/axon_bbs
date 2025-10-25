# Warzone Lite - Implementation Plan
## Real-Time Strategy for Axon BBS with Federation

**Version:** 1.0
**Date:** 2025-10-24
**Status:** Ready for Implementation

---

## Executive Summary

**Warzone Lite** is a JavaScript-native RTS game for Axon BBS that captures the tactical depth of Warzone 2100 while being optimized for browser-based federated multiplayer.

### Key Design Decisions

✅ **Orthographic 3D view** - Classic RTS camera (like Age of Empires)
✅ **Multi-level terrain** - 0-8 ground elevation levels for tactical depth
✅ **Multi-altitude air combat** - 3 distinct air layers (Low/Medium/High)
✅ **Simple shapes + textures** - Extend FortressOverlord's proven approach
✅ **Heartbeat synchronization** - 2-second command sync for BBS federation
✅ **64×80 tile maps** - Perfect for 2-4 player intense matches
✅ **15-20MB total size** - Asset extraction from Warzone 2100 source

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Warzone Lite Architecture                  │
└─────────────────────────────────────────────────────────┘

VISUAL LAYER (What players see)
├── Orthographic Camera (45° angle, no perspective)
├── Multi-level 3D Terrain (heightmap 0-8)
├── Simple 3D Units (boxes, cylinders, cones)
├── Warzone 2100 Textures (applied to simple shapes)
└── Altitude Indicators (shadows, lines, colors)

GAMEPLAY LAYER (Game logic)
├── Terrain System (64×80 tiles, strategic features)
├── Unit System (ground units 0-8, air units 10/15/20)
├── Combat System (elevation bonuses, altitude restrictions)
├── Resource System (power generation, unit costs)
├── Building System (factories, bases, defenses)
└── AI Opponent (pathfinding, tactics)

MULTIPLAYER LAYER (Federation sync)
├── Heartbeat System (2-second command windows)
├── Event Protocol (JSON commands via BBS)
├── State Synchronization (deterministic simulation)
└── BBS API Integration (postEvent, readEvents)

ASSET LAYER (Resources)
├── Textures (~8-12MB, extracted from WZ2100)
├── Models (~200KB, PIE files converted to simple shapes)
├── Maps (~100KB, 3-5 premade heightmaps)
└── Sounds (~2-3MB, essential audio only)
```

---

## Elevation System Design

### Ground Levels (Terrain-Following Units)

```
Level 8: █████ Mountain peaks, ultimate high ground
Level 7: ████  High plateaus
Level 6: ███   Hills
Level 5: ███   Elevated ground
Level 4: ██    Medium ground
Level 3: ██    Slight elevation
Level 2: █     Low ground
Level 1: █     Flat areas, base locations
Level 0: ▁     Valleys, lowest points
```

**Ground Units:** Tank, Artillery, Hover, Scout, AA Tank
**Behavior:** Y position = terrain height + small offset
**Combat:** +30% damage shooting downhill, -30% shooting uphill

### Air Levels (Fixed Altitude Layers)

```
HIGH AIR (20):    🛩️  Bombers, Scout Planes
                       - Safe from most AA
                       - Can't attack ground effectively
                       - Strategic reconnaissance

MEDIUM AIR (15):  ✈️  Fighters, Advanced VTOLs
                       - Air superiority role
                       - Can engage high/low air
                       - Moderate ground attack

LOW AIR (10):     🚁  Helicopters, Basic VTOLs
                       - Heavy ground attack
                       - Vulnerable to AA
                       - Can't engage high air
```

**Air Units:** VTOL, Helicopter, Fighter, Bomber, Scout Plane
**Behavior:** Y position = fixed altitude (can transition between layers)
**Combat:** +15% damage when diving (higher altitude attacking lower)

---

## Phase 1: Core Engine (Weeks 1-2)

### Goal
Get a playable single-player RTS with terrain, units, and basic combat.

### Tasks

#### Week 1: Terrain & Rendering

**Day 1-2: Terrain System**
```javascript
✓ Generate 64×80 heightmap with Perlin noise
✓ Create strategic features:
  - Flat starting zones in corners (level 1)
  - Center plateau for contested area (level 5-7)
  - Valley choke points (level 0)
  - Hill clusters (levels 3-5)
✓ Apply multi-textured material (color by height)
✓ Compute normals for proper lighting
```

**Day 3-4: Camera & Lighting**
```javascript
✓ Set up orthographic camera at 45° angle
✓ Add ambient light (0.5 intensity)
✓ Add directional light from NW (creates shadows)
✓ Enable shadow mapping
✓ Camera controls (zoom, pan)
```

**Day 5-7: Ground Unit System**
```javascript
✓ Create 5 ground unit types:
  - Tank (BoxGeometry 1.5×0.8×2)
  - Artillery (CylinderGeometry 0.5→0.8, height 2)
  - Hover (ConeGeometry 0.8, height 1, 6 sides)
  - Scout (BoxGeometry 1×0.4×1.5)
  - AA Tank (BoxGeometry 1.5×1×2)

✓ Implement terrain-following:
  - Sample heightmap at unit XZ position
  - Set Y = terrain height + offset
  - Update every frame as unit moves

✓ Basic movement:
  - Click-to-move pathfinding
  - Units navigate around obstacles
  - Speed varies by unit type
```

#### Week 2: Air Units & Combat

**Day 1-3: Air Unit System**
```javascript
✓ Create 5 air unit types:
  - VTOL (TetrahedronGeometry 0.8)
  - Helicopter (Box body + cylinder rotor)
  - Fighter (ConeGeometry 0.6, height 2, 3 sides)
  - Bomber (BoxGeometry 2.5×0.5×2)
  - Scout Plane (OctahedronGeometry 0.7)

✓ Implement altitude layers:
  - Low Air: Y = 10
  - Medium Air: Y = 15
  - High Air: Y = 20

✓ Altitude transitions:
  - VTOL & Fighter can change altitude
  - Smooth interpolation (5 units/second)
  - Command: Right-click + Alt key = change layer

✓ Ground shadows:
  - Dark circle projected on terrain
  - Size scales with altitude
  - Shows where air unit actually is
```

**Day 4-5: Combat System**
```javascript
✓ Attack mechanics:
  - Click enemy to attack
  - Auto-attack in range
  - Damage calculation with modifiers

✓ Elevation bonuses:
  - Ground: +30% from high ground
  - Air: +15% when diving
  - Artillery: +20% range from hills

✓ Altitude restrictions:
  - Ground can't hit high air without AA
  - High air can't hit ground effectively
  - Air-to-air only at same/adjacent layer

✓ Line of sight:
  - Raycast through heightmap
  - Terrain blocks vision
  - Hilltops see further
```

**Day 6-7: Building System**
```javascript
✓ Create 5 structure types:
  - HQ (BoxGeometry 6×4×6)
  - Factory (BoxGeometry 8×3×6)
  - Power Plant (CylinderGeometry 3, height 5)
  - Defense Turret (CylinderGeometry 1.5, height 3)
  - Research Lab (BoxGeometry 5×4×5)

✓ Building placement:
  - Must be on flat terrain (±1 level)
  - No overlap with other structures
  - Snap to grid

✓ Building functions:
  - Factory: Produces units (queue system)
  - Power: Generates resources (+5/sec)
  - Turret: Auto-attacks enemies in range
  - Research: Unlocks tech (future feature)
```

**Deliverables (End of Phase 1):**
- ✅ 64×80 terrain with 0-8 elevation levels
- ✅ 10 unit types (5 ground, 5 air)
- ✅ 5 building types
- ✅ Working combat with elevation/altitude mechanics
- ✅ Single-player vs simple AI
- ✅ ~100KB of code, no assets yet

---

## Phase 2: Assets & Polish (Week 3)

### Goal
Extract Warzone 2100 assets, apply textures, add sounds, improve AI.

### Tasks

**Day 1-2: Asset Extraction**
```bash
# From warzone2100/data/base/
Extract textures:
  - page-7-barbarians-arizona.png (terrain)
  - page-17-droid-weapons.png (units)
  - page-19-buildings.png (structures)
  Total: ~8MB (compressed with pngquant)

Extract sounds:
  - Weapon fire (lasers, bullets, explosions)
  - Unit acknowledgments ("Affirmative", "Moving")
  - Building construction sounds
  Total: ~2-3MB (OGG format)

Optional: Extract music
  - One ambient track for background
  Total: ~5MB (streamed, not bundled)
```

**Day 3-4: Apply Textures**
```javascript
✓ Load texture atlas
✓ Apply to unit shapes via UV mapping:
  - Tank: Metal panels texture
  - Artillery: Barrel + base textures
  - Hover: Futuristic panels
  - Air units: Sleek metal textures

✓ Tint textures by player color:
  - Use THREE.js color multiplication
  - Player 1: Blue tint
  - Player 2: Red tint
  - Player 3: Green tint
  - Player 4: Yellow tint

✓ Terrain textures:
  - Multi-texture based on height
  - Blend between sand/grass/rock/snow
  - Normal maps for depth
```

**Day 5: Sound System**
```javascript
✓ Implement audio manager
✓ Trigger sounds on events:
  - Unit created: Build sound
  - Unit selected: Acknowledgment
  - Unit attacked: Weapon sound
  - Unit destroyed: Explosion

✓ Spatial audio:
  - Sounds pan left/right based on position
  - Volume based on distance from camera

✓ Background music:
  - Stream one ambient track
  - Volume slider in settings
```

**Day 6-7: AI Improvements**
```javascript
✓ Better AI opponent:
  - Build order (power → factory → units)
  - Unit composition (mix of types)
  - Attack timing (wait for critical mass)

✓ Tactical AI:
  - Use high ground when possible
  - Fighters patrol at medium altitude
  - Scouts at high altitude for vision
  - AA units protect base

✓ Difficulty levels:
  - Easy: Slow build, poor tactics
  - Medium: Standard build, basic tactics
  - Hard: Fast build, good tactics
```

**Deliverables (End of Phase 2):**
- ✅ Warzone 2100 textures applied to all units/buildings
- ✅ Sound effects for all major actions
- ✅ Improved AI with tactical awareness
- ✅ 15-20MB total asset package
- ✅ Polished single-player experience

---

## Phase 3: Multiplayer Federation (Week 4)

### Goal
Implement 2-second heartbeat synchronization for BBS multiplayer.

### Heartbeat Protocol

```javascript
// ═══════════════════════════════════════════════════════
// HEARTBEAT SYNCHRONIZATION SYSTEM
// ═══════════════════════════════════════════════════════

const HEARTBEAT_INTERVAL = 2000;  // 2 seconds
const GAME_SUBJECT = 'WARZONE_LITE_MP';

const HeartbeatSystem = {
  currentBeat: 0,
  commandQueue: [],
  lastSyncTime: 0,

  // Every 2 seconds, execute all queued commands
  tick() {
    const now = Date.now();
    if (now - this.lastSyncTime < HEARTBEAT_INTERVAL) return;

    // Execute all commands for this beat
    this.executeCommands(this.currentBeat);

    // Send our queued commands to peers
    this.syncToPeers();

    // Advance to next beat
    this.currentBeat++;
    this.lastSyncTime = now;
  },

  // Player issues a command (instant local feedback)
  queueCommand(command) {
    command.beat = this.currentBeat + 1;  // Execute next beat
    command.playerId = localPlayer.pubkey;
    command.timestamp = Date.now();

    this.commandQueue.push(command);

    // Show command preview immediately (not executed yet)
    this.showCommandPreview(command);
  },

  // Send commands to BBS federation
  async syncToPeers() {
    const myCommands = this.commandQueue.filter(
      cmd => cmd.playerId === localPlayer.pubkey &&
             cmd.beat === this.currentBeat
    );

    if (myCommands.length === 0) return;

    await window.bbs.postEvent({
      subject: GAME_SUBJECT,
      body: JSON.stringify({
        type: 'COMMANDS',
        beat: this.currentBeat,
        commands: myCommands
      })
    });
  },

  // Receive commands from peers
  async pollPeerCommands() {
    const events = await window.bbs.readEvents();
    const gameEvents = events.filter(e => e.subject === GAME_SUBJECT);

    for (const event of gameEvents) {
      const data = JSON.parse(event.body);
      if (data.type === 'COMMANDS') {
        data.commands.forEach(cmd => {
          this.commandQueue.push(cmd);
        });
      }
    }
  },

  // Execute all commands for a specific beat
  executeCommands(beat) {
    const commands = this.commandQueue.filter(cmd => cmd.beat === beat);

    // Sort by timestamp for determinism
    commands.sort((a, b) => a.timestamp - b.timestamp);

    commands.forEach(cmd => {
      switch(cmd.type) {
        case 'MOVE_UNIT':
          this.moveUnit(cmd.unitId, cmd.targetX, cmd.targetZ);
          break;
        case 'ATTACK_UNIT':
          this.attackUnit(cmd.attackerId, cmd.targetId);
          break;
        case 'BUILD_UNIT':
          this.buildUnit(cmd.factoryId, cmd.unitType);
          break;
        case 'CHANGE_ALTITUDE':
          this.changeAltitude(cmd.unitId, cmd.newAltitude);
          break;
        case 'BUILD_STRUCTURE':
          this.buildStructure(cmd.type, cmd.x, cmd.z);
          break;
      }
    });

    // Remove executed commands
    this.commandQueue = this.commandQueue.filter(cmd => cmd.beat > beat);
  }
};
```

### Event Protocol

```javascript
// ═══════════════════════════════════════════════════════
// MULTIPLAYER EVENT TYPES
// ═══════════════════════════════════════════════════════

// Lobby events
{
  type: 'JOIN_LOBBY',
  player: {
    pubkey: 'abc123...',
    nickname: 'Player1',
    color: 0  // 0-3
  }
}

{
  type: 'START_GAME',
  seed: 12345,              // Random seed for terrain
  mapName: 'plateau_clash',
  players: [/* player list */]
}

// Gameplay commands (sent every heartbeat)
{
  type: 'COMMANDS',
  beat: 42,
  commands: [
    {
      type: 'MOVE_UNIT',
      unitId: 'unit_123',
      targetX: 45,
      targetZ: 30,
      beat: 42,
      playerId: 'abc123...',
      timestamp: 1698765432000
    },
    {
      type: 'CHANGE_ALTITUDE',
      unitId: 'vtol_5',
      newAltitude: 15,  // Switch to medium air
      beat: 42,
      playerId: 'abc123...',
      timestamp: 1698765432001
    }
  ]
}

// State sync (for late joiners)
{
  type: 'STATE_SNAPSHOT',
  beat: 42,
  state: {
    resources: { player1: 500, player2: 750 },
    units: [/* all units */],
    structures: [/* all structures */]
  }
}

// Game over
{
  type: 'GAME_OVER',
  winner: 'abc123...',
  reason: 'FORTRESS_DESTROYED'
}
```

### Implementation Tasks

**Day 1-2: Lobby System**
```javascript
✓ Create lobby UI
✓ Join game event handling
✓ Player list display
✓ Map selection
✓ Game start synchronization
```

**Day 3-4: Command Queue System**
```javascript
✓ Implement heartbeat timer
✓ Command queuing (instant preview)
✓ BBS event posting (postEvent)
✓ Peer command polling (readEvents, 2s interval)
✓ Command execution at beat boundaries
```

**Day 5: State Synchronization**
```javascript
✓ Deterministic simulation
  - Same commands + same order = same result
  - Use random seed for terrain generation
  - Sort commands by timestamp

✓ State validation
  - Periodic checksum of game state
  - Compare with peers
  - Detect desyncs early

✓ Late join handling
  - Send state snapshot to new players
  - Catch up to current beat
```

**Day 6-7: Testing & Polish**
```javascript
✓ Test 2-player on same BBS
✓ Test 2-player cross-BBS (HostBBS ↔ PiBBS)
✓ Test 4-player (max)
✓ Network interruption handling
✓ Reconnection logic
✓ Victory/defeat conditions
```

**Deliverables (End of Phase 3):**
- ✅ Working 2-4 player multiplayer
- ✅ BBS federation across Tor network
- ✅ 2-second heartbeat synchronization
- ✅ Stable, deterministic simulation
- ✅ Full Warzone Lite experience!

---

## Technical Specifications

### Map Format

```javascript
// 64×80 heightmap stored as JSON
{
  "name": "Plateau Clash",
  "width": 64,
  "depth": 80,
  "heightmap": [
    [0,0,1,1,2,2,3,3, ...],  // Row 0 (80 values)
    [0,1,1,2,2,3,3,4, ...],  // Row 1
    // ... 64 rows total
  ],
  "startPositions": [
    { x: 8, z: 8, team: 0 },
    { x: 56, z: 72, team: 1 },
    { x: 8, z: 72, team: 2 },
    { x: 56, z: 8, team: 3 }
  ],
  "resources": [
    { x: 32, z: 40, amount: 1000 }
  ]
}

// File size: ~20-30KB per map
```

### Unit Stats

```javascript
const UNIT_STATS = {
  // Ground units (follow terrain 0-8)
  TANK: {
    cost: 150, health: 100, damage: 15, range: 3, speed: 2.5,
    type: 'ground', antiAir: false
  },
  ARTILLERY: {
    cost: 200, health: 80, damage: 30, range: 8, speed: 1.5,
    type: 'ground', antiAir: false,
    bonusFromHeight: 1.5  // Extra range bonus on hills
  },
  HOVER: {
    cost: 120, health: 70, damage: 12, range: 3, speed: 3.5,
    type: 'ground', antiAir: false
  },
  SCOUT: {
    cost: 75, health: 50, damage: 8, range: 2, speed: 4,
    type: 'ground', antiAir: false,
    visionBonus: 2  // Sees further
  },
  AA_TANK: {
    cost: 180, health: 90, damage: 20, range: 6, speed: 2,
    type: 'ground', antiAir: true,
    aaMaxAltitude: 12  // Can hit low & medium air
  },

  // Air units (altitude 10, 15, or 20)
  VTOL: {
    cost: 200, health: 60, damage: 18, range: 4, speed: 5,
    type: 'air', altitude: 10, canChangeAlt: true,
    antiAir: false
  },
  HELICOPTER: {
    cost: 250, health: 80, damage: 25, range: 4, speed: 4,
    type: 'air', altitude: 10, canChangeAlt: false,
    antiAir: false,
    groundAttackBonus: 1.3
  },
  FIGHTER: {
    cost: 300, health: 70, damage: 15, range: 5, speed: 7,
    type: 'air', altitude: 15, canChangeAlt: true,
    antiAir: true,
    airToAirBonus: 1.5
  },
  BOMBER: {
    cost: 400, health: 100, damage: 40, range: 6, speed: 5,
    type: 'air', altitude: 20, canChangeAlt: false,
    antiAir: false,
    bombDamage: 50,
    areaOfEffect: 3  // Splash damage
  },
  SCOUT_PLANE: {
    cost: 150, health: 50, damage: 0, range: 0, speed: 8,
    type: 'air', altitude: 20, canChangeAlt: false,
    antiAir: false,
    visionRange: 15
  }
};
```

### Asset Breakdown

```
Total Package: ~15-20MB

Textures: 8-12MB
├── Terrain (2MB)
│   ├── desert_tiles.png (1024×1024)
│   ├── grass_tiles.png (1024×1024)
│   └── rock_tiles.png (1024×1024)
├── Units (3MB)
│   ├── tank_diffuse.png (512×512)
│   ├── artillery_diffuse.png (512×512)
│   ├── hover_diffuse.png (512×512)
│   ├── vtol_diffuse.png (512×512)
│   └── fighter_diffuse.png (512×512)
└── Structures (3MB)
    ├── factory_diffuse.png (1024×1024)
    ├── power_diffuse.png (512×512)
    └── turret_diffuse.png (512×512)

Sounds: 2-3MB
├── Weapons (1MB)
│   ├── laser.ogg
│   ├── bullet.ogg
│   └── explosion.ogg
├── Units (500KB)
│   ├── move_ack.ogg
│   └── build.ogg
└── Music (1MB, optional)
    └── ambient_track.ogg (streamed)

Maps: 100KB
├── plateau_clash.json (30KB)
├── valley_war.json (30KB)
└── mountain_fortress.json (30KB)

Code: ~150KB
└── Warzone_Lite.js (minified)
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Initial Load** | <10s | Download + unpack assets |
| **Frame Rate** | 60 FPS | With 100 units on screen |
| **Memory** | <500MB | Browser heap usage |
| **Heartbeat Latency** | 2-3s | BBS poll interval |
| **State Sync** | <100ms | Command execution time |
| **Max Units** | 200 | Per player (800 total) |

---

## Development Timeline

```
Week 1: Terrain & Ground Units
├── Day 1-2: Heightmap terrain system
├── Day 3-4: Camera & lighting
└── Day 5-7: Ground units + movement

Week 2: Air Units & Combat
├── Day 1-3: Air units + altitude system
├── Day 4-5: Combat mechanics
└── Day 6-7: Building system

Week 3: Assets & Polish
├── Day 1-2: Extract Warzone 2100 assets
├── Day 3-4: Apply textures to all units
├── Day 5: Sound system
└── Day 6-7: Improve AI

Week 4: Multiplayer
├── Day 1-2: Lobby system
├── Day 3-4: Heartbeat command queue
├── Day 5: State synchronization
└── Day 6-7: Testing & polish

TOTAL: 4 weeks (~100 hours)
```

---

## Success Criteria

### Minimum Viable Product (End of Week 4)

- [ ] 64×80 terrain with 0-8 elevation levels
- [ ] 10 unit types (5 ground, 5 air) with distinct roles
- [ ] 5 building types (HQ, Factory, Power, Turret, Research)
- [ ] Elevation combat bonuses (+30% high ground)
- [ ] Multi-altitude air combat (3 layers)
- [ ] Working AI opponent
- [ ] 2-4 player multiplayer via BBS federation
- [ ] 2-second heartbeat synchronization
- [ ] Warzone 2100 textures on all units
- [ ] Sound effects for major actions
- [ ] Victory/defeat conditions
- [ ] Total size: <20MB

### Stretch Goals (Post-Launch)

- [ ] Tech tree / research system
- [ ] 100×100 maps for 6-8 players
- [ ] Campaign mode (scripted missions)
- [ ] Replays (save command history)
- [ ] Spectator mode
- [ ] In-game chat (integrate AxonChat)
- [ ] Fog of war
- [ ] Unit veterancy (XP system)
- [ ] More unit types (20+ total)
- [ ] Map editor

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Desync in multiplayer** | High | Medium | Deterministic simulation, state validation, checksum verification |
| **Performance issues** | Medium | Low | Limit unit count, optimize rendering, use object pooling |
| **Asset size too large** | Low | Low | Aggressive texture compression, remove unnecessary assets |
| **BBS latency too high** | Medium | Low | 2-second heartbeat accommodates Tor latency |
| **Terrain pathfinding complex** | Medium | Medium | Use simple A* on tile grid, avoid complex nav mesh |
| **Air combat confusing** | Low | Medium | Clear visual indicators (shadows, altitude lines, colors) |

---

## Next Steps

1. **Immediate (Today):**
   - [ ] Review and approve this plan
   - [ ] Set up development environment
   - [ ] Create skeleton Warzone_Lite.js file
   - [ ] Test basic Three.js rendering

2. **Week 1 Kickoff (Tomorrow):**
   - [ ] Implement heightmap terrain generation
   - [ ] Set up orthographic camera
   - [ ] Create first ground unit (Tank)
   - [ ] Test terrain-following movement

3. **Milestone Reviews:**
   - End of Week 1: Terrain + ground units demo
   - End of Week 2: Air combat demo
   - End of Week 3: Textured assets demo
   - End of Week 4: Multiplayer test (HostBBS ↔ PiBBS)

---

## File Structure

```
axon_bbs/
├── frontend/src/applets/
│   └── Warzone_Lite.js              # Main applet (~150KB)
├── frontend/public/assets/warzone_lite/
│   ├── textures/                    # 8-12MB
│   ├── sounds/                      # 2-3MB
│   └── maps/                        # 100KB
└── docs/
    ├── Warzone_Lite_Implementation_Plan.md  # This file
    └── Warzone_Lite_Developer_Guide.md      # Future: API docs
```

---

## References

- **FortressOverlord.js** - Proven orthographic 3D RTS framework
- **AxonChat.js** - Real-time federation pattern
- **hexgl.js** - Hybrid asset loading pattern
- **Warzone 2100 Source** - Asset extraction source
- **Axon BBS Developer Handbook** - BBS API reference
- **Applet Dev Guide** - Applet best practices

---

**Document Status:** Ready for Implementation
**Approved By:** [Pending]
**Start Date:** [TBD]
**Target Completion:** 4 weeks from start
