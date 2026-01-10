# Gemini Batch Parallelization Workflow
## Option 3: Hybrid Checkpointing Strategy

**Last Updated:** 2025-10-24

---

## The Strategy

Instead of sequential task-by-task development, we launch **batches** of tasks in parallel, review them together, then proceed to the next batch.

**Benefits:**
- ⚡ 3-5x faster development
- 💰 ~20k token savings per week
- 🎯 Checkpoint-based quality control

---

## Week 1 Batching Plan

### Batch 1: Core Systems (Parallel) ✅ RUNNING NOW

```bash
./START_GEMINI_BATCH.sh week1_batch1 1.1 flash 1.2 flash 1.3 flash
```

**Tasks:**
- Task 1.1: Warzone_Lite.js skeleton with Three.js setup
- Task 1.2: Terrain heightmap system (0-8 levels)
- Task 1.3: Ground unit system (Tank, Artillery, Scout)

**Expected Time:** ~30 seconds all finish
**Review:** Batch review all 3 together
**Integration:** Merge 1.2 and 1.3 into 1.1 skeleton

### Batch 2: Interactive Systems (After Batch 1 Approved)

```bash
./START_GEMINI_BATCH.sh week1_batch2 1.4 flash 1.5 pro
```

**Tasks:**
- Task 1.4: Mouse input and unit selection
- Task 1.5: A* pathfinding with terrain costs (Pro model - complex!)

**Expected Time:** ~30 seconds
**Review:** Batch review both
**Integration:** Add to completed file from Batch 1

---

## Current Status

**RUNNING NOW:**
- Batch: week1_batch1
- Tasks: 1.1, 1.2, 1.3
- Model: Flash (all 3)
- PIDs: 236280, 236281, 236283
- Output: `/tmp/gemini_batch_week1_batch1/`

---

## How to Monitor

### Quick Status Check

```bash
./CHECK_GEMINI_BATCH.sh week1_batch1
```

Output:
```
═══════════════════════════════════════════════════
  Batch Status: week1_batch1
═══════════════════════════════════════════════════

Tasks:
  Task 1.1 (FLASH): PID 236280 → task_1.1_output.txt
  Task 1.2 (FLASH): PID 236281 → task_1.2_output.txt
  Task 1.3 (FLASH): PID 236283 → task_1.3_output.txt

Status Check:
  [RUNNING] PID 236280
  [RUNNING] PID 236281
  [DONE]    PID 236283 ✓

Progress: 1 / 3 complete
⏳ Still running: 2 tasks
```

### Manual Checks

**Watch file sizes (updates every second):**
```bash
watch -n 1 'ls -lh /tmp/gemini_batch_week1_batch1/*.txt'
```

**Check which processes are running:**
```bash
cat /tmp/gemini_batch_week1_batch1/pids.txt | xargs ps -p
```

**View specific task output:**
```bash
tail -f /tmp/gemini_batch_week1_batch1/task_1.1_output.txt
```

---

## When Batch Completes

### You Notify Me

Just say:
```
"Batch week1_batch1 complete"
```

OR if you want to preview:
```bash
cat /tmp/gemini_batch_week1_batch1/tasks.txt
ls -lh /tmp/gemini_batch_week1_batch1/*.txt
```

### I Review All Tasks

Claude Code will:
1. Read all 3 output files
2. Check each against review checklist
3. Approve or request changes for each
4. Integrate approved code
5. Report results

---

## Token Savings Calculation

### Old Sequential Approach

```
Task 1.1: Launch (5k) + Review (7k) = 12k
Task 1.2: Launch (5k) + Review (7k) = 12k
Task 1.3: Launch (5k) + Review (7k) = 12k
Total: 36k tokens
```

### New Batch Approach

```
Batch Launch: 3 tasks (5k total)
Batch Review: 3 tasks together (15k)
Total: 20k tokens
```

**Savings: 16k tokens per batch! (~44% reduction)**

---

## Full Week 1 Timeline

**Traditional Sequential:**
- 5 tasks × 2 minutes each = 10 minutes
- Token usage: ~60k

**Hybrid Batch:**
- Batch 1 (3 tasks): 30 seconds + review
- Batch 2 (2 tasks): 30 seconds + review
- Total: ~2-3 minutes
- Token usage: ~40k
- **Savings: 20k tokens + 7 minutes! 🎉**

---

## Commands Reference

### Launch Batch

```bash
# Syntax
./START_GEMINI_BATCH.sh <batch_name> <task1> <model1> <task2> <model2> ...

# Examples
./START_GEMINI_BATCH.sh week1_batch1 1.1 flash 1.2 flash 1.3 flash
./START_GEMINI_BATCH.sh week1_batch2 1.4 flash 1.5 pro
./START_GEMINI_BATCH.sh week2_air 2.1 flash 2.2 flash 2.3 flash 2.4 pro
```

### Check Status

```bash
./CHECK_GEMINI_BATCH.sh week1_batch1
```

### View All Batches

```bash
ls -ld /tmp/gemini_batch_*
```

---

## Week-by-Week Strategy

### Week 1: Terrain & Ground Units
- **Batch 1:** Tasks 1.1, 1.2, 1.3 (Flash)
- **Batch 2:** Tasks 1.4, 1.5 (Flash + Pro)

### Week 2: Air Combat
- **Batch 1:** Tasks 2.1, 2.2, 2.3 (Flash)
- **Batch 2:** Tasks 2.4, 2.5 (Pro + Flash)

### Week 3: Assets & Polish
- **Batch 1:** Tasks 3.1, 3.2, 3.3 (Flash)
- **Batch 2:** Tasks 3.4, 3.5 (Flash)

### Week 4: Multiplayer (Critical - More Sequential)
- **Batch 1:** Tasks 4.1, 4.2 (Pro) - Event protocol critical
- **Batch 2:** Tasks 4.3, 4.4 (Pro) - Lobby + federation
- **Batch 3:** Task 4.5 (Flash) - Final testing

---

## Troubleshooting

### Batch Stuck / Tasks Not Finishing

```bash
# Check which tasks are running
./CHECK_GEMINI_BATCH.sh week1_batch1

# Kill stuck processes
kill <PID>

# Relaunch individual task
./START_GEMINI_BACKGROUND.sh 1.2 flash
```

### One Task Failed, Others Succeeded

- Review successful tasks
- Relaunch failed task individually
- No need to redo entire batch

### Want to Cancel Batch

```bash
# Get PIDs
cat /tmp/gemini_batch_week1_batch1/pids.txt

# Kill all
cat /tmp/gemini_batch_week1_batch1/pids.txt | xargs kill
```

---

## Current Batch: week1_batch1

**Tasks Running:**
1. Task 1.1 - Warzone_Lite.js skeleton
2. Task 1.2 - Terrain heightmap system
3. Task 1.3 - Ground unit system

**Monitor with:**
```bash
./CHECK_GEMINI_BATCH.sh week1_batch1
```

**Should finish in ~30 seconds from launch (10:12 PM)**

**When done, notify:**
```
"Batch week1_batch1 complete"
```

---

For single task workflow, see: `GEMINI_BACKGROUND_WORKFLOW.md`
For model selection, see: `GEMINI_MODEL_GUIDE.md`
For complete project plan, see: `docs/Warzone_Lite_Implementation_Plan.md`
