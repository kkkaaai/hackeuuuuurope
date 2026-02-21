"""Seed the 5 core system blocks into Supabase.

Usage:
    cd Demo/backend
    python -m scripts.seed_blocks
"""

import sys
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from storage.supabase_client import get_supabase
from storage.embeddings import generate_embedding_sync, block_to_search_text

# ────────────────────────────────────────────
# 5 core system blocks
# ────────────────────────────────────────────

SEED_BLOCKS = [
    {
        "id": "web_search",
        "name": "Web Search",
        "description": "Search the web using Serper API and return organic results.",
        "category": "input",
        "execution_type": "python",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "description": "List of search results with title, link, snippet",
                }
            },
            "required": ["results"],
        },
        "source_code": '''"""Web search via Serper API."""
import os
import httpx

async def execute(inputs: dict, context: dict) -> dict:
    query = inputs["query"]
    api_key = os.environ.get("SERPER_API_KEY", "")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 10},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })
    return {"results": results}
''',
        "use_when": "When you need to search the internet for current information, prices, news, or any web content.",
        "tags": ["search", "web", "internet", "google", "serper"],
        "examples": [
            {"inputs": {"query": "PS5 price 2025"}, "outputs": {"results": [{"title": "PS5 Price", "link": "https://example.com", "snippet": "..."}]}}
        ],
        "metadata": {"created_by": "system", "tier": 0},
    },
    {
        "id": "web_scrape",
        "name": "Web Scrape",
        "description": "Fetch and extract text content from a URL.",
        "category": "input",
        "execution_type": "python",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to scrape"},
                "max_length": {"type": "integer", "description": "Max characters to return", "default": 5000},
            },
            "required": ["url"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Extracted text content"},
                "url": {"type": "string", "description": "The URL that was scraped"},
                "status_code": {"type": "integer", "description": "HTTP status code"},
            },
            "required": ["content", "url"],
        },
        "source_code": '''"""Web scrape — fetch text content from a URL."""
import re
import httpx

async def execute(inputs: dict, context: dict) -> dict:
    url = inputs["url"]
    max_length = inputs.get("max_length", 5000)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(url, timeout=15.0, headers={"User-Agent": "AgentFlow/1.0"})
        resp.raise_for_status()
        html = resp.text
    # Strip HTML tags for plain text
    text = re.sub(r"<script[^>]*>[\\s\\S]*?</script>", "", html)
    text = re.sub(r"<style[^>]*>[\\s\\S]*?</style>", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\\s+", " ", text).strip()
    return {"content": text[:max_length], "url": url, "status_code": resp.status_code}
''',
        "use_when": "When you need to fetch and read the content of a specific web page or URL.",
        "tags": ["scrape", "web", "fetch", "url", "html", "content"],
        "examples": [
            {"inputs": {"url": "https://example.com"}, "outputs": {"content": "Example Domain...", "url": "https://example.com", "status_code": 200}}
        ],
        "metadata": {"created_by": "system", "tier": 0},
    },
    {
        "id": "memory_read",
        "name": "Memory Read",
        "description": "Read a value from the user's persistent memory stored in Supabase.",
        "category": "memory",
        "execution_type": "python",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key to read"}
            },
            "required": ["key"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "value": {"description": "The stored value, or null if not found"}
            },
            "required": ["value"],
        },
        "source_code": '''"""Memory read — read from Supabase user_memory table."""

async def execute(inputs: dict, context: dict) -> dict:
    key = inputs["key"]
    supabase = context.get("supabase")
    user_id = context.get("user_id", "default_user")
    if supabase:
        result = supabase.table("user_memory").select("value").eq("user_id", user_id).eq("key", key).execute()
        if result.data:
            return {"value": result.data[0]["value"]}
    # Fallback to in-context memory
    memory = context.get("memory", {})
    return {"value": memory.get(key)}
''',
        "use_when": "When you need to recall previously stored information for a user.",
        "tags": ["memory", "read", "recall", "storage", "persistence"],
        "examples": [
            {"inputs": {"key": "budget"}, "outputs": {"value": 500}}
        ],
        "metadata": {"created_by": "system", "tier": 0},
    },
    {
        "id": "memory_write",
        "name": "Memory Write",
        "description": "Write a value to the user's persistent memory in Supabase.",
        "category": "memory",
        "execution_type": "python",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key to write"},
                "value": {"description": "Value to store"},
            },
            "required": ["key", "value"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "description": "Whether the write succeeded"}
            },
            "required": ["success"],
        },
        "source_code": '''"""Memory write — upsert into Supabase user_memory table."""
import json

async def execute(inputs: dict, context: dict) -> dict:
    key = inputs["key"]
    value = inputs["value"]
    supabase = context.get("supabase")
    user_id = context.get("user_id", "default_user")
    if supabase:
        supabase.table("user_memory").upsert({
            "user_id": user_id,
            "key": key,
            "value": json.dumps(value) if not isinstance(value, str) else json.dumps(value),
        }).execute()
    # Also update in-context memory so later blocks see it
    memory = context.get("memory", {})
    memory[key] = value
    return {"success": True}
''',
        "use_when": "When you need to store information for later recall, such as user preferences, computed results, or state.",
        "tags": ["memory", "write", "store", "save", "persistence"],
        "examples": [
            {"inputs": {"key": "budget", "value": 500}, "outputs": {"success": True}}
        ],
        "metadata": {"created_by": "system", "tier": 0},
    },
    {
        "id": "notify_push",
        "name": "Push Notification",
        "description": "Send a push notification to the user via Supabase notifications table.",
        "category": "action",
        "execution_type": "python",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Notification title"},
                "body": {"type": "string", "description": "Notification body text"},
            },
            "required": ["title", "body"],
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "delivered": {"type": "boolean", "description": "Whether the notification was delivered"}
            },
            "required": ["delivered"],
        },
        "source_code": '''"""Push notification — insert into Supabase notifications table."""

async def execute(inputs: dict, context: dict) -> dict:
    title = inputs["title"]
    body = inputs["body"]
    supabase = context.get("supabase")
    user_id = context.get("user_id", "default_user")
    if supabase:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "body": body,
        }).execute()
    return {"delivered": True}
''',
        "use_when": "When you need to alert or notify the user about results, events, or important information.",
        "tags": ["notify", "push", "alert", "notification", "message"],
        "examples": [
            {"inputs": {"title": "Price Alert", "body": "PS5 is now $399!"}, "outputs": {"delivered": True}}
        ],
        "metadata": {"created_by": "system", "tier": 0},
    },
]


def seed():
    """Upsert all seed blocks into Supabase with embeddings."""
    sb = get_supabase()

    for block in SEED_BLOCKS:
        print(f"  Seeding {block['id']}...")

        # Generate embedding
        search_text = block_to_search_text(block)
        embedding = generate_embedding_sync(search_text)

        row = {
            "id": block["id"],
            "name": block["name"],
            "description": block["description"],
            "category": block["category"],
            "execution_type": block["execution_type"],
            "input_schema": block["input_schema"],
            "output_schema": block["output_schema"],
            "prompt_template": block.get("prompt_template"),
            "source_code": block.get("source_code"),
            "use_when": block.get("use_when"),
            "tags": block.get("tags", []),
            "examples": block.get("examples", []),
            "metadata": block.get("metadata", {}),
            "embedding": embedding,
        }

        sb.table("blocks").upsert(row).execute()
        print(f"    ✓ {block['id']} seeded")

    print(f"\nDone! {len(SEED_BLOCKS)} blocks seeded.")


if __name__ == "__main__":
    seed()
