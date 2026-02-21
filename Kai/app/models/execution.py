from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeResult(BaseModel):
    node_id: str
    block_id: str
    status: ExecutionStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: float | None = None


class ExecutionState(BaseModel):
    pipeline_id: str
    run_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_node: str | None = None
    shared_context: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    node_results: list[NodeResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    pipeline_id: str
    run_id: str
    status: ExecutionStatus
    shared_context: dict[str, Any] = Field(default_factory=dict)
    node_results: list[NodeResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
