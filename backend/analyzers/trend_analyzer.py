"""Trend Analyzer - Scans multiple sources to find what's trending for Roblox games"""
import httpx
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from backend.config import BRAVE_API_KEY, DATA_DIR, TARGET_MARKET, TARGET_AGE_GROUP
from backend.utils.logger import log, LogLevel, EventType
from backend.utils.claude_client import ask_claude_json

# Cache file for trends
TRENDS_CACHE = DATA_DIR / "trends_cache.json"
TREND_HISTORY = DATA_DIR / "trend_history.json"


async def search_brave(query: str, count: int = 10) -> list[dict]:
    """Search Brave for trending topics."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"},
                params={"q": query, "count": count, "country": "US", "search_lang": "en"},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "source": "brave_search"
                })
            return results
        except Exception as e:
            await log(f"Brave search error: {e}", LogLevel.WARNING, EventType.TREND_SCAN)
            return []


async def search_roblox_trending() -> list[dict]:
    """Scrape Roblox discover/trending games data."""
    async with httpx.AsyncClient() as client:
        try:
            # Use Roblox Games API to get popular games
            resp = await client.get(
                "https://games.roblox.com/v1/games/list",
                params={
                    "model.sortToken": "",
                    "model.gameFilter": "1",  # Default sort (popular)
                    "model.maxRows": "20"
                },
                headers={"User-Agent": "Clankerblox/1.0"},
                timeout=15
            )
            # Fallback: use charts API
            resp2 = await client.get(
                "https://games.roblox.com/v1/games/sorts",
                headers={"User-Agent": "Clankerblox/1.0"},
                timeout=15
            )
            sorts_data = resp2.json() if resp2.status_code == 200 else {}

            # Get top games from multiple sort categories
            results = []
            sort_names = ["MostPopular", "TopEarning", "TopRated", "MostEngaging"]

            for sort in sorts_data.get("sorts", [])[:6]:
                sort_token = sort.get("token", "")
                sort_name = sort.get("name", "Unknown")
                try:
                    games_resp = await client.get(
                        "https://games.roblox.com/v1/games/list",
                        params={"model.sortToken": sort_token, "model.maxRows": "10"},
                        headers={"User-Agent": "Clankerblox/1.0"},
                        timeout=10
                    )
                    if games_resp.status_code == 200:
                        games_data = games_resp.json()
                        for game in games_data.get("games", [])[:10]:
                            results.append({
                                "title": game.get("name", ""),
                                "description": f"Players: {game.get('playerCount', 0)}, Visits: {game.get('totalUpVotes', 0)}",
                                "player_count": game.get("playerCount", 0),
                                "total_votes": game.get("totalUpVotes", 0),
                                "game_id": game.get("universeId", ""),
                                "category": sort_name,
                                "source": "roblox_api"
                            })
                except Exception:
                    continue

            return results
        except Exception as e:
            await log(f"Roblox API error: {e}", LogLevel.WARNING, EventType.TREND_SCAN)
            return []


async def search_youtube_trends() -> list[dict]:
    """Search for trending Roblox content on YouTube via Brave."""
    queries = [
        "roblox trending games 2026",
        "new roblox games popular today",
        "roblox tiktok viral games",
        "most played roblox games this week"
    ]
    results = []
    for q in queries:
        results.extend(await search_brave(q, count=5))
        await asyncio.sleep(0.3)
    return results


async def search_tiktok_trends() -> list[dict]:
    """Search for TikTok viral Roblox trends via Brave."""
    queries = [
        "tiktok viral roblox game 2026",
        "roblox meme game trending tiktok",
        "site:tiktok.com roblox game popular"
    ]
    results = []
    for q in queries:
        results.extend(await search_brave(q, count=5))
        await asyncio.sleep(0.3)
    return results


async def search_meme_trends() -> list[dict]:
    """Search for viral memes that could be turned into Roblox games."""
    queries = [
        "viral meme today 2026",
        "trending meme kids teens",
        "popular meme game concept",
        "what's trending on social media today"
    ]
    results = []
    for q in queries:
        results.extend(await search_brave(q, count=5))
        await asyncio.sleep(0.3)
    return results


async def analyze_trends() -> dict:
    """
    Run full trend analysis across all sources.
    Returns analyzed trends with game recommendations.
    """
    await log("Starting trend analysis across all sources...", LogLevel.STEP, EventType.TREND_SCAN)

    # Gather data from all sources concurrently
    brave_results, roblox_results, youtube_results, tiktok_results, meme_results = await asyncio.gather(
        search_brave("trending roblox games popular kids 2026", count=15),
        search_roblox_trending(),
        search_youtube_trends(),
        search_tiktok_trends(),
        search_meme_trends()
    )

    all_data = {
        "brave_search": brave_results,
        "roblox_trending": roblox_results,
        "youtube_trends": youtube_results,
        "tiktok_trends": tiktok_results,
        "meme_trends": meme_results,
        "scan_time": datetime.now().isoformat()
    }

    source_counts = {
        "brave": len(brave_results),
        "roblox": len(roblox_results),
        "youtube": len(youtube_results),
        "tiktok": len(tiktok_results),
        "memes": len(meme_results)
    }
    await log(
        f"Collected data: {json.dumps(source_counts)}",
        LogLevel.INFO, EventType.TREND_SCAN, data=source_counts
    )

    # Compile summaries for Claude to analyze
    summary_parts = []

    if brave_results:
        summary_parts.append("=== BRAVE SEARCH RESULTS (Trending Roblox) ===")
        for r in brave_results[:15]:
            summary_parts.append(f"- {r['title']}: {r['description'][:200]}")

    if roblox_results:
        summary_parts.append("\n=== TOP ROBLOX GAMES RIGHT NOW ===")
        for r in roblox_results[:20]:
            summary_parts.append(f"- {r['title']} ({r.get('category','')}) - Players: {r.get('player_count', '?')}")

    if youtube_results:
        summary_parts.append("\n=== YOUTUBE TRENDING ROBLOX CONTENT ===")
        for r in youtube_results[:10]:
            summary_parts.append(f"- {r['title']}: {r['description'][:150]}")

    if tiktok_results:
        summary_parts.append("\n=== TIKTOK VIRAL ROBLOX TRENDS ===")
        for r in tiktok_results[:10]:
            summary_parts.append(f"- {r['title']}: {r['description'][:150]}")

    if meme_results:
        summary_parts.append("\n=== VIRAL MEMES (potential game ideas) ===")
        for r in meme_results[:10]:
            summary_parts.append(f"- {r['title']}: {r['description'][:150]}")

    trend_summary = "\n".join(summary_parts)

    # Ask Claude to analyze and recommend game concepts
    await log("Asking Claude to analyze trends and recommend game concepts...", LogLevel.STEP, EventType.TREND_SCAN)

    analysis = await ask_claude_json(
        prompt=f"""Analyze these trending topics and Roblox game data. Recommend exactly 3 game concepts that would be HIGHLY likely to go viral and earn revenue on Roblox.

Target audience: Kids/teens aged {TARGET_AGE_GROUP} in {TARGET_MARKET}
Focus: Games that are FUN, addictive, and leverage current viral trends/memes

TREND DATA:
{trend_summary}

For each game concept, provide:
1. A catchy game name that kids would click on
2. Game type (obby, tycoon, simulator, survival, pvp, roleplay, minigame, story)
3. Core gameplay loop (what players DO every 30 seconds)
4. Why it's trending / what trend it capitalizes on
5. Viral potential score (1-10)
6. Revenue potential score (1-10)
7. Estimated development complexity (simple/medium/complex)
8. Key hooks that keep players coming back
9. Suggested monetization items (game passes, dev products) with Robux prices
10. SEO-optimized title and description for the Roblox game page

Return JSON in this exact format:
{{
    "analysis_summary": "Brief overview of current trends",
    "trend_insights": ["insight1", "insight2", "insight3"],
    "game_concepts": [
        {{
            "name": "Game Name Here",
            "game_type": "obby",
            "tagline": "Short catchy tagline",
            "trend_connection": "What trend this capitalizes on",
            "core_loop": "What players do every 30 seconds",
            "viral_score": 8,
            "revenue_score": 7,
            "complexity": "medium",
            "hooks": ["hook1", "hook2", "hook3"],
            "monetization": [
                {{"item": "VIP Pass", "type": "gamepass", "robux_price": 199, "description": "What it gives"}}
            ],
            "roblox_title": "SEO optimized title",
            "roblox_description": "SEO optimized description for Roblox page",
            "keywords": ["keyword1", "keyword2"]
        }}
    ]
}}""",
        system="""You are Clankerblox, an expert Roblox game trend analyst. You understand what makes games go viral on Roblox, especially for kids aged 10-13. You know the Roblox meta: what types of games get the most plays, what monetization works, and what trends from TikTok/YouTube translate into successful Roblox games.

Your recommendations must be ACTIONABLE - each game must be buildable as a complete Roblox game with Lua scripting. Focus on proven game patterns (obby, tycoon, simulator) but with fresh viral twists.

Monetization must MAKE SENSE with the gameplay - don't suggest irrelevant items. Every purchase should enhance the core gameplay loop.""",
        max_tokens=4096,
        temperature=0.8
    )

    # Save to cache
    result = {
        "timestamp": datetime.now().isoformat(),
        "raw_data": {k: len(v) if isinstance(v, list) else v for k, v in all_data.items()},
        "analysis": analysis
    }

    with open(TRENDS_CACHE, "w") as f:
        json.dump(result, f, indent=2)

    # Append to history
    history = []
    if TREND_HISTORY.exists():
        try:
            with open(TREND_HISTORY) as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(result)
    # Keep last 50 analyses
    history = history[-50:]
    with open(TREND_HISTORY, "w") as f:
        json.dump(history, f, indent=2)

    await log(
        f"Trend analysis complete! Found {len(analysis.get('game_concepts', []))} game concepts",
        LogLevel.SUCCESS, EventType.TREND_SCAN,
        data={"concepts": [c["name"] for c in analysis.get("game_concepts", [])]}
    )

    return result


async def get_cached_trends() -> Optional[dict]:
    """Get the most recent cached trend analysis."""
    if TRENDS_CACHE.exists():
        with open(TRENDS_CACHE) as f:
            return json.load(f)
    return None


async def get_trend_history() -> list:
    """Get trend analysis history."""
    if TREND_HISTORY.exists():
        try:
            with open(TREND_HISTORY) as f:
                return json.load(f)
        except Exception:
            return []
    return []
