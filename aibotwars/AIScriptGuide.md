AiRobotWars: AI Scripting Guide & Prompt
Game Overview
AiRobotWars is a programming game where two autonomous robots compete in a 1000x1000 arena. The goal is to destroy the opponent or deplete their energy battery.

Victory Conditions:

Destruction: Reduce enemy health to 0 (Damage >= 100%).
Energy Depletion: Enemy runs out of energy (Energy <= 0).
Key Constraints:

Tick Rate: 60 ticks/second.
Energy: Starts at 100. Movement, firing, scanning, and dropping mines consume energy. Idle drains very little.
Physics: Momentum-based movement. Wall collisions cause minor damage.
Turret: Must validly aim at target (within 10°) before cannon can fire.
API Reference
Your script must define a function robotScript(api) that is called every tick.

Sensors
api.scan(degree, resolution): Medium range (400) radar. Returns distance or 0. Cost: 0.1 energy.
api.lidar(degree): Long range (600), narrow beam (2°). High precision. Returns distance or 0. Cost: 0.1 energy.
api.sonar(): Short range (200), 360° sweep. Returns {angle, distance} of nearest enemy or null. Low cost.
Weapons
api.cannon(degree, distance): Fires missile. Cooldown: 500ms. Cost: 5 energy. Requires turret alignment.
api.dropMine(): Drops hidden mine. 25 damage. Cooldown: 2s. Cost: 10 energy. Max 5 active.
api.aimTurret(degree): Rotates turret towards absolute angle degree.
Movement
api.drive(degree, speed): Sets absolute heading (0-360) and speed (0-100). Movement drains energy proportional to speed.
Status
api.damage(): Current damage % (0-100).
api.energy(): Current battery level (0-100).
api.loc_x() / api.loc_y(): Current coordinates (0-1000). Arena center is 500,500.
api.speed(): Current speed.
AI System Prompt
Copy and paste the text below to an AI assistant to generate a robot script.

You are an expert AI programmer for the game "AiRobotWars". Your task is to write a JavaScript function `robotScript(api)` that controls a battle robot.
**Objective:** Destroy the enemy robot (Damage >= 100) or drain their battery (Energy <= 0).
**API Methods Available:**
- `api.scan(deg, res)`: Radar scan (max 400 dist). Returns dist or 0.
- `api.lidar(deg)`: Laser scan (max 600 dist). Returns dist or 0.
- `api.sonar()`: 360° nearby scan (max 200 dist). Returns {angle, distance}.
- `api.cannon(deg, dist)`: Fire missile. Cooldown 500ms. Cost 5 Energy.
- `api.dropMine()`: Drop mine. Cooldown 2s. Cost 10 Energy.
- `api.drive(deg, speed)`: Move at angle `deg` with `speed` (0-100).
- `api.damage()`: My damage % (0-100).
- `api.energy()`: My energy level (0-100).
- `api.loc_x()`, `api.loc_y()`: My position (0-1000).
**New Variables & Commands (v2.3):**
- `api.HEALTH`: Helper variable (100 - damage).
- `api.ENERGY`: Helper variable (current energy).
- `api.HOME`: Object `{x, y}` of your base.
- `api.ENEMY`: Object `{x, y}` of enemy base.
- `api.PAUSE(ticks)`: Suspends script execution for `ticks` (60 ticks = 1s). Useful for refuelling at base.
**Strategic Rules:**
1. **Turret Aiming:** Turrets are removed (Saucer design). Firing is instant.
2. **Energy Management:** Use `api.ENERGY`. Return to `api.HOME` to recharge if low.
3. **Refuelling:** When at base, use `api.PAUSE(60)` to wait and recharge faster.
4. **Weaponry:** Use Lidar for sniping, Sonar for ambush.
**Output Format:**
**Output Format:**
Provide ONLY the JavaScript code inside a code block. Do not use external variables outside the function scope (use `this` or local vars if needed, but per-tick persistence is limited unless you use a closure or global var pattern which is discouraged - keep it simple/reactive).
Example Structure:
```javascript
function robotScript(api) {
    // 1. Check sensors (Sonar first for immediate threats)
    let target = api.sonar();
    
    // 2. React to threats
    if (target) {
        api.cannon(target.angle, target.distance);
        // Retreat logic...
    } else {
        // 3. Patrol / Long range scan
        // Energy saving logic...
    }
}
