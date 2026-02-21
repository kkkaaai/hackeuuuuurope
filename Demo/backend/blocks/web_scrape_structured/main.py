"""Structured web scrape block — extracts fields by CSS selector (basic regex fallback)."""

import re

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    url = inputs["url"]
    fields = inputs.get("fields", {})

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "AgentFlow/1.0"})
        html = resp.text

    data = {}
    for name, selector in fields.items():
        # Basic regex extraction using class/id from the selector
        pattern = selector.replace(".", r'class="[^"]*\b') + r'[^"]*"[^>]*>(.*?)<'
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        data[name] = match.group(1).strip() if match else ""

    return {"data": data}
