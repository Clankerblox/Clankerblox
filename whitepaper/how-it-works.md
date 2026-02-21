---
description: The full pipeline from idea to playable Roblox game.
---

# How It Works

ClankerBlox turns a game idea into a downloadable Roblox file in under two minutes. Here's what happens under the hood.

---

## The pipeline

### 1. Trend scanning

The system watches what's blowing up on Roblox — viral game types, trending memes, popular mechanics. It scores each concept on **viral potential** and **revenue potential** before a single line of code is written.

![](.gitbook/assets/dashboard-trends.png)

Current trends are analyzed live. "Brainrot Button Simulator" scored **10/10 viral** and **9/10 revenue** — the system identifies these opportunities automatically.

---

### 2. Procedural generation

Once a concept is chosen, the generator builds the actual game geometry. Not random — it follows real architectural rules:

* **Buildings** with walls, windows, doors, and pitched roofs
* **Factory machines** with chimneys, pipes, smoke effects, and indicator lights
* **Conveyor systems** with proper item flow from droppers to collectors
* **Lighting** — atmosphere, bloom, color correction, point lights
* **Sounds** placed on the right objects with correct names so scripts can find them

A typical tycoon game has **400+ parts, 12 scripts, and 10+ sound effects** — all generated in seconds.

---

### 3. Script injection

Every game gets full Lua scripts injected automatically:

* Server scripts for game logic (tycoon management, data saving, leaderboards)
* Client scripts for UI (HUD, shop, settings, mobile controls)
* CollectionService tags that wire up gameplay elements automatically

Scripts are pre-built and tested — they're not generated from scratch each time. This keeps them reliable.

---

### 4. Quality review

Before a game can be downloaded or published, it goes through an automated quality review across **8 criteria**:

| Criteria | What it checks |
|---|---|
| Visual Density | Enough parts to look like a real game? |
| Script Completeness | All required scripts present? |
| Sound Coverage | Sounds attached and properly named? |
| Gameplay Mechanics | Droppers, conveyors, collectors all functional? |
| Lighting Quality | Atmosphere and effects configured? |
| HUD Quality | Loading screen, settings, mobile support? |
| Monetization Setup | Game passes and dev products configured? |
| Metadata Quality | Title, description, keywords ready for Roblox? |

Games scoring below the threshold get flagged and cannot be downloaded until fixed.

---

### 5. Dashboard

![](.gitbook/assets/dashboard-overview.png)

The live dashboard at [clankerblox-fe.vercel.app](https://clankerblox-fe.vercel.app) shows everything in real time — pipeline status, all built games with quality scores, trend analysis, live activity log, and agent network status.

---

## What comes out

A standard `.rbxlx` file — Roblox Studio's native format. Open it in Studio, hit Play to test, publish to Roblox with one click. Nothing extra needed.
