"""
Flow Creator with Semantic Block Retrieval

Integrates semantic block retrieval with the decomposition prompt
to generate AgentFlow execution plans.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

from block_retriever import BlockDatabase
from prompt_injector import inject_prompt_with_metadata

# Load flow creation prompt
FLOW_CREATION_PROMPT_PATH = Path(__file__).parent / "flow_creation_prompt.json"

API_RATE_LIMIT_SECONDS = 5
_last_api_call_time = 0


def _load_flow_creation_prompt() -> str:
    """Load the base flow creation prompt from JSON."""
    try:
        with open(FLOW_CREATION_PROMPT_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Reconstruct the prompt from the config
        prompt = config.get("system_prompt", "")
        
        if not prompt.endswith("\n\n"):
            prompt += "\n\n"
        
        prompt += "## Available Blocks\n[BLOCKS_PLACEHOLDER]\n\n"
        
        # Add rules
        prompt += "## Rules\n"
        for i, rule in enumerate(config.get("sections", {}).get("rules", []), 1):
            prompt += f"{i}. {rule}\n"
        
        # Add output format
        prompt += "\n## Output\n"
        prompt += "Return ONLY a JSON object (no markdown, no explanation):\n"
        prompt += "{\n"
        prompt += '  "required_blocks": [\n'
        prompt += '    {"block_id": "existing_id", "reason": "why"},\n'
        prompt += '    {"suggested_id": "new_id", "inputs": {...}, "outputs": {...}, "descriptor": "..."}\n'
        prompt += '  ]\n'
        prompt += "}\n\n"
        
        return prompt
    
    except Exception as e:
        print(f"Warning: Could not load flow creation prompt: {e}")
        return _get_default_prompt()


def _get_default_prompt() -> str:
    """Return default flow creation prompt if JSON not found."""
    return """You are a task decomposer for AgentFlow, an AI agent platform.
Given a user's intent and available blocks, break the intent into a sequence of atomic steps.

## Available Blocks
[BLOCKS_PLACEHOLDER]

## Rules
1. Use existing blocks by referencing their "block_id" when they fit the need.
2. If NO existing block fits, describe a NEW block with: suggested_id, inputs, outputs, descriptor.
3. Each block must do ONE atomic thing.
4. List blocks in execution order.
5. Think about data flow: what does each block need as input, and what does it output?

## Output
Return ONLY a JSON object (no markdown, no explanation):
{
  "required_blocks": [
    {"block_id": "existing_id", "reason": "why"},
    {"suggested_id": "new_id", "inputs": {...}, "outputs": {...}, "descriptor": "..."}
  ]
}
"""


def _get_client() -> OpenAI:
    """Get OpenAI client for NVIDIA API."""
    api_key = os.getenv("NVAPI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "NVAPI_KEY=" in line or "NVIDIA_API_KEY=" in line:
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    
    if not api_key:
        raise ValueError("NVAPI_KEY or NVIDIA_API_KEY environment variable not set")
    
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )


class FlowCreator:
    """Creates AgentFlow execution plans with semantic block retrieval."""
    
    def __init__(self, block_db: Optional[BlockDatabase] = None, model: str = "qwen/qwen3-235b-a22b"):
        """
        Initialize the flow creator.
        
        Args:
            block_db: BlockDatabase instance. If not provided, loads from blocks.json.
            model: LLM model to use for flow decomposition.
        """
        self.block_db = block_db or BlockDatabase()
        self.model = model
        self.base_prompt = _load_flow_creation_prompt()
    
    def create_flow(
        self,
        user_intent: str,
        num_blocks: int = 5,
        client: Optional[OpenAI] = None
    ) -> Dict:
        """
        Create an AgentFlow execution plan from user intent.
        
        Uses semantic block retrieval to find relevant blocks based on the query,
        then injects them into the prompt before calling the LLM.
        
        Args:
            user_intent: User's task or workflow description
            num_blocks: Number of relevant blocks to retrieve (default: 5)
            client: Optional OpenAI client
        
        Returns:
            Dict with flow plan, blocks used, and metadata
        """
        global _last_api_call_time
        
        if client is None:
            client = _get_client()
        
        # Use PromptInjector to handle all prompt injection logic
        # This retrieves query-relevant blocks and populates the prompt
        full_prompt, injection_metadata = inject_prompt_with_metadata(
            template_prompt=self.base_prompt,
            query=user_intent,
            num_blocks=num_blocks,
            block_db=self.block_db
        )
        
        retrieved_blocks = injection_metadata['retrieved_blocks']
        
        # Rate limiting
        elapsed = time.time() - _last_api_call_time
        if elapsed < API_RATE_LIMIT_SECONDS:
            time.sleep(API_RATE_LIMIT_SECONDS - elapsed)
        
        try:
            _last_api_call_time = time.time()
            
            # Call LLM
            completion = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.3,
                top_p=0.9,
                max_tokens=3000,
                stream=False
            )
            
            response_text = completion.choices[0].message.content if completion.choices else ""
            
            # Parse response
            flow_plan = self._parse_flow_response(response_text)
            
            return {
                "user_intent": user_intent,
                "retrieved_blocks": retrieved_blocks,
                "num_retrieved": len(retrieved_blocks),
                "flow_plan": flow_plan,
                "raw_response": response_text,
                "error": None,
                "model": self.model
            }
        
        except Exception as e:
            return {
                "user_intent": user_intent,
                "retrieved_blocks": retrieved_blocks,
                "num_retrieved": len(retrieved_blocks),
                "flow_plan": None,
                "raw_response": None,
                "error": str(e),
                "model": self.model
            }
    
    def _parse_flow_response(self, response_text: str) -> Dict:
        """
        Parse LLM response into structured flow plan.
        
        Args:
            response_text: Raw LLM response
        
        Returns:
            Structured flow plan dict
        """
        try:
            # Try to extract JSON from response
            import re
            
            # Look for JSON object in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                plan = json.loads(json_str)
                return plan
            else:
                # Return raw response if JSON parsing fails
                return {"raw_response": response_text}
        
        except json.JSONDecodeError:
            return {"raw_response": response_text, "parse_error": "Could not parse JSON"}
    
    def save_flow(self, flow_result: Dict, output_path: Optional[str] = None) -> str:
        """
        Save flow creation result to file.
        
        Args:
            flow_result: Result dict from create_flow()
            output_path: Optional output path. If not provided, generates timestamped filename.
        
        Returns:
            Path to saved file
        """
        if output_path is None:
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            output_path = Path(__file__).parent / f"flows/{timestamp}_flow.json"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(flow_result, f, indent=2)
        
        print(f"Saved flow to: {output_path}")
        return str(output_path)


def main():
    """Example usage."""
    print("Initializing Flow Creator with semantic block retrieval...")
    
    # Initialize flow creator
    creator = FlowCreator()
    
    # Example intents
    test_intents = [
        "Search the web for AI news, summarize findings, and identify top trends",
        "Analyze customer feedback data to find common issues and rank them by frequency",
        "Generate a market analysis report by searching for competitor info and analyzing prices"
    ]
    
    print("\n" + "="*70)
    print("CREATING FLOWS WITH SEMANTIC BLOCK RETRIEVAL")
    print("="*70)
    
    for intent in test_intents:
        print(f"\nIntent: {intent}")
        print("-" * 70)
        
        flow_result = creator.create_flow(intent, num_blocks=5)
        
        print(f"Retrieved blocks: {flow_result['num_retrieved']}")
        for block in flow_result['retrieved_blocks']:
            print(f"  - {block['id']}: {block['name']}")
        
        if flow_result['error']:
            print(f"Error: {flow_result['error']}")
        else:
            print(f"Flow plan: {json.dumps(flow_result['flow_plan'], indent=2)}")
        
        # Optionally save
        # creator.save_flow(flow_result)


if __name__ == "__main__":
    main()
