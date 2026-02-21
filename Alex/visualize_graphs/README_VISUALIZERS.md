# Task Decomposition Visualizers - Master Guide

Welcome! You have two powerful visualization systems for exploring task hierarchies.

## Quick Start (Choose One)

### Option 1: Dynamic (Recommended for Exploration) ⚡

```bash
python visualize_dynamic.py
# Then open: http://localhost:8889
```

**Best for:**
- Instant startup (no waiting)
- Exploring many tasks
- Interactive analysis
- Beautiful web interface
- Real-time interaction

### Option 2: Static (Recommended for Archival) 📦

```bash
python visualize_decomposition.py
# Then open: visualizations/index.html
```

**Best for:**
- Saving permanent graphs
- Sharing with others
- Offline access
- Final reports
- Historical archive

---

## System Comparison

### Dynamic: `visualize_dynamic.py`

```
🚀 Startup:          Instant
📊 Task Loading:     On-demand (100-200ms)
💾 Storage:          Single web app
📱 Interface:        Beautiful sidebar + graph
⚙️ Customization:     Live (no restart needed)
🔗 Sharing:          Share URL (requires server)
📡 Network:          Needs active server
```

### Static: `visualize_decomposition.py`

```
⏱️  Startup:          2-3 minutes
📊 Task Loading:     Instant (pre-rendered)
💾 Storage:          13+ HTML files
📱 Interface:        Index page + individual graphs
⚙️ Customization:     Regenerate all files
🔗 Sharing:          Email HTML files (fully portable)
📡 Network:          Works completely offline
```

---

## Feature Breakdown

### Graphs & Visualization

Both systems include:
- ✅ Hierarchical tree layout with depth-based positioning
- ✅ Exponential spacing to prevent overlap
- ✅ Large boxes (28px) for readability
- ✅ Improved vertical spacing (shorter connecting lines)
- ✅ Full tree visible by default (optimized zoom)
- ✅ Color coding: Green → Orange → Red (by complexity)
- ✅ Grey boxes for below-threshold or unknown complexity
- ✅ Hover tooltips showing full task details
- ✅ Interactive zoom, pan, and reset controls

### User Interface

**Dynamic System:**
- Sidebar with task list
- Live search/filter (planned)
- Complexity badges
- Beautiful gradient design
- Responsive mobile design
- Toolbar with task info

**Static System:**
- Index page with card grid
- Task summary cards
- Color legend
- Professional styling
- Direct file access
- No dependencies after generation

---

## Installation

### Requirements
Both systems require Python 3.7+

### Dynamic System
```bash
python visualize_dynamic.py
# No external dependencies needed!
# Uses Python's built-in http.server
```

### Static System
```bash
pip install plotly
python visualize_decomposition.py
```

---

## Usage Workflows

### Workflow 1: Quick Exploration
```
$ python visualize_dynamic.py
→ http://localhost:8889
→ Click task in sidebar
→ Instant graph visualization
```

### Workflow 2: Archive & Share
```
$ python visualize_decomposition.py
(wait 2-3 minutes)
→ visualizations/index.html
→ Share/email HTML files
→ Recipient opens in any browser
```

### Workflow 3: Combined Approach
```
Daily:   python visualize_dynamic.py (exploration)
Weekly:  python visualize_decomposition.py (archive)
Result:  Live dev + permanent records
```

### Workflow 4: Team Collaboration
```
Server machine:   python visualize_dynamic.py
Team accesses:    http://server-ip:8889
All see same:     Real-time graphs
```

---

## Documentation Files

### Getting Started
- 📄 **This file** (`README_VISUALIZERS.md`)
  - Overview and quick start

### Dynamic System
- 📖 **DYNAMIC_VISUALIZER_GUIDE.md**
  - Complete dynamic system documentation
  - API endpoints
  - Architecture details
  - Troubleshooting
  - Advanced features

### Static System
- 📖 **VISUALIZER_QUICKSTART.md**
  - Quick start for static system
  - Usage examples
  - Customization options
- 📖 **CREATE_VISUALIZATIONS.md**
  - Technical documentation
  - API reference
  - Data structure details

### Comparison & Planning
- 📊 **VISUALIZER_SYSTEMS_COMPARISON.md**
  - Detailed comparison table
  - When to use each system
  - Feature matrix
  - Decision guide

### Legacy Documentation
- 📊 **VISUALIZATION_SUMMARY.md**
  - Original static system summary
  - Technical implementation details

---

## Key Features

### Graph Rendering ✅
- Real-time position calculation
- Optimized for large hierarchies
- Beautiful color gradient
- Clear hierarchy visualization

### Interactivity ✅
- Zoom (scroll or pinch)
- Pan (click + drag)
- Reset view (button or double-click)
- Hover for details
- Full tree visible by default

### Performance ✅
- Static: Instant viewing (pre-rendered)
- Dynamic: Instant startup (no generation)
- Efficient memory usage
- Scalable to many tasks

### Usability ✅
- Beautiful interfaces
- Intuitive controls
- Helpful tooltips
- Color-coded complexity
- Mobile responsive (dynamic)

---

## File Structure

```
Alex/
├── visualize_decomposition.py      (Static generation)
├── visualize_dynamic.py            (Dynamic web server)
├── cleaned_requests/               (Task data)
│   ├── 20260221T145854Z_*.json
│   ├── 20260221T151338Z_*.json
│   └── ... (11 more tasks)
├── visualizations/                 (Static output)
│   ├── index.html
│   ├── 20260221T145854Z_*_graph.html
│   └── ... (12 more graphs)
└── [documentation files]
    ├── README_VISUALIZERS.md
    ├── DYNAMIC_VISUALIZER_GUIDE.md
    ├── VISUALIZER_QUICKSTART.md
    ├── CREATE_VISUALIZATIONS.md
    └── VISUALIZER_SYSTEMS_COMPARISON.md
```

---

## Quick Troubleshooting

### "Server already running"
```
Port 8889 is in use. Either:
1. Change PORT in visualize_dynamic.py
2. Kill existing process using port
3. Use different port number
```

### "No tasks found"
```
Check:
1. cleaned_requests/ folder exists
2. JSON files are present
3. JSON files are valid (check with text editor)
4. Files have required fields: task_id, input
```

### "Graphs not rendering"
```
For Dynamic:
1. Check http://localhost:8889 loads
2. Check browser console (F12) for errors
3. Verify JSON files are readable
4. Try restarting server

For Static:
1. Regenerate with visualize_decomposition.py
2. Check visualizations/ folder
3. Open index.html directly
4. Verify plotly is installed
```

---

## Performance Notes

### Dynamic System
- **Startup**: < 1 second
- **Task load**: 100-200ms per task
- **Memory**: ~30-50MB
- **Scaling**: Excellent (loads on-demand)

### Static System
- **Generation**: 2-3 minutes for 13 tasks
- **View load**: Instant (already rendered)
- **Memory**: Varies by browser
- **Scaling**: Good (linear with task count)

---

## Advanced Tips

### Customize Dynamic System
Edit `visualize_dynamic.py`:
```python
COMPLEXITY_THRESHOLD = 30  # Change color threshold
PORT = 8889                # Change port
```

### Customize Static System
Edit `visualize_decomposition.py`:
```python
COMPLEXITY_THRESHOLD = 30  # Change color threshold
# Edit get_complexity_color() for different colors
# Edit calculate_tree_positions() for spacing
```

### Change Graph Appearance
Both systems use same algorithm:
- Larger boxes: Increase marker.size (current: 28)
- More spacing: Increase level_width (current: 5.0 * 2^depth)
- Different colors: Edit get_complexity_color() function

---

## Browser Compatibility

Both systems work in:
- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 12+
- ✅ Edge 79+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

---

## Deployment Options

### Personal Use
1. Dynamic: `python visualize_dynamic.py`
2. Open http://localhost:8889

### Team (Local Network)
1. Run server on shared machine
2. Team accesses http://server-ip:8889
3. All see same interface and graphs

### Offline Archive
1. Generate static: `python visualize_decomposition.py`
2. Archive visualizations/ folder
3. Share HTML files or host on web server

### Production
1. Use static system for archives
2. Use dynamic for team exploration
3. Both can run simultaneously
4. Static files never expire

---

## Next Steps

### First Time Users
1. **Try Dynamic** (faster to explore):
   ```bash
   python visualize_dynamic.py
   # Open http://localhost:8889
   # Click a task and explore!
   ```

2. **Read** `DYNAMIC_VISUALIZER_GUIDE.md` for details

3. **Try Static** (when you need to share):
   ```bash
   python visualize_decomposition.py
   # Wait 2-3 minutes
   # Open visualizations/index.html
   ```

4. **Read** `VISUALIZER_SYSTEMS_COMPARISON.md` to understand when to use each

### Experienced Users
- Combine both systems (daily dynamic + weekly static archives)
- Customize colors and spacing to your needs
- Use as part of your task processing pipeline
- Integrate with documentation workflows

---

## Support & Questions

For detailed information, see:
- **Dynamic system questions**: `DYNAMIC_VISUALIZER_GUIDE.md`
- **Static system questions**: `VISUALIZER_QUICKSTART.md` & `CREATE_VISUALIZATIONS.md`
- **Comparison questions**: `VISUALIZER_SYSTEMS_COMPARISON.md`
- **Code questions**: Check comments in source files

---

## Summary

You now have:

| System | Best For | Time | Storage |
|--------|----------|------|---------|
| **Dynamic** | Exploration | Instant | Temporary |
| **Static** | Archival | 2-3 min | Permanent |

Both systems:
- ✅ Display hierarchical task decomposition
- ✅ Show complexity scores with colors
- ✅ Provide interactive zoom/pan
- ✅ Include full task descriptions
- ✅ Visualize parent-child relationships
- ✅ Work in all modern browsers

**Recommended Approach:**
1. Start with Dynamic for exploration
2. Use Static for final deliverables
3. Use both together for maximum flexibility

---

**Ready to explore your tasks? Pick a system and get started!**

```bash
# Quick exploration
python visualize_dynamic.py

# OR

# Permanent archive
python visualize_decomposition.py
```

Happy visualizing! 📊

