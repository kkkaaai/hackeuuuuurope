"""
Dynamic task decomposition visualizer with on-demand rendering.

Creates a web interface where task graphs are rendered client-side at runtime,
eliminating the need to pre-generate all visualizations.

Features:
- Fast dashboard with lazy loading
- Server provides task metadata and JSON data
- Client-side graph rendering with Plotly
- Real-time zoom/pan optimization
- Single page application
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, List
import http.server
import socketserver
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs


CLEANED_DIR = Path(__file__).parent.parent / "cleaned_requests"
COMPLEXITY_THRESHOLD = 30
PORT = 8889


def get_task_files() -> List[Dict]:
    """Get metadata for all cleaned request files."""
    cleaned_files = sorted(glob.glob(os.path.join(CLEANED_DIR, "*.json")))
    
    tasks = []
    for file_path in cleaned_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            filename = os.path.basename(file_path)
            task_id = data.get('task_id', 'unknown')
            task_input = data.get('input', 'No description')
            complexity = data.get('complexity_score')
            subtask_count = len(data.get('subtasks', []))
            
            tasks.append({
                'filename': filename,
                'task_id': task_id,
                'input': task_input,
                'complexity': complexity,
                'subtask_count': subtask_count
            })
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return tasks


def load_task_data(filename: str) -> Dict:
    """Load full task data for a specific file."""
    file_path = os.path.join(CLEANED_DIR, filename)
    
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class TaskVisualizerHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for the task visualizer."""
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # API endpoints
        if path == '/api/tasks':
            self.send_json_response(get_task_files())
            return
        
        elif path == '/api/task':
            filename = query_params.get('file', [None])[0]
            if not filename:
                self.send_error(400, "Missing 'file' parameter")
                return
            
            data = load_task_data(filename)
            if data is None:
                self.send_error(404, "Task not found")
                return
            
            self.send_json_response(data)
            return
        
        # Serve main HTML page
        elif path == '/' or path == '/index.html':
            self.serve_index_html()
            return
        
        # Default 404
        self.send_error(404, "Not found")
    
    def serve_index_html(self):
        """Serve the main HTML interface."""
        html = get_index_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_json_response(self, data):
        """Send JSON response."""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        json_bytes = json_str.encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(json_bytes))
        self.end_headers()
        self.wfile.write(json_bytes)
    
    def log_message(self, format, *args):
        """Suppress verbose logging."""
        if "GET" in format:
            print(f"  {args[0]}")


def get_index_html() -> str:
    """Generate the main HTML interface."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Decomposition Visualizer</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            display: grid;
            grid-template-columns: 500px 1fr;
            height: 100vh;
        }
        
        .sidebar {
            background: white;
            border-right: 1px solid #e0e0e0;
            overflow-y: auto;
            box-shadow: 2px 0 10px rgba(0,0,0,0.05);
        }
        
        .sidebar-header {
            padding: 15px 20px;
            border-bottom: 2px solid #667eea;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .sidebar-header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .sidebar-header h1 {
            font-size: 1.3em;
            margin: 0;
        }
        
        .refresh-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.4);
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.3s;
            font-weight: 500;
        }
        
        .refresh-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.6);
        }
        
        .refresh-btn.loading {
            opacity: 0.6;
            pointer-events: none;
        }
        
        .sidebar-header p {
            font-size: 0.85em;
            opacity: 0.95;
            margin: 0;
        }
        
        .table-container {
            padding: 0;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        
        th {
            background: #f5f5f5;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 2px solid #e0e0e0;
            font-weight: 600;
            color: #333;
            position: sticky;
            top: 0;
            z-index: 5;
        }
        
        td {
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
        }
        
        tbody tr {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        tbody tr:hover {
            background: #f9f9f9;
            border-left: 3px solid #667eea;
            padding-left: 12px;
        }
        
        tbody tr.active {
            background: #e8e8ff;
            border-left: 4px solid #667eea;
            font-weight: 600;
        }
        
        .task-prompt {
            color: #333;
            word-break: break-word;
        }
        
        .complexity-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
            text-align: center;
            width: 50px;
        }
        
        .complexity-low { background: rgba(0, 200, 0, 0.2); color: #0a6600; }
        .complexity-medium { background: rgba(255, 150, 0, 0.2); color: #994400; }
        .complexity-high { background: rgba(255, 0, 0, 0.2); color: #990000; }
        .complexity-unknown { background: rgba(100, 100, 100, 0.2); color: #333; }
        
        .main-content {
            display: flex;
            flex-direction: column;
            background: white;
        }
        
        .toolbar {
            background: #f9f9f9;
            border-bottom: 1px solid #e0e0e0;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .toolbar-title {
            flex: 1;
        }
        
        .toolbar-title h2 {
            font-size: 1.3em;
            color: #333;
            margin-bottom: 3px;
        }
        
        .toolbar-title p {
            font-size: 0.9em;
            color: #666;
            display: -webkit-box;
            -webkit-line-clamp: 1;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        
        .toolbar-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        button {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .graph-container {
            flex: 1;
            position: relative;
            background: white;
            overflow: hidden;
        }
        
        #graphDiv {
            width: 100%;
            height: 100%;
        }
        
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            display: none;
            z-index: 100;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .legend {
            position: absolute;
            top: 15px;
            right: 15px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 50;
            font-size: 0.85em;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .legend-item:last-child {
            margin-bottom: 0;
        }
        
        .legend-box {
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 1px solid #999;
        }
        
        .empty-state {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: #999;
        }
        
        .empty-state svg {
            width: 60px;
            height: 60px;
            margin-bottom: 20px;
            opacity: 0.5;
        }
        
        @media (max-width: 768px) {
            body {
                grid-template-columns: 1fr;
            }
            
            .sidebar {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-header-top">
                <h1>Available Graphs</h1>
                <button class="refresh-btn" id="refreshBtn" title="Refresh task list">↻ Refresh</button>
            </div>
            <p>Click to visualize task decomposition</p>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Task Prompt</th>
                        <th style="width: 60px;">Complexity</th>
                    </tr>
                </thead>
                <tbody id="taskTableBody">
                    <tr style="text-align: center; opacity: 0.7;">
                        <td colspan="2" style="padding: 20px;">Loading tasks...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <div class="main-content">
        <div class="toolbar">
            <div class="toolbar-title">
                <h2 id="taskTitle">Select a task</h2>
                <p id="taskDescription">Choose a task from the list to view its decomposition</p>
            </div>
            <div class="toolbar-controls">
                <button id="resetZoomBtn" disabled>Reset View</button>
            </div>
        </div>
        
        <div class="graph-container">
            <div class="loading" id="loadingSpinner">
                <div class="spinner"></div>
                <p>Rendering graph...</p>
            </div>
            <div id="graphDiv" style="display: none;">
                <div class="legend">
                    <div class="legend-item">
                        <div class="legend-box" style="background: rgb(0, 200, 0);"></div>
                        <span>Low (30-40)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-box" style="background: rgb(200, 150, 0);"></div>
                        <span>Medium (50-70)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-box" style="background: rgb(255, 0, 0);"></div>
                        <span>High (80+)</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-box" style="background: rgb(100, 100, 100);"></div>
                        <span>Below Threshold</span>
                    </div>
                </div>
            </div>
            <div class="empty-state" id="emptyState">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v20M2 12h20M7 7h10v10H7z"/>
                </svg>
                <p>Select a task to get started</p>
            </div>
        </div>
    </div>
    
    <script>
        const COMPLEXITY_THRESHOLD = 30;
        let currentTaskData = null;
        let allTasks = [];
        
        function getComplexityColor(complexity) {
            if (complexity === null || complexity === undefined) {
                return 'rgb(100, 100, 100)';
            }
            
            if (complexity < COMPLEXITY_THRESHOLD) {
                return 'rgb(150, 150, 150)';
            }
            
            const normalized = Math.min(1, (complexity - COMPLEXITY_THRESHOLD) / (100 - COMPLEXITY_THRESHOLD));
            const red = Math.round(255 * normalized);
            const green = Math.round(200 * (1 - normalized));
            const blue = 0;
            
            return `rgb(${red}, ${green}, ${blue})`;
        }
        
        function calculateTreePositions(task, depth = 0, siblingIndex = 0, totalSiblings = 1, parentX = 0) {
            const yOffset = -depth * 3.5;  // Increased vertical spacing
            const levelWidth = 5.0 * Math.pow(2, depth);  // More spread
            const xOffset = parentX + (siblingIndex - totalSiblings / 2.0 + 0.5) * levelWidth;
            
            const nodes = [{
                x: xOffset,
                y: yOffset,
                depth: depth,
                task: task
            }];
            
            const subtasks = task.subtasks || [];
            if (subtasks.length > 0) {
                subtasks.forEach((subtask, idx) => {
                    const subNodes = calculateTreePositions(
                        subtask,
                        depth + 1,
                        idx,
                        subtasks.length,
                        xOffset
                    );
                    nodes.push(...subNodes);
                });
            }
            
            return nodes;
        }
        
        function renderGraph(taskData) {
            currentTaskData = taskData;
            const nodes = calculateTreePositions(taskData);
            
            const nodeX = nodes.map(n => n.x);
            const nodeY = nodes.map(n => n.y);
            const nodeColors = nodes.map(n => getComplexityColor(n.task.complexity_score));
            const nodeTexts = nodes.map(n => {
                const input = n.task.input || 'No description';
                return input.length > 50 ? input.substring(0, 47) + '...' : input;
            });
            const nodeHoverTexts = nodes.map(n => {
                const taskId = n.task.task_id || 'N/A';
                const complexity = n.task.complexity_score !== null ? n.task.complexity_score : 'Unknown';
                const input = n.task.input || 'No description';
                return `<b>${taskId}</b><br><b>Complexity:</b> ${complexity}<br><b>Description:</b> ${input}`;
            });
            
            // Build edge traces
            const edgeX = [];
            const edgeY = [];
            
            nodes.forEach(parentNode => {
                const subtasks = parentNode.task.subtasks || [];
                if (subtasks.length === 0) return;
                
                subtasks.forEach(subtask => {
                    const childNode = nodes.find(n => n.task === subtask);
                    if (childNode) {
                        edgeX.push(parentNode.x, childNode.x, null);
                        edgeY.push(parentNode.y, childNode.y, null);
                    }
                });
            });
            
            const edgeTrace = {
                x: edgeX,
                y: edgeY,
                mode: 'lines',
                line: {
                    width: 1,
                    color: 'rgba(100, 100, 100, 0.3)'
                },
                hoverinfo: 'none',
                showlegend: false
            };
            
            const nodeTrace = {
                x: nodeX,
                y: nodeY,
                mode: 'markers+text',
                text: nodeTexts,
                textposition: 'middle center',
                hovertext: nodeHoverTexts,
                hoverinfo: 'text',
                marker: {
                    size: 28,  // Larger boxes
                    color: nodeColors,
                    line: {
                        width: 2,
                        color: 'rgba(0, 0, 0, 0.3)'
                    },
                    symbol: 'square'
                },
                textfont: {
                    size: 10,
                    family: 'Arial Black',
                    color: 'white'
                },
                showlegend: false
            };
            
            const layout = {
                title: {
                    text: `<b>${taskData.task_id}</b><br><sub>${taskData.input.substring(0, 80)}</sub>`,
                    x: 0.5,
                    xanchor: 'center'
                },
                showlegend: false,
                hovermode: 'closest',
                margin: { b: 20, l: 5, r: 5, t: 100 },
                plot_bgcolor: 'rgba(250, 250, 250, 1)',
                paper_bgcolor: 'white',
                xaxis: {
                    showgrid: false,
                    zeroline: false,
                    showticklabels: false
                },
                yaxis: {
                    showgrid: false,
                    zeroline: false,
                    showticklabels: false
                },
                font: {
                    family: 'Arial, sans-serif',
                    size: 11
                }
            };
            
            const config = {
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToAdd: [
                    {
                        name: 'Reset view',
                        icon: { width: 500, height: 500, path: 'M0 100 L100 100 L100 0' },
                        click: () => Plotly.relayout('graphDiv', { xaxis: { autorange: true }, yaxis: { autorange: true } })
                    }
                ]
            };
            
            Plotly.newPlot('graphDiv', [edgeTrace, nodeTrace], layout, config);
            
            // Zoom out to show full graph
            setTimeout(() => {
                Plotly.relayout('graphDiv', {
                    xaxis: { autorange: true },
                    yaxis: { autorange: true }
                });
            }, 100);
        }
        
        function loadTasks() {
            fetch('/api/tasks')
                .then(r => r.json())
                .then(tasks => {
                    allTasks = tasks;
                    renderTaskTable(tasks);
                })
                .catch(err => console.error('Error loading tasks:', err));
        }
        
        function getComplexityLevel(complexity) {
            if (complexity === null) return 'unknown';
            if (complexity < COMPLEXITY_THRESHOLD) return 'unknown';
            if (complexity < 50) return 'low';
            if (complexity < 80) return 'medium';
            return 'high';
        }
        
        function renderTaskTable(tasks) {
            const tbody = document.getElementById('taskTableBody');
            tbody.innerHTML = '';
            
            if (tasks.length === 0) {
                tbody.innerHTML = '<tr style="text-align: center; opacity: 0.7;"><td colspan="2" style="padding: 20px;">No tasks found</td></tr>';
                return;
            }
            
            tasks.forEach(task => {
                const row = document.createElement('tr');
                const complexity = task.complexity !== null ? task.complexity : 'N/A';
                const complexityLevel = getComplexityLevel(task.complexity);
                const complexityBadge = task.complexity !== null 
                    ? `<div class="complexity-badge complexity-${complexityLevel}">${task.complexity}</div>`
                    : '<div class="complexity-badge complexity-unknown">-</div>';
                
                row.innerHTML = `
                    <td class="task-prompt">${task.input}</td>
                    <td>${complexityBadge}</td>
                `;
                
                row.onclick = () => loadTask(task.filename, task, row);
                tbody.appendChild(row);
            });
        }
        
        function loadTask(filename, taskMeta, rowElement) {
            // Update table highlight
            document.querySelectorAll('tbody tr').forEach(el => {
                el.classList.remove('active');
            });
            rowElement.classList.add('active');
            
            // Update toolbar
            document.getElementById('taskTitle').textContent = taskMeta.task_id;
            document.getElementById('taskDescription').textContent = taskMeta.input.substring(0, 100);
            
            // Show loading
            document.getElementById('loadingSpinner').classList.add('show');
            document.getElementById('graphDiv').style.display = 'none';
            document.getElementById('emptyState').style.display = 'none';
            
            // Load task data
            fetch(`/api/task?file=${encodeURIComponent(filename)}`)
                .then(r => r.json())
                .then(data => {
                    renderGraph(data);
                    document.getElementById('graphDiv').style.display = 'block';
                    document.getElementById('loadingSpinner').classList.remove('show');
                    document.getElementById('resetZoomBtn').disabled = false;
                })
                .catch(err => {
                    console.error('Error loading task:', err);
                    document.getElementById('loadingSpinner').classList.remove('show');
                });
        }
        
        // Initialize
        loadTasks();
        
        // Refresh button functionality
        document.getElementById('refreshBtn').onclick = () => {
            const btn = document.getElementById('refreshBtn');
            btn.classList.add('loading');
            btn.disabled = true;
            
            fetch('/api/tasks')
                .then(r => r.json())
                .then(tasks => {
                    allTasks = tasks;
                    renderTaskTable(tasks);
                    btn.classList.remove('loading');
                    btn.disabled = false;
                })
                .catch(err => {
                    console.error('Error refreshing tasks:', err);
                    btn.classList.remove('loading');
                    btn.disabled = false;
                });
        };
        
        // Auto-refresh every 5 seconds
        setInterval(() => {
            fetch('/api/tasks')
                .then(r => r.json())
                .then(tasks => {
                    // Check if task count changed
                    if (tasks.length !== allTasks.length || 
                        tasks.some((t, i) => !allTasks[i] || t.filename !== allTasks[i].filename)) {
                        allTasks = tasks;
                        renderTaskTable(tasks);
                    }
                })
                .catch(err => console.error('Auto-refresh error:', err));
        }, 5000);
        
        document.getElementById('resetZoomBtn').onclick = () => {
            if (currentTaskData) {
                renderGraph(currentTaskData);
            }
        };
    </script>
</body>
</html>'''


def run_server(port: int = PORT):
    """Start the visualization server."""
    os.chdir(CLEANED_DIR.parent)
    
    with socketserver.TCPServer(("", port), TaskVisualizerHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"Task Decomposition Visualizer (Dynamic)")
        print(f"{'='*60}")
        print(f"\n[*] Server running at http://localhost:{port}")
        print(f"[*] Open your browser to view interactive task graphs")
        print(f"\nFeatures:")
        print(f"  + Real-time rendering on client-side")
        print(f"  + Lazy loading - only loads selected tasks")
        print(f"  + Larger boxes and better spacing")
        print(f"  + Full graph visible by default (optimized zoom)")
        print(f"  + Interactive zoom, pan, and hover")
        print(f"\nPress Ctrl+C to stop the server")
        print(f"{'='*60}\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


if __name__ == "__main__":
    run_server()
