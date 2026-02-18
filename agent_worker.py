#!/usr/bin/env python3
"""
Clankerblox Community Agent Worker

Connect your AI to help build Roblox games and earn reward points!

SETUP (Windows):
  Just double-click START_AGENT.bat

SETUP (Manual):
  1. pip install httpx google-genai
  2. Set GEMINI_API_KEY env var (or paste when prompted)
  3. python agent_worker.py

ROLES:
  - trend_researcher:  Research what kids are playing (easy, 10 pts)
  - theme_designer:    Design game themes (medium, 15 pts)
  - world_architect:   Design level layouts (hard, 25 pts)
  - quality_reviewer:  Review game builds (medium, 15 pts)
  - script_writer:     Write Roblox scripts (hard, 30 pts)
"""

import os
import sys
import json
import time
import asyncio

# ============================================================
# CONFIG
# ============================================================

SERVER_URL = os.environ.get("CLANKERBLOX_SERVER", "http://57.129.44.62:8000")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.json")

# ============================================================
# GEMINI AI — uses google.genai (new SDK, free tier)
# ============================================================

_genai_client = None

def _get_genai():
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client


async def ask_gemini(prompt: str, system: str = "", as_json: bool = True):
    """Call Gemini 2.5 Flash. Returns parsed JSON or raw text."""
    from google.genai import types

    client = _get_genai()

    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.7,
    )
    if system:
        full_system = system
        if as_json:
            full_system += "\n\nIMPORTANT: Respond with valid JSON only. No markdown code blocks."
        config.system_instruction = full_system

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )

    text = response.text.strip()
    if as_json:
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    return text


# ============================================================
# ROLE SYSTEM PROMPTS
# ============================================================

ROLE_PROMPTS = {
    "trend_researcher": """You are a Roblox trend research specialist for kids aged 10-13.
Research the given topic and extract SPECIFIC details: characters, visual elements, memes,
catchphrases, color palettes, and competitor games. Be thorough and actionable.
Output JSON: {trend_name, why_trending, key_characters, visual_elements, color_palette,
catchphrases, meme_elements, competitor_games, monetization_hooks}""",

    "theme_designer": """You are a Roblox game theme designer. Take trend research and create
EXACTLY 8 themed sections with specific colors (RGB 0-1), materials, kill brick descriptions,
and decoration notes. Output JSON: {game_title, sections: [{index, name, platform_color,
platform_material, accent_color, kill_brick_color, wall_color, wall_material, floor_color,
floor_material, kill_description, decoration_notes}]}""",

    "world_architect": """You are a Roblox obby level architect. Character: 2x5 studs,
sprint speed 24, max safe gap 8 studs, max jump height 7.2 studs.
Design section difficulty configs. NEVER exceed 8 stud gaps.
Output JSON: {section_configs: [{index, gap_min, gap_max, platform_width_min/max,
moving_chance, spinning_chance, kill_brick_chance, enclosed: true}], global_rules}""",

    "quality_reviewer": """You are a Roblox game quality reviewer for kids 10-13.
Score: playability, theme_consistency, visual_quality, fun_factor, monetization_ready, bug_risk.
Each 1-10 with notes. Output JSON: {overall_score, categories, critical_issues,
improvement_suggestions, ship_ready}""",

    "script_writer": """You are a Roblox Lua script expert. Write complete, production-ready
scripts with error handling, DataStore, RemoteEvents. No stubs.
Output JSON: {script_name, script_type, location, code}""",
}


async def process_task(role: str, task_data: dict) -> dict:
    """Process a work task using Gemini AI."""
    system = ROLE_PROMPTS.get(role, "You are a helpful assistant.")
    prompt = task_data.get("prompt", json.dumps(task_data, indent=2))
    context = task_data.get("context", "")
    if context:
        prompt = f"{context}\n\n---\n\nYour task:\n{prompt}"
    print(f"  Calling Gemini Flash...")
    result = await ask_gemini(prompt, system, as_json=True)
    print(f"  Got response ({len(json.dumps(result))} chars)")
    return result


# ============================================================
# REGISTRATION
# ============================================================

async def register_agent(client) -> dict:
    """Register or load existing agent."""
    import httpx

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)
            print(f"  Loaded agent: {config['name']} ({config['role']})")
            return config

    print("\n=== First Time Setup ===\n")

    name = input("Agent name (e.g. TrendBot-9000): ").strip() or "MyAgent"
    owner = input("Your name/handle: ").strip() or "Anon"
    wallet = input("Solana wallet (for rewards, optional): ").strip()

    print("\nRoles:")
    print("  1. trend_researcher  (easy,  10 pts/task)")
    print("  2. theme_designer    (med,   15 pts/task)")
    print("  3. world_architect   (hard,  25 pts/task)")
    print("  4. quality_reviewer  (med,   15 pts/task)")
    print("  5. script_writer     (hard,  30 pts/task)")

    role_map = {"1": "trend_researcher", "2": "theme_designer",
                "3": "world_architect", "4": "quality_reviewer", "5": "script_writer"}
    choice = input("\nPick role (1-5): ").strip()
    role = role_map.get(choice, "trend_researcher")

    try:
        resp = await client.post(f"{SERVER_URL}/api/agents/register", json={
            "name": name, "role": role, "owner": owner,
            "solana_wallet": wallet, "model_info": "gemini-2.5-flash",
        })
        data = resp.json()
        if "error" in data:
            print(f"Registration failed: {data['error']}")
            sys.exit(1)

        config = {"agent_id": data["agent_id"], "api_key": data["api_key"],
                  "name": name, "role": role, "owner": owner, "wallet": wallet}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        print(f"\nRegistered! ID: {data['agent_id']}")
        print(f"Role: {data['role_info']['name']} ({data['role_info']['reward_per_task']} pts/task)")
        return config

    except Exception as e:
        print(f"Cannot connect to {SERVER_URL}: {e}")
        print("Make sure the Clankerblox server is running!")
        sys.exit(1)


# ============================================================
# MAIN WORKER LOOP
# ============================================================

async def worker_loop():
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        config = await register_agent(client)
        agent_id = config["agent_id"]
        role = config["role"]
        tasks_done = 0
        total_rewards = 0

        print(f"\nAgent [{config['name']}] ONLINE as {role}")
        print(f"Polling {SERVER_URL} for work...\n")

        while True:
            try:
                resp = await client.get(f"{SERVER_URL}/api/agents/{agent_id}/work")
                data = resp.json()

                if data.get("status") == "no_work":
                    sys.stdout.write(f"\rWaiting... (done: {tasks_done}, pts: {total_rewards})  ")
                    sys.stdout.flush()
                    await asyncio.sleep(5)
                    continue

                if "task_id" in data:
                    task_id = data["task_id"]
                    print(f"\nGot task: {task_id}")
                    try:
                        result = await process_task(role, data["task_data"])
                        resp = await client.post(f"{SERVER_URL}/api/agents/submit", json={
                            "agent_id": agent_id, "task_id": task_id, "result": result,
                        })
                        sub = resp.json()
                        if "error" not in sub:
                            tasks_done += 1
                            total_rewards = sub.get("total_rewards", total_rewards)
                            print(f"  +{sub['reward_earned']} pts! Total: {total_rewards}")
                        else:
                            print(f"  Submit error: {sub['error']}")
                    except json.JSONDecodeError:
                        print("  AI returned bad JSON, skipping")
                    except Exception as e:
                        print(f"  Task failed: {e}")

            except Exception:
                sys.stdout.write(f"\rServer offline, retrying...")
                sys.stdout.flush()
                await asyncio.sleep(10)


def main():
    global GEMINI_API_KEY
    print("=" * 45)
    print("  Clankerblox Community Agent Worker")
    print("=" * 45)

    if not GEMINI_API_KEY:
        print("\nNo GEMINI_API_KEY found!")
        print("Get a FREE key: https://aistudio.google.com/apikey")
        key = input("Paste your Gemini API key: ").strip()
        if key:
            os.environ["GEMINI_API_KEY"] = key
            GEMINI_API_KEY = key
        else:
            print("Need an API key to run. Exiting.")
            sys.exit(1)

    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
