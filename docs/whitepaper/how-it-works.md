# How It Works

The ClankerBlox pipeline turns a game idea into a downloadable Roblox file in under two minutes. Here's what happens under the hood.

## The pipeline

### 1. Game planning

The system takes a concept (like "Factory Tycoon" or "Escape Obby") and creates a detailed game plan. This includes the theme, game mechanics, economy balance, script structure, and visual style.

Game types currently supported:
- **Tycoon** — build factories, collect resources, upgrade machines, rebirth for multipliers
- **Obby** — obstacle courses with checkpoints, kill bricks, moving platforms, and stage progression
- **Simulator** — click-to-collect with areas, pets, upgrades, and rebirths
- **Story Obby** — narrative-driven obstacle courses with dialog and characters

### 2. Procedural generation

Once the plan is set, the procedural generator builds the actual game geometry. This isn't random — it follows architectural rules:

- **Buildings** with walls, windows, doors, and pitched roofs
- **Factory machines** with chimneys, pipes, smoke effects, and indicator lights
- **Conveyor systems** with proper item flow from droppers to collectors
- **Lighting** including atmosphere, bloom, color correction, and point lights
- **Sounds** placed on the right objects with correct names so scripts can find them

A typical tycoon game has 400+ parts, 12 scripts, and 10+ sound effects.

### 3. Script injection

The generator adds all the Lua scripts a game needs to actually function:
- Server scripts for game logic (tycoon management, data saving, leaderboards)
- Client scripts for UI (HUD, shop, settings, mobile controls)
- Collection service tags that wire up gameplay elements automatically

Scripts are pre-built and tested — they're not generated from scratch each time. This keeps them reliable.

### 4. Quality review

Before a game is marked as ready, it goes through an automated quality review. The reviewer checks:

- **Visual density** — enough parts to look like a real game?
- **Script completeness** — all required scripts present?
- **Sound coverage** — sounds attached and properly named?
- **Gameplay mechanics** — droppers, conveyors, collectors all functional?
- **Lighting quality** — atmosphere and effects configured?
- **HUD quality** — loading screen, settings, mobile support?

Games need to score above the threshold to pass. If they don't, the system flags what's wrong.

### 5. Dashboard

The dashboard at [dashboard.clankerblox.com](https://dashboard.clankerblox.com) lets you:
- Trigger new game builds (single game or batch)
- See all built games with their quality scores
- Download .rbxlx files to open in Roblox Studio
- Monitor build logs in real time
- Connect as a community agent to help build games

## What comes out

The final output is a standard `.rbxlx` file — the native Roblox Studio format. You can open it directly in Studio, hit Play to test, and publish to Roblox with one click. Nothing extra needed.
