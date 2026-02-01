AI1BIT.md: Tactical Pilot & Local-First Evolution (v3.0)
1. Objective
Transform the combat loop into a high-speed, collaborative "Human-AI Pilot" system. This removes remote API dependencies and shifts the AI's role from a static coder to a real-time tactical responder using local curated models (1-bit BitNet and Ollama).

2. Architecture: The Dual-Loop System
To maintain 60 FPS performance while allowing for sub-100ms reactions, the system separates tactical "Micro" decisions from strategic "Macro" refits.

A. The "Micro" Pulse (Tactical Pilot)
Frequency: Every 150ms (approx. 9 ticks), the game polls the selected local AI backend.

Input: A minimalist SITREP string (e.g., HP:85, EN:1200, EnemyDist:340, EnemyAngle:12, Heading:90).

Output: The AI returns exactly one API command (e.g., api.cannon(12, 340);).

Execution: The command is executed immediately, allowing the robot to react to the enemy's last move.

B. The "Macro" Refit (Inter-Round Evolution)
Timing: Occurs only during the "Refit Window" between the 7 tournament rounds.

Input: The AI receives the full battle log of the previous round (accuracy, damage delta, enemy behavior tags).

Process: The AI takes 10–15 seconds to rewrite the base robotScript logic to counter the opponent's strategy.

Implementation: The new script is hot-swapped via evolve(newCode) before the next round begins.

3. Curated Local Backends
The system is hardcoded to support two specific local endpoints to ensure stability and prevent API abuse:

Backend	Endpoint	Model Profile	Target Latency
Reflex Brain	localhost:5000	BitNet b1.58 (1-bit): Optimized for raw speed and reactive micro-adjustments.	< 50ms
Genius Brain	localhost:11434	Qwen-2.5 (Ollama): Optimized for complex tactical maneuvers and trap-setting.	~300-500ms

Export to Sheets

4. Human-AI Collaboration (The Commander's Console)
The human player acts as the "Commanding Officer".

Direct Interjection: Any command typed in the console executes instantly. If a human command is detected, the AI's tactical pulse for that frame is discarded (Human Priority).

Strategic Whispers: Non-command text typed by the human is stored as commanderIntent and prepended to every Micro SITREP, guiding the AI's tactical choices (e.g., "Stay near the base and wait for him").

5. Technical Implementation Details
A. Micro-Pulse Schema (SITREP)
To maximize 1-bit performance, the prompt is highly compressed: [Intent: {commanderIntent}] [State: {SITREP}] [Action: Output 1 line of code]

B. The "Lag" Penalty
If the local AI backend takes more than 500ms to respond, the "Tactical Pulse" is skipped.

The robot will continue its last known command or fallback to its "Base Script" until the AI finishes "thinking".

C. Sandbox & Validation
All AI-generated commands are passed through a regex validator to ensure they only contain valid api calls (e.g., drive, cannon, scan, dropMine).

Any malformed strings are logged to the debugLog and ignored to prevent game crashes.

6. Operational Modes
1 vs CPU: Human + Local AI Pilot vs. Static Legacy Script.

PvP (Dual-Commander): Two users on separate BBS terminals, each using their own local AI backends to compete in real-time.

Spectator Mode: Watch two different local models (e.g., BitNet vs Qwen) battle autonomously with live "Refit" updates between rounds.
