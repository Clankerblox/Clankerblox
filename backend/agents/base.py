"""Agent Base Framework — Simple, no-framework multi-agent system.

Each Agent is a Python class with:
  - A role (system prompt describing what it does)
  - A preferred model (gemini-flash for cheap, claude for quality)
  - A run() method that takes input and returns structured output
  - Logging integration for the dashboard

Agents communicate through AgentResult objects — typed dicts that
carry structured data between pipeline stages.

No frameworks. No LangChain. No CrewAI. Just clean Python.
"""

import time
import json
import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from backend.utils.logger import log, LogLevel, EventType


class ModelTier(Enum):
    """Which AI model to use. Cheapest first."""
    GEMINI_FLASH = "gemini-flash"      # $0.10/MTok input — research, validation
    GEMINI_PRO = "gemini-pro"          # $1.25/MTok — moderate quality
    CLAUDE_HAIKU = "claude-haiku"      # $1.00/MTok — fast Claude
    CLAUDE_SONNET = "claude-sonnet"    # $3.00/MTok — high quality
    CLAUDE_OPUS = "claude-opus"        # $5.00/MTok — maximum quality


@dataclass
class AgentResult:
    """Structured output from an agent, passed to the next agent."""
    agent_name: str
    success: bool
    data: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    token_usage: dict = field(default_factory=dict)
    duration_ms: float = 0
    raw_response: str = ""

    def to_context(self) -> str:
        """Convert to a context string for the next agent's prompt."""
        parts = [f"=== Output from {self.agent_name} ==="]
        if self.errors:
            parts.append(f"ERRORS: {json.dumps(self.errors)}")
        if self.warnings:
            parts.append(f"WARNINGS: {json.dumps(self.warnings)}")
        parts.append(json.dumps(self.data, indent=2))
        return "\n".join(parts)


class Agent:
    """Base class for all Clankerblox agents.

    Subclasses must implement:
      - role: str — one-line description
      - system_prompt: str — detailed instructions
      - model_tier: ModelTier — which AI model to use
      - async process(input_data, context) -> dict — the actual work
    """

    role: str = "Generic Agent"
    system_prompt: str = ""
    model_tier: ModelTier = ModelTier.GEMINI_FLASH

    def __init__(self):
        self.name = self.__class__.__name__

    async def run(
        self,
        input_data: dict,
        context: list[AgentResult] = None,
        game_id: str = "unknown",
    ) -> AgentResult:
        """Execute the agent and return structured result.

        Args:
            input_data: Primary input for this agent
            context: Results from previous agents in the pipeline
            game_id: For logging/tracking
        """
        start = time.time()
        context = context or []

        await log(
            f"🤖 Agent [{self.name}] starting — {self.role}",
            LogLevel.STEP, EventType.GAME_BUILD, game_id=game_id,
        )

        try:
            data = await self.process(input_data, context)
            duration = (time.time() - start) * 1000

            result = AgentResult(
                agent_name=self.name,
                success=True,
                data=data,
                duration_ms=duration,
            )

            await log(
                f"✅ Agent [{self.name}] done in {duration:.0f}ms",
                LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id,
            )
            return result

        except Exception as e:
            duration = (time.time() - start) * 1000
            await log(
                f"❌ Agent [{self.name}] failed: {e}",
                LogLevel.ERROR, EventType.GAME_ERROR, game_id=game_id,
            )
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=[str(e)],
                duration_ms=duration,
            )

    async def process(self, input_data: dict, context: list[AgentResult]) -> dict:
        """Override this in subclasses. Returns structured data dict."""
        raise NotImplementedError

    async def ask_ai(self, prompt: str, system: str = None, as_json: bool = True) -> Any:
        """Call the appropriate AI model based on this agent's tier.

        Uses Gemini Flash for cheap tasks, Claude for quality tasks.
        Returns parsed JSON dict if as_json=True, else raw string.
        """
        sys = system or self.system_prompt

        if self.model_tier in (ModelTier.GEMINI_FLASH, ModelTier.GEMINI_PRO):
            from backend.utils.gemini_client import ask_gemini, ask_gemini_json
            if as_json:
                return await ask_gemini_json(prompt, sys)
            return await ask_gemini(prompt, sys)

        else:
            from backend.utils.claude_client import ask_claude, ask_claude_json
            if as_json:
                return await ask_claude_json(prompt, sys)
            return await ask_claude(prompt, sys)

    def _build_context_prompt(self, context: list[AgentResult]) -> str:
        """Build a context section from previous agent outputs."""
        if not context:
            return ""
        parts = ["\n--- PREVIOUS AGENT OUTPUTS ---"]
        for r in context:
            if r.success:
                parts.append(r.to_context())
        parts.append("--- END PREVIOUS OUTPUTS ---\n")
        return "\n".join(parts)


async def run_pipeline(
    agents: list[Agent],
    initial_input: dict,
    game_id: str = "unknown",
) -> list[AgentResult]:
    """Run a sequence of agents, passing each result to the next.

    Each agent receives:
      - The original input_data (initial_input)
      - A list of all previous AgentResults (context)

    Returns list of all AgentResults in order.
    """
    results = []
    total_start = time.time()

    await log(
        f"🚀 Pipeline starting with {len(agents)} agents: "
        + " → ".join(a.name for a in agents),
        LogLevel.STEP, EventType.GAME_BUILD, game_id=game_id,
    )

    for agent in agents:
        result = await agent.run(
            input_data=initial_input,
            context=results,
            game_id=game_id,
        )
        results.append(result)

        # If an agent fails, log but continue (next agent can try to work around it)
        if not result.success:
            await log(
                f"⚠️ Agent [{agent.name}] failed but pipeline continues...",
                LogLevel.WARNING, EventType.GAME_BUILD, game_id=game_id,
            )

    total_time = (time.time() - total_start) * 1000
    success_count = sum(1 for r in results if r.success)

    await log(
        f"🏁 Pipeline done: {success_count}/{len(agents)} agents succeeded, "
        f"total {total_time:.0f}ms",
        LogLevel.SUCCESS, EventType.GAME_BUILD, game_id=game_id,
    )

    return results


async def run_parallel(agents: list[Agent], input_data: dict,
                        context: list[AgentResult] = None,
                        game_id: str = "unknown") -> list[AgentResult]:
    """Run multiple agents in parallel (e.g., researcher + trend scout)."""
    tasks = [
        agent.run(input_data=input_data, context=context, game_id=game_id)
        for agent in agents
    ]
    return await asyncio.gather(*tasks)
