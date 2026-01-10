# Junior Developer Workflow - FINAL VERSION
## Working Methods for Gemini/Grok/ChatGPT Agents

**Last Updated:** 2025-10-24
**Status:** TESTED AND WORKING ✅

---

## What We Learned

### ❌ What Doesn't Work

**Method 1: Gemini Outputs Code as Text**
- Prompting Gemini to output 200+ lines as text
- Response gets truncated at ~60 lines
- Both Flash AND Pro models have this limit
- **Result:** Failed on Tasks 1.1, 1.2, 1.3

**Method 2: Unsafe File Writing with --yolo**
- Using `gemini --yolo` with absolute paths
- Gemini can delete/modify ANY file on system
- **DANGEROUS:** Could delete databases, production files
- **Result:** Works but too risky!

### ✅ What DOES Work

**Method 3: Safe Sandbox Workflow** ⭐ **RECOMMENDED**

**How it works:**
1. Create sandbox directory: `/tmp/gemini_sandbox_task_X/`
2. Gemini writes files to sandbox (isolated, safe)
3. Claude Code reviews files in sandbox
4. If approved, Claude Code moves files to production
5. If rejected, delete sandbox and retry

**Safety features:**
- Gemini can only affect files in `/tmp/gemini_sandbox_task_X/`
- Production code never touched until approved
- Easy rollback (just delete sandbox)
- Can test files before deployment

---

## Safe Sandbox Workflow

### Step 1: Launch Gemini in Safe Mode

```bash
cd /path/to/axon_bbs
./START_GEMINI_SAFE.sh 1.3 flash

# OR with Pro model
./START_GEMINI_SAFE.sh 1.5 pro
```

**What happens:**
- Creates `/tmp/gemini_sandbox_task_1.3/`
- Gemini writes files to sandbox
- Logs output to `/tmp/gemini_task_1.3_output.txt`

### Step 2: Monitor Progress

```bash
# Watch output
tail -f /tmp/gemini_task_1.3_output.txt

# Check sandbox contents
ls -lh /tmp/gemini_sandbox_task_1.3/

# Wait for completion
./WAIT_FOR_GEMINI_BATCH.sh 1.3
```

### Step 3: Notify Claude Code

```
"Task 1.3 finished in sandbox"
```

### Step 4: Claude Code Reviews

Claude Code will:
1. Read files from `/tmp/gemini_sandbox_task_1.3/`
2. Check against review checklist
3. Test code (syntax check, etc.)
4. Approve or reject

### Step 5: Deploy or Retry

**If APPROVED:**
```bash
# Claude Code moves files to production
cp /tmp/gemini_sandbox_task_1.3/Warzone_Lite.js \
   /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
```

**If REJECTED:**
```bash
# Delete sandbox and retry
rm -rf /tmp/gemini_sandbox_task_1.3/
./START_GEMINI_SAFE.sh 1.3 flash  # Try again
```

---

## Current Project Status

### Completed Tasks ✅

**Task 0: BBS API Test**
- Status: APPROVED ✅
- File: `frontend/src/applets/Test_BBS_API.js`
- Method: Gemini Flash (first successful test)
- Result: Working BBS API demonstration

**Task 1.1: Warzone_Lite.js Skeleton**
- Status: APPROVED ✅
- File: `frontend/src/applets/Warzone_Lite.js`
- Method: Senior architect direct implementation (Gemini truncation issue)
- Result: Complete Three.js setup, 242 lines

**Task 1.2: Terrain Heightmap System**
- Status: APPROVED ✅
- File: Modified `Warzone_Lite.js` (lines 173-343)
- Method: Gemini Flash with unsafe --yolo (before safety fix)
- Result: 64×80 heightmap with strategic features

### Remaining Tasks 📋

**Week 1:**
- Task 1.3: Ground Unit System (NEXT)
- Task 1.4: Mouse Input & Selection
- Task 1.5: A* Pathfinding (use Pro model)

**Week 2-4:**
- Air combat (Tasks 2.1-2.5)
- Asset integration (Tasks 3.1-3.5)
- Multiplayer federation (Tasks 4.1-4.5)

---

## Recommended Workflow Going Forward

### For Simple Tasks (Templates provided)

**Use: Gemini Flash in Safe Mode**
```bash
./START_GEMINI_SAFE.sh 1.3 flash
# Wait ~30 seconds
# "Task 1.3 finished in sandbox"
# Claude reviews and deploys
```

**Good for:**
- Tasks 1.3, 1.4, 2.1-2.3, 3.1-3.5
- Following templates exactly
- Routine code generation

### For Complex Tasks (Algorithms, logic)

**Use: Gemini Pro in Safe Mode**
```bash
./START_GEMINI_SAFE.sh 1.5 pro
# Wait ~60 seconds
# Claude reviews and deploys
```

**Good for:**
- Task 1.5 (A* pathfinding)
- Tasks 2.4 (air combat AI)
- Tasks 4.1-4.4 (multiplayer sync, critical!)

### For Very Complex/Critical Tasks

**Use: Claude Code Direct Implementation**
- Task appears too complex for templates
- Multiple failed attempts with Gemini
- Critical multiplayer code that MUST be correct
- Senior architect implements directly

---

## Batch Parallelization (Future)

**Once safe sandbox is proven:**

```bash
# Create safe batch script that uses separate sandboxes
./START_GEMINI_BATCH_SAFE.sh week1_remaining 1.3 flash 1.4 flash

# Each task gets own sandbox:
# /tmp/gemini_sandbox_task_1.3/
# /tmp/gemini_sandbox_task_1.4/

# All finish in parallel
# Claude reviews all
# Approved files deployed
```

**Benefits:**
- 3-5x faster development
- Same safety as single tasks
- Can abort individual tasks
- Isolated failures don't affect others

---

## Token Efficiency

### Current Usage
- **Used:** ~102,000 / 200,000 (51%)
- **Remaining:** ~98,000 (49%)
- **Status:** ✅ On track for full project completion

### Token Savings with Safe Sandbox

**Per task:**
- Launch Gemini: ~500 tokens
- Review sandbox files: ~5,000 tokens
- Deploy approved: ~100 tokens
- **Total: ~5,600 tokens per task**

**vs Direct Implementation:**
- Senior architect implements: ~15,000 tokens per task
- **Savings: ~9,400 tokens per task (63% reduction!)**

**Projected for remaining 17 tasks:**
- With safe sandbox: ~95,000 tokens
- Fits comfortably in remaining budget!

---

## Scripts Available

### Safe Sandbox Workflow ⭐
- `START_GEMINI_SAFE.sh` - Single task, safe mode
- `WAIT_FOR_GEMINI_BATCH.sh` - Auto-wait with completion notification

### Unsafe (For Reference Only)
- ~~`START_GEMINI_BACKGROUND.sh`~~ - Uses --yolo (UNSAFE!)
- ~~`START_GEMINI_BATCH.sh`~~ - Uses --yolo (UNSAFE!)

**DO NOT USE unsafe scripts in production!**

### Monitoring Tools
- `CHECK_GEMINI_BATCH.sh` - Check task status
- All scripts output to `/tmp/gemini_task_X_output.txt`

---

## Next Session Checklist

**When resuming:**

1. Read this file (JUNIOR_DEVELOPER_WORKFLOW_FINAL.md)
2. Read SESSION_SUMMARY.md (for current status)
3. Check completed tasks in git log
4. Continue with Task 1.3 using safe sandbox

**Command to resume:**
```bash
cd /path/to/axon_bbs
./START_GEMINI_SAFE.sh 1.3 flash
```

---

## Troubleshooting

### Gemini Creates Wrong Files

**Problem:** Files in wrong location or wrong names
**Solution:** Check sandbox, delete and retry with clearer prompt

### Gemini Truncates Output

**Problem:** Using old scripts that ask for text output
**Solution:** Use `START_GEMINI_SAFE.sh` (writes files directly)

### Sandbox Full of Junk

**Problem:** Multiple failed attempts clutter sandbox
**Solution:** `rm -rf /tmp/gemini_sandbox_task_X/`

### Want to Test Before Deploy

**Problem:** Need to verify files work
**Solution:**
```bash
# Copy to test location
cp /tmp/gemini_sandbox_task_1.3/Warzone_Lite.js \
   /tmp/test_Warzone_Lite.js

# Test
node -c /tmp/test_Warzone_Lite.js

# If good, deploy
cp /tmp/test_Warzone_Lite.js \
   /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
```

---

## Safety Rules

1. ✅ **ALWAYS use safe sandbox** for Gemini
2. ❌ **NEVER use --yolo** with production paths
3. ✅ **Review ALL code** before deploying
4. ✅ **Test syntax** before deploying
5. ✅ **Keep backups** of working files
6. ✅ **Delete failed sandboxes** to keep /tmp clean

---

## Success Metrics

**What "success" looks like:**

- ✅ Task 0: Gemini completed in 9 seconds
- ✅ Task 1.2: Gemini completed in ~30 seconds
- ✅ Code matches templates exactly
- ✅ No production files touched until approval
- ✅ Easy rollback if issues found
- ✅ ~60% token savings vs direct implementation

**Project is on track for completion within token budget!**

---

For complete task details, see: `docs/JUNIOR_DEV_TASKS.md`
For review criteria, see: `docs/SENIOR_REVIEW_CHECKLIST.md`
For project plan, see: `docs/Warzone_Lite_Implementation_Plan.md`
