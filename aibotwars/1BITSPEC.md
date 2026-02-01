# Specification: 1-Bit Evolutionary AI Strategist

## 1. Objective
Enable a real-time "evolutionary" combat loop where a local 1-bit LLM (via BitNet.cpp or Ollama) observes battle performance and rewrites the robot's control script mid-match to counter opponent tactics.

## 2. Architecture: Asynchronous Evolution
The system must decouple the high-frequency game loop (60 FPS) from the lower-frequency AI reasoning (1–5 second latency).



### A. The SITREP (Situation Report)
Every 200 ticks, the game generates a serialized SITREP containing:
* **Tactical State:** Current HP, Energy, and relative coordinates of the enemy robot.
* **Performance Delta:** Accuracy (Hits/Shots), damage taken since last report, and energy efficiency.
* **Behavioral Signature:** Classification of enemy movement (e.g., "strafing," "camping," "ramming").

### B. The Hot-Reload Mechanism
The `Robot` class in `AiRobotWars.js` must be modified to:
1. **Queue Updates:** Receive new script code via an asynchronous listener.
2. **Validate:** Pass new code through the existing `compileScript` function to ensure syntax validity.
3. **Inject:** Atomically swap `this.controlScript` with the new function without interrupting the `tick()` cycle.

### C. Latency Management
* The robot continues executing its *current* script while the "Strategist" (the 1-bit model) thinks. 
* There is no "Pause" state; the AI must adapt to a moving target.

## 3. Communication Bridge
* **Outgoing:** The applet uses `fetch()` to POST the SITREP to a local Python proxy.
* **Incoming:** The proxy returns a JSON object: `{ "new_script": "function robotScript(api) { ... }" }`.
