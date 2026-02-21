"""Miro add node block — creates a sticky note on a Miro board."""

import os

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    content = inputs["content"]
    color = inputs.get("color", "yellow")

    api_token = os.environ.get("MIRO_API_TOKEN", "")
    board_id = os.environ.get("MIRO_BOARD_ID", "")

    if not api_token or not board_id:
        print(f"[MIRO STUB] add node: {content} ({color})")
        return {"node_id": "stub_node", "board_url": ""}

    color_map = {
        "yellow": "yellow", "blue": "blue", "green": "green",
        "red": "red", "purple": "dark_blue",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.miro.com/v2/boards/{board_id}/sticky_notes",
            headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
            json={
                "data": {"content": content, "shape": "square"},
                "style": {"fillColor": color_map.get(color, "yellow")},
            },
        )

    if resp.status_code in (200, 201):
        data = resp.json()
        return {
            "node_id": data.get("id", ""),
            "board_url": f"https://miro.com/app/board/{board_id}/",
        }

    return {"node_id": "", "board_url": ""}
