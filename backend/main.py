"""Clankerblox - AI Roblox Game Builder - Main Entry Point"""
import sys
import os

# Fix Windows encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api.server import start_server

if __name__ == "__main__":
    print("""
    =============================================

       CLANKERBLOX - AI Roblox Game Builder

       Backend API: http://127.0.0.1:8000
       Dashboard:   http://127.0.0.1:3000

    =============================================
    """)
    start_server()
