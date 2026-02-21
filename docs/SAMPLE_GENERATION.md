# Sample Task Generation System

## Overview

The sample generation system creates synthetic task requests for testing and developing the task decomposition pipeline. It generates diverse, realistic task descriptions across various complexity levels.

---

## Quick Start

### Generate Sample Tasks

```bash
python Alex/generate_requests.py [count]
```

Where `[count]` is the number of samples to generate (default: varies by script).

### Output

Generated tasks are saved to:
- `sample_requests/` - All generated sample tasks
- File naming: `20260221T213112Z_<uuid>.json`

---

## Sample Task Format

Each generated task is a JSON file containing:

```json
{
  "task_id": "unique_identifier",
  "input": "Task description text",
  "timestamp": "ISO 8601 timestamp",
  "complexity_score": null,  // Evaluated later
  "metadata": {
    "generator": "generate_requests.py",
    "version": "1.0"
  }
}
```

---

## Integration with Decomposition Pipeline

```
generate_requests.py
    ↓
sample_requests/
    ↓
clean_requests.py
    ↓
cleaned_requests/
    ↓
clean_dd_requests.py
    ↓
dd_requests/
    ↓
run_io_dd_decomposition.py
    ↓
Decomposed tasks with execution plans
```

---

## Task Categories

Generated tasks span multiple categories:
- Data analysis and reporting
- Content creation and marketing
- Customer service automation
- Sales and lead management
- Research and information gathering
- System integration and workflow automation

---

## Usage Examples

### Generate 100 Sample Tasks
```bash
python Alex/generate_requests.py 100
```

### Generate and Immediately Clean
```bash
python Alex/generate_requests.py 50
python Alex/clean_requests.py
```

### Full Pipeline
```bash
# Generate samples
python Alex/generate_requests.py 20

# Clean samples
python Alex/clean_requests.py

# Create DD structure
python Alex/clean_dd_requests.py

# Decompose tasks
python Alex/io_decomposition/run_io_dd_decomposition.py
```

---

## Sample Task Examples

### Simple Task
```
"Search for the latest AI research papers and summarize the top 3 findings."
```

### Moderate Task
```
"Analyze customer feedback from last quarter, identify common themes, and create a summary report with actionable recommendations."
```

### Complex Task
```
"Research customer insights to produce cohesive blogs, videos, and social posts across all channels while tracking engagement and conversion metrics to hit sales targets."
```

---

## Customization

### Adding Custom Task Templates

Edit `generate_requests.py` to add custom task generation logic:

```python
def generate_custom_task():
    return {
        "task_id": generate_id(),
        "input": "Your custom task description",
        "timestamp": datetime.now().isoformat(),
        "complexity_score": None
    }
```

### Task Complexity Control

The generator can be configured to produce tasks of specific complexity ranges by adjusting the generation parameters or templates.

---

## Best Practices

1. **Generate in Batches**: Generate tasks in reasonable batches (20-100) for testing
2. **Clean Immediately**: Run `clean_requests.py` after generation
3. **Version Control**: Commit generated samples if they represent good test cases
4. **Diversity**: Ensure generated tasks cover various domains and complexity levels

---

## Output Management

### Merging Generated Samples

To merge newly generated samples into the main sample directory:

```bash
# From PowerShell
Copy-Item -Path "Alex/sample_requests/*" -Destination "sample_requests/" -Force
```

### Cleaning Up

To remove all generated samples:

```bash
# Windows PowerShell
Remove-Item sample_requests/*.json
```

---

## Files

- **`generate_requests.py`** - Main generation script
- **`sample_requests/`** - Output directory for generated tasks
- **`cleaned_requests/`** - Cleaned/normalized versions
- **`dd_requests/`** - Final dependency-driven structure

---

## Dependencies

- Python 3.8+
- Standard library modules (`json`, `datetime`, `uuid`)

---

## Notes

- Generated tasks are for testing purposes
- Task complexity is evaluated separately by `complexity_evaluator.py`
- All generated files use UTF-8 encoding
- Timestamp format: ISO 8601 with timezone marker
