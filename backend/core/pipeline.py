"""Pipeline Orchestrator - Manages the full game creation pipeline"""
import json
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum

from backend.config import GAMES_OUTPUT_DIR, DATA_DIR, MAX_GAMES_PER_DAY
from backend.utils.logger import log, LogLevel, EventType
from backend.analyzers.trend_analyzer import analyze_trends, get_cached_trends
from backend.generators.game_planner import create_game_plan, get_plan, list_plans
from backend.generators.lua_generator import generate_all_scripts
from backend.generators.rbxlx_builder import build_rbxlx
from backend.agents.registry import get_registry


class PipelineStatus(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning_trends"
    PLANNING = "creating_plan"
    GENERATING = "generating_scripts"
    BUILDING = "building_rbxlx"
    VALIDATING = "validating"
    COMPLETE = "complete"
    ERROR = "error"
    FIXING = "fixing_errors"


class GameStatus(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    BUILDING = "building"
    VALIDATING = "validating"
    READY = "ready"
    ERROR = "error"
    PUBLISHED = "published"


# Global pipeline state
_pipeline_state = {
    "status": PipelineStatus.IDLE,
    "current_game": None,
    "games_today": 0,
    "last_scan": None,
    "queue": [],
    "completed_games": [],
    "errors": [],
    "stats": {
        "total_games_built": 0,
        "total_scripts_generated": 0,
        "total_trends_analyzed": 0,
        "uptime_start": datetime.now().isoformat()
    }
}

# Pipeline history file
PIPELINE_LOG = DATA_DIR / "pipeline_log.json"


def get_state() -> dict:
    """Get current pipeline state."""
    return {**_pipeline_state, "status": _pipeline_state["status"].value if isinstance(_pipeline_state["status"], PipelineStatus) else _pipeline_state["status"]}


async def run_trend_scan() -> dict:
    """Run a trend analysis scan. Also dispatches to community trend researchers if online."""
    _pipeline_state["status"] = PipelineStatus.SCANNING

    await log("Pipeline: Starting trend scan...", LogLevel.STEP, EventType.TREND_SCAN)

    # Also dispatch to community trend researchers in parallel
    registry = get_registry()
    community_task_id = None
    if registry.has_online_agent_for_role("trend_researcher"):
        community_task_id = registry.post_work("trend_researcher", {
            "prompt": (
                "Research what's trending RIGHT NOW on Roblox for kids aged 10-13. "
                "Check TikTok trends, YouTube Kids, popular Roblox games. "
                "Find: hot memes, viral characters, popular game mechanics, "
                "trending aesthetics, and what kids are talking about. "
                "Output JSON: {trend_name, why_trending, key_characters, visual_elements, "
                "color_palette, catchphrases, meme_elements, competitor_games, monetization_hooks}"
            ),
            "context": "This research will be used to generate new Roblox game concepts.",
        })
        await log("Dispatched trend research to community agent!", LogLevel.INFO, EventType.TREND_SCAN)

    try:
        result = await analyze_trends()
        _pipeline_state["last_scan"] = datetime.now().isoformat()
        _pipeline_state["stats"]["total_trends_analyzed"] += 1
        _pipeline_state["status"] = PipelineStatus.IDLE

        # Check if community agent contributed
        if community_task_id:
            community_result = registry.get_work_result(community_task_id)
            if community_result:
                # Merge community research into our result as extra context
                if "analysis" not in result:
                    result["analysis"] = {}
                result["analysis"]["community_research"] = community_result
                await log("Community trend research merged into results!",
                          LogLevel.SUCCESS, EventType.TREND_SCAN)

        await log("Pipeline: Trend scan complete!", LogLevel.SUCCESS, EventType.TREND_SCAN)
        return result
    except Exception as e:
        _pipeline_state["status"] = PipelineStatus.ERROR
        error_msg = f"Trend scan failed: {str(e)}"
        _pipeline_state["errors"].append({"time": datetime.now().isoformat(), "error": error_msg})
        await log(error_msg, LogLevel.ERROR, EventType.TREND_SCAN, data={"traceback": traceback.format_exc()})
        raise


async def _dispatch_to_community_agents(concept: dict, plan: dict, game_id: str) -> dict:
    """
    Dispatch work to online community agents during a build.
    Returns a dict of {role: result_data} for any agent results we got.
    """
    registry = get_registry()
    agent_results = {}

    # Check which roles have online agents
    roles_to_dispatch = {
        "trend_researcher": {
            "prompt": (
                f"Research the trend '{concept.get('name', '')}' for kids aged 10-13 on Roblox. "
                f"Description: {concept.get('description', concept.get('tagline', ''))}. "
                f"Find specific: characters, visual elements, memes, catchphrases, color palettes, "
                f"and competitor games. Output JSON."
            ),
            "context": f"We're building a {concept.get('game_type', 'obby')} game based on this trend.",
        },
        "theme_designer": {
            "prompt": (
                f"Design a game theme for '{concept.get('name', '')}' "
                f"({concept.get('game_type', 'obby')} game for kids 10-13). "
                f"Create 8 themed sections with specific colors (RGB 0-1), materials, and decoration notes. "
                f"Output JSON with game_title and sections array."
            ),
            "context": f"Trend: {concept.get('trend_connection', '')}. Tagline: {concept.get('tagline', '')}",
        },
        "quality_reviewer": {
            "prompt": (
                f"Pre-review the concept for '{concept.get('name', '')}'. "
                f"Score: playability, theme_consistency, visual_quality, fun_factor, monetization_ready. "
                f"Each 1-10 with notes. Output JSON."
            ),
            "context": f"Game type: {concept.get('game_type', 'obby')}. Description: {concept.get('description', '')}",
        },
    }

    dispatched_tasks = {}  # role -> task_id

    for role, task_data in roles_to_dispatch.items():
        if registry.has_online_agent_for_role(role):
            task_id = registry.post_work(role, task_data, game_id=game_id)
            dispatched_tasks[role] = task_id
            await log(
                f"Dispatched {role} task to community agents ({task_id})",
                LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id
            )

    if not dispatched_tasks:
        await log(
            "No community agents online — building with built-in AI only",
            LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id
        )
        return agent_results

    await log(
        f"Waiting for {len(dispatched_tasks)} community agent(s) to respond...",
        LogLevel.INFO, EventType.GAME_BUILD, game_id=game_id
    )

    # Wait up to 90 seconds for agent results (they're working in parallel)
    for attempt in range(18):  # 18 * 5s = 90s max wait
        await asyncio.sleep(5)
        all_done = True
        for role, task_id in dispatched_tasks.items():
            result = registry.get_work_result(task_id)
            if result:
                if role not in agent_results:
                    agent_results[role] = result
                    await log(
                        f"Got result from community {role} agent!",
                        LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id
                    )
            else:
                all_done = False
        if all_done:
            break

    roles_got = list(agent_results.keys())
    roles_missed = [r for r in dispatched_tasks if r not in agent_results]
    if roles_got:
        await log(
            f"Community agents contributed: {', '.join(roles_got)}",
            LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id
        )
    if roles_missed:
        await log(
            f"Timed out waiting for: {', '.join(roles_missed)} — continuing without them",
            LogLevel.WARNING, EventType.GAME_BUILD, game_id=game_id
        )

    return agent_results


async def build_game_from_concept(concept: dict, auto_fix: bool = True) -> dict:
    """
    Build a complete game from a trend concept.
    This is the main pipeline: concept → plan → scripts → .rbxlx
    Community agents are dispatched in parallel if any are online.
    """
    game_result = {
        "status": GameStatus.QUEUED,
        "concept": concept,
        "plan": None,
        "scripts": {},
        "output_file": None,
        "errors": [],
        "started_at": datetime.now().isoformat(),
    }

    try:
        # === PHASE 0: Dispatch to community agents (runs in parallel with Phase 1) ===
        game_id_temp = f"build_{datetime.now().strftime('%H%M%S')}"
        agent_task = asyncio.create_task(
            _dispatch_to_community_agents(concept, {}, game_id_temp)
        )

        # === PHASE 1: Planning ===
        _pipeline_state["status"] = PipelineStatus.PLANNING
        game_result["status"] = GameStatus.PLANNING

        await log(
            f"Pipeline Phase 1: Creating game plan for '{concept['name']}'",
            LogLevel.STEP, EventType.PLAN_CREATE
        )

        plan = await create_game_plan(concept)
        game_result["plan"] = plan
        game_result["game_id"] = plan["game_id"]
        _pipeline_state["current_game"] = plan["game_id"]

        await log(
            f"Pipeline Phase 1 complete: Plan created with {len(plan.get('scripts_needed', []))} scripts",
            LogLevel.SUCCESS, EventType.PLAN_CREATE, game_id=plan["game_id"]
        )

        # === PHASE 2: Script Generation ===
        _pipeline_state["status"] = PipelineStatus.GENERATING
        game_result["status"] = GameStatus.BUILDING

        game_type = plan.get("game_type", "obby")

        if game_type == "obby":
            # Obby games use hardcoded scripts from obby_scripts.py
            # The rbxlx_builder handles script generation internally
            await log(
                "Pipeline Phase 2: Obby game - using pre-built scripts (no API calls needed)",
                LogLevel.STEP, EventType.GAME_BUILD, game_id=plan["game_id"]
            )
            scripts = {}  # Empty - rbxlx_builder will use obby_scripts.py
        else:
            await log(
                f"Pipeline Phase 2: Generating Lua scripts via Claude...",
                LogLevel.STEP, EventType.GAME_BUILD, game_id=plan["game_id"]
            )
            scripts = await generate_all_scripts(plan)

        if scripts:
            game_result["scripts"] = {name: f"{len(code)} chars" for name, code in scripts.items()}
            _pipeline_state["stats"]["total_scripts_generated"] += len(scripts)
            await log(
                f"Pipeline Phase 2 complete: Generated {len(scripts)} scripts",
                LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=plan["game_id"]
            )
        else:
            await log(
                "Pipeline Phase 2 complete: Using hardcoded scripts",
                LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=plan["game_id"]
            )

        # === Collect agent results (from Phase 0) ===
        agent_results = {}
        try:
            agent_results = await asyncio.wait_for(agent_task, timeout=10)
        except asyncio.TimeoutError:
            await log("Agent results timed out, continuing without them",
                      LogLevel.WARNING, EventType.GAME_BUILD, game_id=plan["game_id"])
        except Exception as e:
            await log(f"Agent dispatch error (non-fatal): {e}",
                      LogLevel.WARNING, EventType.GAME_BUILD, game_id=plan["game_id"])

        # Merge agent theme data into plan if we got it
        if "theme_designer" in agent_results:
            plan["agent_theme_data"] = agent_results["theme_designer"]
            await log("Applying community theme designer data to build!",
                      LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=plan["game_id"])
        if "trend_researcher" in agent_results:
            plan["agent_trend_data"] = agent_results["trend_researcher"]
            await log("Enriching build with community trend research!",
                      LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=plan["game_id"])
        if "quality_reviewer" in agent_results:
            game_result["agent_quality_review"] = agent_results["quality_reviewer"]
            await log("Pre-build quality review received from community!",
                      LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=plan["game_id"])

        game_result["agent_contributions"] = list(agent_results.keys())

        # === PHASE 3: Build RBXLX ===
        _pipeline_state["status"] = PipelineStatus.BUILDING

        await log(
            f"Pipeline Phase 3: Building .rbxlx game file...",
            LogLevel.STEP, EventType.GAME_BUILD, game_id=plan["game_id"]
        )

        output_file = await build_rbxlx(plan, scripts if scripts else None)
        game_result["output_file"] = str(output_file)

        # === PHASE 4: Validation ===
        _pipeline_state["status"] = PipelineStatus.VALIDATING
        game_result["status"] = GameStatus.VALIDATING

        await log(
            f"Pipeline Phase 4: Validating game file...",
            LogLevel.STEP, EventType.GAME_BUILD, game_id=plan["game_id"]
        )

        validation = await _validate_game(output_file, plan, scripts)

        if validation["valid"]:
            game_result["status"] = GameStatus.READY
            game_result["validation"] = validation

            await log(
                f"Game READY: '{plan.get('name', 'Unknown')}' saved to {output_file}",
                LogLevel.SUCCESS, EventType.GAME_COMPLETE, game_id=plan["game_id"],
                data={
                    "file": str(output_file),
                    "scripts": len(scripts),
                    "name": plan.get("name"),
                    "roblox_title": plan.get("roblox_title"),
                }
            )
        else:
            if auto_fix:
                await log(
                    f"Validation issues found, attempting auto-fix...",
                    LogLevel.WARNING, EventType.GAME_BUILD, game_id=plan["game_id"],
                    data={"issues": validation.get("issues", [])}
                )
                _pipeline_state["status"] = PipelineStatus.FIXING
                # Attempt to fix by regenerating problematic scripts
                fixed = await _auto_fix_game(plan, scripts, validation)
                if fixed:
                    output_file = await build_rbxlx(plan, fixed)
                    game_result["output_file"] = str(output_file)
                    game_result["status"] = GameStatus.READY
                    game_result["fix_applied"] = True
                    await log("Auto-fix successful!", LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=plan["game_id"])
                else:
                    game_result["status"] = GameStatus.ERROR
                    game_result["errors"].append("Auto-fix failed - manual review needed")
                    await log(
                        f"CRITICAL: Auto-fix failed for '{plan.get('name')}'. Manual review needed.",
                        LogLevel.CRITICAL, EventType.GAME_ERROR, game_id=plan["game_id"],
                        data={"issues": validation.get("issues", [])}
                    )
            else:
                game_result["status"] = GameStatus.ERROR
                game_result["validation"] = validation

        # Update stats
        _pipeline_state["stats"]["total_games_built"] += 1
        _pipeline_state["games_today"] += 1
        _pipeline_state["completed_games"].append({
            "game_id": plan["game_id"],
            "name": plan.get("name", "Unknown"),
            "status": game_result["status"].value if isinstance(game_result["status"], GameStatus) else game_result["status"],
            "file": str(output_file),
            "completed_at": datetime.now().isoformat()
        })
        _pipeline_state["current_game"] = None
        _pipeline_state["status"] = PipelineStatus.IDLE

        # Save to log
        await _save_pipeline_log(game_result)

        game_result["completed_at"] = datetime.now().isoformat()
        return game_result

    except Exception as e:
        error_msg = f"Pipeline error: {str(e)}"
        game_result["status"] = GameStatus.ERROR
        game_result["errors"].append(error_msg)
        _pipeline_state["status"] = PipelineStatus.ERROR
        _pipeline_state["current_game"] = None
        _pipeline_state["errors"].append({
            "time": datetime.now().isoformat(),
            "error": error_msg,
            "traceback": traceback.format_exc()
        })

        await log(
            f"CRITICAL: Pipeline failed for '{concept.get('name', 'Unknown')}': {e}",
            LogLevel.CRITICAL, EventType.GAME_ERROR,
            data={"traceback": traceback.format_exc()}
        )

        await _save_pipeline_log(game_result)
        return game_result


async def run_full_pipeline(concept_index: int = 0) -> dict:
    """
    Run the full pipeline: scan trends → pick best concept → build game.
    concept_index: which concept to build (0 = best, 1 = second, 2 = third)
    """
    # Check daily limit
    if _pipeline_state["games_today"] >= MAX_GAMES_PER_DAY:
        await log(f"Daily limit reached ({MAX_GAMES_PER_DAY} games)", LogLevel.WARNING, EventType.SYSTEM)
        return {"error": "Daily game limit reached"}

    # Get or scan trends
    trends = await get_cached_trends()
    if not trends:
        trends = await run_trend_scan()

    concepts = trends.get("analysis", {}).get("game_concepts", [])
    if not concepts:
        await log("No game concepts found in trends!", LogLevel.ERROR, EventType.TREND_SCAN)
        return {"error": "No concepts found"}

    # Pick concept
    idx = min(concept_index, len(concepts) - 1)
    concept = concepts[idx]

    await log(
        f"Selected concept #{idx + 1}: {concept['name']}",
        LogLevel.INFO, EventType.SYSTEM,
        data={"name": concept["name"], "viral_score": concept.get("viral_score")}
    )

    # Build the game
    return await build_game_from_concept(concept)


async def build_all_daily_games() -> list[dict]:
    """Build all 3 daily games from the latest trend scan."""
    trends = await run_trend_scan()
    concepts = trends.get("analysis", {}).get("game_concepts", [])

    results = []
    for i, concept in enumerate(concepts[:MAX_GAMES_PER_DAY]):
        await log(f"Building game {i + 1}/{min(len(concepts), MAX_GAMES_PER_DAY)}: {concept['name']}", LogLevel.STEP, EventType.SYSTEM)
        result = await build_game_from_concept(concept)
        results.append(result)
        # Brief pause between games
        if i < len(concepts) - 1:
            await asyncio.sleep(2)

    return results


async def _validate_game(output_file: Path, plan: dict, scripts: dict) -> dict:
    """Validate the generated game file."""
    issues = []

    # Check file exists and has content
    if not output_file.exists():
        issues.append("Output file does not exist")
        return {"valid": False, "issues": issues}

    file_size = output_file.stat().st_size
    if file_size < 1000:
        issues.append(f"File too small ({file_size} bytes) - likely incomplete")

    # Check XML is valid
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(output_file)
        root = tree.getroot()

        # Count elements
        items = root.findall(".//Item")
        scripts_found = [i for i in items if i.get("class") in ("Script", "LocalScript", "ModuleScript")]
        parts_found = [i for i in items if i.get("class") in ("Part", "SpawnLocation")]

        if len(scripts_found) < 3:
            issues.append(f"Only {len(scripts_found)} scripts found - expected at least 3")
        if len(parts_found) < 5:
            issues.append(f"Only {len(parts_found)} parts found - world seems empty")

    except ET.ParseError as e:
        issues.append(f"XML parse error: {str(e)}")

    # Check each script has content
    for name, code in scripts.items():
        if len(code) < 50:
            issues.append(f"Script '{name}' is too short ({len(code)} chars)")
        if "TODO" in code or "placeholder" in code.lower():
            issues.append(f"Script '{name}' contains placeholder code")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "file_size_kb": file_size // 1024 if output_file.exists() else 0,
        "scripts_count": len(scripts),
        "parts_count": len(parts_found) if 'parts_found' in dir() else 0
    }


async def _auto_fix_game(plan: dict, scripts: dict, validation: dict) -> Optional[dict]:
    """Attempt to automatically fix game issues."""
    from backend.utils.claude_client import ask_claude

    issues = validation.get("issues", [])

    for issue in issues:
        if "too short" in issue or "placeholder" in issue:
            # Identify which script has the issue
            for script_name in scripts:
                if script_name in issue:
                    await log(f"Re-generating script: {script_name}", LogLevel.STEP, EventType.GAME_BUILD, game_id=plan.get("game_id"))
                    from backend.generators.lua_generator import _generate_single_script
                    script_info = None
                    for s in plan.get("scripts_needed", []):
                        if s["name"] == script_name:
                            script_info = s
                            break
                    if script_info:
                        new_code = await _generate_single_script(plan, script_info, scripts)
                        scripts[script_name] = new_code

    return scripts


async def _save_pipeline_log(game_result: dict):
    """Save pipeline execution log."""
    log_data = []
    if PIPELINE_LOG.exists():
        try:
            with open(PIPELINE_LOG) as f:
                log_data = json.load(f)
        except Exception:
            log_data = []

    # Serialize status enums
    serializable = {}
    for k, v in game_result.items():
        if isinstance(v, (GameStatus, PipelineStatus)):
            serializable[k] = v.value
        else:
            serializable[k] = v

    log_data.append(serializable)
    log_data = log_data[-100:]  # Keep last 100

    with open(PIPELINE_LOG, 'w') as f:
        json.dump(log_data, f, indent=2, default=str)
