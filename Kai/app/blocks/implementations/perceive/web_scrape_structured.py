from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.blocks.executor import register_implementation
from app.blocks.implementations.perceive.web_scrape import validate_url

logger = logging.getLogger("agentflow.blocks.web_scrape_structured")


@register_implementation("web_scrape_structured")
async def web_scrape_structured(inputs: dict[str, Any]) -> dict[str, Any]:
    """Extract specific structured fields from a webpage using CSS selectors."""
    url = validate_url(inputs["url"])
    fields = inputs["fields"]

    if not isinstance(fields, dict):
        raise TypeError(
            f"'fields' must be a dict mapping field names to CSS selectors, "
            f"got {type(fields).__name__}: {str(fields)[:120]}"
        )

    for field_name, selector in fields.items():
        if not isinstance(selector, str):
            raise TypeError(
                f"CSS selector for field '{field_name}' must be a string, "
                f"got {type(selector).__name__}: {str(selector)[:80]}"
            )

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, timeout=15.0)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    data = {}

    for field_name, selector in fields.items():
        element = soup.select_one(selector)
        data[field_name] = element.get_text(strip=True) if element else None

    return {"data": data}
