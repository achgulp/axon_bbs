# AI Session Continuity Guide

**How to Help AI Assistants Pick Up Where You Left Off**

---

## The Three-Tier Documentation System

### Tier 1: Quick Context (Root Level) - **Read These First**

1. **`/PROJECT_STATUS.md`** (Update: Monthly or after major milestones)
  - Overall project status
  - What's complete vs in-progress
  - Performance metrics
  - Recent changes
  - Version info
  - **Purpose:** "Where is the project now?"

2. **`/CURRENT_WORK.md`** (Update: Weekly or when switching tasks)
  - Active tasks RIGHT NOW
  - What you're focusing on this week
  - Immediate next steps
  - Blockers
  - **Purpose:** "What am I working on today?"

3. **`/ARCHITECTURE.md`** (Update: Rarely, only on major changes)
  - Technical architecture
  - System design
  - Core patterns
  - Reference documentation
  - **Purpose:** "How does the system work?"

### Tier 2: Planning Documents (`/docs/`)

4. **`/docs/ROADMAP.md`** or **`/docs/NETCODE_ROADMAP.md`**
  - Long-term plans
  - Multi-phase projects
  - Milestone tracking
  - **Purpose:** "Where are we going?"

5. **`/docs/[FEATURE]_PLAN.md`** (e.g., Warzone_Lite_Implementation_Plan.md)
  - Detailed feature specs
  - Implementation details
  - Task breakdowns
  - **Purpose:** "How do we build X?"

### Tier 3: Session Notes (`/docs/`)

6. **`/docs/SESSION_NOTES.txt`**
  - Quick, informal notes
  - Recent decisions
  - Context from last session
  - **Purpose:** "What did we just discuss?"

---

## What AI Assistants Look For (in Order)

When an AI starts helping you, they typically check:

1. **Root README.md** - Project overview
2. **PROJECT_STATUS.md** - Current state
3. **CURRENT_WORK.md** - Active tasks
4. **Git status** - Recent changes (`git status`, `git log`)
5. **ARCHITECTURE.md** - Technical reference
6. **Package files** - `package.json`, `requirements.txt`
7. **Documentation folder** - `/docs/`

---

## File Update Frequency Recommendations

| File | Update Frequency | Trigger |
|------|------------------|---------|
| `CURRENT_WORK.md` | Daily/Weekly | When you switch tasks |
| `PROJECT_STATUS.md` | Monthly | Major milestone complete |
| `ARCHITECTURE.md` | Quarterly | Architectural changes |
| `docs/ROADMAP.md` | Quarterly | Long-term plan changes |
| `docs/SESSION_NOTES.txt` | Every session | After AI collaboration |
| Git commits | Daily | After completing work |

---

## Best Practices for Session Continuity

### ✅ DO:

1. **Update `CURRENT_WORK.md` when you switch focus**
  ```markdown
  ## What I'm Working On Right Now
  - [x] Completed: 60fps architecture
  - [ ] In Progress: Bee Adventure AI bees
  - [ ] Next: Port Bee Adventure to Axon BBS
  ```

2. **Keep a `SESSION_NOTES.txt` for quick context**
  ```
  Nov 22, 2025: Reviewed project status with Claude Code
  - 60fps is done (Nov 21)
  - Warzone Lite is complete
  - Bee Adventure in external development
  - Next: Build netcode library after Bee Adventure port
  ```

3. **Use git commits descriptively**
  ```bash
  git commit -m "Add 60fps dual-loop architecture and LAN federation"
  ```

4. **Mark completion dates in docs**
  ```markdown
  - ✅ 60fps Architecture (Nov 21, 2025)
  - 🟡 Bee Adventure (In Progress)
  - ❌ Netcode Library (Planned)
  ```

5. **Provide clear file paths in documentation**
  ```markdown
  See /docs/NETCODE_ROADMAP.md for details
  ```

### ❌ DON'T:

1. **Don't leave ambiguous status**
  ```markdown
  ❌ "Working on stuff"
  ✅ "Implementing AI bees for Bee Adventure"
  ```

2. **Don't forget to mark things complete**
  ```markdown
  ❌ "- [ ] Build 60fps system" (when it's done!)
  ✅ "- [x] Build 60fps system (Nov 21, 2025)"
  ```

3. **Don't mix current work with future plans**
  - Use `CURRENT_WORK.md` for NOW
  - Use `ROADMAP.md` for FUTURE

4. **Don't create orphaned documentation**
  - Every doc should be linked from somewhere
  - Reference docs from `PROJECT_STATUS.md` or `README.md`

5. **Don't update ARCHITECTURE.md for every small change**
  - It's a reference, not a changelog
  - Major changes only

---

## Example Session Restoration Prompt

**When starting a new AI session:**

```
Hi Claude Code, I'm resuming work on Axon BBS.

Please read these files to understand where we are:
1. /path/to/axon_bbs/PROJECT_STATUS.md
2. /path/to/axon_bbs/CURRENT_WORK.md
3. /path/to/axon_bbs/ARCHITECTURE.md (if needed)

Current situation:
- Last worked on: [date]
- Current task: [what you're doing]
- Question: [what you need help with]

After reading, please confirm:
- What's the current project status?
- What am I working on?
- How can you help?
```

---

## Template: CURRENT_WORK.md

```markdown
# Current Work - [Project Name]

**Last Updated:** [Date]
**Active Phase:** [Phase description]

---

## What I'm Working On Right Now

### Primary: [Main Task]
**Status:** [In progress/Blocked/etc]
**Location:** [Where the code is]

**Current Tasks:**
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**When This is Done:**
→ [Next thing to do]

---

## Secondary: [Other Tasks]

[Optional secondary work]

---

## Near Future (Next 2-4 Weeks)

1. [Task 1]
2. [Task 2]

---

## Blockers / Waiting On

- ❌ [What's blocking you]
- Or: None currently

---

## Recently Completed (Last 7 Days)

- ✅ [What you finished]
- ✅ [Another thing]

---

## Notes for Future AI Sessions

**If resuming [Topic A]:**
- [Context about topic A]

**If resuming [Topic B]:**
- [Context about topic B]

---

*Update this file whenever you switch focus or complete major tasks.*
```

---

## Template: SESSION_NOTES.txt

```
[PROJECT NAME] - SESSION NOTES
================================
Date: [YYYY-MM-DD]
Session: [Topic/Focus]

WHAT WE DECIDED
---------------
- Decision 1
- Decision 2

FILES CREATED/MODIFIED
----------------------
- /path/to/file1.md
- /path/to/file2.js

CURRENT STATUS
--------------
- [Status update]

NEXT STEPS
----------
1. [Next action]
2. [Another action]

NOTES
-----
- [Important note]
- [Another note]

END OF SESSION
==============
```

---

## Quick Reference: File Purposes

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `README.md` | Project overview | Rarely |
| `PROJECT_STATUS.md` | Current overall state | Monthly |
| `CURRENT_WORK.md` | Active tasks | Weekly |
| `ARCHITECTURE.md` | Technical reference | Quarterly |
| `docs/ROADMAP.md` | Long-term plans | Quarterly |
| `docs/SESSION_NOTES.txt` | Recent context | Every session |
| `.git/` | Change history | Every commit |

---

## Tools to Help

### Git Aliases for Better Commit Messages

```bash
# Add to ~/.gitconfig
[alias]
  st = status
  cm = commit -m
  last = log -1 HEAD --stat
  lg = log --oneline --graph --all --decorate
```

### File Template Snippets

Save these in your editor:

```bash
# VS Code: Create .vscode/snippets.code-snippets
{
 "Current Work Header": {
  "prefix": "current-work",
  "body": [
   "# Current Work - ${1:Project}",
   "",
   "**Last Updated:** ${CURRENT_YEAR}-${CURRENT_MONTH}-${CURRENT_DATE}",
   "**Active Phase:** ${2:Phase}",
   "",
   "---",
   "",
   "## What I'm Working On Right Now",
   ""
  ]
 }
}
```

---

## Common Mistakes to Avoid

1. **Forgetting to mark completed items**
  - AI will think you're still working on finished tasks

2. **Not dating status updates**
  - AI can't tell if info is current or months old

3. **Mixing documentation purposes**
  - Keep current state separate from future plans
  - Keep technical docs separate from status updates

4. **Creating docs without links**
  - Every doc should be discoverable from root-level files

5. **Not updating after major milestones**
  - When you finish a big feature, update PROJECT_STATUS.md!

---

## For Axon BBS Specifically

**Current Setup (Nov 2025):**

✅ **Have:**
- `PROJECT_STATUS.md` (updated Nov 22, 2025)
- `CURRENT_WORK.md` (created Nov 22, 2025)
- `ARCHITECTURE.md` (v10.30.0, Nov 21, 2025)
- `docs/NETCODE_ROADMAP.md` (created Nov 22, 2025)
- `docs/60FPS_GAMING_SETUP.md`
- `docs/Warzone_Lite_Implementation_Plan.md`
- `docs/SESSION_NOTES.txt`

✅ **Working Well:**
- Three-tier system in place
- Clear separation of concerns
- AI can quickly understand status

📋 **Recommended:**
- Update `CURRENT_WORK.md` when switching from Bee Adventure to netcode
- Update `PROJECT_STATUS.md` when Bee Adventure is ported
- Keep git commits descriptive

---

## Summary: The Golden Rule

> **The best documentation for AI session continuity is:**
> 1. A clear current status (PROJECT_STATUS.md)
> 2. Active work list (CURRENT_WORK.md)
> 3. Stable technical reference (ARCHITECTURE.md)
> 4. Recent git history
>
> **Update them regularly, and AI can pick up instantly.**

---

*Created: November 22, 2025*
*For: Axon BBS Project*
*By: Claude Code *
