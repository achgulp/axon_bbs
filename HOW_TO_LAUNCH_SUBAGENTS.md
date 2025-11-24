# How to Launch Sub-Agent Junior Developers
## Complete Guide for Gemini Flash & Pro

**Last Updated:** 2025-10-24
**Status:** TESTED AND WORKING ✅

---

## 🎯 Overview

**You have two AI junior developers available:**

1. **Gemini Flash** - Junior developer (unlimited requests, fast, good for templates)
2. **Gemini Pro** - Mid-level developer (100 requests/day, slower, better for complex tasks)

**Claude Code (senior architect) reviews their work and approves/rejects.**

---

## 🚀 Quick Start - Launch a Sub-Agent

### Basic Command

```bash
cd /path/to/axon_bbs
./START_GEMINI_SAFE.sh <task_number> <model>
```

**Examples:**
```bash
# Task 1.4 with Flash (routine coding)
./START_GEMINI_SAFE.sh 1.4 flash

# Task 1.5 with Pro (complex pathfinding)
./START_GEMINI_SAFE.sh 1.5 pro
```

---

## 📋 Complete Workflow (Step by Step)

### Step 1: Launch Gemini

```bash
cd /path/to/axon_bbs
./START_GEMINI_SAFE.sh 1.4 flash
```

**What happens:**
```
✅ Creates sandbox: /tmp/gemini_sandbox_task_1.4/
✅ Copies docs/ into sandbox (all documentation)
✅ Copies Warzone_Lite.js into sandbox (existing code)
✅ Gemini works in isolated sandbox
```

**You'll see:**
```
═══════════════════════════════════════════════════
  Starting Gemini FLASH on Task 1.4 (SAFE MODE)
═══════════════════════════════════════════════════

Sandbox directory: /tmp/gemini_sandbox_task_1.4
Output log: /tmp/gemini_task_1.4_output.txt

Setting up sandbox...
  ✓ Copied docs/ to sandbox
  ✓ Copied Warzone_Lite.js to sandbox

✅ Gemini FLASH started in SAFE MODE!
   PID: 123456
```

### Step 2: Monitor Progress (Optional)

**Watch live output:**
```bash
tail -f /tmp/gemini_task_1.4_output.txt
```

**Check sandbox contents:**
```bash
ls -lh /tmp/gemini_sandbox_task_1.4/
```

**Auto-wait (recommended):**
```bash
./WAIT_FOR_GEMINI_BATCH.sh 1.4
```

This will wait until Gemini finishes, then show you a completion message.

### Step 3: Wait for Completion

**Gemini typically takes:**
- Flash: 30-60 seconds
- Pro: 60-120 seconds

**You'll know it's done when:**
- The process PID is no longer running: `ps -p 123456`
- The output file stops growing: `ls -lh /tmp/gemini_task_1.4_output.txt`

### Step 4: Notify Claude Code

**In your Claude Code session, say:**
```
"Task 1.4 finished in sandbox"
```

OR if you want to be more specific:
```
"Gemini finished Task 1.4.
Sandbox: /tmp/gemini_sandbox_task_1.4
Please review and deploy."
```

### Step 5: Claude Code Reviews

Claude Code will:
1. Read files from sandbox
2. Check against review checklist
3. Verify syntax (no errors)
4. Approve or reject

**If APPROVED:**
- Claude Code deploys to production
- Sandbox can be deleted
- Ready for next task!

**If REJECTED:**
- Claude Code explains issues
- Sandbox deleted
- Retry with fixes

---

## 🔍 Monitoring Commands

### Check if Gemini is Still Running

```bash
# Check specific task
ps -p $(cat /tmp/gemini_task_1.4.pid)

# Search for any Gemini process
ps aux | grep gemini
```

### Watch Output in Real-Time

```bash
# Follow the output log
tail -f /tmp/gemini_task_1.4_output.txt

# Last 50 lines
tail -50 /tmp/gemini_task_1.4_output.txt
```

### Check Sandbox Contents

```bash
# List files
ls -lh /tmp/gemini_sandbox_task_1.4/

# See what Gemini modified
diff /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js \
     /tmp/gemini_sandbox_task_1.4/Warzone_Lite.js
```

### Auto-Wait Script

```bash
# This waits until done, then shows ready message
./WAIT_FOR_GEMINI_BATCH.sh 1.4
```

**Output when complete:**
```
═══════════════════════════════════════════════════
🎉 BATCH COMPLETE!
═══════════════════════════════════════════════════

Batch: 1.4
Tasks: 1
Duration: 45 seconds

✅ READY FOR REVIEW

Copy this message to Claude Code:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task 1.4 finished in sandbox
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎛️ Model Selection Guide

### When to Use Gemini Flash

**Use Flash for:**
- ✅ Tasks 1.4, 2.1, 2.2, 2.3, 3.1-3.5 (most tasks)
- ✅ Following provided templates
- ✅ Routine code generation
- ✅ UI and input handling
- ✅ Simple game logic
- ✅ First attempts at any task

**Flash is good at:**
- Template copying
- Straightforward implementation
- Fast turnaround (30-60 seconds)

**Flash struggles with:**
- Complex algorithms (pathfinding, AI)
- Performance optimization
- Subtle bugs

### When to Use Gemini Pro

**Use Pro for:**
- ✅ Task 1.5 (A* pathfinding - complex algorithm!)
- ✅ Task 2.4 (Air combat AI)
- ✅ Tasks 4.1-4.4 (Multiplayer sync - critical!)
- ✅ When Flash fails 2+ times
- ✅ Performance-critical code

**Pro is better at:**
- Complex algorithms
- Multi-system integration
- Debugging subtle issues
- Critical correctness (multiplayer)

**Pro limits:**
- 100 requests per day (resets daily)
- Slower (60-120 seconds vs 30-60)

**Pro budget for project:**
- Need ~10-15 Pro requests total
- Well within 100/day limit!

### Decision Tree

```
Is this task on the Pro list? (1.5, 2.4, 4.1-4.4)
├─ YES → Use Pro
└─ NO → Start with Flash
    ├─ Flash succeeds → Done! ✅
    └─ Flash fails 2+ times → Escalate to Pro
```

---

## ⚠️ Safety & Sandboxing

### Why Sandbox is Critical

**Without sandbox:**
- ❌ Gemini could delete important files
- ❌ Gemini could modify wrong files
- ❌ Gemini could corrupt databases
- ❌ No way to review before deploying

**With sandbox:**
- ✅ Gemini isolated in /tmp/gemini_sandbox_task_X/
- ✅ Can't touch production files
- ✅ Easy to review before deploying
- ✅ Easy to discard and retry
- ✅ Safe testing environment

### How Sandbox Works

**Setup phase:**
```bash
# Script creates sandbox
mkdir /tmp/gemini_sandbox_task_1.4

# Copies documentation
cp -r docs/ /tmp/gemini_sandbox_task_1.4/

# Copies existing code
cp frontend/src/applets/Warzone_Lite.js /tmp/gemini_sandbox_task_1.4/

# Gemini works here (isolated!)
cd /tmp/gemini_sandbox_task_1.4
```

**Gemini's view:**
```
/tmp/gemini_sandbox_task_1.4/
├── docs/                       (all documentation)
│   ├── JUNIOR_DEV_ONBOARDING.md
│   ├── JUNIOR_DEV_TASKS.md
│   └── SENIOR_REVIEW_CHECKLIST.md
├── Warzone_Lite.js            (existing code to modify)
└── Test_BBS_API.js            (reference)
```

**Gemini can:**
- ✅ Read all docs
- ✅ Read existing code
- ✅ Modify files in sandbox
- ❌ Access /path/to/axon_bbs/ (production)

**After review:**
```bash
# If approved, Claude Code deploys:
cp /tmp/gemini_sandbox_task_1.4/Warzone_Lite.js \
   /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

# Clean up
rm -rf /tmp/gemini_sandbox_task_1.4/
```

---

## 📊 Example Complete Session

### Task 1.4: Mouse Input & Selection

**1. Launch Gemini:**
```bash
$ cd /path/to/axon_bbs
$ ./START_GEMINI_SAFE.sh 1.4 flash

✅ Gemini FLASH started in SAFE MODE!
   PID: 250123
```

**2. Monitor (optional):**
```bash
$ tail -f /tmp/gemini_task_1.4_output.txt
# Watch Gemini working...
```

**3. Wait for completion:**
```bash
$ ./WAIT_FOR_GEMINI_BATCH.sh 1.4
# Waits automatically...

🎉 BATCH COMPLETE!
Task 1.4 finished in 52 seconds
```

**4. Notify Claude Code:**
```
"Task 1.4 finished in sandbox"
```

**5. Claude Code reviews:**
```
Reading /tmp/gemini_sandbox_task_1.4/Warzone_Lite.js...
Checking syntax... ✅
Reviewing mouse input code... ✅
Checking raycasting... ✅

✅ TASK 1.4 APPROVED!

Mouse input system looks good! Features:
- Click detection with raycasting
- Unit selection highlighting
- Proper terrain intersection

Deploying to production...
```

**6. Done!**
```bash
$ ls -lh /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
-rw-rw-r-- 1 user user 22K Oct 24 23:15 Warzone_Lite.js
```

---

## 🛠️ Troubleshooting

### Problem: Gemini Creates Wrong Files

**Symptoms:**
- Files in wrong location
- Wrong file names
- Missing files

**Solution:**
```bash
# Check sandbox
ls -lh /tmp/gemini_sandbox_task_X/

# If wrong, delete and retry
rm -rf /tmp/gemini_sandbox_task_X/
./START_GEMINI_SAFE.sh X flash
```

### Problem: Gemini Output Truncated

**Symptoms:**
- Code incomplete
- File only has partial content
- Ends abruptly

**This shouldn't happen with safe sandbox!** But if it does:
```bash
# Try Pro model (better output handling)
./START_GEMINI_SAFE.sh X pro
```

### Problem: Want to Preview Before Telling Claude

**Solution:**
```bash
# Read the file yourself first
cat /tmp/gemini_sandbox_task_X/Warzone_Lite.js

# Check syntax
node -c /tmp/gemini_sandbox_task_X/Warzone_Lite.js

# Compare to original
diff /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js \
     /tmp/gemini_sandbox_task_X/Warzone_Lite.js

# If good, notify Claude Code
```

### Problem: Gemini Taking Too Long

**Normal times:**
- Flash: 30-90 seconds
- Pro: 60-180 seconds

**If > 5 minutes:**
```bash
# Check if still running
ps -p $(cat /tmp/gemini_task_X.pid)

# Check output
tail /tmp/gemini_task_X_output.txt

# If stuck, kill and retry
kill $(cat /tmp/gemini_task_X.pid)
rm -rf /tmp/gemini_sandbox_task_X/
./START_GEMINI_SAFE.sh X flash
```

### Problem: Want to Cancel

**Solution:**
```bash
# Kill the process
kill $(cat /tmp/gemini_task_X.pid)

# Delete sandbox
rm -rf /tmp/gemini_sandbox_task_X/

# Start over
./START_GEMINI_SAFE.sh X flash
```

---

## 📝 Command Quick Reference

### Launch Commands

```bash
# Flash model (default, unlimited)
./START_GEMINI_SAFE.sh 1.4 flash

# Pro model (100/day limit, better quality)
./START_GEMINI_SAFE.sh 1.5 pro
```

### Monitoring Commands

```bash
# Watch output
tail -f /tmp/gemini_task_X_output.txt

# Check sandbox
ls -lh /tmp/gemini_sandbox_task_X/

# Auto-wait
./WAIT_FOR_GEMINI_BATCH.sh X
```

### Status Commands

```bash
# Is it still running?
ps -p $(cat /tmp/gemini_task_X.pid)

# What files were created?
ls -lh /tmp/gemini_sandbox_task_X/

# How long is the output?
wc -l /tmp/gemini_task_X_output.txt
```

### Cleanup Commands

```bash
# Delete sandbox (after approval)
rm -rf /tmp/gemini_sandbox_task_X/

# Clean all old sandboxes
rm -rf /tmp/gemini_sandbox_*

# Clean all old outputs
rm /tmp/gemini_task_*.txt
```

---

## ✅ Best Practices

1. **Always use safe sandbox** (START_GEMINI_SAFE.sh)
2. **Start with Flash**, escalate to Pro if needed
3. **Monitor first few tasks** to learn the workflow
4. **Use auto-wait script** for convenience
5. **Check sandbox before notifying Claude** (optional but helpful)
6. **Clean up sandboxes** after deployment
7. **Track Pro usage** (max 100/day)

---

## 🎓 Learning Path

**First time?** Follow this order:

1. Read this guide completely
2. Try Task 1.4 with Flash
3. Monitor the process
4. See Claude Code review
5. Understand the workflow
6. Try Task 1.5 with Pro
7. Compare Flash vs Pro results
8. You're now an expert!

---

**You're all set to launch sub-agents! The workflow is safe, efficient, and proven to work.** 🚀

For session restoration, see: `HOW_TO_RESUME_SESSION.md`
For project details, see: `SESSION_SUMMARY_2025_10_24.md`
