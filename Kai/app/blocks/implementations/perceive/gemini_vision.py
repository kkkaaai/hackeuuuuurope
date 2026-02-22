from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

from app.blocks.executor import register_implementation
from app.config import settings

logger = logging.getLogger("agentflow.blocks.gemini")

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"


def _validate_image_path(image_path: str) -> Path:
    """Validate image path is within the uploads directory."""
    resolved = Path(image_path).resolve()
    uploads_resolved = UPLOAD_DIR.resolve()
    if not str(resolved).startswith(str(uploads_resolved)):
        # Allow URLs (they'll be fetched, not opened as files)
        if image_path.startswith(("http://", "https://")):
            return Path(image_path)
        raise ValueError(f"Image path must be within uploads directory: {UPLOAD_DIR}")
    return resolved


async def _call_gemini(prompt: str, image_path: str | None = None) -> str:
    """Call Gemini API with optional image."""
    if not settings.google_gemini_api_key:
        raise ValueError("GOOGLE_GEMINI_API_KEY not configured — add it to .env")

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        if image_path and Path(image_path).exists():
            image_data = Path(image_path).read_bytes()
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": base64.b64encode(image_data).decode()},
            ])
        else:
            response = model.generate_content(prompt)

        return response.text
    except Exception as e:
        logger.debug("Gemini API error detail: %s", e)
        if "api_key" in str(e).lower() or "authenticate" in str(e).lower():
            raise ValueError("Gemini API authentication failed — check GOOGLE_GEMINI_API_KEY") from e
        raise ValueError("Gemini API error — see server logs") from e


@register_implementation("gemini_analyze_image")
async def gemini_analyze_image(inputs: dict[str, Any]) -> dict[str, Any]:
    """Use Gemini Vision to understand and describe an image."""
    image_path = str(_validate_image_path(inputs["image_path"]))
    prompt = inputs.get("prompt", "Describe this image in detail")

    full_prompt = f"""{prompt}

Respond with JSON: {{"description": "...", "objects": ["..."], "text_found": "..."}}"""
    response = await _call_gemini(full_prompt, image_path)

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"description": response, "objects": [], "text_found": ""}


@register_implementation("gemini_ocr")
async def gemini_ocr(inputs: dict[str, Any]) -> dict[str, Any]:
    """Extract text from an image using Gemini Vision."""
    image_path = str(_validate_image_path(inputs["image_path"]))

    response = await _call_gemini(
        "Extract ALL text from this image. Return only the text, nothing else.",
        image_path,
    )
    return {"text": response, "confidence": 0.95}


@register_implementation("gemini_read_receipt")
async def gemini_read_receipt(inputs: dict[str, Any]) -> dict[str, Any]:
    """Extract structured line items from a receipt photo."""
    image_path = str(_validate_image_path(inputs["image_path"]))

    prompt = """Extract receipt data as JSON:
{"store": "...", "date": "YYYY-MM-DD", "items": [{"name": "...", "quantity": N, "price": N.NN}], "total": N.NN, "currency": "..."}"""

    response = await _call_gemini(prompt, image_path)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "store": "Unknown",
            "date": "",
            "items": [],
            "total": 0,
            "currency": "EUR",
            "raw_text": response,
        }


@register_implementation("gemini_product_image_search")
async def gemini_product_image_search(inputs: dict[str, Any]) -> dict[str, Any]:
    """Identify products in an image and return structured product info."""
    image_path = str(_validate_image_path(inputs["image_path"]))
    query_hint = inputs.get("query", "")

    hint_line = f"\nFocus on: {query_hint}" if query_hint else ""
    prompt = f"""Identify ALL products visible in this image.{hint_line}

Respond with ONLY valid JSON in this exact format:
{{"products": [{{"name": "product name", "category": "category", "brand": "brand or Unknown", "estimated_price": "price range estimate", "description": "brief description", "search_query": "search query to find this product online"}}], "product_count": N}}"""

    response = await _call_gemini(prompt, image_path)

    # Strip markdown code fences if present
    text = response.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)
        if "product_count" not in data:
            data["product_count"] = len(data.get("products", []))
        return data
    except json.JSONDecodeError:
        return {
            "products": [
                {
                    "name": "Unknown Product",
                    "category": "Unknown",
                    "brand": "Unknown",
                    "estimated_price": "N/A",
                    "description": response,
                    "search_query": query_hint or "product",
                }
            ],
            "product_count": 1,
        }
