# Task: Integrate Yuka.js for Professional Unit Movement

**Version Target**: v3.1.0 - Yuka.js AI Integration
**Complexity**: Moderate
**Estimated Time**: 60-90 minutes
**Agent Model**: Flash (escalate to Pro if needed)

---

## Objective

Replace the current custom pathfinding and movement system with Yuka.js professional AI steering behaviors. This will give units:
- Smooth, natural movement with arrival behaviors (units slow down near target)
- Unit avoidance (units steer around each other)
- Better pathfinding using Yuka's built-in algorithms
- Professional-grade AI state management

---

## Context

**Current Implementation**:
- Custom A* pathfinding at lines ~1610-1673
- Simple linear movement in UnitSystem.update()
- Units snap to targets instantly (no smooth arrival)
- Units can overlap (no collision avoidance)
- Movement is functional but not polished

**After Yuka.js Integration**:
- Yuka Vehicle agents control unit movement
- Steering behaviors: Seek, Arrive, ObstacleAvoidance
- Natural acceleration/deceleration
- Units flow around each other like real RTS games
- Pathfinding still respects terrain and altitude

---

## Prerequisites

✅ Yuka.js installed via npm: `npm install yuka --save`

**Files to Modify**:
- `/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js` (main file)

**DO NOT MODIFY**:
- Debug console system
- Asset loading (PIE models, textures)
- Terrain generation
- Combat system
- Selection system
- Altitude system

---

## Implementation Steps

### Step 1: Import Yuka.js

Add at the top of the file (after line 96 where libraries are loaded):

```javascript
// Load Yuka.js for AI behaviors
await loadScript('/node_modules/yuka/build/yuka.js');
debugLog('✅ Yuka.js AI library loaded');
```

### Step 2: Add Yuka Entity Manager

After terrain initialization (~line 600), add:

```javascript
// ═══════════════════════════════════════════════════════
// Yuka AI System
// ═══════════════════════════════════════════════════════

const yukaEntityManager = new YUKA.EntityManager();
const yukaTime = new YUKA.Time();

debugLog('✅ Yuka.js Entity Manager initialized');
```

### Step 3: Modify Unit Creation to Include Yuka Vehicles

In `UnitSystem.createUnit()` (~lines 750-900), for each unit created:

**ADD** Yuka vehicle creation:

```javascript
// Create Yuka vehicle for AI movement
const vehicle = new YUKA.Vehicle();
vehicle.position.set(unit.position.x, unit.position.y, unit.position.z);
vehicle.maxSpeed = unit.stats.speed;
vehicle.maxForce = 5; // Steering force
vehicle.updateOrientation = false; // We handle rotation separately

// Add obstacle avoidance (units avoid each other)
const avoidBehavior = new YUKA.ObstacleAvoidanceBehavior([], 3);
vehicle.steering.add(avoidBehavior);

// Store reference
unit.yukaVehicle = vehicle;
yukaEntityManager.add(vehicle);

debugLog(`Created Yuka vehicle for ${unit.type} unit #${unit.id}`);
```

### Step 4: Replace Movement Command with Yuka Steering

In `UnitSystem.moveUnit()` or wherever units receive move commands (~line 1000+):

**REPLACE** the current path-following logic with:

```javascript
// Clear previous steering behaviors
unit.yukaVehicle.steering.clear();

// Re-add obstacle avoidance (always active)
const allObstacles = UnitSystem.units
  .filter(u => u !== unit)
  .map(u => u.yukaVehicle);
const avoidBehavior = new YUKA.ObstacleAvoidanceBehavior(allObstacles, 3);
unit.yukaVehicle.steering.add(avoidBehavior);

// Add Arrive behavior for smooth movement to target
const targetPosition = new YUKA.Vector3(targetX, targetY, targetZ);
const arriveBehavior = new YUKA.ArriveBehavior(targetPosition, 2, 0.5);
unit.yukaVehicle.steering.add(arriveBehavior);

debugLog(`Unit ${unit.id} moving to (${targetX}, ${targetY}, ${targetZ}) via Yuka Arrive`);
```

### Step 5: Update Unit Positions in Animation Loop

In the main animation loop (~line 1900+), **BEFORE** rendering:

```javascript
// Update Yuka AI system
const delta = yukaTime.update().getDelta();
yukaEntityManager.update(delta);

// Sync Three.js mesh positions with Yuka vehicles
UnitSystem.units.forEach(unit => {
  if (unit.yukaVehicle) {
    // Copy Yuka position to Three.js mesh
    unit.mesh.position.copy(unit.yukaVehicle.position);

    // Update unit.position for other systems (combat, selection)
    unit.position.x = unit.yukaVehicle.position.x;
    unit.position.y = unit.yukaVehicle.position.y;
    unit.position.z = unit.yukaVehicle.position.z;

    // Keep altitude adherence for air units
    if (unit.isAirUnit && unit.targetAltitude !== undefined) {
      const altitudeY = AltitudeSystem.getYPosition(unit.targetAltitude);
      unit.mesh.position.y = altitudeY;
      unit.position.y = altitudeY;
      unit.yukaVehicle.position.y = altitudeY; // Keep Yuka in sync
    }
  }
});
```

### Step 6: Remove Old Pathfinding Code (Optional but Recommended)

You can keep the old pathfinding as a fallback, but comment it out or mark it as deprecated:

```javascript
// OLD PATHFINDING (DEPRECATED - Now using Yuka.js)
// const PathfindingSystem = { ... };
```

---

## Testing Checklist

After implementation, verify:

- [ ] Units still spawn correctly (3 ground, 3 air)
- [ ] Left-click selection still works
- [ ] Right-click movement commands work
- [ ] Units move smoothly to targets (not instant snap)
- [ ] Units slow down as they approach target (Arrive behavior)
- [ ] Units avoid bumping into each other
- [ ] Air units maintain their altitude while moving
- [ ] Combat system still works (units can attack)
- [ ] No console errors
- [ ] Performance is smooth (60 fps)

---

## Expected File Changes

**Line count**: Should increase by ~100-150 lines (Yuka setup and integration)

**Modified Sections**:
- Library loading (add Yuka.js import)
- Yuka EntityManager setup
- Unit creation (add yukaVehicle to each unit)
- Movement commands (replace with Yuka steering)
- Animation loop (add yukaEntityManager.update())

**Preserved Sections** (DO NOT CHANGE):
- BBS API helper
- Debug console
- Terrain generation
- PIE model loading
- Texture loading
- Combat system
- Selection system
- Altitude system

---

## Validation

Before submitting:

```bash
# Syntax check
node -c /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

# Verify no errors
echo "✅ Syntax valid"
```

---

## Success Criteria

1. ✅ Units move with smooth acceleration/deceleration
2. ✅ Units avoid each other naturally
3. ✅ All existing features still work (selection, combat, altitude)
4. ✅ No syntax errors
5. ✅ Performance is maintained

---

## Notes for Agent

- Be careful with coordinate systems (Yuka uses Vector3, Three.js uses Vector3)
- Preserve ALL existing systems (this is an enhancement, not a replacement)
- Test thoroughly - movement is core to the game
- If you get stuck, ask for clarification rather than guessing
- Keep the debug logging pattern (use `debugLog()` for consistency)

---

## Reference

- Yuka.js Docs: https://mugen87.github.io/yuka/
- Current code: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
- Current version: v3.0.2
- Target version: v3.1.0

---

**Agent Instructions**: Implement this integration step-by-step. Preserve all existing functionality. Focus on smooth, natural unit movement. Test thoroughly before submitting.
