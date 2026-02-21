"""Miro add connection block — creates a connector between two nodes on a Miro board."""

import os

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    from_id = inputs["from_node_id"]
    to_id = inputs["to_node_id"]
    label = inputs.get("label", "")

    api_token = os.environ.get("MIRO_API_TOKEN", "")
    board_id = os.environ.get("MIRO_BOARD_ID", "")

    if not api_token or not board_id:
        print(f"[MIRO STUB] connect: {from_id} -> {to_id} ({label})")
        return {"connection_id": "stub_conn", "success": True}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"https://api.miro.com/v2/boards/{board_id}/connectors",
            headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
            json={
                "startItem": {"id": from_id},
                "endItem": {"id": to_id},
                "captions": [{"content": label}] if label else [],
            },
        )

    if resp.status_code in (200, 201):
        data = resp.json()
        return {"connection_id": data.get("id", ""), "success": True}

    return {"connection_id": "", "success": False}
