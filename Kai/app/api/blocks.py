"""Block registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_registry
from app.models.block import BlockCategory, BlockDefinition

router = APIRouter(prefix="/api", tags=["blocks"])


class BlockSearchRequest(BaseModel):
    query: str = Field(..., max_length=500)


@router.get("/blocks", response_model=list[BlockDefinition])
async def list_blocks(category: str | None = None) -> list[BlockDefinition]:
    """List all blocks, optionally filtered by category."""
    registry = get_registry()
    if category:
        try:
            cat = BlockCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
        return registry.list_by_category(cat)
    return registry.list_all()


@router.get("/blocks/{block_id}", response_model=BlockDefinition)
async def get_block(block_id: str) -> BlockDefinition:
    """Get a block by ID."""
    registry = get_registry()
    block = registry.get(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")
    return block


@router.post("/blocks/search", response_model=list[BlockDefinition])
async def search_blocks(request: BlockSearchRequest) -> list[BlockDefinition]:
    """Search blocks by keyword."""
    registry = get_registry()
    return registry.search(request.query)
