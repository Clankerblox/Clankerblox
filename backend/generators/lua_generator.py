"""Lua Generator - Generates complete Roblox game Lua scripts from game plans

For obby games, scripts are pre-built in obby_scripts.py (no API calls needed).
For other game types, uses Claude API to generate scripts.
"""
import json
from backend.utils.logger import log, LogLevel, EventType
from backend.utils.claude_client import ask_claude


async def generate_all_scripts(plan: dict) -> dict[str, str]:
    """
    Generate all Lua scripts needed for the game based on the plan.
    Returns a dict of {script_name: lua_code}

    For obby games, returns empty dict (scripts handled by rbxlx_builder via obby_scripts.py).
    """
    game_id = plan.get("game_id", "unknown")
    game_type = plan.get("game_type", "obby")

    # Obby games use hardcoded scripts from obby_scripts.py
    # The rbxlx_builder handles this directly, no Claude API needed
    if game_type == "obby":
        await log(
            "Obby game: skipping Claude script generation (using hardcoded obby scripts)",
            LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id
        )
        return {}

    scripts_needed = plan.get("scripts_needed", [])
    all_scripts = {}

    await log(
        f"Generating {len(scripts_needed)} Lua scripts for {plan.get('name', 'Unknown')}",
        LogLevel.STEP, EventType.GAME_BUILD, game_id=game_id
    )

    # Generate each script - we batch related scripts together for context
    # First generate module scripts (shared dependencies)
    modules = [s for s in scripts_needed if s.get("type") == "ModuleScript"]
    server_scripts = [s for s in scripts_needed if s.get("type") == "ServerScript"]
    local_scripts = [s for s in scripts_needed if s.get("type") == "LocalScript"]

    # Generate modules first since others depend on them
    for script_info in modules:
        code = await _generate_single_script(plan, script_info, all_scripts)
        all_scripts[script_info["name"]] = code

    # Then server scripts
    for script_info in server_scripts:
        code = await _generate_single_script(plan, script_info, all_scripts)
        all_scripts[script_info["name"]] = code

    # Then local scripts
    for script_info in local_scripts:
        code = await _generate_single_script(plan, script_info, all_scripts)
        all_scripts[script_info["name"]] = code

    # Always generate core scripts even if not in the plan
    core_scripts = _get_core_script_names()
    for name, info in core_scripts.items():
        if name not in all_scripts:
            code = await _generate_single_script(plan, info, all_scripts)
            all_scripts[name] = code

    await log(
        f"Generated {len(all_scripts)} scripts total",
        LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id,
        data={"scripts": list(all_scripts.keys())}
    )

    return all_scripts


def _get_core_script_names() -> dict:
    """Core scripts every game needs."""
    return {
        "GameManager": {
            "name": "GameManager",
            "type": "ServerScript",
            "location": "ServerScriptService",
            "purpose": "Main game orchestration - handles player joining, game state, core loop",
            "key_functions": ["onPlayerAdded()", "onPlayerRemoving()", "initGame()"],
            "dependencies": []
        },
        "DataManager": {
            "name": "DataManager",
            "type": "ModuleScript",
            "location": "ServerScriptService",
            "purpose": "Handles DataStore saving/loading player data with auto-save",
            "key_functions": ["loadData()", "saveData()", "autoSave()"],
            "dependencies": []
        },
        "ClientUI": {
            "name": "ClientUI",
            "type": "LocalScript",
            "location": "StarterPlayerScripts",
            "purpose": "Handles all client-side GUI creation and updates",
            "key_functions": ["createHUD()", "createMenus()", "updateUI()"],
            "dependencies": []
        },
        "ShopManager": {
            "name": "ShopManager",
            "type": "ServerScript",
            "location": "ServerScriptService",
            "purpose": "Handles game pass and dev product purchases",
            "key_functions": ["promptPurchase()", "onPurchaseComplete()", "checkOwnership()"],
            "dependencies": ["DataManager"]
        }
    }


async def _generate_single_script(plan: dict, script_info: dict, existing_scripts: dict) -> str:
    """Generate a single Lua script."""
    script_name = script_info["name"]

    await log(
        f"Generating script: {script_name} ({script_info.get('type', 'Script')})",
        LogLevel.INFO, EventType.GAME_BUILD, game_id=plan.get("game_id")
    )

    # Build context from existing scripts
    deps_context = ""
    for dep in script_info.get("dependencies", []):
        if dep in existing_scripts:
            deps_context += f"\n--- Already generated: {dep} ---\n{existing_scripts[dep][:500]}...\n"

    # Build a comprehensive prompt
    plan_summary = json.dumps({
        "name": plan.get("name"),
        "game_type": plan.get("game_type"),
        "gameplay": plan.get("gameplay"),
        "player_systems": plan.get("player_systems"),
        "monetization": plan.get("monetization"),
        "gui_design": plan.get("gui_design"),
        "world_design": plan.get("world_design"),
        "data_persistence": plan.get("data_persistence"),
    }, indent=2)

    code = await ask_claude(
        prompt=f"""Generate the COMPLETE Lua script for a Roblox game.

SCRIPT TO GENERATE:
- Name: {script_name}
- Type: {script_info.get('type', 'Script')}
- Location: {script_info.get('location', 'ServerScriptService')}
- Purpose: {script_info.get('purpose', 'Core game functionality')}
- Key Functions: {json.dumps(script_info.get('key_functions', []))}

FULL GAME PLAN:
{plan_summary}

DEPENDENCY SCRIPTS ALREADY GENERATED:
{deps_context if deps_context else "None yet - this is a standalone script"}

REQUIREMENTS:
1. Write COMPLETE, PRODUCTION-READY Lua code - no placeholders, no TODOs, no "add your code here"
2. Use proper Roblox API calls (game:GetService, Instance.new, etc.)
3. Include error handling with pcall/xpcall where appropriate
4. Add clear comments explaining game logic
5. Follow Roblox best practices (no deprecated APIs)
6. If this is a ServerScript, handle RemoteEvents/RemoteFunctions properly
7. If this is a LocalScript, handle UI and player input properly
8. If this is a ModuleScript, return a proper module table
9. Make the code robust against edge cases
10. Include proper cleanup in PlayerRemoving events

OUTPUT: Return ONLY the Lua code. No markdown, no code blocks, no explanations. Just pure Lua code starting with comments and the script.""",

        system=f"""You are Clankerblox, an expert Roblox Lua programmer. You write clean, efficient, and complete Roblox game code.

CRITICAL RULES:
- Write COMPLETE scripts, not stubs or templates
- Every function must have a full implementation
- Use modern Roblox API (no deprecated functions)
- Handle edge cases (player leaves mid-action, nil checks, etc.)
- DataStore operations must use pcall
- Remote events must validate data from clients (anti-exploit)
- GUI creation in LocalScripts must be pixel-perfect with proper sizing
- Use TweenService for smooth animations
- Include proper type annotations in comments
- Script must be plug-and-play: it should work when placed in {script_info.get('location', 'ServerScriptService')}

The game is: {plan.get('name', 'Unknown')} - a {plan.get('game_type', '')} game for kids aged 10-13.
Make the code FUN - add juice, effects, and satisfying feedback loops.""",
        max_tokens=8192,
        temperature=0.3
    )

    # Clean up - remove markdown code blocks if Claude adds them
    code = code.strip()
    if code.startswith("```lua"):
        code = code[6:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()

    return code
