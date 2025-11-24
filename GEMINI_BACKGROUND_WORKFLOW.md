# Gemini Background Job Workflow
## Token-Efficient Development Process

**Last Updated:** 2025-10-24

---

## The Problem We Solved

**Before:** Claude Code had to wait for Gemini to finish (30+ seconds), consuming tokens while idle.

**After:** Claude Code kicks off Gemini in background, you monitor it, then Claude Code reviews when ready.

**Token Savings:** ~20-30k tokens per session!

---

## Quick Start - Background Jobs

### Option 1: Use the Background Script (Recommended)

```bash
cd /path/to/axon_bbs

# Start Gemini Flash on any task (background)
./START_GEMINI_BACKGROUND.sh 0 flash

# OR start Gemini Pro on any task
./START_GEMINI_BACKGROUND.sh 1.5 pro
```

### Option 2: Manual Background Command

```bash
./START_GEMINI_TASK_0.sh > /tmp/gemini_task_0_output.txt 2>&1 &
```

---

## Complete Workflow

### Step 1: Claude Code Starts Gemini (Takes 2 seconds)

Claude Code runs:
```bash
./START_GEMINI_BACKGROUND.sh 0 flash
```

Output:
```
✅ Gemini FLASH started in background!
   PID: 233490

Monitor progress with:
   tail -f /tmp/gemini_task_0_output.txt

Check if still running:
   ps -p 233490

When done, notify Claude Code:
   'Gemini finished Task 0. Review /tmp/gemini_task_0_output.txt'
```

### Step 2: You Monitor Gemini (Optional)

**Watch live output:**
```bash
tail -f /tmp/gemini_task_0_output.txt
```

**Check if still running:**
```bash
ps -p 233490
# Returns nothing when done
```

**Check file size (grows when Gemini writes):**
```bash
watch -n 1 'ls -lh /tmp/gemini_task_0_output.txt'
```

### Step 3: You Notify Claude Code When Done

Just send:
```
"Gemini finished Task 0. Review /tmp/gemini_task_0_output.txt"
```

OR if you want to see the output first:
```
"Gemini finished Task 0. Here's what it produced:"
[paste output]
```

### Step 4: Claude Code Reviews

Claude Code:
- Reads `/tmp/gemini_task_0_output.txt`
- Reviews against checklist
- Approves or requests changes

---

## Background Script Usage

### Basic Syntax

```bash
./START_GEMINI_BACKGROUND.sh <task> <model>
```

**Parameters:**
- `<task>` - Task number (0, 1.1, 1.2, 2.3, etc.)
- `<model>` - flash or pro (default: flash)

### Examples

```bash
# Task 0 with Flash (simple template)
./START_GEMINI_BACKGROUND.sh 0 flash

# Task 1.5 with Pro (complex pathfinding)
./START_GEMINI_BACKGROUND.sh 1.5 pro

# Task 2.1 with Flash (default)
./START_GEMINI_BACKGROUND.sh 2.1
```

### Output Files

All output saved to:
```
/tmp/gemini_task_<number>_output.txt
```

Examples:
- Task 0: `/tmp/gemini_task_0_output.txt`
- Task 1.1: `/tmp/gemini_task_1.1_output.txt`
- Task 4.3: `/tmp/gemini_task_4.3_output.txt`

---

## Monitoring Commands

### Check if Gemini is Running

```bash
# Check specific PID
ps -p 233490

# Or search for any Gemini process
ps aux | grep gemini
```

### Watch Output in Real-time

```bash
# Follow the output file
tail -f /tmp/gemini_task_0_output.txt

# Show last 50 lines
tail -50 /tmp/gemini_task_0_output.txt
```

### Check Progress by File Size

```bash
# One-time check
ls -lh /tmp/gemini_task_0_output.txt

# Watch it grow (updates every 1 second)
watch -n 1 'ls -lh /tmp/gemini_task_0_output.txt'
```

---

## Typical Timeline

| Event | Time | What's Happening |
|-------|------|------------------|
| Start | 0s | Claude Code kicks off background job |
| Running | 1-30s | Gemini reads docs and generates code |
| Done | 30s | Output file complete, Gemini exits |
| Notify | 30s | You tell Claude Code it's ready |
| Review | 30-60s | Claude Code reviews the output |
| **Total** | **~1-2 min** | Complete cycle |

**Key:** Claude Code only consumes tokens for ~60 seconds total (start + review), not the full 2 minutes!

---

## What Gemini Was Trying to Do (First Attempt)

**Problem:** Gemini tried to create files instead of outputting code as text.

**Error:**
```
I apologize, but I cannot directly create or write files using the available tools.
```

**Solution:** Updated scripts with clearer instructions:
- "You do NOT have file writing capabilities"
- "ONLY output the code as text in your response"
- "Do NOT use markdown code blocks"
- "Just output the raw JavaScript code"

**Result:** Second attempt (running now) should output code correctly!

---

## Token Comparison

### Old Workflow (Claude Code Waits)

```
Claude Code starts Gemini → Waits 30s → Reviews
Tokens used: ~56k (context stays loaded)
```

### New Workflow (Background Jobs)

```
Claude Code starts Gemini → Exits
[You monitor]
Claude Code reviews when notified
Tokens used: ~5k (start) + ~10k (review) = ~15k total
```

**Savings:** ~40k tokens per task! 🎉

---

## Next Time Workflow

**For all future tasks:**

1. You say: "Start Task 1.1 with Flash"
2. I run: `./START_GEMINI_BACKGROUND.sh 1.1 flash`
3. I respond: "✅ Gemini started! Let me know when done."
4. You monitor (optional): `tail -f /tmp/gemini_task_1.1_output.txt`
5. You notify: "Gemini finished Task 1.1"
6. I review and approve/reject

**Ultra token-efficient!**

---

## Current Status

**Running Now:**
- Task: 0
- Model: Flash
- PID: 233490
- Output: `/tmp/gemini_task_0_output.txt`
- Status: Should finish in ~30 seconds

**You can check:**
```bash
ps -p 233490          # Still running?
tail /tmp/gemini_task_0_output.txt  # What's the output?
```

**When done, just say:** "Gemini finished Task 0"

---

## Available Scripts

1. `START_GEMINI_BACKGROUND.sh` - Main background job script (any task, any model)
2. `START_GEMINI_TASK_0.sh` - Quick Task 0 with Flash (foreground)
3. `START_GEMINI_TASK_0_PRO.sh` - Quick Task 0 with Pro (foreground)

**Use background script for all future tasks!**

---

For model selection guide, see: `GEMINI_MODEL_GUIDE.md`
For complete workflow, see: `claude.md`
For quick start, see: `docs/QUICK_START_GUIDE.md`
