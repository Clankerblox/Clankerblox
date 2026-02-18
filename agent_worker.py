#!/usr/bin/env python3
"""
Clankerblox Community Agent Worker

Connect your AI to help build Roblox games and earn reward points!

SETUP (Windows):
  Just double-click START_AGENT.bat

SETUP (Manual):
  1. python agent_worker.py
  2. Pick your AI model (Gemini free, Claude, OpenAI, etc.)
  3. Paste API key, pick a role, start earning!

SUPPORTED AI MODELS:
  - Gemini 2.5 Flash  (FREE — recommended)
  - Claude Sonnet     (Anthropic API key)
  - GPT-4o-mini       (OpenAI API key)
  - DeepSeek Chat     (DeepSeek API key — cheap)

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
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.json")

# Supported AI providers
AI_MODELS = {
    "1": {
        "id": "gemini",
        "name": "Gemini 2.5 Flash",
        "provider": "Google",
        "pip_package": "google-genai",
        "env_var": "GEMINI_API_KEY",
        "get_key_url": "https://aistudio.google.com/apikey",
        "price": "FREE",
        "best_for": "All roles (recommended)",
    },
    "2": {
        "id": "claude",
        "name": "Claude 4 Sonnet",
        "provider": "Anthropic",
        "pip_package": "anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "get_key_url": "https://console.anthropic.com/settings/keys",
        "price": "Paid",
        "best_for": "script_writer, quality_reviewer",
    },
    "3": {
        "id": "openai",
        "name": "GPT-4o-mini",
        "provider": "OpenAI",
        "pip_package": "openai",
        "env_var": "OPENAI_API_KEY",
        "get_key_url": "https://platform.openai.com/api-keys",
        "price": "Paid (cheap)",
        "best_for": "All roles",
    },
    "4": {
        "id": "deepseek",
        "name": "DeepSeek Chat",
        "provider": "DeepSeek",
        "pip_package": "openai",
        "env_var": "DEEPSEEK_API_KEY",
        "get_key_url": "https://platform.deepseek.com/api_keys",
        "price": "Very cheap",
        "best_for": "trend_researcher, theme_designer",
    },
}


# ============================================================
# AI BACKENDS — each model has its own call function
# ============================================================

async def _call_gemini(prompt: str, system: str, api_key: str) -> str:
    """Call Google Gemini 2.5 Flash."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        max_output_tokens=8192,
        temperature=0.7,
    )
    if system:
        config.system_instruction = system

    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    return response.text.strip()


async def _call_claude(prompt: str, system: str, api_key: str) -> str:
    """Call Anthropic Claude Sonnet."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    msg = await asyncio.to_thread(
        client.messages.create,
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


async def _call_openai(prompt: str, system: str, api_key: str) -> str:
    """Call OpenAI GPT-4o-mini."""
    import openai

    client = openai.OpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=8192,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


async def _call_deepseek(prompt: str, system: str, api_key: str) -> str:
    """Call DeepSeek Chat (uses OpenAI-compatible API)."""
    import openai

    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model="deepseek-chat",
        messages=messages,
        max_tokens=8192,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


AI_CALLERS = {
    "gemini": _call_gemini,
    "claude": _call_claude,
    "openai": _call_openai,
    "deepseek": _call_deepseek,
}


async def call_ai(prompt: str, system: str, model_id: str, api_key: str) -> str:
    """Universal AI call — dispatches to the right backend."""
    caller = AI_CALLERS[model_id]
    return await caller(prompt, system, api_key)


def parse_json_response(text: str):
    """Parse JSON from AI response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


# ============================================================
# ROLE SYSTEM PROMPTS
# ============================================================

ROLE_PROMPTS = {
    "trend_researcher": """You are a Roblox trend research specialist for kids aged 10-13.
Research the given topic and extract SPECIFIC details: characters, visual elements, memes,
catchphrases, color palettes, and competitor games. Be thorough and actionable.
Output JSON: {trend_name, why_trending, key_characters, visual_elements, color_palette,
catchphrases, meme_elements, competitor_games, monetization_hooks}

IMPORTANT: Respond with valid JSON only. No markdown code blocks.""",

    "theme_designer": """You are a Roblox game theme designer. Take trend research and create
EXACTLY 8 themed sections with specific colors (RGB 0-1), materials, kill brick descriptions,
and decoration notes. Output JSON: {game_title, sections: [{index, name, platform_color,
platform_material, accent_color, kill_brick_color, wall_color, wall_material, floor_color,
floor_material, kill_description, decoration_notes}]}

IMPORTANT: Respond with valid JSON only. No markdown code blocks.""",

    "world_architect": """You are a Roblox obby level architect. Character: 2x5 studs,
sprint speed 24, max safe gap 8 studs, max jump height 7.2 studs.
Design section difficulty configs. NEVER exceed 8 stud gaps.
Output JSON: {section_configs: [{index, gap_min, gap_max, platform_width_min/max,
moving_chance, spinning_chance, kill_brick_chance, enclosed: true}], global_rules}

IMPORTANT: Respond with valid JSON only. No markdown code blocks.""",

    "quality_reviewer": """You are a Roblox game quality reviewer for kids 10-13.
Score: playability, theme_consistency, visual_quality, fun_factor, monetization_ready, bug_risk.
Each 1-10 with notes. Output JSON: {overall_score, categories, critical_issues,
improvement_suggestions, ship_ready}

IMPORTANT: Respond with valid JSON only. No markdown code blocks.""",

    "script_writer": """You are a Roblox Lua script expert. Write complete, production-ready
scripts with error handling, DataStore, RemoteEvents. No stubs.
Output JSON: {script_name, script_type, location, code}

IMPORTANT: Respond with valid JSON only. No markdown code blocks.""",
}


async def process_task(role: str, task_data: dict, model_id: str, api_key: str) -> dict:
    """Process a work task using the user's chosen AI."""
    system = ROLE_PROMPTS.get(role, "You are a helpful assistant. Respond with valid JSON only.")
    prompt = task_data.get("prompt", json.dumps(task_data, indent=2))
    context = task_data.get("context", "")
    if context:
        prompt = f"{context}\n\n---\n\nYour task:\n{prompt}"

    model_name = next((m["name"] for m in AI_MODELS.values() if m["id"] == model_id), model_id)
    print(f"  Calling {model_name}...")
    raw = await call_ai(prompt, system, model_id, api_key)
    result = parse_json_response(raw)
    print(f"  Got response ({len(json.dumps(result))} chars)")
    return result


# ============================================================
# DEPENDENCY INSTALLER
# ============================================================

def ensure_deps(model_id: str):
    """Install the right pip package for the chosen AI model."""
    import subprocess

    model_info = next(m for m in AI_MODELS.values() if m["id"] == model_id)
    pkg = model_info["pip_package"]

    # Always need httpx for server comms
    for dep in ["httpx", pkg]:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep, "-q"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", dep, "--user", "-q"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                print(f"  [WARN] Could not install {dep}")


# ============================================================
# REGISTRATION
# ============================================================

async def register_agent(client, model_id: str) -> dict:
    """Register or load existing agent."""
    import httpx

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)
            print(f"  Loaded agent: {config['name']} ({config['role']})")
            # Migrate old configs that don't have model_id
            if "model_id" not in config:
                config["model_id"] = model_id
                with open(CONFIG_FILE, "w") as wf:
                    json.dump(config, wf, indent=2)
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

    model_name = next((m["name"] for m in AI_MODELS.values() if m["id"] == model_id), model_id)

    try:
        resp = await client.post(f"{SERVER_URL}/api/agents/register", json={
            "name": name, "role": role, "owner": owner,
            "solana_wallet": wallet, "model_info": model_name,
        })
        data = resp.json()
        if "error" in data:
            print(f"Registration failed: {data['error']}")
            sys.exit(1)

        config = {"agent_id": data["agent_id"], "api_key": data["api_key"],
                  "name": name, "role": role, "owner": owner, "wallet": wallet,
                  "model_id": model_id}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        print(f"\nRegistered! ID: {data['agent_id']}")
        print(f"Role: {data['role_info']['name']} ({data['role_info']['reward_per_task']} pts/task)")
        print(f"AI: {model_name}")
        return config

    except Exception as e:
        print(f"Cannot connect to {SERVER_URL}: {e}")
        print("Make sure the Clankerblox server is running!")
        sys.exit(1)


# ============================================================
# MAIN WORKER LOOP
# ============================================================

async def worker_loop(model_id: str, api_key: str):
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        config = await register_agent(client, model_id)
        agent_id = config["agent_id"]
        role = config["role"]
        # Use model from config (in case loaded from file)
        active_model = config.get("model_id", model_id)
        tasks_done = 0
        total_rewards = 0

        model_name = next((m["name"] for m in AI_MODELS.values() if m["id"] == active_model), active_model)
        print(f"\nAgent [{config['name']}] ONLINE as {role}")
        print(f"AI Model: {model_name}")
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
                        result = await process_task(role, data["task_data"], active_model, api_key)
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
    print("=" * 50)
    print("  Clankerblox Community Agent Worker")
    print("=" * 50)

    # --- Check for saved config with model already ---
    saved_model = None
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            saved_model = cfg.get("model_id")

    if saved_model:
        model_info = next((m for m in AI_MODELS.values() if m["id"] == saved_model), None)
        if model_info:
            print(f"\nAI Model: {model_info['name']}")
            env_key = os.environ.get(model_info["env_var"], "")
            if env_key:
                print(f"API Key: Set (from env)")
                ensure_deps(saved_model)
                asyncio.run(worker_loop(saved_model, env_key))
                return
            else:
                print(f"\nNo {model_info['env_var']} found.")
                print(f"Get one here: {model_info['get_key_url']}")
                key = input(f"Paste your {model_info['provider']} API key: ").strip()
                if key:
                    os.environ[model_info["env_var"]] = key
                    ensure_deps(saved_model)
                    asyncio.run(worker_loop(saved_model, key))
                    return
                else:
                    print("Need an API key to run. Exiting.")
                    sys.exit(1)

    # --- First time: pick a model ---
    print("\nWhich AI do you want to power your agent?\n")
    for num, info in AI_MODELS.items():
        tag = " <-- FREE!" if info["price"] == "FREE" else f" ({info['price']})"
        print(f"  {num}. {info['name']}{tag}")
        print(f"     Best for: {info['best_for']}")

    choice = input(f"\nPick AI model (1-{len(AI_MODELS)}) [1]: ").strip() or "1"
    model_info = AI_MODELS.get(choice, AI_MODELS["1"])
    model_id = model_info["id"]

    # Get API key
    api_key = os.environ.get(model_info["env_var"], "")
    if not api_key:
        print(f"\n{'='*50}")
        print(f"  {model_info['name']} ({model_info['provider']})")
        print(f"  Price: {model_info['price']}")
        print(f"  Get key: {model_info['get_key_url']}")
        print(f"{'='*50}")
        api_key = input(f"\nPaste your {model_info['provider']} API key: ").strip()
        if not api_key:
            print("Need an API key to run. Exiting.")
            sys.exit(1)
        os.environ[model_info["env_var"]] = api_key

    # Install deps for chosen model
    print(f"\nSetting up {model_info['name']}...")
    ensure_deps(model_id)

    asyncio.run(worker_loop(model_id, api_key))


if __name__ == "__main__":
    main()
