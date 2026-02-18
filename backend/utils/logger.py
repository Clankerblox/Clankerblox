"""Clankerblox Logger - handles logging and live event broadcasting"""
import json
import sys
import os
import asyncio
from datetime import datetime
from typing import Optional
from enum import Enum

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class LogLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    STEP = "step"

class EventType(str, Enum):
    TREND_SCAN = "trend_scan"
    PLAN_CREATE = "plan_create"
    GAME_BUILD = "game_build"
    GAME_COMPLETE = "game_complete"
    GAME_ERROR = "game_error"
    SYSTEM = "system"
    MONETIZATION = "monetization"

# Global event subscribers (WebSocket connections)
_subscribers: list = []
_event_history: list = []
MAX_HISTORY = 500

def subscribe(callback):
    _subscribers.append(callback)

def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)

async def _broadcast(event: dict):
    _event_history.append(event)
    if len(_event_history) > MAX_HISTORY:
        _event_history.pop(0)

    dead = []
    for sub in _subscribers:
        try:
            await sub(event)
        except Exception:
            dead.append(sub)
    for d in dead:
        _subscribers.remove(d)

def get_history():
    return list(_event_history)

async def log(
    message: str,
    level: LogLevel = LogLevel.INFO,
    event_type: EventType = EventType.SYSTEM,
    data: Optional[dict] = None,
    game_id: Optional[str] = None
):
    timestamp = datetime.now().isoformat()
    event = {
        "timestamp": timestamp,
        "level": level.value,
        "event_type": event_type.value,
        "message": message,
        "data": data or {},
        "game_id": game_id
    }

    # Console output (Windows-safe)
    icon = {"info": "[i]", "success": "[OK]", "warning": "[!]", "error": "[ERR]", "critical": "[!!!]", "step": "[>>]"}.get(level.value, "[.]")
    try:
        print(f"[{timestamp[11:19]}] {icon} [{event_type.value}] {message}")
    except (UnicodeEncodeError, OSError):
        print(f"[{timestamp[11:19]}] {icon} [{event_type.value}] {message.encode('ascii', 'replace').decode()}")

    # Broadcast to WebSocket subscribers
    await _broadcast(event)
    return event

def log_sync(message: str, level: LogLevel = LogLevel.INFO, event_type: EventType = EventType.SYSTEM, data: Optional[dict] = None, game_id: Optional[str] = None):
    """Synchronous log for non-async contexts"""
    timestamp = datetime.now().isoformat()
    event = {
        "timestamp": timestamp,
        "level": level.value,
        "event_type": event_type.value,
        "message": message,
        "data": data or {},
        "game_id": game_id
    }
    icon = {"info": "[i]", "success": "[OK]", "warning": "[!]", "error": "[ERR]", "critical": "[!!!]", "step": "[>>]"}.get(level.value, "[.]")
    try:
        print(f"[{timestamp[11:19]}] {icon} [{event_type.value}] {message}")
    except (UnicodeEncodeError, OSError):
        print(f"[{timestamp[11:19]}] {icon} [{event_type.value}] {message.encode('ascii', 'replace').decode()}")
    _event_history.append(event)
    if len(_event_history) > MAX_HISTORY:
        _event_history.pop(0)
    return event
