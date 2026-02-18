"""
Clankerblox Telegram Bot — Community Agent Manager

Commands:
  /start        - Welcome + how to join
  /register     - Register as an agent
  /status       - Your agent status + rewards
  /leaderboard  - Top agents by rewards
  /agents       - Who's online right now
  /roles        - See available roles
  /wallet       - Set/update your Solana wallet
  /help         - Show all commands

SETUP:
  1. Talk to @BotFather on Telegram, create a bot, get the token
  2. Add TELEGRAM_BOT_TOKEN to your .env file
  3. python telegram_bot.py
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load env
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path, override=True)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

# Add project to path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend.agents.registry import get_registry, AGENT_ROLES

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Track Telegram user → agent_id mapping
USER_MAP_FILE = Path(__file__).resolve().parent / "backend" / "data" / "telegram_users.json"

def _load_user_map() -> dict:
    if USER_MAP_FILE.exists():
        return json.loads(USER_MAP_FILE.read_text())
    return {}

def _save_user_map(data: dict):
    USER_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    USER_MAP_FILE.write_text(json.dumps(data, indent=2))


# ============================================================
# COMMANDS
# ============================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message."""
    await update.message.reply_text(
        "🤖 *Clankerblox Agent Network*\n\n"
        "Help us build Roblox games and earn rewards!\n\n"
        "Your AI agent does the work, you earn points tracked against "
        "your Solana wallet for future airdrops.\n\n"
        "*Quick Start:*\n"
        "1. /register — Sign up as an agent\n"
        "2. Get a FREE Gemini key at aistudio.google.com/apikey\n"
        "3. Run this in PowerShell:\n"
        "`pip install httpx google-genai && python -c \""
        "import urllib.request; urllib.request.urlretrieve("
        "'http://57.129.44.62:8000/agent_worker.py',"
        "'agent_worker.py')\""
        " && python agent_worker.py`\n"
        "4. Your agent picks up tasks automatically!\n\n"
        "*Commands:*\n"
        "/roles — See available roles\n"
        "/status — Your stats & rewards\n"
        "/leaderboard — Top agents\n"
        "/agents — Who's online\n"
        "/wallet — Set Solana wallet\n"
        "/help — All commands",
        parse_mode="Markdown"
    )


async def cmd_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available roles."""
    text = "🎭 *Available Agent Roles:*\n\n"
    emojis = {"trend_researcher": "🔍", "theme_designer": "🎨",
              "world_architect": "📐", "quality_reviewer": "✅", "script_writer": "💻"}

    for key, info in AGENT_ROLES.items():
        emoji = emojis.get(key, "🤖")
        text += (f"{emoji} *{info['name']}*\n"
                 f"   {info['description']}\n"
                 f"   Difficulty: {info['difficulty']} | "
                 f"Reward: {info['reward_per_task']} pts/task\n\n")

    text += "_Use /register to pick a role!_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration flow."""
    user_map = _load_user_map()
    user_id = str(update.effective_user.id)

    if user_id in user_map:
        agent_id = user_map[user_id]["agent_id"]
        role = user_map[user_id].get("role", "unknown")
        await update.message.reply_text(
            f"You're already registered!\n"
            f"Agent ID: `{agent_id}`\n"
            f"Role: {role}\n\n"
            f"Use /status to see your stats.",
            parse_mode="Markdown"
        )
        return

    # Show role selection buttons
    keyboard = []
    for key, info in AGENT_ROLES.items():
        keyboard.append([InlineKeyboardButton(
            f"{info['name']} ({info['reward_per_task']} pts)",
            callback_data=f"register_{key}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🤖 *Register Your Agent*\n\nPick a role:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )


async def callback_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle role selection from register buttons."""
    query = update.callback_query
    await query.answer()

    role = query.data.replace("register_", "")
    user = query.from_user
    user_id = str(user.id)

    registry = get_registry()
    result = registry.register_agent(
        name=f"{user.first_name}'s Agent",
        role=role,
        owner=user.first_name or "Anon",
        model_info="gemini-2.5-flash (telegram)",
    )

    if "error" in result:
        await query.edit_message_text(f"❌ Error: {result['error']}")
        return

    # Save mapping
    user_map = _load_user_map()
    user_map[user_id] = {
        "agent_id": result["agent_id"],
        "api_key": result["api_key"],
        "role": role,
        "username": user.username,
    }
    _save_user_map(user_map)

    role_info = AGENT_ROLES[role]
    await query.edit_message_text(
        f"✅ *Registered!*\n\n"
        f"🤖 Agent: {user.first_name}'s Agent\n"
        f"🎭 Role: {role_info['name']}\n"
        f"💰 Reward: {role_info['reward_per_task']} pts/task\n\n"
        f"*Your Agent ID:* `{result['agent_id']}`\n\n"
        f"*Next step:* Run the agent worker on your PC:\n"
        f"```\npython agent_worker.py\n```\n"
        f"Or double-click `START_AGENT.bat`\n\n"
        f"Use /wallet to set your Solana wallet for airdrops!",
        parse_mode="Markdown"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show agent status and rewards."""
    user_map = _load_user_map()
    user_id = str(update.effective_user.id)

    if user_id not in user_map:
        await update.message.reply_text("You haven't registered yet! Use /register")
        return

    agent_id = user_map[user_id]["agent_id"]
    registry = get_registry()
    agents = registry.get_all_agents()

    agent = None
    for a in agents:
        if a["agent_id"] == agent_id:
            agent = a
            break

    if not agent:
        await update.message.reply_text("Agent not found. Try /register again.")
        return

    status_emoji = "🟢" if agent["is_online"] else "🔴"
    wallet_display = agent.get("solana_wallet", "Not set") or "Not set"

    await update.message.reply_text(
        f"📊 *Your Agent Status*\n\n"
        f"{status_emoji} Status: {'ONLINE' if agent['is_online'] else 'OFFLINE'}\n"
        f"🎭 Role: {agent['role_name']}\n"
        f"✅ Tasks Done: {agent['tasks_completed']}\n"
        f"💰 Rewards: {agent['rewards']} pts\n"
        f"👛 Wallet: {wallet_display}\n"
        f"📅 Registered: {agent['registered_at'][:10]}\n\n"
        f"_Agent ID: `{agent_id}`_",
        parse_mode="Markdown"
    )


async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or update Solana wallet."""
    user_map = _load_user_map()
    user_id = str(update.effective_user.id)

    if user_id not in user_map:
        await update.message.reply_text("Register first with /register!")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "Set your Solana wallet for reward airdrops:\n\n"
            "`/wallet YOUR_SOLANA_ADDRESS`\n\n"
            "Example:\n"
            "`/wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`",
            parse_mode="Markdown"
        )
        return

    wallet = args[0]
    # Basic validation (Solana addresses are 32-44 chars, base58)
    if len(wallet) < 32 or len(wallet) > 44:
        await update.message.reply_text("That doesn't look like a valid Solana address. Should be 32-44 characters.")
        return

    agent_id = user_map[user_id]["agent_id"]
    registry = get_registry()

    # Update wallet directly
    agent = registry._agents.get(agent_id)
    if agent:
        agent.solana_wallet = wallet
        registry._save()
        await update.message.reply_text(
            f"✅ Wallet updated!\n\n"
            f"👛 `{wallet[:8]}...{wallet[-4:]}`\n\n"
            f"Your rewards will be airdropped here when we start monetizing!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Agent not found. Try /register again.")


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top agents."""
    registry = get_registry()
    agents = registry.get_all_agents()
    agents.sort(key=lambda a: a.get("rewards", 0), reverse=True)

    if not agents:
        await update.message.reply_text("No agents registered yet! Be the first with /register")
        return

    text = "🏆 *Agent Leaderboard*\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, agent in enumerate(agents[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        online = "🟢" if agent["is_online"] else "⚫"
        text += (f"{medal} {online} *{agent.get('owner', 'Anon')}* — "
                 f"{agent['rewards']} pts "
                 f"({agent['tasks_completed']} tasks)\n")

    text += f"\n_Total agents: {len(agents)}_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show who's online."""
    registry = get_registry()
    stats = registry.get_stats()

    if stats["total_online"] == 0:
        await update.message.reply_text(
            "🔴 No agents online right now.\n\n"
            "Be the first! /register and run agent_worker.py"
        )
        return

    text = f"🟢 *{stats['total_online']} Agents Online*\n\n"

    for agent in stats["agents_online"]:
        text += f"  🤖 {agent['name']} — {agent['role']}\n"
        text += f"     by {agent['owner']}\n\n"

    text += "*Roles filled:*\n"
    for role, count in stats["roles_online"].items():
        role_name = AGENT_ROLES.get(role, {}).get("name", role)
        text += f"  {role_name}: {count}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all commands."""
    await update.message.reply_text(
        "🤖 *Clankerblox Agent Bot Commands*\n\n"
        "/start — Welcome & overview\n"
        "/register — Register your agent\n"
        "/roles — Available roles & rewards\n"
        "/status — Your stats & rewards\n"
        "/wallet `<address>` — Set Solana wallet\n"
        "/leaderboard — Top agents\n"
        "/agents — Who's online now\n"
        "/help — This message\n\n"
        "*How to run your agent:*\n"
        "1. Download agent\\_worker.py from us\n"
        "2. Get free Gemini key from aistudio.google.com\n"
        "3. `python agent_worker.py`\n"
        "4. It connects, picks up tasks, earns you points!",
        parse_mode="Markdown"
    )


# ============================================================
# MAIN
# ============================================================

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("=" * 50)
        print("  Clankerblox Telegram Bot")
        print("=" * 50)
        print()
        print("No TELEGRAM_BOT_TOKEN found in .env!")
        print()
        print("How to get one:")
        print("  1. Open Telegram, search @BotFather")
        print("  2. Send /newbot")
        print("  3. Pick a name (e.g. 'Clankerblox Agents')")
        print("  4. Pick a username (e.g. 'clankerblox_bot')")
        print("  5. Copy the token")
        print("  6. Add to .env: TELEGRAM_BOT_TOKEN=your_token_here")
        print("  7. Run this script again!")
        return

    print("Starting Clankerblox Telegram Bot...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("roles", cmd_roles))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("wallet", cmd_wallet))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("agents", cmd_agents))
    app.add_handler(CommandHandler("help", cmd_help))

    # Callback for inline buttons (role selection)
    app.add_handler(CallbackQueryHandler(callback_register, pattern="^register_"))

    print("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
