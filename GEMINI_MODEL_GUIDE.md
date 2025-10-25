# Gemini Model Selection Guide
## For Warzone Lite Development

**Last Updated:** 2025-10-24

---

## Available Models

### Flash Model - Junior Developer
- **Model ID:** `gemini-2.5-flash`
- **Speed:** Fast (seconds)
- **Request Limit:** Unlimited
- **Cost:** Free tier
- **Best For:** Template following, routine coding
- **Code Quality:** Good for straightforward tasks

### Pro Model - Mid-level Developer
- **Model ID:** `gemini-2.5-pro`
- **Speed:** Slower (10-30 seconds)
- **Request Limit:** 100 requests per day
- **Cost:** Free tier (limited)
- **Best For:** Complex logic, debugging, critical code
- **Code Quality:** Superior reasoning and implementation

---

## Decision Tree

```
New Task?
│
├─ Simple template following? → Flash
├─ Routine code generation? → Flash
├─ First attempt at any task? → Flash
│
└─ Complex? → Check complexity level:
   │
   ├─ Flash failed 2+ times? → Pro
   ├─ Pathfinding/AI algorithms? → Pro
   ├─ Multiplayer sync/federation? → Pro
   ├─ Performance optimization? → Pro
   ├─ Debugging subtle issues? → Pro
   │
   └─ Still unsure? → Try Flash first, escalate to Pro if needed
```

---

## Task-by-Task Recommendations

### Week 1: Terrain & Ground Units

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| **Task 0** | Flash | Simple BBS API template copy |
| **Task 1.1** | Flash | Skeleton setup, follows pattern |
| **Task 1.2** | Flash | Terrain template provided |
| **Task 1.3** | Flash → Pro if fails | Unit system moderate complexity |
| **Task 1.4** | Flash | Mouse input straightforward |
| **Task 1.5** | **Pro** | A* pathfinding is complex |

### Week 2: Air Combat

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| **Task 2.1** | Flash | Air unit basics similar to ground |
| **Task 2.2** | Flash | Altitude system follows template |
| **Task 2.3** | Flash → Pro if fails | Combat modifiers moderate |
| **Task 2.4** | **Pro** | Air-to-air combat AI complex |
| **Task 2.5** | Flash | Visual polish straightforward |

### Week 3: Asset Integration

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| **Task 3.1** | Flash | Asset extraction scripting |
| **Task 3.2** | Flash | Texture loading from hexgl.js |
| **Task 3.3** | Flash | Sound system straightforward |
| **Task 3.4** | Flash → Pro if fails | Animation moderate complexity |
| **Task 3.5** | Flash | UI polish routine |

### Week 4: Multiplayer

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| **Task 4.1** | **Pro** | Event protocol critical |
| **Task 4.2** | **Pro** | Command sync complex |
| **Task 4.3** | **Pro** | Lobby system multi-component |
| **Task 4.4** | **Pro** | Federation integration critical |
| **Task 4.5** | Flash → Pro if fails | Final testing/polish |

---

## Pro Model Budget Planning

**Total Pro quota:** 100 requests/day

**Estimated Pro usage for project:**

- Week 1: ~3 requests (Task 1.5 + potential fixes)
- Week 2: ~5 requests (Task 2.4 + potential fixes)
- Week 3: ~2 requests (only if Flash struggles)
- Week 4: ~15 requests (most multiplayer tasks)
- **Total: ~25 requests** (well within daily limit!)

**Strategy:**
- Can complete entire project in 3-4 days using Pro strategically
- Or spread over weeks using Flash for routine work
- Pro quota resets daily, so pace accordingly

---

## Command Examples

### Flash Commands (Unlimited)

```bash
# Task 0 - Simple
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Complete Task 0..."

# Task 1.2 - Following template
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_TASKS.md Complete Task 1.2..."
```

### Pro Commands (100/day limit)

```bash
# Task 1.5 - Pathfinding (complex)
gemini -m "gemini-2.5-pro" -p "@docs/JUNIOR_DEV_TASKS.md Complete Task 1.5. A* pathfinding with terrain costs. Take your time, get it right."

# Task 4.2 - Multiplayer sync (critical)
gemini -m "gemini-2.5-pro" -p "@docs/JUNIOR_DEV_TASKS.md Complete Task 4.2. Command synchronization is critical for multiplayer. Ensure deterministic execution."
```

---

## Scripts Available

### Flash Scripts
- `START_GEMINI_TASK_0.sh` - Flash on Task 0

### Pro Scripts
- `START_GEMINI_TASK_0_PRO.sh` - Pro on Task 0 (if Flash fails)

### Manual Commands
- See `claude.md` for all task templates
- Just change `-m "gemini-2.5-flash"` to `-m "gemini-2.5-pro"`

---

## When Flash Fails

**If Flash produces incorrect code:**

1. Check Claude Code's review feedback
2. If issue is simple (typo, missing semicolon) → Fix manually or retry Flash
3. If issue is logic/algorithm → Escalate to Pro
4. If Flash fails twice on same task → Always escalate to Pro

**Escalation Pattern:**

```bash
# First attempt (Flash)
gemini -m "gemini-2.5-flash" -p "@docs/... Complete Task X"
# → Claude Code reviews, finds issues

# Second attempt (Flash with specific fixes)
gemini -m "gemini-2.5-flash" -p "@docs/... Complete Task X. Fix these issues: [list]"
# → Claude Code reviews, still has issues

# Third attempt (Escalate to Pro)
gemini -m "gemini-2.5-pro" -p "@docs/... Complete Task X. Previous attempts failed due to: [reasons]. Please implement correctly."
```

---

## Cost Analysis

**Flash (Unlimited):**
- Use freely for all routine work
- No need to worry about quota
- Perfect for iteration

**Pro (100/day):**
- Reset at midnight daily
- Use strategically for complex tasks
- Don't waste on simple template following
- Save quota for Week 4 multiplayer

**Example daily usage:**
- Day 1: Tasks 0-1.2 (Flash only) - 0 Pro requests
- Day 2: Tasks 1.3-1.4 (Flash only) - 0 Pro requests
- Day 3: Task 1.5 (Pro) + fixes - 3-5 Pro requests
- Quota remaining: 95-97 for rest of project!

---

## Pro Model Benefits

**Why use Pro for complex tasks:**

1. **Better Algorithm Implementation**
   - More sophisticated pathfinding
   - Smarter combat AI
   - Optimized performance

2. **Fewer Iterations**
   - Gets it right first time more often
   - Saves Claude Code review cycles
   - Faster overall development

3. **Complex System Integration**
   - Better at connecting multiple systems
   - Understands architectural implications
   - Handles edge cases better

4. **Critical Code Correctness**
   - Multiplayer sync MUST be correct
   - Federation events MUST work first time
   - Pro model more reliable for mission-critical code

---

## Summary

**Default choice:** Flash
**Escalation trigger:** 2 failures OR inherently complex task
**Pro quota:** 100/day (resets daily)
**Project needs:** ~25 Pro requests total (easily achievable)

**Golden Rule:** Start with Flash, escalate to Pro when needed. Don't waste Pro quota on simple tasks!

---

For detailed command syntax, see `claude.md`.
For task specifications, see `docs/JUNIOR_DEV_TASKS.md`.
For review criteria, see `docs/SENIOR_REVIEW_CHECKLIST.md`.
