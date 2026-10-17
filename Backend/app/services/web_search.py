"""Web search for the remedy agent. Uses Tavily when a key is configured, DuckDuckGo otherwise."""

import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _tavily(query: str, max_results: int, api_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": api_key, "query": query, "max_results": max_results},
        )
        response.raise_for_status()
    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
        for r in response.json().get("results", [])
    ]


def _duckduckgo(query: str, max_results: int) -> list[dict]:
    from ddgs import DDGS

    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in DDGS().text(query, max_results=max_results)
    ]


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    settings = get_settings()
    try:
        if settings.tavily_api_key:
            return await _tavily(query, max_results, settings.tavily_api_key)
        return await asyncio.to_thread(_duckduckgo, query, max_results)
    except Exception as e:  # search backends raise a variety of errors; never fail the turn
        logger.warning("Web search failed: %s", e)
        return []
