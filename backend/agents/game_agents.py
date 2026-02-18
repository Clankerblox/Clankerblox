"""Specialized Game-Building Agents for Clankerblox.

5 agents that collaborate to build high-quality Roblox games:

1. TrendResearcherAgent (Gemini Flash — cheap)
   - Searches what kids are watching/playing RIGHT NOW
   - Outputs: trend brief with characters, memes, visual style

2. ThemeDesignerAgent (Gemini Flash — cheap)
   - Turns trend brief into concrete game theme specifications
   - Outputs: section themes, color palettes, obstacle descriptions, themed text

3. WorldArchitectAgent (Claude — quality)
   - Takes theme spec and generates physics-valid level design
   - Outputs: section configs, difficulty curves, obstacle placement rules

4. PhysicsValidatorAgent (Gemini Flash — cheap)
   - Simulates player movement through generated geometry
   - Catches: impossible gaps, unreachable platforms, ground shortcuts
   - Outputs: pass/fail per stage + specific fix instructions

5. QualityReviewerAgent (Gemini Flash — cheap)
   - Final check on everything
   - Verifies scripts reference correct part names, theme consistency
   - Outputs: quality score + issues list
"""

import json
import math
from backend.agents.base import Agent, AgentResult, ModelTier
from backend.utils.logger import log, LogLevel, EventType


# ============================================================
# AGENT 1: TREND RESEARCHER
# ============================================================

class TrendResearcherAgent(Agent):
    """Researches what's trending for kids aged 10-13 RIGHT NOW.
    Uses Gemini Flash (cheapest model) since this is just research."""

    role = "Trend Research — finds what kids are into right now"
    model_tier = ModelTier.GEMINI_FLASH

    system_prompt = """You are a Roblox trend research specialist for kids aged 10-13.
Your job is to analyze trending topics and extract SPECIFIC, ACTIONABLE details for
game theming. Not vague buzzwords — actual characters, visual elements, memes, and
catchphrases that kids would recognize.

OUTPUT FORMAT (JSON):
{
    "trend_name": "Skibidi Toilet",
    "why_trending": "YouTube series with 65+ episodes, billions of views...",
    "key_characters": [
        {"name": "Skibidi Toilet", "description": "toilet with a human head sticking out, sings"},
        {"name": "Cameraman", "description": "humanoid with camera head, fights toilets"},
        {"name": "TV Man", "description": "humanoid with TV head, ally of cameraman"}
    ],
    "visual_elements": [
        "toilets everywhere (main enemy/obstacle)",
        "cameras, TV screens, speakers as allied characters",
        "industrial/bathroom environments",
        "glitch/corruption effects (purple/black)"
    ],
    "color_palette": {
        "primary": "white porcelain + chrome",
        "secondary": "bathroom tile blue/green",
        "accent": "neon purple (glitch/corruption)",
        "danger": "dark red (enemy toilets)"
    },
    "catchphrases": ["skibidi dop dop", "brrr skibidi"],
    "sound_vibes": "electronic/dubstep beats, toilet flush sounds",
    "meme_elements": ["toilet head popping up", "cameraman stance", "G-man upgrade"],
    "competitor_games": ["Skibi Defense", "Toilet Tower Defense"],
    "monetization_hooks": ["G-Man upgrade skin", "Titan Cameraman trail"]
}"""

    async def process(self, input_data: dict, context: list[AgentResult]) -> dict:
        """Research the trend specified in input_data."""
        trend_name = input_data.get("trend_name", input_data.get("name", "trending Roblox game"))
        game_type = input_data.get("game_type", "obby")

        prompt = f"""Research this trending topic for a Roblox {game_type} game: "{trend_name}"

What SPECIFIC visual elements, characters, memes, and aesthetics define this trend?
I need enough detail to theme an entire game around it — not generic descriptions,
but the actual recognizable elements that make kids go "OMG it's {trend_name}!"

If you don't have specific knowledge of this trend, research based on the name
and common Roblox game patterns. Focus on what would make a 10-13 year old
IMMEDIATELY recognize the theme when they join the game.

Return detailed JSON with all fields filled in."""

        result = await self.ask_ai(prompt, as_json=True)
        return result


# ============================================================
# AGENT 2: THEME DESIGNER
# ============================================================

class ThemeDesignerAgent(Agent):
    """Converts trend research into concrete game theme specifications.
    Maps abstract trend info to specific Roblox parts, colors, and sections."""

    role = "Theme Design — turns trends into game specs"
    model_tier = ModelTier.GEMINI_FLASH

    system_prompt = """You are a Roblox game theme designer for obby games.
You take trend research and convert it into CONCRETE specifications that a
procedural level generator can use.

You must specify for each section:
- Section name (themed, fun, recognizable)
- Color scheme (RGB values 0-1 for Roblox parts)
- Material (from Roblox materials: SmoothPlastic, Neon, Glass, Wood, Grass, Sand, Ice, Marble, Brick, Concrete, Metal, Foil, DiamondPlate, Granite, Slate, Cobblestone, Pebble, ForceField, Plastic, WoodPlanks, CorrodedMetal, Fabric)
- Obstacle descriptions (what do platforms look like in this theme?)
- Kill brick flavor text (what kills the player — lava? toxic waste? enemy attack?)
- Checkpoint flavor text
- Decoration elements (what non-gameplay elements sell the theme?)
- Stage sign text template

OUTPUT FORMAT (JSON):
{
    "game_title": "Skibidi Toilet Obby Rush",
    "game_description": "Escape the toilet invasion! Jump through 30 insane stages...",
    "sections": [
        {
            "index": 0,
            "name": "Toilet Sewers",
            "description": "Tutorial area — escape the underground sewers",
            "platform_color": [0.6, 0.65, 0.7],
            "platform_material": "Concrete",
            "accent_color": [0.2, 0.8, 0.3],
            "kill_brick_color": [0.1, 0.6, 0.1],
            "kill_description": "Toxic sewer water",
            "checkpoint_text": "Sewer Checkpoint",
            "wall_color": [0.3, 0.3, 0.35],
            "wall_material": "Concrete",
            "floor_color": [0.2, 0.25, 0.2],
            "floor_material": "Slate",
            "decoration_notes": "Pipe decorations, dripping water particles, green glow",
            "stage_sign_prefix": "Sewer Level"
        }
    ],
    "welcome_sign_text": "SKIBIDI TOILET OBBY\\nCan you escape the toilets?",
    "victory_text": "YOU SURVIVED THE SKIBIDI INVASION!",
    "death_messages": ["Got flushed!", "Skibidi got you!", "Fell into the sewers!"],
    "sprint_label": "SPRINT",
    "hud_theme": {
        "primary_color": "white",
        "accent_color": "cyan",
        "font_style": "bold futuristic"
    }
}

IMPORTANT: You MUST provide EXACTLY 8 sections (indexed 0-7).
Each section must feel like a progression through the trend's world."""

    async def process(self, input_data: dict, context: list[AgentResult]) -> dict:
        """Design theme based on trend research."""
        # Get trend research from previous agent
        trend_data = {}
        for r in context:
            if r.agent_name == "TrendResearcherAgent" and r.success:
                trend_data = r.data
                break

        game_name = input_data.get("name", "Epic Obby")
        game_type = input_data.get("game_type", "obby")

        ctx = self._build_context_prompt(context)

        prompt = f"""Design the complete theme for a Roblox {game_type} called "{game_name}".

{ctx}

Using the trend research above, create EXACTLY 8 themed sections that take the player
on a journey through the trend's world. Each section should feel different but cohesive.

The sections should progress from "intro/easy" to "epic finale" in both difficulty
feel and visual intensity.

Make it feel like the ACTUAL trend, not just colored blocks.
Kids should join and IMMEDIATELY think "this is {game_name}!"

Return the complete theme specification JSON with all 8 sections."""

        result = await self.ask_ai(prompt, as_json=True)

        # Validate we got 8 sections
        sections = result.get("sections", [])
        if len(sections) != 8:
            await log(
                f"ThemeDesigner returned {len(sections)} sections (expected 8), padding/trimming",
                LogLevel.WARNING, EventType.GAME_BUILD,
            )
            # Pad with defaults if needed
            while len(sections) < 8:
                sections.append({
                    "index": len(sections),
                    "name": f"Section {len(sections) + 1}",
                    "platform_color": [0.5, 0.5, 0.5],
                    "platform_material": "SmoothPlastic",
                    "accent_color": [1, 1, 0],
                    "kill_brick_color": [1, 0, 0],
                    "kill_description": "Danger!",
                    "wall_color": [0.3, 0.3, 0.3],
                    "wall_material": "Concrete",
                    "floor_color": [0.2, 0.2, 0.2],
                    "floor_material": "Slate",
                })
            result["sections"] = sections[:8]

        return result


# ============================================================
# AGENT 3: WORLD ARCHITECT
# ============================================================

class WorldArchitectAgent(Agent):
    """Designs level architecture with physics-valid geometry.
    This agent understands Roblox character physics and ensures
    every jump is possible but challenging."""

    role = "Level Architecture — physics-valid level design"
    model_tier = ModelTier.GEMINI_FLASH  # Can be upgraded to Claude if quality needs it

    system_prompt = """You are a Roblox obby level architect who understands PHYSICS.

ROBLOX CHARACTER PHYSICS (CRITICAL):
- Character hitbox: 2 studs wide × 5 studs tall × 1 stud deep (R15)
- Default WalkSpeed: 16 studs/sec
- Sprint WalkSpeed: 24 studs/sec (our game has sprint on Shift)
- JumpPower: 50 → max jump HEIGHT: 7.2 studs (center of mass)
- Character can clear ~3 stud gap at walk speed, ~4 stud gap at sprint
- Absolute MAX jumpable gap at sprint: ~11 studs (frame-perfect, unreliable)
- SAFE max gap at sprint: 8 studs (comfortable for a kid to clear)
- SAFE max gap at walk: 5 studs
- Falling: player falls faster than they rise, so downward jumps can span further

SECTION DIFFICULTY RULES:
Section 0 (Tutorial): Gaps 3-4 studs, platforms 10x10, no obstacles. A CHILD must be able to do this.
Section 1: Gaps 3-5 studs, platforms 8x8, gentle intro to moving platforms
Section 2: Gaps 4-5.5 studs, platforms 6-8, some moving, some kill bricks
Section 3: Gaps 4.5-6 studs, platforms 5-7, more moving, spinning intros
Section 4: Gaps 5-6.5 studs, platforms 5-6, moving + spinning + disappearing
Section 5: Gaps 5.5-7 studs, platforms 4-6, complex combos
Section 6: Gaps 6-7.5 studs, platforms 4-5, hard combos, thin walkways
Section 7 (Finale): Gaps 6.5-8 studs MAX, platforms 3-5, everything at once

CRITICAL RULES:
1. NEVER place a gap wider than 8 studs (even at sprint, wider is unreliable)
2. Downward jumps can be 1-2 studs wider than flat jumps
3. Upward jumps must be 1-2 studs shorter than flat jumps
4. Moving platforms: if platform moves AWAY from player, reduce effective gap by move distance
5. Kill bricks MUST have a visible safe path (at least 2 studs wide)
6. Section boundaries MUST be walled — player CANNOT walk on the ground to skip obstacles
7. Each section needs a floor at Y=-10 or lower that kills (void kill or kill brick floor)

OUTPUT FORMAT (JSON):
{
    "section_configs": [
        {
            "index": 0,
            "gap_min": 3.0,
            "gap_max": 4.0,
            "platform_width_min": 8,
            "platform_width_max": 10,
            "platform_depth_min": 8,
            "platform_depth_max": 10,
            "platform_y_variation": 0,
            "moving_chance": 0.0,
            "spinning_chance": 0.0,
            "disappearing_chance": 0.0,
            "kill_brick_chance": 0.0,
            "thin_walkway_chance": 0.0,
            "boundary_wall_height": 30,
            "kill_floor_y": -10,
            "enclosed": true
        }
    ],
    "global_rules": {
        "max_gap_ever": 8.0,
        "min_platform_size": 3,
        "wall_height": 30,
        "kill_floor_enabled": true,
        "section_spacing": 2000
    }
}"""

    async def process(self, input_data: dict, context: list[AgentResult]) -> dict:
        """Design level architecture with physics validation."""
        game_type = input_data.get("game_type", "obby")
        num_stages = input_data.get("num_stages", 30)

        ctx = self._build_context_prompt(context)

        prompt = f"""Design the level architecture for a {num_stages}-stage Roblox {game_type}.

{ctx}

Based on the theme designed above, create physics-valid section configurations.
EVERY gap must be jumpable. EVERY section must be enclosed (no ground shortcuts).

Remember the player has SPRINT (24 studs/sec) and the max SAFE gap is 8 studs.
Section 0 must be easy enough for a 10 year old who has never played an obby.
Section 7 should be hard but NEVER impossible.

Return the section_configs and global_rules JSON."""

        result = await self.ask_ai(prompt, as_json=True)

        # Validate and clamp physics values
        configs = result.get("section_configs", [])
        for cfg in configs:
            # Clamp gap_max to 8 studs absolute max
            if cfg.get("gap_max", 0) > 8.0:
                cfg["gap_max"] = 8.0
            if cfg.get("gap_min", 0) > cfg.get("gap_max", 8.0):
                cfg["gap_min"] = cfg["gap_max"] - 0.5
            # Ensure platforms are at least 3 studs (character is 2 wide)
            if cfg.get("platform_width_min", 0) < 3:
                cfg["platform_width_min"] = 3
            # Force enclosed
            cfg["enclosed"] = True

        result["section_configs"] = configs
        return result


# ============================================================
# AGENT 4: PHYSICS VALIDATOR
# ============================================================

class PhysicsValidatorAgent(Agent):
    """Validates generated geometry by simulating player movement.
    This is the agent that catches impossible obbys and ground shortcuts.
    Runs AFTER the level is generated, on the actual part data."""

    role = "Physics Validation — catches impossible levels"
    model_tier = ModelTier.GEMINI_FLASH  # No AI needed — pure math

    system_prompt = ""  # Not used — this agent is pure Python, no AI calls

    # Roblox character physics constants
    WALK_SPEED = 16.0       # studs/sec
    SPRINT_SPEED = 24.0     # studs/sec
    JUMP_POWER = 50.0       # jump impulse
    JUMP_HEIGHT = 7.2       # max Y gain from jump (studs)
    CHAR_WIDTH = 2.0        # character hitbox width
    CHAR_HEIGHT = 5.0       # character hitbox height
    GRAVITY = 196.2         # Roblox gravity (studs/sec^2)

    # Max horizontal distance during a jump at sprint speed
    # Time in air = 2 * sqrt(2 * JUMP_HEIGHT / GRAVITY) ≈ 0.54s
    # Max flat distance = SPRINT_SPEED * air_time ≈ 24 * 0.54 ≈ 13 studs
    # But players don't get perfect timing, so cap at 10 for flat, 8 for safe
    MAX_SAFE_GAP_SPRINT = 8.0
    MAX_SAFE_GAP_WALK = 5.0
    MAX_ABSOLUTE_GAP = 10.0  # frame-perfect sprint jump, barely possible

    async def process(self, input_data: dict, context: list[AgentResult]) -> dict:
        """Validate generated parts data for physics feasibility.

        Expects input_data to contain 'parts' and 'stages' from the obby generator.
        Returns validation results with specific fixes needed.
        """
        parts = input_data.get("parts", [])
        stages = input_data.get("stages", [])
        sections = input_data.get("sections", [])

        if not parts:
            return {
                "valid": False,
                "errors": ["No parts data to validate"],
                "fixes_needed": [],
            }

        issues = []
        fixes = []
        stats = {
            "total_stages": len(stages),
            "stages_checked": 0,
            "impossible_gaps": 0,
            "ground_shortcuts": 0,
            "missing_walls": 0,
            "missing_kill_floor": 0,
        }

        # Group jumpable platforms by section (NOT across sections — players TELEPORT)
        section_platforms = {}
        for p in parts:
            sec = p.get("section_index")
            if sec is None:
                # Assign section based on stage if available
                stage = p.get("stage")
                if stage is not None:
                    for s in stages:
                        if s.get("stage") == stage:
                            sec = s.get("section_index")
                            break
            if sec is None:
                continue

            # Only count collidable, non-kill, non-wall platforms
            name = p.get("name", "").lower()
            if (p.get("is_kill_brick") or p.get("is_wall") or p.get("is_baseplate")
                    or p.get("is_section_floor") or p.get("is_welcome_sign")
                    or not p.get("can_collide", True)
                    or "wall" in name  # wall_jump walls are obstacles, not platforms
                    or "ring" in name  # decorative rings
                    or "sign" in name  # signs
                    or "glow" in name  # glow effects
                    or "pillar" in name and "lobby" in name.lower()  # lobby pillars
                    ):
                continue

            if sec not in section_platforms:
                section_platforms[sec] = []
            section_platforms[sec].append(p)

        # Check 1: Validate gaps between consecutive jumpable platforms WITHIN each section
        for sec_idx in sorted(section_platforms.keys()):
            plats = section_platforms[sec_idx]
            stats["stages_checked"] += 1

            # Sort by Z position (forward direction within section)
            plats.sort(key=lambda p: p.get("position", [0, 0, 0])[2])

            for i in range(len(plats) - 1):
                p1 = plats[i]
                p2 = plats[i + 1]

                pos1 = p1.get("position", [0, 0, 0])
                pos2 = p2.get("position", [0, 0, 0])
                size1 = p1.get("size", [4, 1, 4])
                size2 = p2.get("size", [4, 1, 4])

                # Skip if platforms are right next to each other (same obstacle group)
                # or if this is a teleport/checkpoint pad (large, non-obstacle)
                if p1.get("is_teleport") or p2.get("is_teleport"):
                    continue
                if p1.get("is_checkpoint") or p1.get("is_section_entry"):
                    continue

                # Calculate edge-to-edge gap (not center-to-center)
                dx = abs(pos2[0] - pos1[0]) - (size1[0] + size2[0]) / 2
                dy = pos2[1] - pos1[1]  # positive = upward jump
                dz = abs(pos2[2] - pos1[2]) - (size1[2] + size2[2]) / 2

                # Total horizontal gap
                gap_h = math.sqrt(max(0, dx) ** 2 + max(0, dz) ** 2)

                # Skip small gaps (easily jumpable at walk speed without sprint)
                if gap_h < 3.0:
                    continue

                # Adjust for height difference
                if dy > 0:
                    # Jumping UP — reduce effective jumpable distance
                    effective_max = self.MAX_SAFE_GAP_SPRINT - dy * 0.5
                elif dy < 0:
                    # Jumping DOWN — increase effective jumpable distance
                    effective_max = self.MAX_SAFE_GAP_SPRINT + abs(dy) * 0.3
                else:
                    effective_max = self.MAX_SAFE_GAP_SPRINT

                # Check if gap exceeds safe maximum
                if gap_h > effective_max:
                    stage_num = p1.get("stage") or p2.get("stage") or "?"
                    stats["impossible_gaps"] += 1
                    issues.append({
                        "type": "impossible_gap",
                        "section": sec_idx,
                        "stage": stage_num,
                        "platform_from": p1.get("name"),
                        "platform_to": p2.get("name"),
                        "gap": round(gap_h, 2),
                        "max_allowed": round(effective_max, 2),
                        "height_diff": round(dy, 2),
                    })
                    fixes.append({
                        "action": "reduce_gap",
                        "section": sec_idx,
                        "stage": stage_num,
                        "platform": p2.get("name"),
                        "current_gap": round(gap_h, 2),
                        "target_gap": round(effective_max * 0.85, 2),
                        "suggestion": "Move platform closer or add intermediate platform",
                    })

                # Check if upward jump is too high
                if dy > self.JUMP_HEIGHT:
                    stage_num = p1.get("stage") or p2.get("stage") or "?"
                    issues.append({
                        "type": "impossible_height",
                        "section": sec_idx,
                        "stage": stage_num,
                        "platform_from": p1.get("name"),
                        "platform_to": p2.get("name"),
                        "height_diff": round(dy, 2),
                        "max_jump_height": self.JUMP_HEIGHT,
                    })
                    fixes.append({
                        "action": "reduce_height",
                        "section": sec_idx,
                        "stage": stage_num,
                        "platform": p2.get("name"),
                        "current_height": round(dy, 2),
                        "max_height": self.JUMP_HEIGHT,
                    })

        # Check 2: Section enclosure — are walls present?
        for sec in sections:
            sec_idx = sec.get("index", sec.get("section_index", -1))
            sec_parts = [p for p in parts if p.get("section_index") == sec_idx]

            walls = [p for p in sec_parts if p.get("is_wall")]
            floor = [p for p in sec_parts if p.get("is_section_floor") or p.get("is_baseplate")]

            if not walls or len(walls) < 4:
                stats["missing_walls"] += 1
                issues.append({
                    "type": "missing_walls",
                    "section": sec_idx,
                    "walls_found": len(walls),
                    "walls_needed": 4,
                })
                fixes.append({
                    "action": "add_walls",
                    "section": sec_idx,
                    "detail": "Section needs 4 boundary walls to prevent ground shortcuts",
                })

            # Check if there's a kill floor below the platforms
            has_kill_floor = any(
                p.get("is_kill_brick") and p.get("position", [0, 0, 0])[1] < 0
                for p in sec_parts
            )
            if not has_kill_floor and sec_idx > 0:  # Section 0 (lobby) might not need it
                stats["missing_kill_floor"] += 1
                issues.append({
                    "type": "missing_kill_floor",
                    "section": sec_idx,
                })
                fixes.append({
                    "action": "add_kill_floor",
                    "section": sec_idx,
                    "detail": "Add kill brick floor at Y=-5 to prevent ground walking",
                })

        # Check 3: Can player reach ground level and walk around?
        # Find the lowest non-kill-brick platform in each section
        for sec in sections:
            sec_idx = sec.get("index", sec.get("section_index", -1))
            sec_platforms = [
                p for p in parts
                if p.get("section_index") == sec_idx
                and not p.get("is_kill_brick")
                and not p.get("is_wall")
                and not p.get("is_baseplate")
                and not p.get("is_section_floor")
                and p.get("position", [0, 0, 0])[1] > 0
            ]

            if sec_platforms:
                lowest_y = min(p.get("position", [0, 0, 0])[1] for p in sec_platforms)
                floor_parts = [p for p in parts
                               if p.get("section_index") == sec_idx
                               and (p.get("is_baseplate") or p.get("is_section_floor"))]
                if floor_parts:
                    floor_y = floor_parts[0].get("position", [0, 0, 0])[1]
                    floor_top = floor_y + floor_parts[0].get("size", [1, 1, 1])[1] / 2

                    # If lowest platform is less than 8 studs above floor AND floor is walkable
                    if lowest_y - floor_top < 8 and not any(
                        p.get("is_kill_brick") and abs(p.get("position", [0, 0, 0])[1] - floor_top) < 2
                        for p in parts if p.get("section_index") == sec_idx
                    ):
                        stats["ground_shortcuts"] += 1
                        issues.append({
                            "type": "ground_shortcut",
                            "section": sec_idx,
                            "lowest_platform_y": round(lowest_y, 1),
                            "floor_y": round(floor_top, 1),
                            "detail": "Player can fall to ground and walk to exit, bypassing obstacles",
                        })
                        fixes.append({
                            "action": "add_kill_floor_or_raise",
                            "section": sec_idx,
                            "detail": "Make floor a kill brick or raise platforms higher above floor",
                        })

        valid = len(issues) == 0
        return {
            "valid": valid,
            "stats": stats,
            "issues": issues,
            "fixes_needed": fixes,
            "summary": (
                f"{'PASS' if valid else 'FAIL'}: "
                f"{stats['stages_checked']} stages checked, "
                f"{stats['impossible_gaps']} impossible gaps, "
                f"{stats['ground_shortcuts']} ground shortcuts, "
                f"{stats['missing_walls']} missing walls"
            ),
        }


# ============================================================
# AGENT 5: QUALITY REVIEWER
# ============================================================

class QualityReviewerAgent(Agent):
    """Final quality check on the complete game build.
    Verifies everything works together — scripts, parts, theme, gameplay."""

    role = "Quality Review — final check before ship"
    model_tier = ModelTier.GEMINI_FLASH

    system_prompt = """You are a Roblox game quality reviewer for kids aged 10-13.
You review the COMPLETE game build and score it on multiple dimensions.

Score each category 1-10 and provide specific issues:

OUTPUT FORMAT (JSON):
{
    "overall_score": 7.5,
    "categories": {
        "playability": {"score": 8, "notes": "All stages reachable, good difficulty curve"},
        "theme_consistency": {"score": 6, "notes": "Section 3-5 feel generic, need more themed elements"},
        "visual_quality": {"score": 7, "notes": "Good color variety but lacks decorative elements"},
        "fun_factor": {"score": 8, "notes": "Moving platforms add good variety"},
        "monetization_ready": {"score": 5, "notes": "Shop system exists but no compelling items"},
        "bug_risk": {"score": 9, "notes": "Scripts look solid, proper error handling"}
    },
    "critical_issues": ["ground can be walked on in section 4"],
    "improvement_suggestions": ["Add more themed decorations", "Vary platform shapes"],
    "ship_ready": true
}"""

    async def process(self, input_data: dict, context: list[AgentResult]) -> dict:
        """Review the complete game build."""
        ctx = self._build_context_prompt(context)

        # Summarize what we have
        parts_count = len(input_data.get("parts", []))
        stages_count = input_data.get("total_stages", 0)
        sections_count = input_data.get("total_sections", 0)

        # Get validation results if available
        validation = {}
        for r in context:
            if r.agent_name == "PhysicsValidatorAgent" and r.success:
                validation = r.data
                break

        prompt = f"""Review this complete Roblox obby game build:

Game: {input_data.get('name', 'Unknown')}
Parts: {parts_count}
Stages: {stages_count}
Sections: {sections_count}

{ctx}

Physics validation results: {json.dumps(validation.get('summary', 'not run'), indent=2)}
Issues found: {len(validation.get('issues', []))}

Score the game on playability, theme consistency, visual quality, fun factor,
monetization readiness, and bug risk. Be honest — if it's not ready to ship, say so.

Return the quality review JSON."""

        result = await self.ask_ai(prompt, as_json=True)
        return result
