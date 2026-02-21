"""
Semantic Block Retrieval System using mbxai-embed-large

Queries a database of available blocks to retrieve contextually relevant blocks
for flow creation based on semantic similarity to user intent.
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from openai import OpenAI

# Embedding model config
EMBEDDING_MODEL = "nvidia/llama-3.2-nv-embedqa-1b-v1"
EMBEDDING_DIMENSION = 1024
SIMILARITY_THRESHOLD = 0.4  # Cosine similarity threshold for relevance

# Initialize client
_client = None


def _get_client() -> OpenAI:
    """Get or create OpenAI client for NVIDIA API."""
    global _client
    if _client is None:
        api_key = os.getenv("NVAPI_KEY") or os.getenv("NVIDIA_API_KEY")
        if not api_key:
            # Try loading from .env
            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    if "NVAPI_KEY=" in line or "NVIDIA_API_KEY=" in line:
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        
        if not api_key:
            raise ValueError("NVAPI_KEY or NVIDIA_API_KEY environment variable not set")
        
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
    
    return _client


@dataclass
class Block:
    """Represents an available block in the system."""
    id: str
    inputs: Dict  # Input parameters and their types
    outputs: Dict  # Output parameters and their types
    descriptor: str  # Explanation of what the block does
    location: str  # API endpoint or file path to call the block
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding embedding."""
        return {
            "id": self.id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "descriptor": self.descriptor,
            "location": self.location
        }


class BlockDatabase:
    """Manages a database of available blocks with semantic indexing."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize block database.
        
        Args:
            db_path: Path to blocks.json file. If not provided, looks in current directory.
        """
        if db_path is None:
            db_path = Path(__file__).parent / "blocks.json"
        else:
            db_path = Path(db_path)
        
        self.db_path = db_path
        self.blocks: Dict[str, Block] = {}
        self.embeddings_cache: Dict[str, np.ndarray] = {}
        
        # Load blocks if database exists
        if self.db_path.exists():
            self._load_blocks()
    
    def _load_blocks(self):
        """Load blocks from JSON database."""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for block_data in data.get('blocks', []):
                block = Block(
                    id=block_data['id'],
                    inputs=block_data['inputs'],
                    outputs=block_data['outputs'],
                    descriptor=block_data['descriptor'],
                    location=block_data['location']
                )
                self.blocks[block.id] = block
            
            print(f"Loaded {len(self.blocks)} blocks from {self.db_path}")
        
        except Exception as e:
            print(f"Warning: Could not load blocks database: {e}")
    
    def save_blocks(self):
        """Save blocks to JSON database."""
        data = {
            "version": "1.0",
            "blocks": [block.to_dict() for block in self.blocks.values()]
        }
        
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(self.blocks)} blocks to {self.db_path}")
    
    def add_block(self, block: Block):
        """Add a block to the database."""
        self.blocks[block.id] = block
    
    def get_block(self, block_id: str) -> Optional[Block]:
        """Retrieve a block by ID."""
        return self.blocks.get(block_id)
    
    def embed_blocks(self):
        """Generate embeddings for all blocks."""
        client = _get_client()
        
        for block_id, block in self.blocks.items():
            if block.embedding is not None:
                continue  # Already embedded
            
            # Use the descriptor for embedding
            text = block.descriptor
            
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                
                embedding = response.data[0].embedding
                block.embedding = embedding
                self.embeddings_cache[block_id] = np.array(embedding)
                
                print(f"Embedded block: {block.id}")
            
            except Exception as e:
                print(f"Error embedding block {block_id}: {e}")
    
    def get_relevant_blocks(self, query: str, k: int = 5) -> List[Block]:
        """
        Retrieve relevant blocks for a given query using semantic similarity.
        
        Args:
            query: User intent or task description
            k: Number of top results to return
        
        Returns:
            List of relevant blocks sorted by similarity score
        """
        client = _get_client()
        
        # Ensure all blocks are embedded
        if not self.embeddings_cache:
            self.embed_blocks()
        
        # Embed the query
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query
            )
            query_embedding = np.array(response.data[0].embedding)
        
        except Exception as e:
            print(f"Error embedding query: {e}")
            return []
        
        # Compute similarity scores
        scores = {}
        for block_id, block_embedding in self.embeddings_cache.items():
            # Cosine similarity
            similarity = np.dot(query_embedding, block_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(block_embedding) + 1e-10
            )
            
            if similarity >= SIMILARITY_THRESHOLD:
                scores[block_id] = float(similarity)
        
        # Sort by similarity and return top k
        sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        relevant_blocks = [self.blocks[block_id] for block_id, _ in sorted_ids[:k]]
        
        return relevant_blocks


class FlowCreationBlockRetriever:
    """Retrieves and formats blocks for flow creation prompts."""
    
    def __init__(self, block_db: Optional[BlockDatabase] = None):
        """
        Initialize the retriever.
        
        Args:
            block_db: BlockDatabase instance. If not provided, creates a new one.
        """
        if block_db is None:
            block_db = BlockDatabase()
        
        self.block_db = block_db
    
    def get_blocks_for_intent(self, user_intent: str, k: int = 5) -> Tuple[List[Block], str]:
        """
        Get relevant blocks and format them for injection into the flow creation prompt.
        
        Args:
            user_intent: User's task or intent
            k: Number of blocks to retrieve
        
        Returns:
            Tuple of (blocks_list, formatted_json_string)
        """
        # Retrieve relevant blocks
        relevant_blocks = self.block_db.get_relevant_blocks(user_intent, k=k)
        
        if not relevant_blocks:
            print(f"Warning: No relevant blocks found for: {user_intent}")
            return [], "[]"
        
        # Format blocks for injection
        blocks_json = json.dumps(
            [block.to_dict() for block in relevant_blocks],
            indent=2
        )
        
        return relevant_blocks, blocks_json
    
    def inject_blocks_into_prompt(self, base_prompt: str, user_intent: str, k: int = 5) -> str:
        """
        Inject retrieved blocks into the flow creation prompt.
        
        Args:
            base_prompt: The base decomposition prompt template
            user_intent: User's task or intent
            k: Number of blocks to retrieve
        
        Returns:
            Complete prompt with injected blocks
        """
        relevant_blocks, blocks_json = self.get_blocks_for_intent(user_intent, k=k)
        
        # Inject into prompt
        prompt = base_prompt.replace(
            "## Available Blocks\n[BLOCKS_PLACEHOLDER]",
            f"## Available Blocks\n{blocks_json}"
        )
        
        return prompt


def create_sample_blocks_database():
    """Create a sample blocks database for testing."""
    blocks = [
        Block(
            id="web_search",
            inputs={"query": "string", "num_results": "integer (optional)"},
            outputs={"results": "array of {title, url, snippet}"},
            descriptor="Search the web for information on any topic. Returns search results with URLs and summaries.",
            location="https://api.example.com/blocks/web_search"
        ),
        Block(
            id="claude_summarize",
            inputs={"content": "string", "length": "string (short/medium/long, optional)"},
            outputs={"summary": "string"},
            descriptor="Summarize text content into concise summaries. Works with articles, reports, or long text.",
            location="https://api.example.com/blocks/claude_summarize"
        ),
        Block(
            id="claude_analyze",
            inputs={"data": "string", "analysis_type": "string (optional)"},
            outputs={"analysis": "string", "insights": "array of strings"},
            descriptor="Analyze data or text for patterns, insights, and conclusions.",
            location="https://api.example.com/blocks/claude_analyze"
        ),
        Block(
            id="filter_threshold",
            inputs={"items": "array", "threshold": "number", "field": "string (optional)"},
            outputs={"filtered_items": "array"},
            descriptor="Filter items based on numerical thresholds. Use for ranking, sorting, or filtering.",
            location="https://api.example.com/blocks/filter_threshold"
        ),
        Block(
            id="memory_write",
            inputs={"key": "string", "value": "string"},
            outputs={"success": "boolean"},
            descriptor="Store data in memory for retrieval by later steps.",
            location="https://api.example.com/blocks/memory_write"
        ),
        Block(
            id="memory_read",
            inputs={"key": "string"},
            outputs={"value": "string"},
            descriptor="Retrieve data previously stored in memory.",
            location="https://api.example.com/blocks/memory_read"
        )
    ]
    
    db = BlockDatabase()
    for block in blocks:
        db.add_block(block)
    
    db.save_blocks()
    db.embed_blocks()
    
    return db


if __name__ == "__main__":
    # Example usage
    print("Creating sample blocks database...")
    db = create_sample_blocks_database()
    
    print("\n" + "="*60)
    print("Testing block retrieval...")
    print("="*60)
    
    # Test retrieval
    retriever = FlowCreationBlockRetriever(db)
    
    test_intents = [
        "Search for information and summarize results",
        "Filter data and store in memory",
        "Analyze trends in the data"
    ]
    
    for intent in test_intents:
        print(f"\nIntent: {intent}")
        blocks, blocks_json = retriever.get_blocks_for_intent(intent, k=3)
        print(f"Retrieved {len(blocks)} blocks:")
        for block in blocks:
            print(f"  - {block.id}: {block.name}")
