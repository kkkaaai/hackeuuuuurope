"""
Test script demonstrating query-powered prompt injection.

Shows how different queries retrieve different blocks and inject them
into the decomposition prompt.
"""

import json
from flow_creator import FlowCreator
from block_retriever import BlockDatabase, create_sample_blocks_database


def test_query_injection():
    """Test query-powered block retrieval and injection."""
    
    print("=" * 80)
    print("QUERY-POWERED PROMPT INJECTION TEST")
    print("=" * 80)
    
    # Create sample database if needed
    print("\n1. Initializing block database...")
    try:
        db = BlockDatabase()
        if len(db.blocks) == 0:
            print("   No blocks found. Creating sample database...")
            db = create_sample_blocks_database()
    except Exception as e:
        print(f"   Error loading blocks: {e}")
        return
    
    print(f"   ✓ Loaded {len(db.blocks)} blocks")
    
    # Initialize flow creator
    print("\n2. Initializing FlowCreator...")
    creator = FlowCreator(db)
    print("   ✓ FlowCreator initialized")
    
    # Test queries
    test_queries = [
        {
            "intent": "Search the web for information and summarize findings",
            "description": "Search + Summarize"
        },
        {
            "intent": "Filter data by threshold and analyze trends",
            "description": "Filter + Analyze"
        },
        {
            "intent": "Store results in memory and retrieve them later",
            "description": "Memory Operations"
        }
    ]
    
    print("\n" + "=" * 80)
    print("TESTING QUERY-POWERED INJECTION")
    print("=" * 80)
    
    for i, test in enumerate(test_queries, 1):
        intent = test["intent"]
        description = test["description"]
        
        print(f"\n{i}. Test: {description}")
        print(f"   Intent: '{intent}'")
        print("-" * 80)
        
        # This is where the magic happens:
        # FlowCreator.create_flow() automatically:
        # 1. Embeds the query
        # 2. Searches for similar blocks
        # 3. Injects retrieved blocks into the prompt
        # 4. Calls LLM
        
        print("   Retrieving blocks for query...")
        
        # Retrieve blocks using the same logic as create_flow()
        retrieved_blocks, blocks_json = creator.retriever.get_blocks_for_intent(
            intent,
            k=5
        )
        
        print(f"   ✓ Retrieved {len(retrieved_blocks)} blocks:")
        for block in retrieved_blocks:
            print(f"      - {block.id}: {block.descriptor[:60]}...")
        
        # Show what gets injected into the prompt
        print("\n   Blocks being injected into prompt:")
        print("   " + "-" * 76)
        
        # Parse and display the JSON
        blocks_data = json.loads(blocks_json)
        for block_data in blocks_data:
            print(f"   - {block_data['id']}")
            print(f"     Inputs: {', '.join(block_data['inputs'].keys())}")
            print(f"     Outputs: {', '.join(block_data['outputs'].keys())}")
        
        print("   " + "-" * 76)
        
        print("\n   Full injection happens in create_flow():")
        print('   base_prompt.replace("[BLOCKS_PLACEHOLDER]", blocks_json)')
        print("\n   Then added to prompt:")
        print(f'   full_prompt = f"{{prompt}}\\n\\nUser Intent:\\n{intent}"')
    
    # Show the actual prompt that would be sent to LLM
    print("\n" + "=" * 80)
    print("EXAMPLE: ACTUAL PROMPT SENT TO LLM")
    print("=" * 80)
    
    intent = test_queries[0]["intent"]
    retrieved_blocks, blocks_json = creator.retriever.get_blocks_for_intent(
        intent,
        k=3  # Show with just 3 blocks for brevity
    )
    
    prompt = creator.base_prompt.replace("[BLOCKS_PLACEHOLDER]", blocks_json)
    full_prompt = f"{prompt}\n\nUser Intent:\n{intent}"
    
    print("\nPrompt that will be sent to LLM:")
    print("-" * 80)
    
    # Show first 500 chars
    print(full_prompt[:800])
    print("\n... [full prompt continues] ...\n")
    
    # Show the blocks section
    print("\nBlocks section of prompt:")
    print("-" * 80)
    print(blocks_json[:600])
    if len(blocks_json) > 600:
        print("\n... [more blocks] ...\n")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
Query-Powered Prompt Injection Process:

1. User provides intent/query
2. Intent is embedded using NVIDIA embedding model
3. Blocks are searched using cosine similarity
4. Top-K relevant blocks are selected
5. Retrieved blocks are formatted as JSON
6. JSON replaces [BLOCKS_PLACEHOLDER] in base prompt
7. User intent is appended to prompt
8. Complete prompt is sent to LLM

Result: LLM sees only relevant blocks for the query!

Benefits:
✓ Faster LLM processing (fewer tokens)
✓ Better flow generation (focused block set)
✓ Reduced hallucination (can't suggest blocks not in set)
✓ Query-aware responses (different queries → different blocks)
    """)


if __name__ == "__main__":
    test_query_injection()
