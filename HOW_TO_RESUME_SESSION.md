# How to Resume Your Warzone Lite Session
## Quick Restoration Guide

**Last Updated:** 2025-10-24

---

## 🚀 Quick Start (30 Seconds)

**When starting a new Claude Code session, say exactly this:**

```
Resume Warzone Lite project.

Read these files:
1. /home/dukejer/axon_bbs/SESSION_SUMMARY_2025_10_24.md
2. /home/dukejer/axon_bbs/HOW_TO_LAUNCH_SUBAGENTS.md

Current status: Tasks 0-1.3 complete. Ready for Task 1.4.

Let's continue!
```

**That's it!** Claude Code will read the files and be fully restored.

---

## 📂 Critical Files to Reference

### Must-Read Files (For Claude Code)

**1. SESSION_SUMMARY_2025_10_24.md**
- Complete session history
- What was accomplished
- Current status
- Token usage
- Problems solved
- **Location:** `/home/dukejer/axon_bbs/SESSION_SUMMARY_2025_10_24.md`

**2. HOW_TO_LAUNCH_SUBAGENTS.md**
- How to work with Gemini Flash/Pro
- Safe sandbox workflow
- Command examples
- **Location:** `/home/dukejer/axon_bbs/HOW_TO_LAUNCH_SUBAGENTS.md`

### Reference Files (When Needed)

**3. JUNIOR_DEV_TASKS.md**
- All task specifications with code templates
- **Location:** `/home/dukejer/axon_bbs/docs/JUNIOR_DEV_TASKS.md`

**4. SENIOR_REVIEW_CHECKLIST.md**
- Review criteria for each task
- **Location:** `/home/dukejer/axon_bbs/docs/SENIOR_REVIEW_CHECKLIST.md`

**5. Warzone_Lite_Implementation_Plan.md**
- Complete 4-week technical roadmap
- **Location:** `/home/dukejer/axon_bbs/docs/Warzone_Lite_Implementation_Plan.md`

---

## 🎯 Current Project Status

### Completed Tasks ✅

- **Task 0:** BBS API Test (Gemini Flash)
- **Task 1.1:** Warzone_Lite.js Skeleton (Senior architect - Gemini truncation issue)
- **Task 1.2:** Terrain Heightmap System (Gemini Flash unsafe --yolo)
- **Task 1.3:** Ground Unit System (Gemini Flash safe sandbox) ⭐ **NEW!**

### Next Tasks 📋

- **Task 1.4:** Mouse Input & Selection (Gemini Flash - NEXT)
- **Task 1.5:** A* Pathfinding (Gemini Pro - complex algorithm)

### Production Files

**Code files ready:**
- `frontend/src/applets/Test_BBS_API.js` (Task 0)
- `frontend/src/applets/Warzone_Lite.js` (Tasks 1.1, 1.2, 1.3 - 595 lines)

---

## 🔧 How to Continue Development

### Option 1: Start Next Task (Recommended)

```bash
cd /home/dukejer/axon_bbs
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

**Current Usage:** ~120,000 / 200,000 (60%)
**Remaining:** ~80,000 (40%)
**Estimated for completion:** ~75,000 more tokens
**Status:** 🟢 On track!

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
1. /home/dukejer/axon_bbs/SESSION_SUMMARY_2025_10_24.md
2. /home/dukejer/axon_bbs/HOW_TO_LAUNCH_SUBAGENTS.md

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
