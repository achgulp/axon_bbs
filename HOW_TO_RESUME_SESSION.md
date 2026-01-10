# How to Resume Your Warzone Lite Session
## Quick Restoration Guide

**Last Updated:** 2025-10-24

---

## 🚀 Quick Start (30 Seconds)

**FIRST: Start the token monitor (prevents running out of tokens):**

```bash
cd /path/to/axon_bbs
./START_TOKEN_MONITOR.sh
```

**THEN: Resume Claude Code session by saying exactly this:**

```
Resume Warzone Lite project.

IMPORTANT: Token monitor is running. When you see token check notifications, report your current usage.

Read these files:
1. /path/to/axon_bbs/QUICK_RESTART.txt
2. /path/to/axon_bbs/SESSION_SUMMARY_2025_10_25_EVENING.md

Current status: v1.10.0 - PIE models working, need to fix WASD controls and white textures.

Let's continue!
```

**That's it!** Claude Code will read the files and be fully restored.

---

## 🔔 Token Monitor (AUTO-SAVE PROTECTION)

**What it does:** Background process that monitors session time and reminds Claude to save session summaries before hitting 200k token limit.

### Start the Monitor

```bash
./START_TOKEN_MONITOR.sh
```

**Output:**
```
✅ TOKEN MONITOR STARTED
PID: 123456
Monitor will check every 30 minutes
Notifications sent to screen session 'Claude'
```

### How It Works

- ⏱️  **30min:** "Quick token check?"
- ⏱️  **60min:** "How are tokens?"
- ⚠️  **90min:** "Likely approaching 80% - Consider saving!"
- 🔴 **120min:** "SAVE SESSION SUMMARY NOW!"

**Notifications appear in Claude's screen session automatically!**

### Stop the Monitor

```bash
./STOP_TOKEN_MONITOR.sh
```

### Why This Matters

**Without monitor:** Easy to hit 200k limit and lose session context
**With monitor:** Automatic reminders ensure you save summaries at 80% (160k tokens)

---

## 📂 Critical Files to Reference

### Must-Read Files (For Claude Code)

**1. SESSION_SUMMARY_2025_10_24.md**
- Complete session history
- What was accomplished
- Current status
- Token usage
- Problems solved
- **Location:** `/path/to/axon_bbs/SESSION_SUMMARY_2025_10_24.md`

**2. HOW_TO_LAUNCH_SUBAGENTS.md**
- How to work with Gemini Flash/Pro
- Safe sandbox workflow
- Command examples
- **Location:** `/path/to/axon_bbs/HOW_TO_LAUNCH_SUBAGENTS.md`

### Reference Files (When Needed)

**3. JUNIOR_DEV_TASKS.md**
- All task specifications with code templates
- **Location:** `/path/to/axon_bbs/docs/JUNIOR_DEV_TASKS.md`

**4. SENIOR_REVIEW_CHECKLIST.md**
- Review criteria for each task
- **Location:** `/path/to/axon_bbs/docs/SENIOR_REVIEW_CHECKLIST.md`

**5. Warzone_Lite_Implementation_Plan.md**
- Complete 4-week technical roadmap
- **Location:** `/path/to/axon_bbs/docs/Warzone_Lite_Implementation_Plan.md`

---

## 🎯 Current Project Status

### Completed Tasks ✅

- **Task 0-1.3:** Terrain, units, pathfinding, rendering
- **Task 1.4:** Mouse selection with raycasting
- **Task 1.5:** Click-to-move with A* pathfinding
- **Task 1.6:** Invisible hitboxes for easier clicking
- **Task 1.7:** Warzone 2100 texture atlas loading
- **Task 1.8 (v1.9.0):** ⭐ **PIE model loader** - Authentic WZ2100 models!
- **Task 1.9 (v1.10.0):** Camera zoom + pan controls

### Next Tasks 📋

- **URGENT:** Fix WASD keyboard controls (not firing)
- **URGENT:** Fix white texture on PIE models
- **Soon:** Implement TCMASK team colors
- **Soon:** Add propulsion + weapon PIE models

### Production Files

**Code files ready:**
- `frontend/src/applets/Test_BBS_API.js` (Task 0)
- `frontend/src/applets/Warzone_Lite.js` (Tasks 1.1, 1.2, 1.3 - 595 lines)

---

## 🔧 How to Continue Development

### Option 1: Start Next Task (Recommended)

```bash
cd /path/to/axon_bbs
./START_GEMINI_SAFE.sh 1.4 flash
```

**Monitor:**
```bash
tail -f /tmp/gemini_task_1.4_output.txt
```

**When done, say to Claude Code:**
```
"Task 1.4 finished in sandbox"
```

### Option 2: Review Current Code

**Ask Claude Code to explain:**
```
"Explain the current state of Warzone_Lite.js"
```

**Or review specific feature:**
```
"Show me how the terrain system works"
```

### Option 3: Commit Progress

```bash
git add frontend/src/applets/Test_BBS_API.js
git add frontend/src/applets/Warzone_Lite.js
git commit -m "Warzone Lite Tasks 0-1.3

- Task 0: BBS API test applet
- Task 1.1: Three.js skeleton
- Task 1.2: Terrain heightmap (64×80, heights 0-8)
- Task 1.3: Ground unit system (Tank, Artillery, Scout)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## 📊 Token Budget Status

**Current Usage:** ~112,000 / 200,000 (56%)
**Remaining:** ~88,000 (44%)
**Last Session:** Oct 25 Evening - PIE models + camera controls
**Status:** 🟢 Excellent! Plenty of runway remaining

---

## ⚠️ Important Notes

### DO Use

✅ `START_GEMINI_SAFE.sh` - Safe sandbox workflow
✅ Read SESSION_SUMMARY before continuing
✅ Check token usage regularly

### DON'T Use

❌ `START_GEMINI_BACKGROUND.sh` - Uses unsafe --yolo
❌ `START_GEMINI_BATCH.sh` - Uses unsafe --yolo
❌ Old task-specific scripts (deprecated)

---

## 🆘 Troubleshooting

### "I don't remember where we left off"

**Say to Claude Code:**
```
"Read SESSION_SUMMARY_2025_10_24.md and tell me where we are"
```

### "What task should I do next?"

**Say to Claude Code:**
```
"What's the next task in the sequence?"
```
Claude will check the summary and tell you (Task 1.4).

### "I want to review what's been done"

**Say to Claude Code:**
```
"Review the completed tasks and show me what's working"
```

### "Token usage seems high"

**Say to Claude Code:**
```
"Check token usage and let me know if we need to save"
```

---

## 📝 Session Restoration Template

**Copy and paste this into a new Claude Code session:**

```
Resume Warzone Lite RTS development project.

Please read these files to restore context:
1. /path/to/axon_bbs/SESSION_SUMMARY_2025_10_24.md
2. /path/to/axon_bbs/HOW_TO_LAUNCH_SUBAGENTS.md

Current Status:
- Tasks 0, 1.1, 1.2, 1.3 complete (75% of Week 1 done)
- Next task: 1.4 (Mouse Input & Selection)
- Token usage: ~120k/200k used

I'm ready to continue. What should we do next?
```

---

## 🎓 Learning Resources

**If you want to understand the workflow:**
- Read: `HOW_TO_LAUNCH_SUBAGENTS.md` (detailed sub-agent guide)
- Read: `GEMINI_MODEL_GUIDE.md` (when to use Flash vs Pro)
- Read: `JUNIOR_DEVELOPER_WORKFLOW_FINAL.md` (full workflow documentation)

**If you want to see the plan:**
- Read: `docs/Warzone_Lite_Implementation_Plan.md` (complete 4-week roadmap)

**If you want to understand tasks:**
- Read: `docs/JUNIOR_DEV_TASKS.md` (all task details with code templates)

---

## ✅ Success Checklist

**Before resuming, make sure you:**
- [ ] Have Claude Code read SESSION_SUMMARY_2025_10_24.md
- [ ] Know what task to do next (Task 1.4)
- [ ] Understand the safe sandbox workflow
- [ ] Know how to launch Gemini (`./START_GEMINI_SAFE.sh 1.4 flash`)
- [ ] Know how to notify Claude when done ("Task 1.4 finished in sandbox")

---

## 📞 Quick Commands Reference

```bash
# Start next task
./START_GEMINI_SAFE.sh 1.4 flash

# Monitor progress
tail -f /tmp/gemini_task_1.4_output.txt

# Check sandbox
ls -lh /tmp/gemini_sandbox_task_1.4/

# Check token usage
# (Just ask Claude Code: "Check token usage")

# Commit progress
git add frontend/src/applets/Warzone_Lite.js
git commit -m "Task 1.4 complete"
```

---

**You're all set! Just use the restoration template above and you'll be back in action!** 🚀
