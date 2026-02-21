from __future__ import annotations

import logging
from typing import Any

import httpx

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.miro")

MIRO_API = "https://api.miro.com/v2"


@register_implementation("miro_add_node")
async def miro_add_node(inputs: dict[str, Any]) -> dict[str, Any]:
    """Add a sticky note node to the Miro memory board."""
    content = inputs["content"]
    color = inputs.get("color", "yellow")
    tags = inputs.get("tags", [])

    color_map = {
        "yellow": "yellow",
        "blue": "blue",
        "green": "green",
        "red": "red",
        "orange": "orange",
        "purple": "dark_blue",
    }

    if not settings.miro_api_token or not settings.miro_board_id:
        raise ValueError("MIRO_API_TOKEN and MIRO_BOARD_ID must both be configured — add them to .env")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MIRO_API}/boards/{settings.miro_board_id}/sticky_notes",
                headers={"Authorization": f"Bearer {settings.miro_api_token}"},
                json={
                    "data": {"content": content, "shape": "square"},
                    "style": {"fillColor": color_map.get(color, "yellow")},
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Miro API error: {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ValueError(f"Miro API request failed: {e}") from e

    return {
        "node_id": data.get("id", ""),
        "board_url": f"https://miro.com/app/board/{settings.miro_board_id}/",
    }


@register_implementation("miro_add_connection")
async def miro_add_connection(inputs: dict[str, Any]) -> dict[str, Any]:
    """Draw a connector between two existing nodes on the Miro board."""
    from_node_id = inputs["from_node_id"]
    to_node_id = inputs["to_node_id"]
    label = inputs.get("label", "")

    if not settings.miro_api_token or not settings.miro_board_id:
        raise ValueError("MIRO_API_TOKEN and MIRO_BOARD_ID must both be configured — add them to .env")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MIRO_API}/boards/{settings.miro_board_id}/connectors",
                headers={"Authorization": f"Bearer {settings.miro_api_token}"},
                json={
                    "startItem": {"id": from_node_id},
                    "endItem": {"id": to_node_id},
                    "captions": [{"content": label}] if label else [],
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Miro API error: {e.response.status_code}") from e
    except httpx.RequestError as e:
        raise ValueError(f"Miro API request failed: {e}") from e

    return {
        "connection_id": data.get("id", ""),
        "success": True,
    }
