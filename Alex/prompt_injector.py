"""
Prompt Injector Module

Handles all prompt injection logic for flow creation.
Takes an internal prompt template, populates it with query-relevant blocks,
and returns the fully populated prompt ready for LLM execution.
"""

import json
from typing import Dict, Tuple, Optional
from pathlib import Path

from block_retriever import BlockDatabase, FlowCreationBlockRetriever


class PromptInjector:
    """Injects query-relevant blocks into prompts."""
    
    def __init__(self, block_db: Optional[BlockDatabase] = None):
        """
        Initialize the prompt injector.
        
        Args:
            block_db: BlockDatabase instance. If not provided, loads from blocks.json.
        """
        self.block_db = block_db or BlockDatabase()
        self.retriever = FlowCreationBlockRetriever(self.block_db)
    
    def inject_prompt(
        self,
        template_prompt: str,
        query: str,
        num_blocks: int = 5,
        placeholder: str = "[BLOCKS_PLACEHOLDER]"
    ) -> str:
        """
        Inject query-relevant blocks into prompt template.
        
        Process:
        1. Retrieve blocks relevant to the query using semantic search
        2. Format retrieved blocks as JSON
        3. Replace placeholder in template with block JSON
        4. Return fully populated prompt ready for LLM
        
        Args:
            template_prompt: Base prompt with [BLOCKS_PLACEHOLDER]
            query: User intent/query for block retrieval
            num_blocks: Number of blocks to retrieve (default: 5)
            placeholder: Text to replace in template (default: "[BLOCKS_PLACEHOLDER]")
        
        Returns:
            Fully populated prompt with injected blocks and query
        """
        # Step 1: Retrieve blocks relevant to the query
        retrieved_blocks, blocks_json = self.retriever.get_blocks_for_intent(
            query,
            k=num_blocks
        )
        
        # Step 2: Inject blocks into template
        prompt_with_blocks = template_prompt.replace(placeholder, blocks_json)
        
        # Step 3: Add query to prompt
        populated_prompt = f"{prompt_with_blocks}\n\nUser Intent:\n{query}"
        
        return populated_prompt
    
    def inject_prompt_only_blocks(
        self,
        template_prompt: str,
        query: str,
        num_blocks: int = 5,
        placeholder: str = "[BLOCKS_PLACEHOLDER]"
    ) -> str:
        """
        Inject blocks only (without appending the query).
        Useful when the prompt template already handles query placement.
        
        Args:
            template_prompt: Base prompt with placeholder
            query: User intent/query for block retrieval
            num_blocks: Number of blocks to retrieve
            placeholder: Text to replace in template
        
        Returns:
            Prompt with injected blocks only (no query appended)
        """
        retrieved_blocks, blocks_json = self.retriever.get_blocks_for_intent(
            query,
            k=num_blocks
        )
        
        populated_prompt = template_prompt.replace(placeholder, blocks_json)
        return populated_prompt
    
    def inject_prompt_and_return_metadata(
        self,
        template_prompt: str,
        query: str,
        num_blocks: int = 5,
        placeholder: str = "[BLOCKS_PLACEHOLDER]"
    ) -> Tuple[str, Dict]:
        """
        Inject blocks and return both the prompt and metadata about retrieved blocks.
        
        Args:
            template_prompt: Base prompt with placeholder
            query: User intent/query for block retrieval
            num_blocks: Number of blocks to retrieve
            placeholder: Text to replace in template
        
        Returns:
            Tuple of (populated_prompt, metadata_dict)
            
            metadata_dict contains:
                - retrieved_blocks: List of Block objects
                - num_retrieved: Count of retrieved blocks
                - query: The original query
        """
        retrieved_blocks, blocks_json = self.retriever.get_blocks_for_intent(
            query,
            k=num_blocks
        )
        
        prompt_with_blocks = template_prompt.replace(placeholder, blocks_json)
        populated_prompt = f"{prompt_with_blocks}\n\nUser Intent:\n{query}"
        
        metadata = {
            "retrieved_blocks": [block.to_dict() for block in retrieved_blocks],
            "num_retrieved": len(retrieved_blocks),
            "query": query
        }
        
        return populated_prompt, metadata


def inject_prompt(
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    block_db: Optional[BlockDatabase] = None,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> str:
    """
    Standalone function for prompt injection.
    
    Simple interface for injecting blocks into a prompt template.
    
    Args:
        template_prompt: Base prompt with placeholder
        query: User intent/query for block retrieval
        num_blocks: Number of relevant blocks to retrieve (default: 5)
        block_db: Optional BlockDatabase instance
        placeholder: Placeholder text to replace (default: "[BLOCKS_PLACEHOLDER]")
    
    Returns:
        Fully populated prompt ready for LLM execution
    
    Example:
        >>> from prompt_injector import inject_prompt
        >>> 
        >>> base_prompt = '''You are a decomposer.
        ... ## Available Blocks
        ... [BLOCKS_PLACEHOLDER]
        ... '''
        >>> 
        >>> full_prompt = inject_prompt(base_prompt, "search and summarize")
        >>> # Send full_prompt to LLM
    """
    injector = PromptInjector(block_db)
    return injector.inject_prompt(
        template_prompt,
        query,
        num_blocks,
        placeholder
    )


def inject_prompt_with_metadata(
    template_prompt: str,
    query: str,
    num_blocks: int = 5,
    block_db: Optional[BlockDatabase] = None,
    placeholder: str = "[BLOCKS_PLACEHOLDER]"
) -> Tuple[str, Dict]:
    """
    Standalone function for prompt injection with metadata.
    
    Returns both the populated prompt and information about retrieved blocks.
    
    Args:
        template_prompt: Base prompt with placeholder
        query: User intent/query for block retrieval
        num_blocks: Number of relevant blocks to retrieve (default: 5)
        block_db: Optional BlockDatabase instance
        placeholder: Placeholder text to replace (default: "[BLOCKS_PLACEHOLDER]")
    
    Returns:
        Tuple of (populated_prompt, metadata_dict)
    
    Example:
        >>> from prompt_injector import inject_prompt_with_metadata
        >>> 
        >>> full_prompt, metadata = inject_prompt_with_metadata(
        ...     base_prompt,
        ...     "search and summarize"
        ... )
        >>> print(f"Retrieved {metadata['num_retrieved']} blocks")
        >>> # Send full_prompt to LLM
    """
    injector = PromptInjector(block_db)
    return injector.inject_prompt_and_return_metadata(
        template_prompt,
        query,
        num_blocks,
        placeholder
    )


if __name__ == "__main__":
    # Example usage
    from block_retriever import create_sample_blocks_database
    
    print("Testing Prompt Injector")
    print("=" * 80)
    
    # Create sample blocks
    print("\n1. Creating sample block database...")
    db = create_sample_blocks_database()
    print(f"   ✓ Created {len(db.blocks)} sample blocks")
    
    # Create sample template
    template = """You are a task decomposer for AgentFlow.

## Available Blocks
[BLOCKS_PLACEHOLDER]

## Rules
1. Use existing blocks when they fit
2. Create new blocks if needed

## Output
Return JSON with required_blocks"""
    
    # Test basic injection
    print("\n2. Testing basic injection...")
    query = "search and summarize news"
    
    full_prompt = inject_prompt(template, query, num_blocks=3, block_db=db)
    
    print(f"   Query: '{query}'")
    print(f"   Full prompt length: {len(full_prompt)} characters")
    print("\n   First 500 chars of populated prompt:")
    print("   " + "-" * 76)
    print("   " + full_prompt[:500].replace("\n", "\n   "))
    print("   " + "-" * 76)
    
    # Test with metadata
    print("\n3. Testing injection with metadata...")
    query2 = "filter data and analyze"
    
    full_prompt2, metadata = inject_prompt_with_metadata(
        template,
        query2,
        num_blocks=3,
        block_db=db
    )
    
    print(f"   Query: '{query2}'")
    print(f"   Retrieved blocks: {metadata['num_retrieved']}")
    print("   Block IDs:")
    for block in metadata['retrieved_blocks']:
        print(f"      - {block['id']}")
    
    print("\n✓ Prompt injection working correctly!")
