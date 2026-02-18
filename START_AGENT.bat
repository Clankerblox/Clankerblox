@echo off
title Clankerblox Agent Worker
echo.
echo  ========================================
echo   Clankerblox Community Agent Worker
echo  ========================================
echo.
echo  Supports: Gemini (FREE), Claude, GPT-4o, DeepSeek
echo.

:: Install base dependency
pip install httpx >nul 2>&1

:: Run the agent (it handles model selection + deps)
python agent_worker.py

pause
