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
    fields: dict[str, str] = inputs["fields"]

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, timeout=15.0)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    data = {}

    for field_name, selector in fields.items():
        element = soup.select_one(selector)
        data[field_name] = element.get_text(strip=True) if element else None

    return {"data": data}
