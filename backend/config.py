"""Clankerblox Configuration"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
GAMES_OUTPUT_DIR = Path(os.getenv("GAMES_OUTPUT_DIR", str(PROJECT_ROOT / "games" / "output")))
TEMPLATES_DIR = BACKEND_DIR / "templates"
DATA_DIR = BACKEND_DIR / "data"

# Ensure directories exist
GAMES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Claude Model
CLAUDE_MODEL = "claude-opus-4-20250514"
CLAUDE_MAX_TOKENS = 4096

# Gemini Model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# Trend Analysis
TREND_SOURCES = ["brave_search", "roblox_discover", "youtube", "tiktok", "google_trends"]
TREND_SCHEDULE_HOURS = [8, 14, 20]  # 3 times a day
TARGET_MARKET = "US"
TARGET_AGE_GROUP = "10-13"

# Game Generation
MAX_GAMES_PER_DAY = 1
GAME_QUALITY = "thorough"  # fast, medium, thorough
GAME_TYPES = ["obby", "tycoon", "simulator", "minigame", "roleplay", "survival", "pvp", "story"]

# Monetization
ROBUX_PRICE_RANGE = (25, 2000)  # min/max for game passes
PREMIUM_PAYOUT_OPTIMIZE = True

# Server
API_HOST = "127.0.0.1"
API_PORT = 8000
FRONTEND_PORT = 3000
