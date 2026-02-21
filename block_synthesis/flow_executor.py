"""Flow Executor - Executes multiple blocks in a shared sandbox.

This module handles execution-time orchestration where:
1. All blocks in a flow share a single sandbox
2. Dependencies are collected and installed once
3. Blocks execute in dependency order with data passing
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from .synthesizer import (
    DockerSandbox,
    ExecutionResult,
    OutputFormat,
    SandboxError,
    SandboxManager,
    DOCKER_AVAILABLE,
)

logger = logging.getLogger(__name__)


@dataclass
class Block:
    """A synthesized block ready for execution."""
    id: str
    code: str
    output_format: OutputFormat
    required_packages: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)


@dataclass
class FlowDefinition:
    """Definition of a flow - multiple blocks with dependencies."""
    id: str
    name: str
    blocks: list[Block]
    
    def get_all_packages(self) -> list[str]:
        """Collect all unique packages required by all blocks."""
        packages = set()
        for block in self.blocks:
            packages.update(block.required_packages)
        return list(packages)
    
    def get_execution_order(self) -> list[Block]:
        """Topological sort of blocks based on dependencies."""
        visited = set()
        order = []
        block_map = {b.id: b for b in self.blocks}
        
        def visit(block_id: str):
            if block_id in visited:
                return
            visited.add(block_id)
            block = block_map.get(block_id)
            if block:
                for dep_id in block.depends_on:
                    visit(dep_id)
                order.append(block)
        
        for block in self.blocks:
            visit(block.id)
        
        return order


@dataclass
class BlockResult:
    """Result of executing a single block."""
    block_id: str
    success: bool
    output: Any
    stdout: str
    stderr: str
    error: str | None = None


@dataclass
class FlowResult:
    """Result of executing an entire flow."""
    flow_id: str
    success: bool
    block_results: dict[str, BlockResult]
    final_output: Any = None
    error: str | None = None


class FlowSandbox:
    """Shared sandbox for flow execution.
    
    Unlike generation sandboxes (one per block), this sandbox:
    - Is shared across all blocks in a flow
    - Has all dependencies pre-installed
    - Maintains state between block executions
    - Supports data passing via environment/files
    """
    
    def __init__(
        self,
        image: str = "block-sandbox",
        memory_limit: str = "1g",
        cpu_quota: int = 100000,
    ):
        if not DOCKER_AVAILABLE:
            raise SandboxError("Docker required for FlowSandbox")
        
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_quota = cpu_quota
        self.sandbox: DockerSandbox | None = None
        self.installed_packages: set[str] = set()
    
    def start(self) -> str:
        """Start the shared flow sandbox."""
        self.sandbox = DockerSandbox(
            image=self.image,
            allow_network=True,
            allow_pip_install=True,
            memory_limit=self.memory_limit,
            cpu_quota=self.cpu_quota,
        )
        return self.sandbox.start()
    
    def install_all_packages(self, packages: list[str], timeout: int = 120) -> ExecutionResult:
        """Install all packages needed for the flow at once."""
        if not self.sandbox:
            raise SandboxError("Sandbox not started")
        
        new_packages = [p for p in packages if p not in self.installed_packages]
        if not new_packages:
            return ExecutionResult(
                success=True,
                stdout="All packages already installed",
                stderr="",
                exit_code=0,
            )
        
        logger.info("Installing flow packages: %s", new_packages)
        result = self.sandbox.install_packages(new_packages, timeout)
        
        if result.success:
            self.installed_packages.update(new_packages)
        
        return result
    
    def execute_block(
        self,
        block: Block,
        input_data: Any,
        context: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> BlockResult:
        """Execute a single block with input and context.
        
        Args:
            block: The block to execute
            input_data: Primary input data
            context: Results from previous blocks (block_id -> output)
            timeout: Execution timeout
            
        Returns:
            BlockResult with output and status
        """
        if not self.sandbox:
            raise SandboxError("Sandbox not started")
        
        execution_input = {
            "input": input_data,
            "context": context or {},
        }
        
        wrapper_code = f'''
import sys
import json

# Parse execution input
exec_input = json.loads(sys.stdin.read())
input_data = exec_input["input"]
context = exec_input["context"]

# Make context available as variables
for key, value in context.items():
    globals()[key] = value

# Also make input_data available directly
globals()["input_data"] = input_data

# Execute block code
{block.code}
'''
        
        result = self.sandbox.execute(wrapper_code, execution_input, timeout)
        
        output = None
        if result.success:
            try:
                if block.output_format == OutputFormat.JSON:
                    output = json.loads(result.stdout.strip())
                else:
                    output = result.stdout.strip()
            except json.JSONDecodeError:
                output = result.stdout.strip()
        
        return BlockResult(
            block_id=block.id,
            success=result.success,
            output=output,
            stdout=result.stdout,
            stderr=result.stderr,
            error=result.error,
        )
    
    def cleanup(self) -> None:
        """Clean up the sandbox."""
        if self.sandbox:
            self.sandbox.cleanup()
            self.sandbox = None
            self.installed_packages.clear()


class FlowExecutor:
    """Executes a flow of blocks in a shared sandbox.
    
    Handles:
    - Collecting all dependencies
    - Installing packages once
    - Executing blocks in dependency order
    - Passing data between blocks
    """
    
    def __init__(
        self,
        image: str = "block-sandbox",
        memory_limit: str = "1g",
    ):
        self.image = image
        self.memory_limit = memory_limit
    
    def execute(
        self,
        flow: FlowDefinition,
        initial_input: Any,
        timeout_per_block: int = 30,
    ) -> FlowResult:
        """Execute a complete flow.
        
        Args:
            flow: The flow definition with all blocks
            initial_input: Input to the first block(s)
            timeout_per_block: Timeout for each block execution
            
        Returns:
            FlowResult with all block results and final output
        """
        sandbox = FlowSandbox(
            image=self.image,
            memory_limit=self.memory_limit,
        )
        
        try:
            sandbox.start()
            
            all_packages = flow.get_all_packages()
            if all_packages:
                logger.info("Installing %d packages for flow", len(all_packages))
                install_result = sandbox.install_all_packages(all_packages)
                if not install_result.success:
                    return FlowResult(
                        flow_id=flow.id,
                        success=False,
                        block_results={},
                        error=f"Failed to install packages: {install_result.stderr}",
                    )
            
            execution_order = flow.get_execution_order()
            block_results: dict[str, BlockResult] = {}
            context: dict[str, Any] = {}
            
            for block in execution_order:
                if block.depends_on:
                    block_input = {
                        dep_id: context.get(dep_id)
                        for dep_id in block.depends_on
                    }
                else:
                    block_input = initial_input
                
                logger.info("Executing block: %s", block.id)
                result = sandbox.execute_block(
                    block=block,
                    input_data=block_input,
                    context=context,
                    timeout=timeout_per_block,
                )
                
                block_results[block.id] = result
                
                if not result.success:
                    return FlowResult(
                        flow_id=flow.id,
                        success=False,
                        block_results=block_results,
                        error=f"Block {block.id} failed: {result.error}",
                    )
                
                context[block.id] = result.output
            
            final_block = execution_order[-1] if execution_order else None
            final_output = context.get(final_block.id) if final_block else None
            
            return FlowResult(
                flow_id=flow.id,
                success=True,
                block_results=block_results,
                final_output=final_output,
            )
        
        finally:
            sandbox.cleanup()


class FlowBuilder:
    """Helper to build flows from synthesized blocks."""
    
    def __init__(self):
        self.blocks: list[Block] = []
    
    def add_block(
        self,
        block_id: str,
        code: str,
        output_format: OutputFormat = OutputFormat.JSON,
        required_packages: list[str] | None = None,
        depends_on: list[str] | None = None,
    ) -> "FlowBuilder":
        """Add a block to the flow."""
        self.blocks.append(Block(
            id=block_id,
            code=code,
            output_format=output_format,
            required_packages=required_packages or [],
            depends_on=depends_on or [],
        ))
        return self
    
    def build(self, flow_id: str, name: str) -> FlowDefinition:
        """Build the flow definition."""
        return FlowDefinition(
            id=flow_id,
            name=name,
            blocks=self.blocks,
        )


# =============================================================================
# Convenience function
# =============================================================================


def execute_flow(
    blocks: list[dict],
    initial_input: Any,
    flow_id: str = "flow_1",
    flow_name: str = "Generated Flow",
    docker_image: str = "block-sandbox",
    timeout_per_block: int = 30,
) -> FlowResult:
    """Execute a flow from a list of block definitions.
    
    Args:
        blocks: List of block dicts with keys: id, code, output_format, required_packages, depends_on
        initial_input: Input to the first block(s)
        flow_id: Flow identifier
        flow_name: Human-readable flow name
        docker_image: Docker image for sandbox
        timeout_per_block: Timeout per block
        
    Returns:
        FlowResult with all outputs
        
    Example:
        result = execute_flow(
            blocks=[
                {
                    "id": "fetch_data",
                    "code": "import json; print(json.dumps({'data': [1,2,3]}))",
                    "output_format": "json",
                    "required_packages": [],
                },
                {
                    "id": "process_data",
                    "code": "import json; data = fetch_data['data']; print(json.dumps({'sum': sum(data)}))",
                    "output_format": "json",
                    "depends_on": ["fetch_data"],
                },
            ],
            initial_input={},
        )
    """
    builder = FlowBuilder()
    
    for b in blocks:
        builder.add_block(
            block_id=b["id"],
            code=b["code"],
            output_format=OutputFormat(b.get("output_format", "json")),
            required_packages=b.get("required_packages", []),
            depends_on=b.get("depends_on", []),
        )
    
    flow = builder.build(flow_id, flow_name)
    executor = FlowExecutor(image=docker_image)
    
    return executor.execute(flow, initial_input, timeout_per_block)
