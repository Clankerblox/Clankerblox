@echo off
title Clankerblox Agent Worker
echo.
echo  ========================================
echo   Clankerblox Community Agent Worker
echo  ========================================
echo.

:: Install dependencies
pip install httpx google-genai >nul 2>&1

:: Set Gemini API key from .env
for /f "tokens=2 delims==" %%a in ('findstr "GEMINI_API_KEY" .env') do set GEMINI_API_KEY=%%a

:: Run the agent
python agent_worker.py

pause
