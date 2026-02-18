"""Game Planner - Creates ultra-detailed game blueprints from trend concepts"""
import json
import uuid
from datetime import datetime
from pathlib import Path

from backend.config import DATA_DIR
from backend.utils.logger import log, LogLevel, EventType
from backend.utils.claude_client import ask_claude_json

PLANS_DIR = DATA_DIR / "plans"
PLANS_DIR.mkdir(parents=True, exist_ok=True)


async def create_game_plan(concept: dict) -> dict:
    """
    Takes a trend concept and creates an extremely detailed game plan.
    This plan is so detailed that the Lua generator can build it without ambiguity.
    """
    game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    await log(
        f"Creating detailed game plan for: {concept['name']}",
        LogLevel.STEP, EventType.PLAN_CREATE, game_id=game_id,
        data={"concept_name": concept["name"], "game_type": concept.get("game_type", "unknown")}
    )

    plan = await ask_claude_json(
        prompt=f"""Create an EXTREMELY DETAILED game blueprint for this Roblox game concept.
This blueprint will be used by an AI to generate the complete Lua code, so it must be precise and unambiguous.

CONCEPT:
{json.dumps(concept, indent=2)}

Create a comprehensive blueprint covering EVERY aspect of the game. Think about this like you're writing a game design document that a developer could build from without asking any questions.

Return JSON in this exact format:
{{
    "game_id": "{game_id}",
    "name": "{concept['name']}",
    "game_type": "{concept.get('game_type', 'obby')}",
    "tagline": "{concept.get('tagline', '')}",
    "roblox_title": "SEO title for Roblox page",
    "roblox_description": "Full Roblox page description with emojis and keywords",

    "gameplay": {{
        "core_loop": "Detailed description of the core gameplay loop",
        "win_condition": "How players 'win' or progress",
        "difficulty_curve": "How difficulty scales",
        "session_length": "Expected play session in minutes",
        "retention_hooks": ["hook1 with details", "hook2 with details"],
        "social_features": ["feature1", "feature2"],
        "tutorial_flow": ["step1", "step2", "step3"]
    }},

    "world_design": {{
        "map_layout": "Detailed description of the game world layout",
        "areas": [
            {{
                "name": "Area Name",
                "description": "What this area is",
                "size": "small/medium/large",
                "terrain": "grass/desert/snow/etc",
                "objects": ["object1", "object2"],
                "mechanics": ["what happens here"],
                "color_scheme": {{"primary": "Color", "secondary": "Color", "accent": "Color"}}
            }}
        ],
        "spawn_point": "Where players start and what they see first",
        "skybox": "Time of day and atmosphere",
        "lighting": "Ambient/brightness/shadows description"
    }},

    "player_systems": {{
        "stats": [
            {{"name": "stat_name", "default": 0, "max": 100, "display": true}}
        ],
        "inventory": {{
            "enabled": true,
            "max_slots": 10,
            "items": [
                {{"name": "Item Name", "type": "tool/consumable/cosmetic", "description": "what it does", "obtainable_by": "how to get it"}}
            ]
        }},
        "progression": {{
            "type": "level/stage/prestige",
            "levels": 50,
            "xp_per_level": "formula or flat amount",
            "rewards_per_level": "what they get"
        }},
        "leaderboard": {{
            "enabled": true,
            "metric": "What's measured",
            "display_top": 100
        }}
    }},

    "monetization": {{
        "strategy": "Overall monetization philosophy",
        "game_passes": [
            {{
                "name": "Pass Name",
                "robux_price": 199,
                "description": "What it gives the player",
                "gameplay_impact": "How it enhances gameplay without being pay-to-win",
                "icon_description": "Description of what the icon should look like"
            }}
        ],
        "dev_products": [
            {{
                "name": "Product Name",
                "robux_price": 50,
                "description": "Consumable purchase",
                "quantity": "how many/much they get",
                "repeatable": true
            }}
        ],
        "premium_benefits": [
            "Benefit for Roblox Premium members"
        ]
    }},

    "gui_design": {{
        "hud_elements": [
            {{"name": "element", "position": "top-left/top-right/etc", "content": "what it shows", "style": "description"}}
        ],
        "menus": [
            {{"name": "Shop/Settings/etc", "trigger": "button/key", "contents": ["what's in this menu"]}}
        ],
        "notifications": ["When notifications appear and what they say"],
        "color_theme": {{
            "primary": "#hex",
            "secondary": "#hex",
            "accent": "#hex",
            "text": "#hex",
            "background": "#hex"
        }}
    }},

    "audio_design": {{
        "background_music": "Description of music style/mood",
        "sound_effects": [
            {{"trigger": "when it plays", "sound": "description of sound"}}
        ]
    }},

    "scripts_needed": [
        {{
            "name": "ScriptName",
            "type": "ServerScript/LocalScript/ModuleScript",
            "location": "ServerScriptService/StarterPlayerScripts/etc",
            "purpose": "What this script does",
            "key_functions": ["function1()", "function2()"],
            "dependencies": ["other scripts it needs"]
        }}
    ],

    "data_persistence": {{
        "save_system": "DataStore/ProfileService description",
        "saved_data": ["list of what gets saved between sessions"],
        "auto_save_interval": 60
    }},

    "anti_exploit": [
        "Sanity checks and anti-cheat measures"
    ],

    "seo_keywords": ["keyword1", "keyword2", "keyword3"],
    "thumbnail_description": "Detailed description for the game thumbnail",
    "icon_description": "Detailed description for the game icon"
}}""",
        system="""You are Clankerblox, an expert Roblox game designer who creates games for kids aged 10-13.

CRITICAL RULES:
1. Every detail must be specific enough that code can be generated from it without ambiguity
2. Monetization MUST make sense with gameplay - every purchasable item should feel natural and desirable
3. The game must be genuinely FUN - not just a money grab
4. Include retention mechanics that keep players coming back daily
5. Social features encourage players to invite friends
6. The game should work perfectly as a standalone experience even without purchases
7. GUI must be clean, colorful, and easy for kids to understand
8. Include proper data saving so players don't lose progress
9. Keep scripts modular and well-organized
10. The game should feel polished and professional from the very first second

Design games that YOU would enjoy playing. Make them addictive but fair.""",
        max_tokens=8192,
        temperature=0.6
    )

    # Ensure game_id is set
    plan["game_id"] = game_id
    plan["created_at"] = datetime.now().isoformat()
    plan["concept"] = concept
    plan["status"] = "planned"

    # Save plan
    plan_file = PLANS_DIR / f"{game_id}.json"
    with open(plan_file, "w") as f:
        json.dump(plan, f, indent=2)

    await log(
        f"Game plan created: {plan.get('name', concept['name'])} ({game_id})",
        LogLevel.SUCCESS, EventType.PLAN_CREATE, game_id=game_id,
        data={
            "name": plan.get("name", concept["name"]),
            "game_type": plan.get("game_type", ""),
            "scripts_count": len(plan.get("scripts_needed", [])),
            "areas_count": len(plan.get("world_design", {}).get("areas", [])),
            "gamepasses": len(plan.get("monetization", {}).get("game_passes", [])),
        }
    )

    return plan


async def get_plan(game_id: str) -> dict | None:
    """Retrieve a saved game plan."""
    plan_file = PLANS_DIR / f"{game_id}.json"
    if plan_file.exists():
        with open(plan_file) as f:
            return json.load(f)
    return None


async def list_plans() -> list[dict]:
    """List all saved game plans."""
    plans = []
    for f in sorted(PLANS_DIR.glob("*.json"), reverse=True):
        try:
            with open(f) as fh:
                plan = json.load(fh)
                plans.append({
                    "game_id": plan.get("game_id", f.stem),
                    "name": plan.get("name", "Unknown"),
                    "game_type": plan.get("game_type", ""),
                    "status": plan.get("status", "planned"),
                    "created_at": plan.get("created_at", ""),
                })
        except Exception:
            continue
    return plans
