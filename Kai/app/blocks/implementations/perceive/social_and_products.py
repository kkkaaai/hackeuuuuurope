from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.blocks.executor import register_implementation
from app.blocks.implementations.perceive.web_scrape import validate_url

logger = logging.getLogger("agentflow.blocks.social")

HN_API = "https://hacker-news.firebaseio.com/v0"


@register_implementation("social_hackernews_top")
async def social_hackernews_top(inputs: dict[str, Any]) -> dict[str, Any]:
    """Fetch top stories from Hacker News API."""
    count = int(inputs.get("count", 10))

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HN_API}/topstories.json", timeout=10.0)
        resp.raise_for_status()
        story_ids = resp.json()[:count]

        stories = []
        for sid in story_ids:
            item_resp = await client.get(f"{HN_API}/item/{sid}.json", timeout=10.0)
            item = item_resp.json()
            if item:
                stories.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    "score": item.get("score", 0),
                    "author": item.get("by", ""),
                    "comments": item.get("descendants", 0),
                })

    return {"stories": stories}


@register_implementation("product_get_price")
async def product_get_price(inputs: dict[str, Any]) -> dict[str, Any]:
    """Scrape the current price of a product from its URL."""
    raw_url = inputs["url"]
    # Handle case where a list of search results is passed instead of a URL string
    if isinstance(raw_url, list):
        # Extract the first URL from the results list
        for item in raw_url:
            if isinstance(item, dict) and "url" in item:
                raw_url = item["url"]
                break
            elif isinstance(item, str) and item.startswith("http"):
                raw_url = item
                break
        else:
            raw_url = str(raw_url[0]) if raw_url else ""
    url = validate_url(str(raw_url))
    price_selector = inputs.get("price_selector")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            url,
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AgentFlow/1.0)"},
        )
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    title_tag = soup.title
    product_name = title_tag.string.strip() if title_tag and title_tag.string else ""

    price = None
    currency = "EUR"

    if price_selector:
        el = soup.select_one(price_selector)
        if el:
            price_text = el.get_text(strip=True)
            price = _parse_price(price_text)
    else:
        # Try common price selectors
        for selector in [".price", "#price", "[data-price]", ".a-price-whole", ".product-price"]:
            el = soup.select_one(selector)
            if el:
                price_text = el.get_text(strip=True)
                price = _parse_price(price_text)
                if price is not None:
                    break

    return {
        "price": price,
        "currency": currency,
        "product_name": product_name,
        "in_stock": True,
    }


def _parse_price(text: str) -> float | None:
    """Extract a numeric price from text like '$49.99' or '49,99 €'."""
    import re

    cleaned = re.sub(r"[^\d.,]", "", text)
    # Handle European format: 49,99 -> 49.99
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None
