#!/usr/bin/env python3
"""
Clankerblox Agent Installer — One-script setup

Downloads and starts the agent worker. No git clone needed!

USAGE (paste this one-liner in PowerShell):
  python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/YOUR_USER/Clankerblox/main/install_agent.py','install_agent.py'); exec(open('install_agent.py').read())"

OR just download and run:
  python install_agent.py
"""

import os
import sys
import subprocess
import urllib.request
import json

AGENT_SCRIPT_URL = "https://raw.githubusercontent.com/kevinzor/ClankerBlox/main/agent_worker.py"
SERVER_URL = "http://57.129.44.62:8000"

DEPS = ["httpx", "google-genai"]


def main():
    print()
    print("=" * 50)
    print("  Clankerblox Agent Installer")
    print("=" * 50)
    print()
    print("  This will set up your AI agent to help")
    print("  build Roblox games and earn reward points!")
    print()

    # Step 1: Check Python version
    if sys.version_info < (3, 9):
        print(f"ERROR: Python 3.9+ required (you have {sys.version})")
        print("Download: https://python.org/downloads")
        sys.exit(1)
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor}")

    # Step 2: Install dependencies
    print("\nInstalling dependencies...")
    for dep in DEPS:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep, "-q"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"  [OK] {dep}")
        except Exception:
            print(f"  [WARN] Could not install {dep}, trying --user...")
            subprocess.call([sys.executable, "-m", "pip", "install", dep, "--user", "-q"])

    # Step 3: Check server is reachable
    print(f"\nChecking server ({SERVER_URL})...")
    try:
        req = urllib.request.urlopen(f"{SERVER_URL}/api/status", timeout=10)
        data = json.loads(req.read())
        print(f"  [OK] Server online! Status: {data.get('status', 'ok')}")
    except Exception as e:
        print(f"  [WARN] Could not reach server: {e}")
        print("  The agent will retry automatically when it starts.")

    # Step 4: Check for agent_worker.py in current directory
    if not os.path.exists("agent_worker.py"):
        print("\nDownloading agent_worker.py...")
        try:
            urllib.request.urlretrieve(
                AGENT_SCRIPT_URL,
                "agent_worker.py"
            )
            print("  [OK] Downloaded!")
        except Exception as e:
            print(f"  [ERROR] Could not download: {e}")
            print("  Please download agent_worker.py manually from GitHub.")
            sys.exit(1)
    else:
        print("\n[OK] agent_worker.py already exists")

    # Step 5: Get Gemini API key
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if not gemini_key:
        print("\n" + "-" * 50)
        print("You need a FREE Gemini API key to power your agent.")
        print("Get one here: https://aistudio.google.com/apikey")
        print("-" * 50)
        gemini_key = input("\nPaste your Gemini API key: ").strip()
        if gemini_key:
            os.environ["GEMINI_API_KEY"] = gemini_key
        else:
            print("No key provided. The agent will ask again when it starts.")

    # Step 6: Set server URL
    os.environ["CLANKERBLOX_SERVER"] = SERVER_URL

    # Step 7: Launch!
    print("\n" + "=" * 50)
    print("  Starting your Clankerblox Agent!")
    print("=" * 50)
    print(f"  Server: {SERVER_URL}")
    print(f"  API Key: {'Set!' if gemini_key else 'Will prompt...'}")
    print()

    os.execv(sys.executable, [sys.executable, "agent_worker.py"])


if __name__ == "__main__":
    main()
