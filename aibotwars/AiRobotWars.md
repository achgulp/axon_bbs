1. Project Overview
AIRobotWars is a web-based competitive platform where users pit different AI models (Gemini vs. Claude, etc.) against each other. The AIs are prompted to write a control script for a virtual robot. These robots then battle in a 2D arena, and the result is displayed as a high-fidelity graphical simulation.

2. Core Gameplay Mechanics (The "C-Robots" Legacy)
To keep it true to the original, the robots will have four primary systems:

Scanner: scan(degree, resolution) — Returns the distance to the nearest robot in a specific arc.

Cannon: cannon(degree, distance) — Fires a missile. Robots have a cooldown period between shots.

Drive: drive(degree, speed) — Moves the robot. Faster speeds make turning harder.

Status: damage(), loc_x(), loc_y(), speed() — Real-time telemetry for the script to make decisions.

3. The Tech Stack
Component	Technology	Reason
Frontend	React or Next.js	Modern, component-based, easy to host.
Physics/Graphics	Matter.js + PixiJS	Matter.js for collisions; PixiJS for high-performance 2D rendering.
Logic Engine	Web Workers	Runs the AI scripts in a sandboxed thread so they don't freeze the UI.
AI Integration	Vercel AI SDK	Easy switching between Gemini, Claude, and GPT models.

Export to Sheets

4. User Flow & Specification
Phase A: The Prompting Stage
The user selects two "Contestants" (e.g., Gemini 1.5 Pro and Claude 3.5 Sonnet).

The system sends a standardized System Prompt to both:

"Write a JavaScript function controlRobot(api) that survives in a 1000x1000 arena. You must use api.scan, api.cannon, and api.drive. Your goal is to be the last one standing."

The LLMs return the raw JS code.

Phase B: The Simulation
Code Sanitization: The system wraps the AI code in a Sandbox to prevent window or document access.

Execution: The engine runs the scripts at 60 ticks per second.

Visualization: The web page renders the "video" of the action:

Robots moving and rotating.

Radar "pings" visualizing the scan() calls.

Missiles flying and explosion radii.

Phase C: The Verdict
Win/Loss: A robot dies at 100% damage.

Stats: The UI displays "Accuracy," "Distance Traveled," and "Total Damage Dealt."

The "Winner": The winning AI is crowned, and the user can share the battle replay via a unique URL.

5. Roadmap
V1 (MVP): Static arena, 2 hardcoded AI scripts, basic 2D shapes for robots.

V2 (LLM Integration): Add the "Generate via Prompt" button for Gemini and Claude.

V3 (Social): Leaderboards showing which AI model has the highest win rate globally.

Would you like me to write the "System Prompt" that we will send to the AIs to ensure they produce compatible code?
Modern Web-Based Programming Games This video showcases how modern web-based programming games (like Bot Land) allow users to write scripts that control units in a graphical arena, which is the exact architectural pattern needed for your project.
