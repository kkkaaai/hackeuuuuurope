from __future__ import annotations

import logging
from typing import Any

import httpx

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.web_search")

SERPER_URL = "https://google.serper.dev/search"


@register_implementation("web_search")
async def web_search(inputs: dict[str, Any]) -> dict[str, Any]:
    """Search the web using Serper API (Google Search)."""
    query = inputs["query"]
    num_results = int(inputs.get("num_results", 5))

    if not settings.serper_api_key:
        raise ValueError("SERPER_API_KEY not configured — add it to .env")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SERPER_URL,
                headers={"X-API-KEY": settings.serper_api_key},
                json={"q": query, "num": num_results},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Serper API error: {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ValueError(f"Serper API request failed: {e}") from e

    results = []
    for item in data.get("organic", [])[:num_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })

    return {"results": results}
