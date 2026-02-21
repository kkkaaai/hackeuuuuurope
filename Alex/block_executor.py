"""
Block Executor - Calls blocks at their specified locations

Demonstrates how to use the block's location field to execute blocks
via HTTP, file paths, or other endpoints.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urljoin

from block_retriever import Block, BlockDatabase


@dataclass
class BlockExecutionResult:
    """Result of executing a block."""
    block_id: str
    success: bool
    output: Optional[Dict] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BlockExecutor:
    """Executes blocks by calling their location endpoints."""
    
    def __init__(self, block_db: Optional[BlockDatabase] = None, base_url: str = ""):
        """
        Initialize the executor.
        
        Args:
            block_db: BlockDatabase instance
            base_url: Base URL for relative endpoint paths
        """
        self.block_db = block_db or BlockDatabase()
        self.base_url = base_url
    
    def execute_block(
        self,
        block_id: str,
        inputs: Dict[str, Any],
        timeout: float = 30.0
    ) -> BlockExecutionResult:
        """
        Execute a block by calling its location endpoint.
        
        Args:
            block_id: ID of the block to execute
            inputs: Dictionary of input parameters
            timeout: Request timeout in seconds
        
        Returns:
            BlockExecutionResult with output or error
        """
        import time
        
        start_time = time.time()
        
        try:
            # Get block metadata
            block = self.block_db.get_block(block_id)
            if not block:
                return BlockExecutionResult(
                    block_id=block_id,
                    success=False,
                    error=f"Block '{block_id}' not found in database"
                )
            
            # Execute based on location type
            result = self._execute_by_location(block, inputs, timeout)
            
            elapsed_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = elapsed_ms
            
            return result
        
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return BlockExecutionResult(
                block_id=block_id,
                success=False,
                error=str(e),
                execution_time_ms=elapsed_ms
            )
    
    def _execute_by_location(
        self,
        block: Block,
        inputs: Dict[str, Any],
        timeout: float
    ) -> BlockExecutionResult:
        """
        Execute block based on its location type.
        
        Supports:
        - HTTP/HTTPS URLs: POST request
        - File paths: Load and execute Python file
        - Service endpoints: POST request with base_url prefix
        """
        location = block.location
        
        # HTTP/HTTPS endpoints
        if location.startswith(("http://", "https://")):
            return self._execute_http(block, inputs, timeout)
        
        # File paths
        elif location.startswith(("file://", "/")):
            return self._execute_file(block, inputs)
        
        # Relative service endpoints
        elif location.startswith("/"):
            if not self.base_url:
                return BlockExecutionResult(
                    block_id=block.id,
                    success=False,
                    error=f"Relative endpoint '{location}' requires base_url"
                )
            full_url = urljoin(self.base_url, location)
            return self._execute_http(block, inputs, timeout, full_url)
        
        # S3 and other cloud storage
        elif location.startswith("s3://"):
            return self._execute_s3(block, inputs)
        
        else:
            return BlockExecutionResult(
                block_id=block.id,
                success=False,
                error=f"Unsupported location type: {location}"
            )
    
    def _execute_http(
        self,
        block: Block,
        inputs: Dict[str, Any],
        timeout: float,
        url: Optional[str] = None
    ) -> BlockExecutionResult:
        """Execute block via HTTP POST request."""
        url = url or block.location
        
        try:
            response = requests.post(
                url,
                json={"block_id": block.id, "inputs": inputs},
                timeout=timeout,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            
            output = response.json()
            
            return BlockExecutionResult(
                block_id=block.id,
                success=True,
                output=output
            )
        
        except requests.exceptions.RequestException as e:
            return BlockExecutionResult(
                block_id=block.id,
                success=False,
                error=f"HTTP request failed: {str(e)}"
            )
    
    def _execute_file(
        self,
        block: Block,
        inputs: Dict[str, Any]
    ) -> BlockExecutionResult:
        """Execute block from Python file."""
        location = block.location
        
        # Handle file:// protocol
        if location.startswith("file://"):
            file_path = location[7:]  # Remove 'file://'
        else:
            file_path = location
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            return BlockExecutionResult(
                block_id=block.id,
                success=False,
                error=f"File not found: {file_path}"
            )
        
        if not file_path.suffix == ".py":
            return BlockExecutionResult(
                block_id=block.id,
                success=False,
                error=f"Expected Python file, got: {file_path}"
            )
        
        try:
            # Load and execute Python file
            # This is a simplified version - in production, use proper isolation
            import importlib.util
            
            spec = importlib.util.spec_from_file_location("block_module", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Call execute function if it exists
            if hasattr(module, "execute"):
                output = module.execute(inputs)
                return BlockExecutionResult(
                    block_id=block.id,
                    success=True,
                    output=output
                )
            else:
                return BlockExecutionResult(
                    block_id=block.id,
                    success=False,
                    error=f"Module {file_path} has no 'execute' function"
                )
        
        except Exception as e:
            return BlockExecutionResult(
                block_id=block.id,
                success=False,
                error=f"Failed to execute file: {str(e)}"
            )
    
    def _execute_s3(
        self,
        block: Block,
        inputs: Dict[str, Any]
    ) -> BlockExecutionResult:
        """Execute block from S3 bucket."""
        # This would require boto3
        return BlockExecutionResult(
            block_id=block.id,
            success=False,
            error="S3 execution not yet implemented. Install boto3 and configure AWS credentials."
        )
    
    def execute_flow(
        self,
        flow_plan: Dict,
        initial_inputs: Dict[str, Any]
    ) -> Dict:
        """
        Execute a complete flow plan.
        
        Args:
            flow_plan: Flow plan with required_blocks
            initial_inputs: Initial inputs for the flow
        
        Returns:
            Dict with execution results for each block
        """
        results = {
            "flow_id": flow_plan.get("flow_id", "unknown"),
            "blocks_executed": [],
            "total_success": True,
            "final_outputs": initial_inputs
        }
        
        required_blocks = flow_plan.get("required_blocks", [])
        
        for i, block_spec in enumerate(required_blocks):
            block_id = block_spec.get("block_id") or block_spec.get("suggested_id")
            
            # Get inputs for this block
            # In a real system, this would come from previous outputs
            block_inputs = initial_inputs
            
            # Execute block
            execution_result = self.execute_block(block_id, block_inputs)
            
            results["blocks_executed"].append({
                "block_id": block_id,
                "success": execution_result.success,
                "error": execution_result.error,
                "execution_time_ms": execution_result.execution_time_ms,
                "output": execution_result.output
            })
            
            if not execution_result.success:
                results["total_success"] = False
                break  # Stop on first failure
            
            # Update final outputs with block output
            if execution_result.output:
                results["final_outputs"].update(execution_result.output)
        
        return results


def main():
    """Example usage of block executor."""
    print("Block Executor Example")
    print("=" * 60)
    
    # Create sample database
    from block_retriever import create_sample_blocks_database
    db = create_sample_blocks_database()
    
    # Create executor
    executor = BlockExecutor(db, base_url="https://api.example.com")
    
    # Example: Get block information
    print("\nAvailable Blocks:")
    print("-" * 60)
    for block_id, block in db.blocks.items():
        print(f"{block_id}:")
        print(f"  Location: {block.location}")
        print(f"  Inputs: {list(block.inputs.keys())}")
        print(f"  Outputs: {list(block.outputs.keys())}")
    
    # Example: Execute a block (will fail without actual endpoint)
    print("\n\nExample Block Execution:")
    print("-" * 60)
    
    result = executor.execute_block(
        "web_search",
        {"query": "python programming", "num_results": 5}
    )
    
    print(f"Block ID: {result.block_id}")
    print(f"Success: {result.success}")
    print(f"Error: {result.error}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")
    
    # Example: Execute flow
    print("\n\nExample Flow Execution:")
    print("-" * 60)
    
    flow_plan = {
        "flow_id": "example_flow",
        "required_blocks": [
            {"block_id": "web_search", "reason": "Search for information"},
            {"block_id": "claude_summarize", "reason": "Summarize results"}
        ]
    }
    
    flow_result = executor.execute_flow(
        flow_plan,
        {"query": "artificial intelligence"}
    )
    
    print(f"Flow ID: {flow_result['flow_id']}")
    print(f"Total Success: {flow_result['total_success']}")
    print(f"Blocks Executed: {len(flow_result['blocks_executed'])}")
    
    for block_result in flow_result['blocks_executed']:
        print(f"\n  Block: {block_result['block_id']}")
        print(f"  Success: {block_result['success']}")
        print(f"  Time: {block_result['execution_time_ms']:.2f}ms")


if __name__ == "__main__":
    main()
