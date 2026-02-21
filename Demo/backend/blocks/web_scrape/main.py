"""Web scrape block — fetches a URL and extracts text content."""

import httpx


async def execute(inputs: dict, context: dict) -> dict:
    url = inputs["url"]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "AgentFlow/1.0"})
        html = resp.text

    # Basic text extraction — strip HTML tags
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Extract title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""

    return {"text": text[:10_000], "title": title, "url": url}
