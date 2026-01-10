
# Using Gemini CLI for Large Codebase Analysis

When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive
context window. Use `gemini -p` to leverage Google Gemini's large context capacity.

## File and Directory Inclusion Syntax

Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
  gemini command:

## Gemini Model Selection

### Available Models

**Flash Model (Junior Developer):**
- Model: `-m "gemini-2.5-flash"`
- Speed: Fast
- Limit: Unlimited requests
- Use for: Routine coding, templates, repetitive tasks
- Quality: Good for straightforward implementation

**Pro Model (Mid-level Developer):**
- Model: `-m "gemini-2.5-pro"`
- Speed: Slower but more thorough
- Limit: 100 requests per day
- Use for: Complex logic, debugging, architecture decisions
- Quality: Better reasoning and code quality

### When to Use Each Model

**Use Flash (Default):**
- Following templates exactly (Tasks 0-1.3)
- Simple feature implementation
- Repetitive code generation
- Quick iterations
- When you have Claude Code for review

**Use Pro (Special Cases):**
- Flash made mistakes multiple times
- Complex algorithms (pathfinding, combat AI)
- Performance optimization needed
- Debugging difficult issues
- Critical code that needs to be right first time

### Model Usage Strategy

1. Start with Flash for all routine tasks
2. If Flash fails 2+ times, escalate to Pro
3. Use Pro for Week 4 multiplayer (most complex)
4. Reserve Pro quota for critical reviews

## Using gemini and a Junior Coder
Default: use -m "gemini-2.5-flash

### Examples:


**Single file analysis:**
gemini -p "@src/main.py Explain this file's purpose and structure"

Multiple files:
gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"

Entire directory:
gemini -p "@src/ Summarize the architecture of this codebase"

Multiple directories:
gemini -p "@src/ @tests/ Analyze test coverage for the source code"

Current directory and subdirectories:
gemini -p "@./ Give me an overview of this entire project"

# Or use --all_files flag:
gemini --all_files -p "Analyze the project structure and dependencies"

Implementation Verification Examples

Check if a feature is implemented:
gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"

Verify authentication implementation:
gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"

Check for specific patterns:
gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"

Verify error handling:
gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"

Check for rate limiting:
gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"

Verify caching strategy:
gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"

Check for specific security measures:
gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"

Verify test coverage for features:
gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"

When to Use Gemini CLI

Use gemini -p when:
- Analyzing entire codebases or large directories
- Comparing multiple large files
- Need to understand project-wide patterns or architecture
- Current context window is insufficient for the task
- Working with files totaling more than 100KB
- Verifying if specific features, patterns, or security measures are implemented

Important Notes

- Paths in @ syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results
- Checking for the presence of certain coding patterns across the entire codebase

---

## Warzone Lite Project - Junior Developer Workflow

### Team Structure
- **Project Manager:** You (Human)
- **Senior Architect:** Claude Code (reviews, architecture, debugging)
- **Junior Developer:** Gemini Flash (implementation, coding)

### Why This Workflow

**Efficient Resource Usage:**
- Claude Code has deep context but limited tokens (~200k)
- Gemini Flash has huge context and is good for implementation
- Use Claude Code for high-value tasks (architecture, review)
- Use Gemini Flash for high-volume tasks (writing code)

### Workflow Commands

**STEP 1: Assign Task to Gemini**

```bash
# Task 0: BBS API Test (Flash - Simple template following)
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Read the onboarding guide completely, then implement Task 0. Create the file at frontend/src/applets/Test_BBS_API.js following the template EXACTLY. Submit the complete code when done."

# OR use Pro if Flash fails:
gemini -m "gemini-2.5-pro" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Read the onboarding guide completely, then implement Task 0. Create the file at frontend/src/applets/Test_BBS_API.js following the template EXACTLY. Submit the complete code when done."
```

**STEP 2: Verify Gemini's Output**

```bash
# Check if Gemini created the file correctly
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Test_BBS_API.js @docs/SENIOR_REVIEW_CHECKLIST.md Does this file pass the Task 0 review criteria? List any issues."
```

**STEP 3: Send to Claude Code for Senior Review**

Return to Claude Code and say:
```
Gemini completed Task 0. File: frontend/src/applets/Test_BBS_API.js
Please review using SENIOR_REVIEW_CHECKLIST.md
```

**STEP 4: Claude Code Reviews**

Claude Code will:
- Read the file
- Check against review checklist
- Approve or request changes
- Provide detailed feedback

**STEP 5: If Changes Needed**

```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Test_BBS_API.js @docs/SENIOR_REVIEW_CHECKLIST.md Claude Code found these issues: [paste issues]. Fix them exactly as specified."
```

**STEP 6: Repeat for Each Task**

Once approved, continue to next task:
```bash
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_TASKS.md @frontend/src/applets/Warzone_Lite.js Task 0 approved. Now complete Task 1.1 (Warzone_Lite.js skeleton). Follow the template exactly."
```

### Task Assignment Templates

**Task 0: BBS API Test (Flash - Simple)**
```bash
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Complete Task 0. Create frontend/src/applets/Test_BBS_API.js using the template. Output the complete file."
```

**Task 1.1: Warzone_Lite.js Skeleton (Flash - Routine)**
```bash
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_TASKS.md @frontend/src/applets/FortressOverlord.js Complete Task 1.1. Create frontend/src/applets/Warzone_Lite.js skeleton. Reference FortressOverlord.js for Three.js patterns. Output the complete file."
```

**Task 1.2: Terrain Heightmap (Flash - Following template)**
```bash
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_TASKS.md @frontend/src/applets/Warzone_Lite.js Complete Task 1.2. Add terrain heightmap system to Warzone_Lite.js. Follow the template exactly. Output the modified file."
```

**Task 1.3: Ground Units (Flash or Pro - More complex)**
```bash
# Try Flash first:
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_TASKS.md @frontend/src/applets/Warzone_Lite.js @frontend/src/applets/FortressOverlord.js Complete Task 1.3. Add ground unit system. Reference FortressOverlord.js for unit patterns. Output the complete file."

# If Flash struggles, use Pro:
gemini -m "gemini-2.5-pro" -p "@docs/JUNIOR_DEV_TASKS.md @frontend/src/applets/Warzone_Lite.js @frontend/src/applets/FortressOverlord.js Complete Task 1.3. Add ground unit system. Reference FortressOverlord.js for unit patterns. Output the complete file."
```

**Task 1.5: Pathfinding (Use Pro - Complex algorithm)**
```bash
# Pathfinding is complex, use Pro from the start:
gemini -m "gemini-2.5-pro" -p "@docs/JUNIOR_DEV_TASKS.md @frontend/src/applets/Warzone_Lite.js Complete Task 1.5. Implement A* pathfinding with terrain height costs. This is algorithmically complex - take your time and get it right. Output the complete file."
```

### Quick Verification Commands

**Check if BBS API helper is correct:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Warzone_Lite.js Does the BBS API helper match the mandatory template from JUNIOR_DEV_ONBOARDING.md? Show any differences."
```

**Check terrain implementation:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Warzone_Lite.js Is the terrain system implemented with 64x80 tiles, heights 0-8, and strategic features (plateau, valleys, flat corners)?"
```

**Verify code quality:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Warzone_Lite.js Are there any syntax errors, missing semicolons, or code quality issues?"
```

### Reference File Analysis

**Study reference applets:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/hexgl.js @frontend/src/applets/FortressOverlord.js @frontend/src/applets/AxonChat.js Analyze these three applets and explain: 1) How hexgl.js loads assets, 2) How FortressOverlord.js handles Three.js rendering, 3) How AxonChat.js does multiplayer events."
```

**Compare implementations:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Warzone_Lite.js @frontend/src/applets/FortressOverlord.js Compare the camera setup in both files. Is Warzone_Lite using the same orthographic pattern?"
```

### Debugging with Gemini

**Find errors:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Warzone_Lite.js This code is producing error: [paste error]. Find the issue and suggest a fix."
```

**Performance analysis:**
```bash
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Warzone_Lite.js Are there any performance issues? Check for: object creation in loops, missing disposal, inefficient rendering."
```

### When to Use Claude Code vs Gemini Flash vs Gemini Pro

**Use Gemini Flash (Junior Dev) for:**
- ✅ Initial code implementation
- ✅ Following templates/patterns exactly
- ✅ Large file analysis
- ✅ Finding syntax errors
- ✅ Comparing multiple files
- ✅ Repetitive coding tasks
- ✅ Simple feature additions
- ✅ Most of Week 1-2 tasks

**Use Gemini Pro (Mid-level Dev) for:**
- ✅ Complex algorithms (A* pathfinding, combat AI)
- ✅ When Flash failed 2+ times
- ✅ Performance-critical code
- ✅ Multi-system integration
- ✅ Week 4 multiplayer (federation, sync)
- ✅ Debugging subtle bugs
- ✅ Optimization tasks
- ⚠️ Limited to 100 requests/day - use wisely!

**Use Claude Code (Senior Architect) for:**
- ✅ Final code review
- ✅ Architectural decisions
- ✅ Complex debugging guidance
- ✅ Approval/rejection decisions
- ✅ Explaining "why" not just "what"
- ✅ Mentoring and guidance
- ✅ Breaking ties when Pro disagrees with Flash
- ⚠️ Limited to ~200k tokens - conserve for reviews!

### Token Conservation Strategy

**Claude Code monitors tokens:**
- Current usage shown in system warnings
- Auto-save session at 85% (~170k tokens)
- Use Gemini for bulk work
- Reserve Claude Code for reviews

**Example Token-Efficient Workflow:**

1. Gemini implements Task 0-1.3 (saves ~30k Claude tokens)
2. Claude Code reviews all 4 tasks (uses ~10k tokens)
3. Gemini fixes any issues (saves ~5k Claude tokens)
4. Claude Code approves (uses ~2k tokens)

**Result:** 4 tasks completed, only ~12k Claude tokens used vs ~35k if Claude did it all!

### Complete Example Session

```bash
# 1. Assign Task 0
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md Complete Task 0"

# 2. Gemini creates Test_BBS_API.js
# [Gemini outputs the code]

# 3. Quick check
gemini -m "gemini-2.5-flash" -p "@frontend/src/applets/Test_BBS_API.js Any syntax errors?"

# 4. Send to Claude Code
# Return to Claude Code: "Review Task 0: frontend/src/applets/Test_BBS_API.js"

# 5. Claude Code reviews and approves
# Claude: "✅ Task 0 APPROVED"

# 6. Continue to Task 1.1
gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_TASKS.md Complete Task 1.1"

# Repeat...
```

### Tips for Best Results

1. **Be Specific:** Tell Gemini exactly which task and what to output
2. **Reference Files:** Use `@` syntax to include templates and examples
3. **Verify First:** Have Gemini self-check before Claude review
4. **Batch Tasks:** Gemini can do multiple small tasks in one go
5. **Save Claude Tokens:** Only use Claude Code for reviews and decisions

### Session Save Trigger

Claude Code will auto-save when token usage reaches ~170k (85% of 200k):
```
CHECKPOINT: Token usage at 85%
Saving session to docs/CLAUDE_CODE_SESSION_SUMMARY.md
Status: [current task]
Next: [what to do when resuming]
```

---
