import pytest


@pytest.fixture
def sample_pipeline_json():
    """Minimal 2-node pipeline using only Python blocks (no LLM needed)."""
    return {
        "id": "test_pipeline",
        "name": "Test Pipeline",
        "user_prompt": "test",
        "nodes": [
            {
                "id": "n1",
                "block_id": "filter_threshold",
                "inputs": {"value": 42, "operator": ">", "threshold": 10},
            },
            {
                "id": "n2",
                "block_id": "notify_push",
                "inputs": {"title": "Result", "body": "Filter passed: {{n1.passed}}"},
            },
        ],
        "edges": [{"from": "n1", "to": "n2"}],
        "memory_keys": [],
    }


@pytest.fixture
def three_node_pipeline():
    """3-node pipeline: filter → branch → notify."""
    return {
        "id": "test_3_node",
        "name": "Three Node Test",
        "user_prompt": "test",
        "nodes": [
            {
                "id": "n1",
                "block_id": "filter_threshold",
                "inputs": {"value": 100, "operator": ">=", "threshold": 50},
            },
            {
                "id": "n2",
                "block_id": "conditional_branch",
                "inputs": {"condition": "{{n1.passed}}", "data": "{{n1.value}}"},
            },
            {
                "id": "n3",
                "block_id": "notify_push",
                "inputs": {"title": "Branch", "body": "Took: {{n2.branch}}"},
            },
        ],
        "edges": [
            {"from": "n1", "to": "n2"},
            {"from": "n2", "to": "n3"},
        ],
        "memory_keys": [],
    }


@pytest.fixture
def parallel_pipeline():
    """Pipeline with two independent root nodes that should run in parallel."""
    return {
        "id": "test_parallel",
        "name": "Parallel Test",
        "user_prompt": "test",
        "nodes": [
            {
                "id": "n1",
                "block_id": "filter_threshold",
                "inputs": {"value": 5, "operator": "<", "threshold": 10},
            },
            {
                "id": "n2",
                "block_id": "filter_threshold",
                "inputs": {"value": 20, "operator": ">", "threshold": 10},
            },
            {
                "id": "n3",
                "block_id": "notify_push",
                "inputs": {
                    "title": "Both done",
                    "body": "n1={{n1.passed}}, n2={{n2.passed}}",
                },
            },
        ],
        "edges": [
            {"from": "n1", "to": "n3"},
            {"from": "n2", "to": "n3"},
        ],
        "memory_keys": [],
    }
