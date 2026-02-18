"""Gemini API Client wrapper for Clankerblox - using google.genai (new SDK)"""
import time
import json
import asyncio
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.utils.logger import log_sync, LogLevel, EventType

_client = None

# Rate limiting
_last_request_time = 0
MIN_REQUEST_INTERVAL = 4  # seconds between requests


def get_client() -> genai.Client:
    """Get or create the Gemini client (singleton)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def ask_gemini(
    prompt: str,
    system: str = "",
    max_tokens: int = 8192,
    temperature: float = 0.7,
    max_retries: int = 5
) -> str:
    """Send a prompt to Gemini and return the response text."""
    global _last_request_time
    client = get_client()

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
    )
    if system:
        config.system_instruction = system

    for attempt in range(max_retries):
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed
            await asyncio.sleep(wait_time)

        try:
            _last_request_time = time.time()
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            return response.text

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
                backoff = 15 * (2 ** attempt)
                log_sync(
                    f"Gemini rate limit (attempt {attempt + 1}/{max_retries}). Waiting {backoff}s...",
                    LogLevel.WARNING, EventType.SYSTEM
                )
                await asyncio.sleep(backoff)
            else:
                raise

    raise Exception(f"Gemini: Failed after {max_retries} retries")


async def ask_gemini_json(
    prompt: str,
    system: str = "",
    max_tokens: int = 8192,
    temperature: float = 0.5
) -> dict:
    """Send a prompt to Gemini and parse the response as JSON."""
    if system:
        system += "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no code blocks, no extra text."
    else:
        system = "IMPORTANT: Respond with valid JSON only. No markdown, no code blocks, no extra text."

    response_text = await ask_gemini(prompt, system, max_tokens, temperature)

    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    return json.loads(text)
