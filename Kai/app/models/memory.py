from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    namespace: str = Field(default="default", max_length=256, description="Namespace for scoping keys")
    key: str = Field(..., max_length=256)
    value: Any


class MemoryQuery(BaseModel):
    namespace: str = Field(default="default", max_length=256)
    key: str | None = Field(default=None, max_length=256)
    search_text: str | None = Field(default=None, max_length=1000)
