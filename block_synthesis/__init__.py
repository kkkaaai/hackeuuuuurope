"""Autonomous Block Synthesis System.

A production-grade system for generating, testing, and iteratively repairing
Python blocks using LLM and sandboxed execution.

Architecture:
- Generation-time: Each block gets its own isolated sandbox (SandboxManager)
- Execution-time: All blocks share a single sandbox (FlowExecutor)

Supports two sandbox backends:
- subprocess (no Docker required, works everywhere)
- docker (strongest isolation, supports pip install)
"""

from .synthesizer import (
    BaseSandbox,
    BlockRequest,
    BlockValidator,
    BlockSynthesizer,
    DockerSandbox,
    ExecutionResult,
    MaxIterationsError,
    Orchestrator,
    OutputFormat,
    SandboxError,
    SandboxManager,
    SubprocessSandbox,
    SynthesisError,
    SynthesisResult,
    ValidationError,
    synthesize_block,
)

from .flow_executor import (
    Block,
    BlockResult,
    FlowBuilder,
    FlowDefinition,
    FlowExecutor,
    FlowResult,
    FlowSandbox,
    execute_flow,
)

from .run_synthesis import (
    ParsedPrompt,
    parse_block_prompt,
    synthesize_from_prompt,
)

__all__ = [
    # Synthesis (generation-time)
    "BaseSandbox",
    "BlockRequest",
    "BlockValidator",
    "BlockSynthesizer",
    "DockerSandbox",
    "ExecutionResult",
    "MaxIterationsError",
    "Orchestrator",
    "OutputFormat",
    "SandboxError",
    "SandboxManager",
    "SubprocessSandbox",
    "SynthesisError",
    "SynthesisResult",
    "ValidationError",
    "synthesize_block",
    # Flow execution (execution-time)
    "Block",
    "BlockResult",
    "FlowBuilder",
    "FlowDefinition",
    "FlowExecutor",
    "FlowResult",
    "FlowSandbox",
    "execute_flow",
    # Prompt-based synthesis
    "ParsedPrompt",
    "parse_block_prompt",
    "synthesize_from_prompt",
]
