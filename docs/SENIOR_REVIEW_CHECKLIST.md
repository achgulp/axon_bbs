# Warzone Lite - Senior Architect Review Checklist
## For Claude Code (Senior Dev) and User (Project Manager)

**Purpose:** This checklist ensures consistent code review quality and helps junior developers understand expectations.

---

## How to Use This Document

**For User (Project Manager):**
- Use this to verify junior dev submissions before sending to me
- Check off items as you test
- If anything fails, send back to junior dev for fixes

**For Claude Code (Senior Architect):**
- Use this checklist when reviewing junior dev code
- Provide specific, constructive feedback
- Approve only when ALL criteria are met

---

## Task 0 Review: BBS API Test

### Code Quality
- [ ] File exists at `/path/to/axon_bbs/frontend/src/applets/Test_BBS_API.js`
- [ ] BBS API helper is included exactly as specified
- [ ] No syntax errors (check with ESLint or manual review)
- [ ] Code is properly indented (2 spaces)
- [ ] No console.warn or console.error in normal operation

### Functionality
- [ ] Loads without errors
- [ ] Calls `getUserInfo()` successfully
- [ ] Calls `getAppletInfo()` successfully
- [ ] Displays user nickname on page
- [ ] Displays user pubkey on page
- [ ] Displays applet ID on page
- [ ] Shows success message

### Console Output
Expected console messages:
```
=== BBS API Test Starting ===
User Info: {username: "...", nickname: "...", pubkey: "..."}
Applet Info: {id: "...", name: "...", parameters: {...}}
=== BBS API Test Complete ===
```

### Approval Comments

If APPROVED:
```
✅ Task 0 APPROVED

Good work! Your BBS API test is working correctly. You've demonstrated understanding of:
- BBS API helper structure
- Async/await usage
- Error handling
- Console logging

You may proceed to Task 1.1.
```

If REJECTED:
```
❌ Task 0 NEEDS REVISION

Issues found:
1. [Specific issue]
2. [Specific issue]

Please fix these issues and resubmit. Do NOT proceed to Task 1.1 until this is approved.
```

---

## Task 1.1 Review: Warzone_Lite.js Skeleton

### Code Quality
- [ ] File exists at `/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js`
- [ ] BBS API helper matches template exactly
- [ ] Header comment includes copyright and GPL notice
- [ ] Code sections are clearly labeled with STEP comments
- [ ] No syntax errors
- [ ] Proper indentation throughout

### Library Loading
- [ ] Three.js loads from CDN
- [ ] `loadScript()` function handles errors properly
- [ ] Checks for `window.THREE` after loading
- [ ] Console shows "Three.js loaded successfully"

### Scene Setup
- [ ] Scene is created
- [ ] Background color is set to #1a2e40
- [ ] Fog is added
- [ ] Orthographic camera is used (NOT perspective)
- [ ] Camera aspect ratio is calculated correctly
- [ ] Camera positioned at (30, 40, 30)
- [ ] Camera looks at origin (0, 0, 0)

### Renderer
- [ ] WebGL renderer created with antialias
- [ ] Size set to window dimensions
- [ ] Shadow mapping enabled
- [ ] Renderer DOM element appended to mount point

### Lighting
- [ ] Ambient light added (0.5 intensity)
- [ ] Directional light added (0.8 intensity)
- [ ] Directional light positioned correctly (-50, 80, -50)
- [ ] Shadow camera bounds set

### Test Geometry
- [ ] Ground plane is 80×80 units
- [ ] Ground material is gray (#334155)
- [ ] Ground receives shadows
- [ ] Test cube is 2×2×2
- [ ] Cube is blue (#007bff)
- [ ] Cube casts shadows
- [ ] Cube positioned at (0, 1, 0)

### Animation
- [ ] Animation loop uses `requestAnimationFrame`
- [ ] Cube rotates smoothly
- [ ] Scene renders without errors
- [ ] FPS is ~60 (check in DevTools)

### Error Handling
- [ ] Entire code wrapped in try/catch
- [ ] Errors logged to console
- [ ] Error displayed to user on failure

### Testing Checklist
- [ ] Opens without errors in browser
- [ ] Console shows all expected initialization messages
- [ ] Three.js scene is visible
- [ ] Ground plane visible
- [ ] Blue cube visible and rotating
- [ ] Window resize works (camera adjusts)

### Approval Comments

If APPROVED:
```
✅ Task 1.1 APPROVED

Excellent work! Your Three.js skeleton is solid. I can see:
- Proper orthographic camera setup for RTS view
- Good lighting (ambient + directional with shadows)
- Clean code organization with clear sections
- Working animation loop

The test cube is rendering and rotating correctly, which proves the rendering pipeline works.

You may proceed to Task 1.2 (Terrain Heightmap).
```

If NEEDS REVISION:
```
❌ Task 1.1 NEEDS REVISION

Issues found:
1. [Specific issue with line number]
2. [Specific issue with line number]

Good work on [something they did right].

Please address these issues and resubmit.
```

---

## Task 1.2 Review: Terrain Heightmap

### Code Quality
- [ ] Old ground plane code removed
- [ ] TerrainSystem object is well-structured
- [ ] Functions are properly commented
- [ ] No code duplication

### Terrain Generation
- [ ] `noise2D()` function implemented correctly
- [ ] `generatePerlinNoise()` creates smooth noise
- [ ] Uses 3 octaves for natural variation
- [ ] Noise is normalized to 0-1 range

### Strategic Features
- [ ] Center plateau at height 5
- [ ] Center plateau is ~8 tile radius
- [ ] Slope area around plateau at height 3
- [ ] Four corner starting zones at height 1
- [ ] Valley choke point at x=32, z=20-60, height 0
- [ ] Heights clamped to 0-8 range

### Mesh Creation
- [ ] PlaneGeometry has correct subdivisions (63×79)
- [ ] Geometry rotated to horizontal
- [ ] Heights applied to vertices correctly
- [ ] Vertex normals recomputed for lighting
- [ ] Material is MeshStandardMaterial
- [ ] Mesh receives shadows

### Helper Functions
- [ ] `getHeightAt()` returns correct height
- [ ] `getHeightAt()` handles out-of-bounds gracefully
- [ ] Coordinate conversion from world to tile is correct

### Visual Verification
- [ ] Terrain is visible
- [ ] Center plateau is elevated and visible
- [ ] Corner areas are noticeably flat
- [ ] Valley choke point is visible
- [ ] Terrain has natural-looking variation
- [ ] Shadows show elevation clearly
- [ ] Test cube sits on terrain (not floating)

### Console Output
Expected:
```
Generating terrain...
Terrain generated with 5120 vertices
Test cube placed at height: [some number 0-8]
```

### Performance
- [ ] Rendering at ~60 FPS
- [ ] No lag or stuttering
- [ ] Terrain loads quickly (<1 second)

### Approval Comments

If APPROVED:
```
✅ Task 1.2 APPROVED

Outstanding terrain implementation! The heightmap looks great:
- Strategic features are clearly visible
- Plateau provides tactical high ground
- Starting zones are appropriately flat
- Noise generation creates natural variation
- Lighting shows elevation beautifully

The test cube correctly follows terrain height, proving your `getHeightAt()` function works.

Performance is good at 5,120 vertices - well within browser capabilities.

You may proceed to Task 1.3 (Ground Units).
```

---

## Task 1.3 Review: Ground Unit System

### Code Quality
- [ ] UNIT_STATS defined with all required properties
- [ ] PLAYER_COLORS array has 4 colors
- [ ] UnitSystem object is well-organized
- [ ] Functions have clear responsibilities

### Unit Stats
- [ ] TANK stats are correct (cost 150, health 100, etc.)
- [ ] ARTILLERY stats are correct
- [ ] SCOUT stats are correct
- [ ] All units have type: 'ground'

### Unit Creation
- [ ] `createUnit()` validates unit type
- [ ] Generates unique unit IDs
- [ ] Creates correct geometry per type:
  - Tank: BoxGeometry 1.5×0.8×2
  - Artillery: CylinderGeometry 0.5→0.8, height 2
  - Scout: BoxGeometry 1×0.4×1.5
- [ ] Materials use player colors
- [ ] Meshes cast shadows
- [ ] Units added to scene
- [ ] Units added to tracking array

### Terrain Following
- [ ] `updateUnitHeight()` calls `TerrainSystem.getHeightAt()`
- [ ] Coordinate conversion is correct
- [ ] Unit Y position = terrain height + offset
- [ ] Mesh position updated correctly

### Movement System
- [ ] `moveUnit()` sets target position
- [ ] `update()` called every frame with deltaTime
- [ ] Units move at correct speed (stats.speed * deltaTime)
- [ ] Movement direction calculated correctly
- [ ] Units rotate to face movement direction
- [ ] Units stop at destination
- [ ] Terrain height updated during movement

### Animation Loop
- [ ] Delta time calculated correctly
- [ ] `UnitSystem.update(deltaTime)` called each frame
- [ ] No performance issues

### Test Units
- [ ] 3 test units created
- [ ] Different unit types
- [ ] Different player colors
- [ ] Positioned at different locations
- [ ] Scout unit is moving

### Visual Verification
- [ ] Can see all 3 units on terrain
- [ ] Units are different shapes
- [ ] Units are different colors (blue, red, green/yellow)
- [ ] Units sit ON terrain (not floating or underground)
- [ ] Scout moves from start to destination
- [ ] Scout rotates while moving
- [ ] Scout follows terrain as it moves uphill/downhill

### Console Output
Expected:
```
Initializing unit system...
Created TANK unit #unit_0 for player 0
Created ARTILLERY unit #unit_1 for player 1
Created SCOUT unit #unit_2 for player 0
Unit system initialized with 3 test units
```

### Approval Comments

If APPROVED:
```
✅ Task 1.3 APPROVED

Fantastic work on the unit system! This is the foundation of the gameplay.

What you've accomplished:
- Clean unit data structure
- Proper terrain-following (units climb hills realistically)
- Smooth movement with rotation
- Delta-time based movement (frame-rate independent)
- Good visual variety (different shapes per unit type)

The moving scout proves your movement system works correctly. I can see it:
- Moves smoothly
- Rotates to face direction
- Follows terrain elevation changes
- Stops at destination

This is professional-quality code. Well done!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 CHECKPOINT 1 COMPLETE! 🎉

You've successfully completed:
✅ Task 0: BBS API understanding
✅ Task 1.1: Three.js skeleton
✅ Task 1.2: Terrain heightmap
✅ Task 1.3: Ground unit system

Your code is ready for the next phase. Before proceeding:

1. Save your work
2. Test thoroughly
3. Take a break!

When you're ready, I'll unlock the next tasks (1.4 onwards).

Excellent work so far! 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Review Process

### For Each Submission

1. **Read the submission message**
   - What task did they complete?
   - What files were modified?
   - What do they claim works?

2. **Code review**
   - Open the file
   - Check against the checklist above
   - Look for common mistakes
   - Verify code quality

3. **Testing** (if possible)
   - Run the applet in Axon BBS
   - Verify functionality
   - Check console for errors
   - Test edge cases

4. **Provide feedback**
   - Be specific (line numbers, exact issues)
   - Be constructive (explain why it's wrong)
   - Be encouraging (praise what's right)
   - Be clear (approve or reject, no ambiguity)

### Feedback Template

```
[✅ APPROVED / ❌ NEEDS REVISION]

Task: [Task Number and Name]
Reviewer: Claude Code (Senior Architect)
Date: [Date]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CODE REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[For each section, check if it passes]

Structure: ✅ / ❌
- [Specific feedback]

Functionality: ✅ / ❌
- [Specific feedback]

Code Quality: ✅ / ❌
- [Specific feedback]

Performance: ✅ / ❌
- [Specific feedback]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ISSUES FOUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[If any issues:]

1. [Issue description]
   Location: [File:Line]
   Problem: [What's wrong]
   Fix: [How to fix it]

2. [Next issue...]

[If no issues:]

No issues found! Code is clean and functional.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT I LIKED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- [Something they did well]
- [Another good thing]
- [Etc.]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DECISION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[If approved:]
✅ APPROVED - Proceed to [Next Task]

[If rejected:]
❌ NEEDS REVISION - Fix the issues above and resubmit.
Do NOT proceed to the next task until this is approved.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Common Issues to Watch For

### Junior Dev Mistakes

1. **Forgot BBS API Helper**
   - Missing or modified the helper code
   - Fix: Copy exact template

2. **Wrong File Path**
   - Created file in wrong directory
   - Fix: Move to correct location

3. **Syntax Errors**
   - Missing semicolons, braces, etc.
   - Fix: Run through ESLint

4. **Not Following Template**
   - Modified template code unnecessarily
   - Fix: Revert to template, then add their changes

5. **No Error Handling**
   - Missing try/catch blocks
   - Fix: Wrap async code in try/catch

6. **Hardcoded Values**
   - Not using constants or config
   - Fix: Use UNIT_STATS, TerrainSystem.size, etc.

7. **Performance Issues**
   - Creating too many objects
   - Not cleaning up
   - Fix: Object pooling, proper disposal

8. **Not Testing**
   - Submitted without verifying it works
   - Fix: Require screenshots/video proof

### Red Flags

🚩 Code that looks copy-pasted without understanding
🚩 No console logs (means they can't debug)
🚩 Vague submission messages ("I did the thing")
🚩 Defensive responses to feedback
🚩 Skipping steps or tasks
🚩 Asking to proceed before approval

---

## Success Metrics

A junior dev is doing well if:
- ✅ Follows instructions precisely
- ✅ Asks good questions when stuck
- ✅ Tests before submitting
- ✅ Accepts feedback gracefully
- ✅ Learns from mistakes
- ✅ Code quality improves over time

---

**Remember:** The goal is to teach, not just to get code. Be patient, be thorough, be encouraging!
