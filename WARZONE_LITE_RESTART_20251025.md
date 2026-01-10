# Warzone Lite - Development Restart Document
**Date:** October 25, 2025
**Current Version:** v1.8.0 - Warzone 2100 Textured Units
**Status:** Texture implementation complete, browser testing pending

---

## 🎯 Project Overview

**Warzone Lite** is a JavaScript-native RTS game for Axon BBS, inspired by Warzone 2100. It runs in the browser using Three.js for 3D rendering.

**Main File:** `/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js`

---

## 📊 Current Status (Week 1 Complete)

### ✅ Completed Features

**Tasks 0-1.3: Core Game Foundation**
- Multi-level terrain generation (heights 0-8, Perlin noise)
- 3 unit types: TANK (box), ARTILLERY (cylinder), SCOUT (small box)
- Three.js rendering with orthographic camera (45° isometric)
- A* pathfinding with terrain height costs

**Task 1.4: Mouse Input & Selection**
- Raycasting for click detection
- Yellow selection rings around selected units
- Debug console (enabled with `BBS_DEBUG_MODE`)

**Task 1.5: Click-to-Move Pathfinding**
- Right-click to issue move commands
- Units navigate around terrain obstacles
- Dynamic path recalculation

**Task 1.6: Improved Selection (v1.7.0)**
- Added invisible hitboxes 2-3x larger than visible meshes
- Artillery cylinder made wider (easier to click)
- Selection system uses hitboxes instead of visible meshes

**Task 1.7: Texture Implementation (v1.8.0)** ⭐ JUST COMPLETED
- THREE.TextureLoader loads Warzone 2100 texture atlas
- UV mapping: TANK (0,0), ARTILLERY (0.25,0), SCOUT (0.5,0)
- Player colors preserved as emissive glow (30% intensity)
- Graceful fallback to solid colors if textures fail

---

## 🗂️ Key Files & Locations

### Game Code
```
/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
```
- Main game file (1,160+ lines)
- Systems: Terrain, Units, Pathfinding, Input, Rendering

### Textures (Web-Accessible)
```
/path/to/axon_bbs/frontend/public/warzone_textures/
  ├── page-14-droid-hubs.png    (197KB, 1024x1024) - Unit bodies/hubs
  ├── page-16-droid-drives.png  (52KB) - Wheels/tracks
  └── page-17-droid-weapons.png (368KB) - Turrets/weapons
```

### Warzone 2100 Source Assets
```
/path/to/axon_bbs/frontend/src/applets/warzone2100/
  ├── data/base/texpages/      - 133MB of texture atlases
  ├── src/astar.cpp            - A* pathfinding reference
  ├── src/map.h                - MAPTILE structure reference
  └── src/move.cpp             - Movement system reference
```

### Development Tools
```
/path/to/axon_bbs/debug_screenshot.sh  - Optimize screenshots for Claude
/path/to/axon_bbs/START_GEMINI_SAFE.sh - Launch Gemini agents in sandbox
```

---

## 🔧 Technical Implementation Details

### Texture System (v1.8.0)

**Initialization (lines 120-148):**
```javascript
let unitTexture = null;
const textureLoader = new THREE.TextureLoader();

await new Promise((resolve, reject) => {
  textureLoader.load(
    '/warzone_textures/page-14-droid-hubs.png',
    (texture) => {
      texture.wrapS = THREE.ClampToEdgeWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      unitTexture = texture;
      debugLog('✅ Warzone 2100 textures loaded (1024x1024)');
      resolve();
    },
    undefined,
    (err) => {
      console.warn('Failed to load textures, using solid colors:', err);
      resolve(); // Continue without textures
    }
  );
});
```

**UV Mapping (lines 509-524):**
- Each unit type gets a 256x256 section (0.25 × 0.25) of the 1024x1024 atlas
- TANK: offset (0, 0) - top-left quadrant
- ARTILLERY: offset (0.25, 0) - second quadrant from left
- SCOUT: offset (0.5, 0) - third quadrant from left

**Material Configuration (lines 526-546):**
```javascript
const material = new THREE.MeshPhongMaterial({
  color: 0xffffff,  // White base to show texture
  emissive: PLAYER_COLORS[ownerId],  // Player color glow
  emissiveIntensity: 0.3,  // Subtle 30% tint
  specular: 0x666666,
  shininess: 30
});

if (unitTexture) {
  material.map = unitTexture.clone();
  material.map.offset.set(uvOffset.x, uvOffset.y);
  material.map.repeat.set(uvRepeat.x, uvRepeat.y);
}
```

### Hitbox System (v1.7.0)

**Sizes:**
- TANK: 5×3×6 (vs visible 3×1.5×4)
- ARTILLERY: cylinder radius 3, height 5 (vs visible 1.5-2 radius, height 3)
- SCOUT: 4×2×5 (vs visible 2×0.8×3)

**Selection (lines 958-970):**
```javascript
const selectableObjects = UnitSystem.units.map(unit => unit.hitbox);
const intersects = this.raycaster.intersectObjects(selectableObjects, true);
```

### Player Colors
```javascript
const PLAYER_COLORS = [0x007bff, 0xff4136, 0x2ecc40, 0xffdc00];
// Blue, Red, Green, Yellow
```

---

## 🧪 Testing Checklist

### ⏳ Pending: Browser Testing (Priority)

**Must Verify:**
1. ✅ Textures load without console errors
2. ✅ All 3 unit types show different textures (not same sprite)
3. ✅ Player colors distinguishable (emissive glow visible)
4. ✅ Hitboxes still work (easy unit selection)
5. ✅ Selection rings appear correctly
6. ✅ Pathfinding unaffected
7. ✅ Performance acceptable (no lag from texture loading)

**How to Test:**
```bash
# Enable debug mode to see texture loading status
# In browser console before loading applet:
window.BBS_DEBUG_MODE = true;

# Look for these debug messages:
# "Loading Warzone 2100 texture atlas..."
# "✅ Warzone 2100 textures loaded (1024x1024)"
```

**Expected Behavior:**
- Units should have textured appearance instead of solid colors
- Blue/red/green/yellow glow should overlay textures
- Artillery should be easiest to click (large hitbox)

**If Textures Don't Appear:**
1. Check browser console for texture loading errors
2. Verify `/warzone_textures/page-14-droid-hubs.png` is accessible
3. Check UV coordinates may need adjustment
4. Fallback: units will show solid player colors

---

## 🔍 Known Issues & Limitations

### Current Limitations
1. **Textures not optimized:** Using full 1024x1024 atlas (197KB)
2. **UV mapping untested:** Coordinates are estimates, may need adjustment
3. **Single texture atlas:** Only using page-14 (hubs), not drives/weapons
4. **No LOD system:** All units use same detail level regardless of distance
5. **Team color masks unused:** Could use `*_tcmask.png` for better recoloring

### Previous User Feedback
- ✅ **Fixed:** Artillery hard to select (solved with larger hitboxes)
- ✅ **Fixed:** Terrain too bumpy (adjusted noise scale to 16)
- ⚠️ **Reported:** Units sometimes clip through terrain at elevation changes

---

## 📋 Next Steps & Future Tasks

### Immediate (Post-Testing)
1. **Browser test textured units** - verify implementation works
2. **Adjust UV coordinates** - if textures don't map correctly
3. **Optimize texture loading** - consider using smaller atlas or sprites
4. **Fix terrain clipping** - address unit elevation interpolation

### Week 2 Tasks (Locked - From JUNIOR_DEV_TASKS.md)
- Task 2.1: Combat system (unit damage, health bars)
- Task 2.2: Resource system (power, factories)
- Task 2.3: Building placement
- Task 2.4: Fog of war
- Task 2.5: AI opponent

### Future Enhancements
- **Better texture mapping:** Use separate textures for body/drive/weapon
- **Team color masks:** Implement `_tcmask.png` for authentic Warzone 2100 coloring
- **Asset package system:** Bundle textures for faster loading
- **Sprite-based rendering:** Consider 2D sprites if 3D performance issues
- **More unit types:** VTOLs, cyborgs, structures

---

## 🛠️ Development Workflow

### Testing Changes
```bash
# Syntax check
node -c /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

# Check git status
cd /path/to/axon_bbs
git status

# View recent changes
git diff frontend/src/applets/Warzone_Lite.js
```

### Using Gemini Agents (Junior Developers)
```bash
# Launch agent in safe sandbox
./START_GEMINI_SAFE.sh <task#> <flash|pro>

# Monitor progress
tail -f /tmp/gemini_task_<task#>_output.txt

# Wait for completion
./WAIT_FOR_GEMINI_BATCH.sh <task#>

# Review sandbox output
ls -lh /tmp/gemini_sandbox_task_<task#>/
diff /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js \
     /tmp/gemini_sandbox_task_<task#>/Warzone_Lite.js
```

### Git Workflow
```bash
# Check status
git status

# Stage changes
git add frontend/src/applets/Warzone_Lite.js

# Commit (Claude will auto-format with co-author)
# Just say: "commit these changes"
```

---

## 💡 Important Context

### User Preferences
- **Texture approach chosen:** Option 3 - "Keep 3D + Add Decals"
  - Maintain current 3D geometry
  - Apply Warzone 2100 texture decals on top
  - Preserve hitbox system

- **Development speed:** User requested using Gemini agents to accelerate work

- **Context management:** User prefers early context cleanup with restart docs

### Architecture Decisions
- **No asset packages:** Using individual PNG files instead of .wz archives
- **Web-native:** Browser loads textures via HTTP, no extraction needed
- **Three.js r128:** Using specific version for compatibility
- **Orthographic camera:** RTS-style fixed angle, not free-look

### Code Style
- ES6+ JavaScript (async/await, arrow functions)
- Self-contained in single file (no module system)
- BBS API integration via postMessage
- Debug logging gated behind `window.BBS_DEBUG_MODE`

---

## 📞 Quick Reference

### Verify Texture Files
```bash
ls -lh /path/to/axon_bbs/frontend/public/warzone_textures/
identify /path/to/axon_bbs/frontend/public/warzone_textures/page-14-droid-hubs.png
```

### Check Current Version
```bash
grep "APPLET_VERSION" /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
# Should show: v1.8.0 - Warzone 2100 Textured Units
```

### View Texture Loading Code
```bash
sed -n '120,148p' /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
```

### View UV Mapping Code
```bash
sed -n '509,546p' /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
```

---

## 🎮 Session End State

**Last Actions Completed:**
1. ✅ Updated version to v1.8.0
2. ✅ Added THREE.TextureLoader with async loading
3. ✅ Implemented UV coordinate mapping for 3 unit types
4. ✅ Applied textured materials with player color emissive
5. ✅ Syntax validated successfully
6. ✅ Created this restart document

**What to Say When Resuming:**
> "I'm resuming work on Warzone Lite. Here's the restart document from our last session: [paste this file]. We just implemented texture system v1.8.0 and need to browser test it."

**Files to Review on Restart:**
- `/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js` (main file)
- `/path/to/axon_bbs/frontend/public/warzone_textures/` (texture assets)
- This document: `/path/to/axon_bbs/WARZONE_LITE_RESTART_20251025.md`

---

**Document Version:** 1.0
**Created:** October 25, 2025, 3:30 PM EDT
**Next Review:** After browser testing of v1.8.0 textures
