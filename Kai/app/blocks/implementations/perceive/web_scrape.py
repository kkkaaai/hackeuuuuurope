from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.blocks.executor import register_implementation

logger = logging.getLogger("agentflow.blocks.web_scrape")

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / AWS IMDS
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def validate_url(url: str) -> str:
    """Validate URL: HTTPS/HTTP only, no private/loopback IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Blocked URL scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")

    try:
        resolved = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {parsed.hostname}")

    for family, _, _, _, addr in resolved:
        ip = ipaddress.ip_address(addr[0])
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise ValueError(f"Blocked private/internal IP: {ip}")

    return url


@register_implementation("web_scrape")
async def web_scrape(inputs: dict[str, Any]) -> dict[str, Any]:
    """Scrape text content from a URL, optionally using a CSS selector."""
    url = validate_url(inputs["url"])
    selector = inputs.get("selector")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, timeout=15.0)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    if selector:
        elements = soup.select(selector)
        text = "\n".join(el.get_text(strip=True) for el in elements)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Truncate to avoid massive outputs
    max_chars = 10000
    if len(text) > max_chars:
        text = text[:max_chars] + "..."

    return {"text": text, "title": title, "url": str(url)}
