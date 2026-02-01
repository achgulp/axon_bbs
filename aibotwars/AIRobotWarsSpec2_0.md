Specification: AI Robot Wars v2.0
The Evolutionary Multimodal Battleground
1. Core Concept
A real-time 60 FPS combat simulation where two robots (Red vs. Blue) are controlled by hot-swappable JavaScript scripts. Unlike traditional games, these scripts are rewritten mid-match by diverse AI models (the "Strategists") based on live game data and real-time Human Commander guidance.

2. Architecture: The "Async-Evolution" Model
To maintain 60 FPS performance while using LLMs (which have latency), the system uses three layers:

Layer 1: The Arena (60 FPS): The Three.js engine executes the current robotScript(api) every tick.

Layer 2: The Observer (Asynchronous): Every 200 ticks (~3 seconds), the game generates a SITREP (Situation Report) and sends it to the designated Team API.

Layer 3: The Strategist (LLM): The LLM analyzes the SITREP + Human Prompts, rewrites the script to counter the enemy, and sends it back to the Arena for a Hot-Reload.

3. Multi-Agent & AI-Agnostic API
The game is no longer hardcoded to one model. It features two independent "Brain Slots":

Feature	Red Team API	Blue Team API
Model Example	Qwen-2.5-7B (Ollama)	BitNet b1.58 (1-Bit local)
Endpoint	http://localhost:11434/api	http://localhost:5000/evolve
Specialty	Complex Logic & Pathing	High-Speed Reactive Counters
User Input	Commander Red's Console	Commander Blue's Console

Export to Sheets

The SITREP Schema (Data sent to AI)
JSON

{
  "team": "RED",
  "status": { "hp": 85, "energy": 1200, "pos": [450, 210] },
  "performance": { "accuracy": "20%", "recent_damage_taken": 15 },
  "enemy_signature": "Circling clockwise, high usage of Mines",
  "commander_guidance": "Stop kiting and go for a close-range ram!",
  "current_code": "function controlRobot(api) { ... }"
}
4. Multi-User Sync (BBS Integration)
Using the Axon BBS as the coordination layer, two users can participate in the same match from different terminals.

Host Mode (Authority): The first user to join runs the physics engine and Three.js.

Commander Mode (Sync): The second user joins the same session. Their applet receives state updates via window.bbs.postEvent and mirrors the action.

Dual-Prompting: Both users see the same live feed, but each has a private text box to "whisper" commands to their respective AI (Red or Blue).

5. Operational Modes
Human vs. CPU: You (Human+AI) fight against a static, pre-programmed script.

AI vs. AI (Spectator): Two different models (e.g., Gemini vs. 1-bit) fight while you watch the logs.

Commander vs. Commander (PvP): Two humans on different screens compete to see who can better "guide" their evolving AI scripts to victory.

6. Technical Requirements
Hot-Swapping: Use new Function('api', code) to inject LLM-generated logic without stopping the simulation.

Sandboxing: AI-generated code is limited to the api object (cannot access window, document, or BBS internals).

Hardware Market: (Integrated from MarketUpgradeTech.md) The cost of LLM "Evolutions" is deducted from the match budget, preventing infinite spamming of script updates.
