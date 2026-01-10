# Warzone Lite - Next Session Quick Start

**Last Session:** November 1, 2025
**Current Version:** v3.2.3 - Debug Ground Unit Rendering ✅
**Status:** Ground units working perfectly! Ready for combat polish.

---

## 🚀 Quick Resume (Copy & Paste to Claude Code)

```
Resume Warzone Lite development - Combat Polish phase.

IMPORTANT: Use Gemini Flash and Gemini Pro sub-agents for tasks.

Read these files:
1. /path/to/axon_bbs/SESSION_SUMMARY_2025_11_01_WARZONE.md
2. /path/to/axon_bbs/docs/Warzone_Lite_Implementation_Plan.md

Current state: v3.2.3 working perfectly
- Ground units render with Warzone 2100 PIE models ✅
- Textures load correctly ✅
- Combat system functional ✅
- 2155 lines, ~105KB code

Next phase: Option A - Combat Polish
Tasks:
1. Visual effects (muzzle flash, explosions, particles) - Gemini Flash
2. Audio system (sounds, music, spatial audio) - Gemini Flash
3. Combat balance (elevation bonuses, damage types) - Gemini Flash
4. UI improvements (health bars, minimap, info panel) - Gemini Pro

Let's start with Task 1: Visual Effects using Gemini Flash!
```

---

## 📋 Task Breakdown for Gemini Sub-Agents

### Task 1: Visual Effects (Gemini Flash)
**Estimated:** 2-3 hours
**Command:**
```bash
./START_GEMINI_SAFE.sh combat-vfx flash
```

**Prompt for Gemini:**
```
Add visual effects to Warzone Lite v3.2.3.

File: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

Implement these effects:

1. Muzzle Flash (when unit fires)
   - Bright orange/yellow flash at weapon position
   - Duration: 100ms
   - Use THREE.PointLight for illumination

2. Explosion Particles (when unit destroyed)
   - 20-30 particles shooting outward
   - Orange/red/yellow colors
   - Gravity affects particles
   - Fade out over 1 second

3. Hit Indicators (when unit damaged)
   - Floating damage number (red text)
   - Rises up and fades (1.5 seconds)
   - Position above hit unit

4. Projectile Smoke Trail
   - Thin line behind projectile
   - Fades over 0.5 seconds
   - Light gray color

Use THREE.js particle systems. Keep performance high (60fps target).
Update CombatSystem.attack() and CombatSystem.createProjectile().

Test with 3 units fighting to verify effects work correctly.
```

---

### Task 2: Audio System (Gemini Flash)
**Estimated:** 2-3 hours
**Command:**
```bash
./START_GEMINI_SAFE.sh combat-audio flash
```

**Prompt for Gemini:**
```
Add audio system to Warzone Lite v3.2.3.

File: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

Implement AudioSystem with:

1. Sound Manager
   - Preload sounds from URLs (use free sound effects)
   - Volume control (master, sfx, music)
   - Spatial audio (pan based on unit position relative to camera)

2. Sound Effects
   - Weapon fire: "pew" laser sound
   - Explosion: boom/bang sound
   - Unit selected: click/beep sound
   - Unit moving: acknowledgment beep

3. Background Music
   - One ambient/techno track (stream, don't bundle)
   - Loop continuously
   - Lower volume than SFX

4. Trigger Points
   - CombatSystem.attack() → weapon fire sound
   - CombatSystem.destroyUnit() → explosion sound
   - SelectionSystem.selectUnit() → selection sound
   - UnitSystem.moveUnit() → movement acknowledgment

Use Web Audio API for spatial audio.
Sounds should pan left/right based on position.
Volume decreases with distance from camera.

Provide free sound effect URLs (freesound.org or similar).
```

---

### Task 3: Combat Balance (Gemini Flash)
**Estimated:** 1-2 hours
**Command:**
```bash
./START_GEMINI_SAFE.sh combat-balance flash
```

**Prompt for Gemini:**
```
Add combat balance mechanics to Warzone Lite v3.2.3.

File: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

Implement in CombatSystem.attack():

1. Elevation Bonus (ground units)
   - If attacker.position.y > defender.position.y + 2:
     damage *= 1.3 (30% bonus from high ground)
   - If attacker.position.y < defender.position.y - 2:
     damage *= 0.7 (30% penalty shooting uphill)
   - Log bonus/penalty to debug console

2. Diving Attack Bonus (air units)
   - If attacker.altitude > defender.altitude + 1:
     damage *= 1.15 (15% diving bonus)
   - Log bonus to debug console

3. Damage Types & Armor
   - Add to UNIT_STATS: damageType ('kinetic', 'energy', 'explosive')
   - Add to UNIT_STATS: armorType ('light', 'medium', 'heavy')
   - Kinetic vs Heavy: 0.7x damage
   - Energy vs Light: 1.3x damage
   - Explosive vs all: 1.0x damage
   - Log effective damage calculation

4. Attack Cooldown
   - Add lastAttackTime to unit object
   - Require 1 second between attacks
   - Prevent attack spam

Update UNIT_STATS with damage/armor types.
Test balance with different unit matchups.
Verify high ground gives tactical advantage.
```

---

### Task 4: UI Improvements (Gemini Pro)
**Estimated:** 3-4 hours (Complex UI system)
**Command:**
```bash
./START_GEMINI_SAFE.sh combat-ui pro
```

**Prompt for Gemini:**
```
Add comprehensive UI system to Warzone Lite v3.2.3.

File: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

Implement UISystem with:

1. Health Bars Above Units
   - Canvas-based 2D overlay
   - Bar above each unit (width: 40px, height: 4px)
   - Color: green (>60% health) → yellow (30-60%) → red (<30%)
   - Background: dark gray
   - Update every frame using unit.position projected to screen coords

2. Mini-Map
   - 160x200px canvas in bottom-right corner
   - Semi-transparent background (rgba(0,0,0,0.5))
   - Show terrain heightmap (darker = lower, lighter = higher)
   - Draw units as colored dots (player colors)
   - Clickable: click minimap to move camera
   - Draw camera viewport rectangle (white outline)

3. Unit Info Panel (Selected Unit)
   - 200px wide panel on right side
   - Show when unit selected:
     * Unit type name
     * Health: 80/100 (with bar)
     * Damage: 15
     * Range: 3
     * Speed: 2.5
   - Portrait: Colored box with unit type icon/text
   - Background: semi-transparent dark panel

4. Resource Counter (Future-Proofing)
   - Top-right corner
   - Show: "Power: 500" (placeholder for building system)
   - Icon + number

Create UISystem object to manage all UI elements.
Use HTML5 Canvas for minimap, CSS for panels.
Update UI in animation loop (60fps).
Position UI elements in screen space, not world space.

Test UI with multiple units selected/moving/fighting.
```

---

## 🎯 Success Criteria

After all tasks complete, the game should have:

- ✅ **Visual Effects:** Muzzle flashes, explosions, hit indicators, smoke trails
- ✅ **Audio:** Weapon sounds, explosions, acknowledgments, background music
- ✅ **Combat Balance:** Elevation bonuses, damage types, armor, cooldowns
- ✅ **UI:** Health bars, minimap, unit info panel, resource counter

**Result:** Professional-feeling RTS with satisfying combat!

---

## 📊 Token Budget Management

**Current:** 106,646 / 200,000 remaining (53%)
**Strategy:**
- Use Gemini Flash for 3 tasks (~10-15k tokens each)
- Use Gemini Pro for complex UI task (~20-30k tokens)
- Reserve 40k tokens for review/testing/publishing

**Monitor with:**
```bash
./START_TOKEN_MONITOR.sh
```

---

## 🔧 Testing After Each Task

**Quick Test Command:**
```bash
node -c frontend/src/applets/Warzone_Lite.js && echo "✅ Syntax valid"
```

**In-Browser Test:**
1. Hard refresh: `Ctrl + Shift + R`
2. Check debug console for version
3. Test specific feature added
4. Verify no performance regression (60fps)

---

## 📝 Publishing After All Tasks

**When all 4 tasks complete:**

```bash
# 1. Update manifests
source venv/bin/activate
python manage.py update_applet_manifests

# 2. Post to Applet Library
python manage.py post_applet_update frontend/src/applets/Warzone_Lite.js \
  --name "Warzone Lite" \
  --description "v3.3.0 - Combat Polish: Visual effects, audio, balance, UI improvements"

# 3. Commit to git
git add frontend/src/applets/Warzone_Lite.js
git commit -m "Warzone Lite v3.3.0 - Combat Polish Complete

Added visual effects, audio system, combat balance, and UI improvements.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push

# 4. Users must hard refresh browser!
```

---

## ✅ Ready to Start!

**Next Steps:**
1. ✅ Start token monitor
2. ✅ Resume Claude Code session with quick start prompt
3. ✅ Launch Gemini Flash for Task 1: Visual Effects
4. ✅ Complete all 4 tasks sequentially
5. ✅ Test, publish, commit

**Let's make combat feel amazing!** 🎮✨
