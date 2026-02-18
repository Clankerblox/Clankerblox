"""Clankerblox Multi-Agent System

Specialized AI agents that collaborate to build high-quality Roblox games.
Each agent has a specific role, uses the cheapest model that works, and
passes structured work products to the next agent in the pipeline.

Agent roles:
  - TrendResearcher: Finds what kids are playing/watching RIGHT NOW
  - ThemeDesigner:   Turns trends into concrete game themes + visual specs
  - WorldArchitect:  Designs level layouts with physics-validated geometry
  - PhysicsValidator: Simulates player movement to catch impossible obbys
  - QualityReviewer: Final pass — checks everything works together

Cost strategy:
  - Gemini Flash for research, validation, review (~$0.10/MTok)
  - Claude for complex design + code generation (~$3/MTok)
  - Total per game: ~$0.20-0.50
"""

from backend.agents.base import Agent, AgentResult, run_pipeline
from backend.agents.game_agents import (
    TrendResearcherAgent,
    ThemeDesignerAgent,
    WorldArchitectAgent,
    PhysicsValidatorAgent,
    QualityReviewerAgent,
)
