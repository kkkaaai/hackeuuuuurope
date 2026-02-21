"""
Interactive visualization for task decomposition graphs.

Generates zoomable/navigable Plotly visualizations of task hierarchies with:
- Depth-based positioning to separate branches
- Box coloring: green (low complexity) -> red (high complexity), grey (below threshold)
- Hover info showing task and complexity score
- Interactive navigation and zoom
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, List, Tuple
import plotly.graph_objects as go
import plotly.io as pio


CLEANED_DIR = Path(__file__).parent / "cleaned_requests"
OUTPUT_DIR = Path(__file__).parent / "visualizations"
COMPLEXITY_THRESHOLD = 30  # Tasks below this shown in grey


def load_cleaned_request(file_path: str) -> Dict:
    """Load a cleaned request JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_tree_positions(
    task: Dict,
    depth: int = 0,
    sibling_index: int = 0,
    total_siblings: int = 1,
    parent_x: float = 0.0
) -> Tuple[List[float], List[float], List[Dict]]:
    """
    Calculate positions for task nodes in a hierarchical layout.
    
    Returns:
        Tuple of (x_positions, y_positions, node_info_list)
    """
    x_positions = []
    y_positions = []
    node_info = []
    
    # Vertical spacing between levels
    y_offset = -depth * 2.0
    
    # Horizontal spacing - spread siblings at each depth level
    # Each level can have more nodes, so spacing adjusts
    level_width = 3.0 * (2 ** depth)  # Exponential spread based on depth
    x_offset = parent_x + (sibling_index - total_siblings / 2.0 + 0.5) * level_width
    
    # Add current node
    x_positions.append(x_offset)
    y_positions.append(y_offset)
    node_info.append({
        'x': x_offset,
        'y': y_offset,
        'depth': depth,
        'task': task
    })
    
    # Process subtasks
    subtasks = task.get('subtasks', [])
    if subtasks:
        total_subtasks = len(subtasks)
        for idx, subtask in enumerate(subtasks):
            sub_x, sub_y, sub_info = calculate_tree_positions(
                subtask,
                depth=depth + 1,
                sibling_index=idx,
                total_siblings=total_subtasks,
                parent_x=x_offset
            )
            x_positions.extend(sub_x)
            y_positions.extend(sub_y)
            node_info.extend(sub_info)
    
    return x_positions, y_positions, node_info


def get_complexity_color(complexity_score: float, threshold: int = COMPLEXITY_THRESHOLD) -> str:
    """
    Get RGB color based on complexity score.
    Grey: below threshold or unknown
    Green (0): low complexity
    Red (100): high complexity
    """
    # Handle None or missing scores
    if complexity_score is None:
        return 'rgb(100, 100, 100)'  # Darker grey for unknown
    
    if complexity_score < threshold:
        return 'rgb(150, 150, 150)'  # Grey for below threshold
    
    # Normalize complexity to 0-1 range (threshold to 100)
    normalized = (complexity_score - threshold) / (100 - threshold)
    normalized = max(0, min(1, normalized))  # Clamp to 0-1
    
    # Green to red gradient
    # Green: rgb(0, 200, 0)
    # Red: rgb(255, 0, 0)
    red = int(255 * normalized)
    green = int(200 * (1 - normalized))
    blue = 0
    
    return f'rgb({red}, {green}, {blue})'


def create_graph_visualization(
    cleaned_request_path: str,
    output_html_path: str = None,
    complexity_threshold: int = COMPLEXITY_THRESHOLD
) -> str:
    """
    Create an interactive Plotly visualization for a task decomposition tree.
    
    Args:
        cleaned_request_path: Path to cleaned request JSON
        output_html_path: Where to save the HTML (if None, returns HTML string)
        complexity_threshold: Complexity threshold for color coding
    
    Returns:
        Path to the created HTML file or HTML string
    """
    # Load task data
    task_data = load_cleaned_request(cleaned_request_path)
    
    # Calculate positions
    x_positions, y_positions, node_info = calculate_tree_positions(task_data)
    
    # Prepare node data
    node_texts = []
    node_colors = []
    node_x = []
    node_y = []
    node_hover = []
    
    for info in node_info:
        task = info['task']
        x = info['x']
        y = info['y']
        complexity = task.get('complexity_score', 0)
        task_id = task.get('task_id', 'N/A')
        
        node_x.append(x)
        node_y.append(y)
        node_colors.append(get_complexity_color(complexity, complexity_threshold))
        
        # Truncate task input for display
        task_input = task.get('input', 'No description')
        if len(task_input) > 50:
            task_input = task_input[:47] + '...'
        node_texts.append(task_input)
        
        # Hover text with full info
        hover_text = (
            f"<b>{task_id}</b><br>"
            f"<b>Complexity:</b> {complexity}<br>"
            f"<b>Description:</b> {task.get('input', 'N/A')}"
        )
        node_hover.append(hover_text)
    
    # Create edge traces (connections between parent and children)
    edge_x = []
    edge_y = []
    
    for i, info in enumerate(node_info):
        task = info['task']
        parent_x = info['x']
        parent_y = info['y']
        
        subtasks = task.get('subtasks', [])
        if not subtasks:
            continue
        
        # Find child indices in node_info
        for j, child_info in enumerate(node_info):
            if child_info['task'] in subtasks:
                child_x = child_info['x']
                child_y = child_info['y']
                
                # Draw line from parent to child
                edge_x.extend([parent_x, child_x, None])
                edge_y.extend([parent_y, child_y, None])
    
    # Create figure
    fig = go.Figure()
    
    # Add edges
    if edge_x:
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            line=dict(width=1, color='rgba(100, 100, 100, 0.3)'),
            hoverinfo='none',
            showlegend=False
        ))
    
    # Add nodes
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_texts,
        textposition='middle center',
        hovertext=node_hover,
        hoverinfo='text',
        marker=dict(
            size=20,
            color=node_colors,
            line=dict(width=2, color='rgba(0, 0, 0, 0.3)'),
            symbol='square'
        ),
        textfont=dict(size=9, family='Arial Black', color='white'),
        showlegend=False
    ))
    
    # Update layout
    title = f"Task Decomposition: {task_data.get('task_id', 'Unknown')}"
    main_task = task_data.get('input', 'Unknown')
    if len(main_task) > 60:
        main_task = main_task[:57] + '...'
    
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b><br><sub>{main_task}</sub>",
            x=0.5,
            xanchor='center'
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=100),
        plot_bgcolor='rgba(240, 240, 240, 0.9)',
        paper_bgcolor='white',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        width=1400,
        height=900,
        font=dict(family='Arial', size=11)
    )
    
    # Add legend for color coding
    legend_html = (
        "<div style='position: absolute; top: 10px; right: 10px; "
        "background: white; padding: 10px; border: 1px solid grey; "
        "border-radius: 5px; font-size: 11px;'>"
        "<div><span style='display:inline-block; width:15px; height:15px; "
        "background:rgb(0,200,0); margin-right:5px;'></span>Low Complexity</div>"
        "<div><span style='display:inline-block; width:15px; height:15px; "
        "background:rgb(255,100,0); margin-right:5px;'></span>Medium Complexity</div>"
        "<div><span style='display:inline-block; width:15px; height:15px; "
        "background:rgb(255,0,0); margin-right:5px;'></span>High Complexity</div>"
        "<div><span style='display:inline-block; width:15px; height:15px; "
        "background:rgb(150,150,150); margin-right:5px;'></span>Below Threshold</div>"
        "</div>"
    )
    
    # Save as HTML
    if output_html_path is None:
        output_html_path = str(CLEANED_DIR) + "_viz.html"
    
    os.makedirs(os.path.dirname(output_html_path) if os.path.dirname(output_html_path) else '.', exist_ok=True)
    
    html_str = pio.to_html(fig, include_plotlyjs='cdn')
    html_str = html_str.replace('</body>', legend_html + '</body>')
    
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_str)
    
    return output_html_path


def generate_index_html(output_dir: str, files_info: List[Tuple[str, str]]):
    """
    Generate an index.html file listing all visualizations.
    
    Args:
        output_dir: Path where to save the index
        files_info: List of tuples (filename, task_title)
    """
    index_path = os.path.join(output_dir, 'index.html')
    
    # Build visualization list
    viz_list = []
    for filename, title in sorted(files_info):
        viz_list.append(
            f"            {{ file: '{filename}', title: '{title.replace("'", "&apos;")}' }},"
        )
    
    viz_list_str = "\n".join(viz_list)
    
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Decomposition Visualizations</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            color: white;
            margin-bottom: 50px;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .subtitle {{
            font-size: 1.1em;
            opacity: 0.95;
            margin-bottom: 20px;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            color: white;
            font-size: 0.95em;
        }}
        
        .legend-box {{
            width: 24px;
            height: 24px;
            border-radius: 4px;
            border: 1px solid rgba(0,0,0,0.2);
        }}
        
        .green {{ background-color: rgb(0, 200, 0); }}
        .yellow {{ background-color: rgb(200, 150, 0); }}
        .red {{ background-color: rgb(255, 0, 0); }}
        .grey {{ background-color: rgb(100, 100, 100); }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }}
        
        .card a {{
            text-decoration: none;
            color: inherit;
            display: block;
        }}
        
        .card-title {{
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            word-break: break-word;
        }}
        
        .card-timestamp {{
            font-size: 0.85em;
            color: #999;
            margin-bottom: 12px;
            font-family: 'Courier New', monospace;
        }}
        
        .card-link {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: 500;
            transition: opacity 0.3s;
        }}
        
        .card-link:hover {{
            opacity: 0.9;
        }}
        
        .stats {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 20px;
            color: white;
            margin-bottom: 30px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            opacity: 0.9;
            font-size: 0.95em;
        }}
        
        footer {{
            text-align: center;
            color: white;
            opacity: 0.8;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Task Decomposition Visualizations</h1>
            <p class="subtitle">Interactive graphs showing task hierarchies, complexity scores, and decomposition trees</p>
        </header>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-box green"></div>
                <span>Low Complexity (30-40)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box yellow"></div>
                <span>Medium Complexity (50-70)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box red"></div>
                <span>High Complexity (80+)</span>
            </div>
            <div class="legend-item">
                <div class="legend-box grey"></div>
                <span>Below Threshold / Unknown</span>
            </div>
        </div>
        
        <div class="stats">
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number" id="total-count">0</div>
                    <div class="stat-label">Visualizations</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label" style="margin-top: 5px;">Use your mouse to zoom and pan each graph</div>
                </div>
            </div>
        </div>
        
        <div class="grid" id="graph-grid">
            <!-- Dynamically populated -->
        </div>
        
        <footer>
            <p>Generated by Task Decomposition Graph Visualizer</p>
            <p>All graphs are interactive - zoom, pan, and hover for details</p>
        </footer>
    </div>
    
    <script>
        // List of all visualization files
        const visualizations = [
{viz_list_str}
        ];
        
        function extractTimestamp(filename) {{
            const match = filename.match(/(\\d{{8}}T\\d{{6}}Z)/);
            if (match) {{
                const ts = match[1];
                // Format: 20260221T145854Z -> 2026-02-21 14:58:54
                const year = ts.substring(0, 4);
                const month = ts.substring(4, 6);
                const day = ts.substring(6, 8);
                const hour = ts.substring(9, 11);
                const min = ts.substring(11, 13);
                const sec = ts.substring(13, 15);
                return `${{year}}-${{month}}-${{day}} ${{hour}}:${{min}}:${{sec}}`;
            }}
            return filename;
        }}
        
        function populateGrid() {{
            const grid = document.getElementById('graph-grid');
            
            visualizations.forEach(viz => {{
                const card = document.createElement('div');
                card.className = 'card';
                
                const timestamp = extractTimestamp(viz.file);
                const displayTitle = viz.title || viz.file;
                
                card.innerHTML = `
                    <a href="${{viz.file}}">
                        <div class="card-title">${{displayTitle}}</div>
                        <div class="card-timestamp">${{timestamp}}</div>
                        <div class="card-link">View Graph →</div>
                    </a>
                `;
                
                grid.appendChild(card);
            }});
            
            document.getElementById('total-count').textContent = visualizations.length;
        }}
        
        // Populate grid on page load
        document.addEventListener('DOMContentLoaded', populateGrid);
    </script>
</body>
</html>'''
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def visualize_all_requests(
    cleaned_dir: str = None,
    output_dir: str = None,
    complexity_threshold: int = COMPLEXITY_THRESHOLD
):
    """
    Generate visualizations for all cleaned requests in the directory.
    
    Args:
        cleaned_dir: Path to cleaned_requests directory
        output_dir: Path where to save HTML visualizations
        complexity_threshold: Complexity threshold for color coding
    """
    if cleaned_dir is None:
        cleaned_dir = str(CLEANED_DIR)
    if output_dir is None:
        output_dir = str(OUTPUT_DIR)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all cleaned request files
    cleaned_files = sorted(glob.glob(os.path.join(cleaned_dir, "*.json")))
    
    if not cleaned_files:
        print(f"No cleaned request files found in {cleaned_dir}")
        return
    
    print(f"Found {len(cleaned_files)} cleaned request files")
    print(f"Generating visualizations in {output_dir}\n")
    
    files_info = []
    
    for i, cleaned_file in enumerate(cleaned_files, 1):
        try:
            # Load task data for title
            with open(cleaned_file, 'r', encoding='utf-8') as f:
                task_data = json.load(f)
            
            task_title = task_data.get('input', 'Task')
            if len(task_title) > 60:
                task_title = task_title[:57] + '...'
            
            # Generate output filename
            base_name = os.path.basename(cleaned_file).replace('.json', '')
            output_file = os.path.join(output_dir, f"{base_name}_graph.html")
            
            # Create visualization
            result_path = create_graph_visualization(
                cleaned_file,
                output_file,
                complexity_threshold
            )
            
            files_info.append((os.path.basename(result_path), task_title))
            print(f"[{i}/{len(cleaned_files)}] Created: {os.path.basename(result_path)}")
            
        except Exception as e:
            print(f"[{i}/{len(cleaned_files)}] Error processing {os.path.basename(cleaned_file)}: {e}")
    
    # Generate index page
    if files_info:
        generate_index_html(output_dir, files_info)
        print(f"\nGenerated index page: {os.path.join(output_dir, 'index.html')}")
    
    print(f"\nAll visualizations saved to: {output_dir}")
    print(f"Open index.html or any HTML files in a web browser to interact with the graphs.")
    print(f"Features:")
    print(f"  - Zoom: Scroll wheel or pinch")
    print(f"  - Pan: Click and drag")
    print(f"  - Hover: View task details and complexity score")
    print(f"  - Color coding: Green=Low, Red=High, Grey=Below threshold ({complexity_threshold})")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    custom_cleaned_dir = None
    custom_output_dir = None
    custom_threshold = COMPLEXITY_THRESHOLD
    
    for arg in sys.argv[1:]:
        if arg.startswith('--cleaned-dir='):
            custom_cleaned_dir = arg.split('=', 1)[1]
        elif arg.startswith('--output-dir='):
            custom_output_dir = arg.split('=', 1)[1]
        elif arg.startswith('--threshold='):
            try:
                custom_threshold = int(arg.split('=', 1)[1])
            except ValueError:
                print(f"Invalid threshold: {arg}")
    
    print("=" * 60)
    print("Task Decomposition Graph Visualizer")
    print("=" * 60)
    
    visualize_all_requests(
        cleaned_dir=custom_cleaned_dir,
        output_dir=custom_output_dir,
        complexity_threshold=custom_threshold
    )
