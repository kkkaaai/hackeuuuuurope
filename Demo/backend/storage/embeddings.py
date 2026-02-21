"""Embedding helpers — OpenAI text-embedding-3-small for block/pipeline search."""

import asyncio
from functools import lru_cache

from pydantic_settings import BaseSettings


class EmbeddingSettings(BaseSettings):
    openai_api_key: str = ""
    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def _get_openai():
    from openai import OpenAI
    settings = EmbeddingSettings()
    return OpenAI(api_key=settings.openai_api_key)


def generate_embedding_sync(text: str) -> list[float]:
    """Generate an embedding vector for the given text (synchronous)."""
    client = _get_openai()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text (async wrapper)."""
    return await asyncio.to_thread(generate_embedding_sync, text)


def block_to_search_text(block: dict) -> str:
    """Build a searchable text representation of a block for embedding."""
    parts = [
        block.get("name", ""),
        block.get("description", ""),
        block.get("use_when", "") or "",
        " ".join(block.get("tags", [])),
    ]
    return " ".join(p for p in parts if p).strip()
