"""Clankerblox API Server - FastAPI backend with WebSocket for live updates"""
import json
import asyncio
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from backend.config import API_HOST, API_PORT, GAMES_OUTPUT_DIR, DATA_DIR
from backend.utils.logger import subscribe, unsubscribe, get_history, log, LogLevel, EventType
from backend.core.pipeline import (
    get_state, run_trend_scan, build_game_from_concept,
    run_full_pipeline, build_all_daily_games, PipelineStatus
)
from backend.analyzers.trend_analyzer import get_cached_trends, get_trend_history
from backend.generators.game_planner import list_plans, get_plan


# === WebSocket Manager ===
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

        # Register as event subscriber
        async def send_event(event: dict):
            try:
                await websocket.send_json(event)
            except Exception:
                pass

        websocket._event_callback = send_event
        subscribe(send_event)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if hasattr(websocket, '_event_callback'):
            unsubscribe(websocket._event_callback)

    async def broadcast(self, message: dict):
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)


manager = ConnectionManager()


# === App Setup ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    await log("Clankerblox API server starting...", LogLevel.SUCCESS, EventType.SYSTEM)
    yield
    await log("Clankerblox API server shutting down.", LogLevel.INFO, EventType.SYSTEM)


app = FastAPI(
    title="Clankerblox",
    description="AI-Powered Roblox Game Builder",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Pydantic Models ===
class BuildRequest(BaseModel):
    concept_index: int = 0

class CustomBuildRequest(BaseModel):
    name: str
    game_type: str
    description: str
    tagline: Optional[str] = ""
    viral_score: Optional[int] = 7
    revenue_score: Optional[int] = 7


# === WebSocket Endpoint ===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send event history on connect
        history = get_history()
        await websocket.send_json({"type": "history", "events": history[-50:]})

        # Send current state
        state = get_state()
        await websocket.send_json({"type": "state", "data": state})

        while True:
            data = await websocket.receive_text()
            # Handle ping/pong to keep connection alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# === API Endpoints ===

@app.get("/api/status")
async def get_status():
    """Get current pipeline status."""
    return {
        "status": "ok",
        "pipeline": get_state(),
        "server_time": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/trends/scan")
async def trigger_trend_scan(background_tasks: BackgroundTasks):
    """Trigger a trend analysis scan."""
    state = get_state()
    if state["status"] != PipelineStatus.IDLE.value and state["status"] != "idle":
        raise HTTPException(400, "Pipeline is busy. Wait for current operation to finish.")

    background_tasks.add_task(_run_trend_scan_bg)
    return {"message": "Trend scan started", "status": "scanning"}


async def _run_trend_scan_bg():
    try:
        await run_trend_scan()
    except Exception as e:
        await log(f"Background trend scan failed: {e}", LogLevel.ERROR, EventType.TREND_SCAN)


@app.get("/api/trends/latest")
async def get_latest_trends():
    """Get the latest trend analysis results."""
    trends = await get_cached_trends()
    if not trends:
        raise HTTPException(404, "No trend analysis found. Run a scan first.")
    return trends


@app.get("/api/trends/history")
async def get_trends_history():
    """Get trend analysis history."""
    history = await get_trend_history()
    return {"history": history, "total": len(history)}


@app.post("/api/build/single")
async def build_single_game(request: BuildRequest, background_tasks: BackgroundTasks):
    """Build a single game from the latest trend analysis."""
    state = get_state()
    if state["status"] != PipelineStatus.IDLE.value and state["status"] != "idle":
        raise HTTPException(400, "Pipeline is busy.")

    background_tasks.add_task(_run_build_bg, request.concept_index)
    return {"message": f"Building game from concept #{request.concept_index + 1}", "status": "building"}


async def _run_build_bg(concept_index: int):
    try:
        await run_full_pipeline(concept_index)
    except Exception as e:
        await log(f"Background build failed: {e}", LogLevel.ERROR, EventType.GAME_ERROR)


@app.post("/api/build/all")
async def build_all_games(background_tasks: BackgroundTasks):
    """Build all 3 daily games."""
    state = get_state()
    if state["status"] != PipelineStatus.IDLE.value and state["status"] != "idle":
        raise HTTPException(400, "Pipeline is busy.")

    background_tasks.add_task(_run_build_all_bg)
    return {"message": "Building all daily games", "status": "building"}


async def _run_build_all_bg():
    try:
        await build_all_daily_games()
    except Exception as e:
        await log(f"Background build-all failed: {e}", LogLevel.ERROR, EventType.GAME_ERROR)


@app.post("/api/build/custom")
async def build_custom_game(request: CustomBuildRequest, background_tasks: BackgroundTasks):
    """Build a custom game from user-provided concept."""
    state = get_state()
    if state["status"] != PipelineStatus.IDLE.value and state["status"] != "idle":
        raise HTTPException(400, "Pipeline is busy.")

    concept = {
        "name": request.name,
        "game_type": request.game_type,
        "tagline": request.tagline or "",
        "description": request.description,
        "core_loop": request.description,
        "viral_score": request.viral_score,
        "revenue_score": request.revenue_score,
        "trend_connection": "Custom user concept",
        "hooks": [],
        "monetization": [],
        "roblox_title": request.name,
        "roblox_description": request.description,
        "keywords": []
    }

    background_tasks.add_task(_run_custom_build_bg, concept)
    return {"message": f"Building custom game: {request.name}", "status": "building"}


async def _run_custom_build_bg(concept: dict):
    try:
        await build_game_from_concept(concept)
    except Exception as e:
        await log(f"Background custom build failed: {e}", LogLevel.ERROR, EventType.GAME_ERROR)


@app.get("/api/games")
async def list_games():
    """List all built games."""
    games = []
    if GAMES_OUTPUT_DIR.exists():
        for game_dir in sorted(GAMES_OUTPUT_DIR.iterdir(), reverse=True):
            if game_dir.is_dir():
                info_file = game_dir / "game_info.json"
                if info_file.exists():
                    try:
                        with open(info_file) as f:
                            info = json.load(f)
                            info["folder"] = str(game_dir)
                            games.append(info)
                    except Exception:
                        continue
    return {"games": games, "total": len(games)}


@app.get("/api/games/{game_id}")
async def get_game_detail(game_id: str):
    """Get detailed information about a specific game."""
    plan = await get_plan(game_id)
    if not plan:
        raise HTTPException(404, f"Game {game_id} not found")

    # Find the output folder
    game_dir = None
    if GAMES_OUTPUT_DIR.exists():
        for d in GAMES_OUTPUT_DIR.iterdir():
            info_file = d / "game_info.json"
            if info_file.exists():
                with open(info_file) as f:
                    info = json.load(f)
                    if info.get("game_id") == game_id:
                        game_dir = d
                        break

    scripts = {}
    if game_dir:
        scripts_dir = game_dir / "scripts"
        if scripts_dir.exists():
            for lua_file in scripts_dir.glob("*.lua"):
                scripts[lua_file.stem] = lua_file.read_text(encoding='utf-8')

    return {
        "plan": plan,
        "scripts": scripts,
        "folder": str(game_dir) if game_dir else None
    }


@app.get("/api/plans")
async def list_all_plans():
    """List all game plans."""
    plans = await list_plans()
    return {"plans": plans, "total": len(plans)}


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent event logs."""
    history = get_history()
    return {"logs": history[-limit:], "total": len(history)}


@app.get("/api/stats")
async def get_stats():
    """Get overall statistics."""
    state = get_state()
    games_list = []
    if GAMES_OUTPUT_DIR.exists():
        for d in GAMES_OUTPUT_DIR.iterdir():
            if d.is_dir() and (d / "game_info.json").exists():
                games_list.append(d.name)

    return {
        "pipeline": state["stats"],
        "games_built": len(games_list),
        "games_today": state["games_today"],
        "last_scan": state["last_scan"],
        "status": state["status"],
        "errors_count": len(state["errors"]),
    }


# ============================================================
# COMMUNITY AGENT ENDPOINTS
# ============================================================

from backend.agents.registry import get_registry, AGENT_ROLES

class AgentRegisterRequest(BaseModel):
    name: str                       # Agent display name
    role: str                       # One of: trend_researcher, theme_designer, etc.
    owner: str                      # Your name/handle
    solana_wallet: Optional[str] = ""   # For reward airdrops
    model_info: Optional[str] = ""      # What AI model you use

class AgentSubmitRequest(BaseModel):
    agent_id: str
    task_id: str
    result: dict


@app.get("/api/agents/roles")
async def get_agent_roles():
    """List available agent roles that community members can fill."""
    return {"roles": AGENT_ROLES}


@app.post("/api/agents/register")
async def register_agent(req: AgentRegisterRequest):
    """Register a new community agent.

    Returns an agent_id and api_key. SAVE YOUR API KEY — it's only shown once!
    Use agent_id + api_key for all subsequent calls.
    """
    registry = get_registry()
    result = registry.register_agent(
        name=req.name,
        role=req.role,
        owner=req.owner,
        solana_wallet=req.solana_wallet,
        model_info=req.model_info,
    )

    if "error" in result:
        raise HTTPException(400, result["error"])

    await log(
        f"New community agent registered: {req.name} ({req.role}) by {req.owner}",
        LogLevel.SUCCESS, EventType.SYSTEM,
    )
    return result


@app.post("/api/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    """Send heartbeat to stay online. Call every 30 seconds."""
    registry = get_registry()
    result = registry.heartbeat(agent_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/api/agents/{agent_id}/work")
async def get_agent_work(agent_id: str):
    """Check for available work. If work exists, claims it automatically.

    Poll this every 5-10 seconds. Returns task details when work is available,
    or {"status": "no_work"} when there's nothing to do.
    """
    registry = get_registry()

    # Also count as heartbeat
    registry.heartbeat(agent_id)

    work = registry.claim_work(agent_id)
    if work:
        await log(
            f"Agent {agent_id} claimed task {work['task_id']} ({work['role']})",
            LogLevel.INFO, EventType.GAME_BUILD,
        )
        return work

    return {"status": "no_work", "message": "No tasks available right now. Keep polling!"}


@app.post("/api/agents/submit")
async def submit_agent_work(req: AgentSubmitRequest):
    """Submit completed work for a claimed task.

    Include the full result dict that the task requested.
    You'll earn reward points based on your role.
    """
    registry = get_registry()
    result = registry.submit_work(req.agent_id, req.task_id, req.result)

    if "error" in result:
        raise HTTPException(400, result["error"])

    await log(
        f"Agent {req.agent_id} completed task {req.task_id} (+{result['reward_earned']} points)",
        LogLevel.SUCCESS, EventType.GAME_BUILD,
    )
    return result


@app.get("/api/agents/online")
async def get_online_agents():
    """Get all currently online community agents."""
    registry = get_registry()
    agents = registry.get_online_agents()
    return {"agents": agents, "count": len(agents)}


@app.get("/api/agents/all")
async def get_all_agents():
    """Get all registered agents (online and offline)."""
    registry = get_registry()
    return {"agents": registry.get_all_agents()}


@app.get("/api/agents/stats")
async def get_agent_stats():
    """Get agent network statistics for the dashboard."""
    registry = get_registry()
    return registry.get_stats()


@app.get("/api/agents/leaderboard")
async def get_agent_leaderboard():
    """Get top agents by rewards earned."""
    registry = get_registry()
    agents = registry.get_all_agents()
    # Sort by rewards descending
    agents.sort(key=lambda a: a.get("rewards", 0), reverse=True)
    return {"leaderboard": agents[:20]}


# ============================================================
# FILE SERVING — Let community download agent_worker.py directly
# ============================================================

from fastapi.responses import FileResponse, PlainTextResponse

@app.get("/agent_worker.py")
async def download_agent_worker():
    """Download the agent worker script. Community one-liner uses this."""
    worker_path = Path(__file__).resolve().parent.parent.parent / "agent_worker.py"
    if worker_path.exists():
        return FileResponse(worker_path, filename="agent_worker.py", media_type="text/x-python")
    raise HTTPException(404, "agent_worker.py not found")


@app.get("/install")
async def get_install_instructions():
    """Show install one-liner for community agents."""
    return PlainTextResponse(
        "# Clankerblox Agent — One-liner install (PowerShell)\n"
        "# 1. Get a FREE Gemini API key: https://aistudio.google.com/apikey\n"
        "# 2. Paste this in PowerShell:\n\n"
        'pip install httpx google-genai; '
        'python -c "import urllib.request; '
        "urllib.request.urlretrieve('http://57.129.44.62:8000/agent_worker.py','agent_worker.py')\"; "
        "python agent_worker.py\n"
    )


@app.get("/api/games/{game_id}/download")
async def download_game_file(game_id: str):
    """Download the .rbxlx file for a built game."""
    if GAMES_OUTPUT_DIR.exists():
        for d in GAMES_OUTPUT_DIR.iterdir():
            if d.is_dir():
                info_file = d / "game_info.json"
                if info_file.exists():
                    with open(info_file) as f:
                        info = json.load(f)
                        if info.get("game_id") == game_id:
                            # Find the .rbxlx file
                            for rbxlx in d.glob("*.rbxlx"):
                                return FileResponse(
                                    rbxlx,
                                    filename=rbxlx.name,
                                    media_type="application/octet-stream"
                                )
    raise HTTPException(404, f"Game file not found for {game_id}")


def start_server():
    """Start the API server."""
    import uvicorn
    uvicorn.run(
        "backend.api.server:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
