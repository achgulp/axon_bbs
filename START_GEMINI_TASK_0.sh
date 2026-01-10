#!/bin/bash
# Warzone Lite - Start Gemini on Task 0
# Run this from /path/to/axon_bbs/ directory

echo "═══════════════════════════════════════════════════"
echo "  Starting Gemini Flash on Warzone Lite Task 0"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Gemini will:"
echo "  1. Read onboarding documentation"
echo "  2. Read task breakdown"
echo "  3. Implement Task 0 (BBS API test)"
echo "  4. Output complete code"
echo ""
echo "After Gemini completes, send output to Claude Code for review."
echo ""
echo "═══════════════════════════════════════════════════"
echo ""

gemini -m "gemini-2.5-flash" -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md You are a junior developer on the Warzone Lite project. Your senior architect is Claude Code.

TASK: Complete Task 0 from JUNIOR_DEV_TASKS.md

CRITICAL: You do NOT have file writing capabilities. Do NOT try to create files. ONLY output the code as text in your response.

INSTRUCTIONS:
1. Read JUNIOR_DEV_ONBOARDING.md completely to understand Axon BBS
2. Read the Task 0 section in JUNIOR_DEV_TASKS.md
3. Generate the Test_BBS_API.js code using the EXACT template provided
4. Output the COMPLETE file contents as TEXT in your response (ready to copy-paste)
5. Do NOT modify the BBS API helper - copy it exactly as shown
6. Include all sections: header comment, BBS API helper, main execution

OUTPUT FORMAT:
Output ONLY the JavaScript code as plain text in your response.
Start with: // --- Start of Applet API Helper (MANDATORY) ---
End with the closing of the main IIFE.

Do NOT use markdown code blocks. Do NOT try to write files. Just output the raw JavaScript code.

Ready? Output the complete Test_BBS_API.js code now."
