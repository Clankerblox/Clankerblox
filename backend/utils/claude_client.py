"""Claude API Client wrapper for Clankerblox - with rate limit handling"""
import time
import asyncio
import anthropic
from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS
from backend.utils.logger import log_sync, LogLevel, EventType

_client = None

# Rate limiting: track last request time to space them out
_last_request_time = 0
MIN_REQUEST_INTERVAL = 12  # seconds between requests (safe margin for 8k tokens/min)


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def ask_claude(
    prompt: str,
    system: str = "",
    max_tokens: int = CLAUDE_MAX_TOKENS,
    temperature: float = 0.7,
    max_retries: int = 5
) -> str:
    """Send a prompt to Claude and return the response text.
    Includes automatic rate limit handling with exponential backoff."""
    global _last_request_time
    client = get_client()

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature
    }
    if system:
        kwargs["system"] = system

    for attempt in range(max_retries):
        # Rate limiting: ensure minimum interval between requests
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed
            log_sync(f"Rate limit spacing: waiting {wait_time:.1f}s before API call", LogLevel.INFO, EventType.SYSTEM)
            await asyncio.sleep(wait_time)

        try:
            _last_request_time = time.time()
            response = client.messages.create(**kwargs)
            return response.content[0].text

        except anthropic.RateLimitError as e:
            # Exponential backoff: 30s, 60s, 120s, 240s, 480s
            backoff = 30 * (2 ** attempt)
            log_sync(
                f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {backoff}s...",
                LogLevel.WARNING, EventType.SYSTEM
            )
            await asyncio.sleep(backoff)

        except anthropic.APIError as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                backoff = 30 * (2 ** attempt)
                log_sync(
                    f"API rate limit (attempt {attempt + 1}/{max_retries}). Waiting {backoff}s...",
                    LogLevel.WARNING, EventType.SYSTEM
                )
                await asyncio.sleep(backoff)
            else:
                raise

    raise Exception(f"Failed after {max_retries} retries due to rate limiting")


async def ask_claude_json(
    prompt: str,
    system: str = "",
    max_tokens: int = CLAUDE_MAX_TOKENS,
    temperature: float = 0.5
) -> dict:
    """Send a prompt to Claude and parse the response as JSON."""
    import json

    if system:
        system += "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no code blocks, no extra text."
    else:
        system = "IMPORTANT: Respond with valid JSON only. No markdown, no code blocks, no extra text."

    response_text = await ask_claude(prompt, system, max_tokens, temperature)

    # Clean up response - remove markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    return json.loads(text)
