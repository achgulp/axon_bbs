# Warzone Lite - Quick Start Guide
## TL;DR - Start Developing in 5 Minutes

**Last Updated:** 2025-10-24

---

## What This Project Is

**Warzone Lite:** A JavaScript RTS game for Axon BBS with:
- Multi-level terrain (0-8 elevations)
- Multi-altitude air combat (3 layers)
- Federated multiplayer via BBS events
- 15-20MB total size

---

## Team Structure

**You:** Project Manager
**Claude Code:** Senior Architect (me)
**Gemini Flash:** Junior Developer (unlimited requests, routine coding)
**Gemini Pro:** Mid-level Developer (100/day limit, complex tasks)
**Other AIs:** Backup developers (Grok, ChatGPT, etc.)

---

## Files You Need

All in `/path/to/axon_bbs/docs/`:

1. **`JUNIOR_DEV_ONBOARDING.md`** - Give this to junior AIs first
2. **`JUNIOR_DEV_TASKS.md`** - Step-by-step tasks with code
3. **`SENIOR_REVIEW_CHECKLIST.md`** - For code reviews
4. **`Warzone_Lite_Implementation_Plan.md`** - Full technical spec
5. **`CLAUDE_CODE_SESSION_SUMMARY.md`** - Restore context later
6. **`GEMINI_MODEL_GUIDE.md`** - When to use Flash vs Pro
7. **`claude.md`** - Complete workflow with model selection

---

## Model Selection (Quick Reference)

**Use Gemini Flash (default):**
- Simple template following (Tasks 0-1.2)
- Routine code generation
- Unlimited requests - use freely!

**Use Gemini Pro (special cases):**
- Complex algorithms (Task 1.5 pathfinding)
- When Flash fails 2+ times
- Week 4 multiplayer tasks
- Limited to 100/day - use wisely!

**See `GEMINI_MODEL_GUIDE.md` for complete decision tree**

---

## How to Start (Right Now!)

### Step 1: Pick Your Model
- **Gemini Flash** (recommended for Task 0)
- **Gemini Pro** (if you want best quality from start)
- Grok or ChatGPT (backup options)

### Step 2: Run Gemini Command

**Option A - Flash (recommended):**
```bash
cd /path/to/axon_bbs
./START_GEMINI_TASK_0.sh
```

**Option B - Pro (if you want best quality):**
```bash
cd /path/to/axon_bbs
./START_GEMINI_TASK_0_PRO.sh
```

**Option C - Manual command:**
```bash
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Complete Task 0..."
# OR
gemini -m "gemini-2.5-pro" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Complete Task 0..."
```

### Step 3: When They Submit

Send to me (Claude Code):
```
Junior dev completed Task 0.
Files: /path/to/axon_bbs/frontend/src/applets/Test_BBS_API.js
Please review using SENIOR_REVIEW_CHECKLIST.md
```

### Step 4: I Review

I'll check the code and respond:
- ✅ APPROVED - Proceed to next task
- ❌ NEEDS REVISION - Fix these issues

### Step 5: Repeat

Continue through tasks 1.1, 1.2, 1.3, etc. until complete!

---

## When You Come Back Later

Start new conversation:
```
Resume Warzone Lite project as senior architect.

Read:
1. /path/to/axon_bbs/docs/CLAUDE_CODE_SESSION_SUMMARY.md
2. /path/to/axon_bbs/docs/Warzone_Lite_Implementation_Plan.md

Status: [Tell me where you are]
Let's continue!
```

---

## Task Overview

**Week 1: Terrain & Ground Units**
- Task 0: BBS API test
- Task 1.1: Three.js skeleton
- Task 1.2: Heightmap terrain
- Task 1.3: Ground units
- Task 1.4: Mouse input
- Task 1.5: Pathfinding

**Week 2: Air Combat**
- Tasks 2.1-2.5: Air units, altitude system

**Week 3: Assets**
- Tasks 3.1-3.5: Textures, sounds, polish

**Week 4: Multiplayer**
- Tasks 4.1-4.5: Federation, lobbies, sync

---

## Key Numbers

- **Map:** 64×80 tiles
- **Ground levels:** 0-8
- **Air altitudes:** 10, 15, 20
- **Unit types:** 10 (5 ground, 5 air)
- **Building types:** 5
- **Total size:** 15-20MB
- **Heartbeat:** 2 seconds
- **Timeline:** 4 weeks

---

## That's It!

Everything else is in the detailed docs. Start with Task 0 and go from there!

**Questions?** Ask me (Claude Code) anytime.
