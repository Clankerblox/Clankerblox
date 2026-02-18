@echo off
title Clankerblox Telegram Bot
echo.
echo  ========================================
echo   Clankerblox Telegram Agent Bot
echo  ========================================
echo.

pip install python-telegram-bot python-dotenv >nul 2>&1

python telegram_bot.py

pause
