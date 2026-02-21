# Task Decomposition Graph Visualizations

This script creates interactive, zoomable visualizations of task decomposition hierarchies from cleaned request JSON files.

## Features

✨ **Interactive Graphs**
- **Zoom**: Use mouse wheel or trackpad pinch to zoom in/out
- **Pan**: Click and drag to move around the graph
- **Hover**: View full task description and complexity score on hover

🎨 **Color Coding**
- **Green** (RGB 0-200-0): Low complexity tasks (typically 30-40 range)
- **Yellow-Orange**: Medium complexity (50-70 range)
- **Red** (RGB 255-0-0): High complexity tasks (80+)
- **Grey** (RGB 100-150-150): Tasks below complexity threshold or with unknown complexity

📊 **Depth-Based Layout**
- Vertical position (Y-axis) represents depth in the task hierarchy
- Horizontal position (X-axis) spreads sibling tasks to avoid overlap
- Parent tasks connect to their subtasks with lines

## Usage

### Generate All Visualizations

```bash
python visualize_decomposition.py
```

This creates HTML files in `./visualizations/` for all cleaned requests.

### Custom Parameters

```bash
# Specify custom cleaned requests directory
python visualize_decomposition.py --cleaned-dir=/path/to/cleaned_requests

# Specify custom output directory
python visualize_decomposition.py --output-dir=/path/to/output

# Change complexity threshold (default: 30)
python visualize_decomposition.py --threshold=50

# Combine options
python visualize_decomposition.py --cleaned-dir=/custom/input --output-dir=/custom/output --threshold=40
```

### View Visualizations

1. Open any generated `_graph.html` file in your web browser
2. Use mouse/trackpad controls to navigate:
   - **Scroll wheel**: Zoom in/out
   - **Click + drag**: Pan around the canvas
   - **Hover over boxes**: See task ID, complexity score, and full description

## Output Format

Each cleaned request generates one HTML file named:
```
{timestamp}_{hash}_graph.html
```

For example:
```
20260221T145854Z_34bc49fdc8834488af68950a67d22073_graph.html
```

## Customization

Edit `visualize_decomposition.py` to adjust:

- **COMPLEXITY_THRESHOLD** (line 12): Default threshold for grey coloring
- **Box colors**: Modify `get_complexity_color()` function
- **Layout spacing**: Adjust `level_width` in `calculate_tree_positions()`
- **Node size**: Change `marker.size` in `create_graph_visualization()`
- **Font sizes**: Modify font values in the figure layout

## Data Structure

The script expects cleaned request JSON files with this structure:

```json
{
  "task_id": "abc123",
  "input": "Task description",
  "complexity_score": 75,
  "eval_gen": 1,
  "subtasks": [
    {
      "task_id": "abc123.0",
      "input": "Subtask description",
      "complexity_score": 60,
      "eval_gen": 1,
      "subtasks": [...]
    }
  ]
}
```

## Example Output

The generated graphs show:

```
          [Main Task - Complexity: 80]
                    |
        ____________|____________
       |            |            |
    [Sub1]       [Sub2]       [Sub3]
    C:60         C:45         C:70
```

Tasks are color-coded based on complexity, and you can zoom/pan to explore the entire hierarchy.

## Dependencies

- `plotly`: For interactive visualizations
- `python 3.7+`: For JSON and pathlib support

Install with:
```bash
pip install plotly
```

## Troubleshooting

**Error: No cleaned request files found**
- Check that cleaned_requests directory exists and contains .json files
- Use `--cleaned-dir` parameter to specify the correct path

**Graphs look cluttered**
- Try adjusting the complexity threshold to hide simpler tasks
- Zoom in on specific areas of interest

**Missing complexity scores**
- Some tasks may not have complexity assigned (shown in darker grey)
- Run complexity evaluation first to assign scores

## Integration with Task Decomposer

This script works with the `task_decomposer.py` pipeline:

1. Generate requests with `generate_requests.py`
2. Evaluate complexity with `complexity_evaluator.py`
3. Decompose tasks with `task_decomposer.py`
4. Visualize with `visualize_decomposition.py`

Run the full pipeline:
```bash
python task_decomposer.py 50  # Decompose tasks with complexity > 50
python visualize_decomposition.py  # Then visualize all results
```
