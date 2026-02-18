"""Community Agent Registry — Manages connected agents from the community.

Agents connect via HTTP, register their capabilities, send heartbeats,
and pick up work when a game build needs them. They get reward points
tracked against their Solana wallet for future airdrops.

Architecture:
  - Agents poll /api/agents/work for available tasks
  - When a task is available, they claim it and submit results
  - Heartbeat every 30s keeps them "online"
  - Wallet + reward points tracked in agents_registry.json

This is a PULL-based system (agents poll for work) rather than PUSH
(we call their API). This is simpler, works behind NATs/firewalls,
and doesn't require agents to expose ports.
"""

import time
import json
import uuid
import asyncio
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime

from backend.config import DATA_DIR
from backend.utils.logger import log, LogLevel, EventType

# ============================================================
# DATA STORAGE
# ============================================================

REGISTRY_FILE = DATA_DIR / "agents_registry.json"
WORK_QUEUE_FILE = DATA_DIR / "agent_work_queue.json"

# Agent goes offline after 60s without heartbeat
HEARTBEAT_TIMEOUT = 60

# Available agent roles that community can fill
AGENT_ROLES = {
    "trend_researcher": {
        "name": "Trend Researcher",
        "description": "Researches what kids are watching/playing right now",
        "difficulty": "easy",
        "reward_per_task": 10,
    },
    "theme_designer": {
        "name": "Theme Designer",
        "description": "Turns trends into concrete game theme specifications",
        "difficulty": "medium",
        "reward_per_task": 15,
    },
    "world_architect": {
        "name": "World Architect",
        "description": "Designs physics-valid level layouts",
        "difficulty": "hard",
        "reward_per_task": 25,
    },
    "quality_reviewer": {
        "name": "Quality Reviewer",
        "description": "Reviews and scores completed game builds",
        "difficulty": "medium",
        "reward_per_task": 15,
    },
    "script_writer": {
        "name": "Script Writer",
        "description": "Writes or improves Roblox Lua scripts",
        "difficulty": "hard",
        "reward_per_task": 30,
    },
}


# ============================================================
# AGENT REGISTRY
# ============================================================

@dataclass
class RegisteredAgent:
    """A community agent that's registered to help build games."""
    agent_id: str
    name: str
    role: str                      # One of AGENT_ROLES keys
    owner: str                     # Display name
    solana_wallet: str = ""        # For future reward airdrops
    api_key_hash: str = ""         # For auth (hash of their key)
    model_info: str = ""           # What AI model they use (optional)
    registered_at: str = ""
    last_heartbeat: float = 0
    total_tasks_completed: int = 0
    total_rewards: int = 0         # Reward points earned
    is_online: bool = False
    current_task_id: str = ""      # Task they're working on


class AgentRegistry:
    """Manages community agent registration, heartbeats, and work distribution."""

    def __init__(self):
        self._agents: dict[str, RegisteredAgent] = {}
        self._work_queue: list[dict] = []
        self._completed_work: list[dict] = []
        self._load()

    def _load(self):
        """Load registry from disk."""
        if REGISTRY_FILE.exists():
            try:
                data = json.loads(REGISTRY_FILE.read_text())
                for agent_data in data.get("agents", []):
                    agent = RegisteredAgent(**agent_data)
                    agent.is_online = False  # Start offline, need heartbeat
                    self._agents[agent.agent_id] = agent
            except Exception as e:
                print(f"Warning: Could not load agent registry: {e}")

        if WORK_QUEUE_FILE.exists():
            try:
                data = json.loads(WORK_QUEUE_FILE.read_text())
                self._work_queue = data.get("queue", [])
                self._completed_work = data.get("completed", [])
            except Exception:
                pass

    def _save(self):
        """Persist registry to disk."""
        data = {
            "agents": [asdict(a) for a in self._agents.values()],
            "last_updated": datetime.now().isoformat(),
        }
        REGISTRY_FILE.write_text(json.dumps(data, indent=2))

    def _save_work(self):
        """Persist work queue to disk."""
        data = {
            "queue": self._work_queue[-100:],  # Keep last 100
            "completed": self._completed_work[-200:],  # Keep last 200
        }
        WORK_QUEUE_FILE.write_text(json.dumps(data, indent=2))

    # ---- Registration ----

    def register_agent(self, name: str, role: str, owner: str,
                        solana_wallet: str = "", model_info: str = "") -> dict:
        """Register a new community agent. Returns agent_id and api_key."""
        if role not in AGENT_ROLES:
            return {"error": f"Invalid role. Choose from: {list(AGENT_ROLES.keys())}"}

        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        api_key = f"cb_{uuid.uuid4().hex}"  # Simple API key

        agent = RegisteredAgent(
            agent_id=agent_id,
            name=name,
            role=role,
            owner=owner,
            solana_wallet=solana_wallet,
            api_key_hash=str(hash(api_key)),
            model_info=model_info,
            registered_at=datetime.now().isoformat(),
            last_heartbeat=time.time(),
            is_online=True,
        )

        self._agents[agent_id] = agent
        self._save()

        return {
            "agent_id": agent_id,
            "api_key": api_key,  # Only returned once at registration!
            "role": role,
            "role_info": AGENT_ROLES[role],
            "message": f"Welcome {name}! You're registered as a {AGENT_ROLES[role]['name']}. "
                       f"Keep your api_key safe — it's shown only once.",
        }

    # ---- Heartbeat ----

    def heartbeat(self, agent_id: str, api_key: str = "") -> dict:
        """Agent sends heartbeat to stay online. Call every 30s."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        agent.last_heartbeat = time.time()
        agent.is_online = True
        self._save()

        return {
            "status": "ok",
            "agent_id": agent_id,
            "is_online": True,
            "total_rewards": agent.total_rewards,
            "tasks_completed": agent.total_tasks_completed,
            "has_work": any(w["status"] == "pending" and w["role"] == agent.role
                           for w in self._work_queue),
        }

    # ---- Online Status ----

    def _refresh_online_status(self):
        """Mark agents as offline if heartbeat expired."""
        now = time.time()
        for agent in self._agents.values():
            if now - agent.last_heartbeat > HEARTBEAT_TIMEOUT:
                agent.is_online = False

    def get_online_agents(self) -> list[dict]:
        """Get all currently online agents."""
        self._refresh_online_status()
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role,
                "role_name": AGENT_ROLES.get(a.role, {}).get("name", a.role),
                "owner": a.owner,
                "model_info": a.model_info,
                "tasks_completed": a.total_tasks_completed,
                "rewards": a.total_rewards,
                "is_online": a.is_online,
                "working_on": a.current_task_id if a.current_task_id else None,
            }
            for a in self._agents.values()
            if a.is_online
        ]

    def get_all_agents(self) -> list[dict]:
        """Get all registered agents (online and offline)."""
        self._refresh_online_status()
        return [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "role": a.role,
                "role_name": AGENT_ROLES.get(a.role, {}).get("name", a.role),
                "owner": a.owner,
                "solana_wallet": a.solana_wallet[:8] + "..." if a.solana_wallet else "",
                "tasks_completed": a.total_tasks_completed,
                "rewards": a.total_rewards,
                "is_online": a.is_online,
                "registered_at": a.registered_at,
            }
            for a in self._agents.values()
        ]

    def get_stats(self) -> dict:
        """Get dashboard stats about agents."""
        self._refresh_online_status()
        online = [a for a in self._agents.values() if a.is_online]
        all_agents = list(self._agents.values())

        roles_online = {}
        for a in online:
            role = a.role
            roles_online[role] = roles_online.get(role, 0) + 1

        return {
            "total_registered": len(all_agents),
            "total_online": len(online),
            "roles_online": roles_online,
            "total_tasks_completed": sum(a.total_tasks_completed for a in all_agents),
            "total_rewards_distributed": sum(a.total_rewards for a in all_agents),
            "roles_available": AGENT_ROLES,
            "agents_online": [
                {"name": a.name, "role": AGENT_ROLES.get(a.role, {}).get("name", a.role),
                 "owner": a.owner}
                for a in online
            ],
        }

    # ---- Work Distribution ----

    def post_work(self, role: str, task_data: dict, game_id: str = "") -> str:
        """Post a work item for a specific role. Returns task_id."""
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        work_item = {
            "task_id": task_id,
            "role": role,
            "game_id": game_id,
            "task_data": task_data,
            "status": "pending",  # pending → claimed → completed / failed
            "created_at": datetime.now().isoformat(),
            "claimed_by": None,
            "claimed_at": None,
            "result": None,
            "completed_at": None,
        }
        self._work_queue.append(work_item)
        self._save_work()
        return task_id

    def claim_work(self, agent_id: str) -> Optional[dict]:
        """Agent claims the next available work item for their role.
        Returns task details or None if no work available."""
        agent = self._agents.get(agent_id)
        if not agent or not agent.is_online:
            return None

        for work in self._work_queue:
            if work["status"] == "pending" and work["role"] == agent.role:
                work["status"] = "claimed"
                work["claimed_by"] = agent_id
                work["claimed_at"] = datetime.now().isoformat()

                agent.current_task_id = work["task_id"]
                self._save()
                self._save_work()

                return {
                    "task_id": work["task_id"],
                    "role": work["role"],
                    "game_id": work["game_id"],
                    "task_data": work["task_data"],
                    "message": "Work claimed! Complete and submit via /api/agents/submit",
                }

        return None  # No work available

    def submit_work(self, agent_id: str, task_id: str, result: dict) -> dict:
        """Agent submits completed work. Awards reward points."""
        agent = self._agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        work = None
        for w in self._work_queue:
            if w["task_id"] == task_id:
                work = w
                break

        if not work:
            return {"error": "Task not found"}

        if work["claimed_by"] != agent_id:
            return {"error": "This task wasn't claimed by you"}

        # Complete the work
        work["status"] = "completed"
        work["result"] = result
        work["completed_at"] = datetime.now().isoformat()

        # Award points
        role_info = AGENT_ROLES.get(agent.role, {})
        reward = role_info.get("reward_per_task", 10)
        agent.total_tasks_completed += 1
        agent.total_rewards += reward
        agent.current_task_id = ""

        # Move to completed
        self._completed_work.append(work)
        self._work_queue = [w for w in self._work_queue if w["task_id"] != task_id]

        self._save()
        self._save_work()

        return {
            "status": "completed",
            "reward_earned": reward,
            "total_rewards": agent.total_rewards,
            "total_tasks": agent.total_tasks_completed,
            "message": f"Great work! +{reward} points. Total: {agent.total_rewards} points.",
        }

    def get_work_result(self, task_id: str) -> Optional[dict]:
        """Get the result of a completed task."""
        for w in self._completed_work:
            if w["task_id"] == task_id:
                return w.get("result")
        return None

    def has_online_agent_for_role(self, role: str) -> bool:
        """Check if there's an online community agent for a given role."""
        self._refresh_online_status()
        return any(a.is_online and a.role == role for a in self._agents.values())


# Singleton
_registry = None

def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
