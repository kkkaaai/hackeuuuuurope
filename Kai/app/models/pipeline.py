from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    CREATED = "created"
    APPROVED = "approved"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    MANUAL = "manual"
    WEBHOOK = "webhook"
    FILE_UPLOAD = "file_upload"
    EVENT = "event"


class TriggerConfig(BaseModel):
    type: TriggerType
    schedule: str | None = Field(default=None, max_length=128)
    interval_seconds: int | None = Field(default=None, ge=10, description="Minimum 10 seconds")
    webhook_path: str | None = Field(default=None, max_length=256)


class PipelineNode(BaseModel):
    id: str = Field(..., max_length=128, description="Unique node ID within the pipeline")
    block_id: str = Field(..., max_length=128, description="References a BlockDefinition.id")
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Input mapping — values can be literals or templates like {{node_id.field}}",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Static config for this block invocation",
    )


class PipelineEdge(BaseModel):
    from_node: str = Field(..., max_length=128)
    to_node: str = Field(..., max_length=128)
    condition: str | None = Field(
        default=None,
        max_length=512,
        description="Optional condition expression for conditional routing",
    )


class Pipeline(BaseModel):
    id: str = Field(..., max_length=128, description="Unique pipeline ID")
    user_intent: str = Field(..., max_length=2000, description="Original natural language request")
    trigger: TriggerConfig
    nodes: list[PipelineNode]
    edges: list[PipelineEdge]
    memory_keys: list[str] = Field(
        default_factory=list,
        description="Memory keys this pipeline reads/writes",
    )
    status: PipelineStatus = PipelineStatus.CREATED
