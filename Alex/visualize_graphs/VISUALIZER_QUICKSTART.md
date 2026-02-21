# Task Decomposition Graph Visualizer - Quick Start Guide

## What It Does

This visualization tool creates **interactive, zoomable graphs** that display your task decomposition hierarchies. Each graph shows:

- **Task nodes** as colored boxes (green→yellow→orange→red based on complexity)
- **Task descriptions** truncated in the boxes, with full text on hover
- **Complexity scores** displayed in the hover information
- **Hierarchical connections** with lines showing parent-child task relationships
- **Depth-based layout** where vertical position indicates task nesting level

## Installation

The script requires `plotly` for visualization:

```bash
pip install plotly
```

## Running the Visualizer

### Quick Start (Default)

```bash
python visualize_decomposition.py
```

This will:
1. Find all JSON files in `./cleaned_requests/`
2. Generate individual graph HTML files in `./visualizations/`
3. Create an `index.html` page listing all visualizations

### View Your Graphs

Open `visualizations/index.html` in any web browser to see a beautiful dashboard with links to all task decomposition graphs.

Alternatively, open any individual `_graph.html` file directly.

## Using the Visualizations

### Navigation

| Action | How |
|--------|-----|
| **Zoom In** | Scroll wheel up or trackpad pinch |
| **Zoom Out** | Scroll wheel down or trackpad pinch |
| **Pan (Move)** | Click and drag the graph |
| **Reset View** | Double-click anywhere on the graph |

### Information

**Hover over any task box** to see:
- Task ID (hierarchical)
- Complexity score
- Full task description

### Color Legend

```
🟢 Green       - Low Complexity (30-40)
🟠 Orange      - Medium Complexity (50-70)
🔴 Red         - High Complexity (80+)
⚫ Dark Grey    - Below Threshold or Unknown
```

## Advanced Usage

### Custom Cleaned Requests Directory

```bash
python visualize_decomposition.py --cleaned-dir=/path/to/your/requests
```

### Custom Output Directory

```bash
python visualize_decomposition.py --output-dir=/path/to/output
```

### Change Complexity Threshold

Adjust which tasks appear grey (below threshold):

```bash
python visualize_decomposition.py --threshold=50
```

### Combine Options

```bash
python visualize_decomposition.py \
  --cleaned-dir=/custom/input \
  --output-dir=/custom/output \
  --threshold=40
```

## Output Files

After running, you'll find:

```
visualizations/
├── index.html                                          # Master dashboard
├── 20260221T145854Z_..._graph.html                    # Individual graphs
├── 20260221T151338Z_..._graph.html
├── 20260221T151518Z_..._graph.html
└── ... (one per cleaned request)
```

Each HTML file is **standalone** and can be:
- Opened directly in any modern web browser
- Shared with others
- Embedded in reports or documentation

## Graph Layout Explained

The graphs use a **hierarchical tree layout**:

```
                    [Parent Task]
                    Complexity: 80
                            |
        ____________________|____________________
       |                    |                    |
    [Sub 1]             [Sub 2]              [Sub 3]
    C: 60               C: 45                C: 70
     |                   |
   [Sub 1.1]          [Sub 2.1]
   C: 35              C: 40
```

**Vertical Position (Y-axis):** Indicates depth in the hierarchy
- Top = Root task
- Bottom = Leaf tasks

**Horizontal Position (X-axis):** Spreads siblings to avoid overlap
- Each level's width expands with depth to accommodate more tasks

## Customization

Edit `visualize_decomposition.py` to modify:

| Variable | Line | Purpose |
|----------|------|---------|
| `COMPLEXITY_THRESHOLD` | 12 | Default threshold for grey coloring |
| `get_complexity_color()` | 40 | Color scheme for complexity ranges |
| `calculate_tree_positions()` | 60 | Spacing and layout algorithm |
| Node size | ~355 | `marker.size=20` - change the value |
| Font size | ~365 | `textfont=dict(size=9, ...)` |
| Plot size | ~372 | `width=1400, height=900` |

### Example: Change Colors

To use a different color scheme, modify `get_complexity_color()`:

```python
def get_complexity_color(complexity_score, threshold=COMPLEXITY_THRESHOLD):
    if complexity_score is None or complexity_score < threshold:
        return 'rgb(150, 150, 150)'  # Grey
    
    # Your custom colors here
    normalized = (complexity_score - threshold) / (100 - threshold)
    # ... rest of function
```

## Troubleshooting

### No visualizations generated?

Check that cleaned_requests directory exists and contains JSON files:

```bash
ls cleaned_requests/*.json
```

### "Invalid threshold" error?

The threshold must be an integer between 0-100:

```bash
# ✓ Correct
python visualize_decomposition.py --threshold=50

# ✗ Wrong
python visualize_decomposition.py --threshold=50.5
```

### Graphs look too crowded?

Try one of these:
1. Increase the threshold to hide simple tasks
2. Zoom in on the area of interest
3. Edit the script to increase `level_width` in `calculate_tree_positions()`

### Missing complexity scores?

Some tasks may not have complexity evaluated. They'll appear in dark grey. Run complexity evaluation first:

```bash
python complexity_evaluator.py
```

## Integration with Task Pipeline

This works perfectly with your existing task processing:

```bash
# 1. Generate sample requests
python generate_requests.py

# 2. Evaluate complexity
python complexity_evaluator.py

# 3. Decompose tasks
python task_decomposer.py 50

# 4. Visualize everything
python visualize_decomposition.py
```

## Data Format

The script expects JSON files in this structure:

```json
{
  "task_id": "abc123",
  "input": "Main task description",
  "complexity_score": 75,
  "eval_gen": 1,
  "subtasks": [
    {
      "task_id": "abc123.0",
      "input": "Subtask description",
      "complexity_score": 60,
      "eval_gen": 1,
      "subtasks": []
    }
  ]
}
```

## Tips & Tricks

### Use cases for different thresholds:

- **Threshold = 0**: Show all tasks, color-coded by complexity
- **Threshold = 30**: Hide trivial tasks, focus on complex work
- **Threshold = 70**: Show only very complex tasks (often reveals bottlenecks)

### Dashboard tips:

- Bookmark `index.html` for quick access to all graphs
- Click-through multiple graphs to compare complexity patterns
- Use browser dev tools (F12) to inspect task details in the interactive elements

### Sharing graphs:

All HTML files are self-contained! You can:
- Email the HTML files directly
- Upload to a web server for team access
- Include in documentation or reports
- Archive them for historical reference

## Performance Notes

- Graph generation: ~2-3 seconds per task (depending on depth)
- File size: ~200-500 KB per HTML file (includes interactive library)
- Browser support: All modern browsers (Chrome, Firefox, Safari, Edge)

## What's Next?

Use these visualizations to:

1. **Identify complexity bottlenecks** - Look for red tasks
2. **Plan resource allocation** - Higher complexity = more resources needed
3. **Detect patterns** - Compare graphs to find repeating problem structures
4. **Document processes** - Use graphs in technical documentation
5. **Track decomposition quality** - Ensure good balance across subtasks

## Questions or Issues?

Refer to `CREATE_VISUALIZATIONS.md` for detailed API documentation, or check the code comments in `visualize_decomposition.py`.
