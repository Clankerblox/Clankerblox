@echo off
chcp 65001 >nul 2>&1
title Clankerblox - AI Roblox Game Builder
echo.
echo  ========================================
echo   CLANKERBLOX - AI Roblox Game Builder
echo  ========================================
echo.

cd /d "%~dp0"

echo [1/3] Installing Python dependencies...
pip install -r backend\requirements.txt --quiet 2>nul
echo       Done!

echo [2/3] Starting Backend API server...
set PYTHONIOENCODING=utf-8
start "ClankerbloxBackend" cmd /c "cd /d "%~dp0" && set PYTHONIOENCODING=utf-8 && python -m backend.main"
timeout /t 4 /nobreak > nul

echo [3/3] Starting Frontend dashboard...
cd frontend
call npm run dev
