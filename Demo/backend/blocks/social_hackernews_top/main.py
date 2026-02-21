"""Hacker News top stories block — fetches from the official HN API."""

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    count = min(max(inputs.get("count", 10), 1), 30)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
        story_ids = resp.json()[:count]

        stories = []
        for sid in story_ids:
            item_resp = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
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
