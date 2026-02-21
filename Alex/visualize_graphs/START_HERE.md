# 🚀 START HERE - Task Decomposition Visualizer

Welcome! You have a complete visualization system. Here's what to do next.

## Choose Your Path

### 🏃 I want to explore tasks RIGHT NOW
```bash
python visualize_dynamic.py
```
Then open: **http://localhost:8889**

**Why?** Instant startup, beautiful interface, click any task to see its graph.

---

### 📦 I want to save/share graphs permanently
```bash
python visualize_decomposition.py
```
Then open: **visualizations/index.html**

**Why?** Creates permanent HTML files you can email, share, or archive.

---

## What You Got

| System | File | Start Time | Best For |
|--------|------|-----------|----------|
| **Dynamic** | `visualize_dynamic.py` | 1 second | Exploration |
| **Static** | `visualize_decomposition.py` | 2-3 minutes | Archival |

## Key Features (Both Systems)

✅ Hierarchical task trees with color-coded complexity
✅ Interactive zoom, pan, and hover tooltips
✅ Larger boxes for readability
✅ Better spacing (shorter connection lines)
✅ Full tree visible by default
✅ Mobile-friendly interface
✅ Works in all modern browsers

---

## Documentation

Read in this order:

### 1. Quick Overview (5 min read)
📄 **`README_VISUALIZERS.md`**
- System comparison
- Quick start for both
- Basic troubleshooting

### 2. Your Chosen System (10 min read)

**For Dynamic:**
📖 **`DYNAMIC_VISUALIZER_GUIDE.md`**
- How the web interface works
- API endpoints
- Advanced features

**For Static:**
📖 **`VISUALIZER_QUICKSTART.md`**
- How to use HTML files
- Customization options
- Examples

### 3. When to Use Which (5 min read)
📊 **`VISUALIZER_SYSTEMS_COMPARISON.md`**
- Detailed comparison table
- Workflow examples
- Decision guide

### 4. Technical Details (Optional)
📚 **`IMPLEMENTATION_SUMMARY.md`**
- What was built
- Architecture
- Performance notes

---

## 5-Minute Quick Start

### Dynamic System (1 minute setup)

```bash
# Step 1: Start server
python visualize_dynamic.py

# Step 2: Open browser
# Go to: http://localhost:8889

# Step 3: Click a task
# Graph loads instantly!
```

**That's it!** You're exploring task hierarchies in 1 minute.

### Static System (2-3 minutes setup)

```bash
# Step 1: Generate all graphs
python visualize_decomposition.py

# Step 2: Wait (2-3 minutes)
# Progress shown in terminal

# Step 3: Open browser
# Go to: visualizations/index.html

# Step 4: Click any graph
# Instant interactive visualization!
```

---

## Colors Explained

When you see the graphs, colors represent complexity:

🟢 **Green** (30-40 complexity)
- Simple tasks

🟡 **Yellow** (40-60 complexity)  
- Medium tasks

🟠 **Orange** (60-80 complexity)
- Complex tasks

🔴 **Red** (80+ complexity)
- Very complex tasks

⚫ **Grey** (below 30 or unknown)
- Threshold tasks or data missing

---

## How to Use the Graphs

### 🔍 Zoom In/Out
- **Scroll wheel**: Up to zoom in, down to zoom out
- **Trackpad**: Pinch to zoom

### ➡️ Move Around
- **Click and drag**: Pan across the graph

### ℹ️ See Details
- **Hover over any box**: Shows full task details
  - Task ID
  - Complexity score
  - Complete description

### 🔄 Reset View
- **Double-click**: Returns to default view
- **Reset View button** (dynamic only): Same effect

---

## Common Questions

### Q: Can I use both systems?
**A:** Yes! Use Dynamic for exploration, Static for archival. They complement each other.

### Q: Which one should I start with?
**A:** Start with Dynamic (1-second startup). Switch to Static when you want to share/archive.

### Q: Do I need Python installed to view graphs?
**A:** Dynamic: Yes (to run server). Static: No (just a browser).

### Q: Can I customize the colors?
**A:** Yes! Edit the source code and regenerate. See documentation for details.

### Q: What if I want to share graphs?
**A:** Use Static system - generates HTML files you can email to anyone.

### Q: Does it work offline?
**A:** Static: Yes (completely offline). Dynamic: No (needs server running).

### Q: Can multiple people use it?
**A:** Dynamic: Yes (on same network). Static: Yes (share HTML files).

---

## Troubleshooting (30 seconds)

### Dynamic won't start
```
Port 8889 in use? Edit visualize_dynamic.py, change PORT = 8889 to something else
```

### No tasks showing up
```
Check: Do you have files in cleaned_requests/ folder?
If not: Run your task generation script first
```

### Graphs look wrong
```
Try: Refresh browser (Ctrl+R or Cmd+R)
Or: Restart server (Ctrl+C then run again)
```

### Need more help?
```
See troubleshooting in:
- DYNAMIC_VISUALIZER_GUIDE.md
- VISUALIZER_QUICKSTART.md
```

---

## Pro Tips

💡 **Tip 1: Keep it running**
Leave the Dynamic server running in a terminal - instant access anytime.

💡 **Tip 2: Archive weekly**
Generate Static graphs weekly for permanent records.

💡 **Tip 3: Bookmark the URL**
Save http://localhost:8889 in your bookmarks for quick access.

💡 **Tip 4: Screenshot complex graphs**
Use browser's screenshot tool (right-click → Screenshot) to save graphs.

💡 **Tip 5: Share the index**
For Static system, share visualizations/index.html with team - it links to all graphs!

---

## Next Steps

### Right Now
✅ Choose System (Dynamic for speed, Static for sharing)
✅ Run the command
✅ Open in browser
✅ Explore!

### In 5 Minutes
✅ Click a few tasks
✅ Try zooming and panning
✅ Hover to see details
✅ Click Reset View button

### In 10 Minutes
✅ Read `README_VISUALIZERS.md`
✅ Understand both systems
✅ Decide which fits your workflow

### Later
✅ Read detailed guides as needed
✅ Customize colors if desired
✅ Integrate into your workflow
✅ Archive graphs as needed

---

## File Structure

You'll find:

```
Alex/
├── visualize_dynamic.py          ← Run this for web interface
├── visualize_decomposition.py    ← Run this to generate HTML files
│
├── START_HERE.md                 ← You are here! 👈
├── README_VISUALIZERS.md         ← System overview
├── DYNAMIC_VISUALIZER_GUIDE.md   ← Dynamic system docs
├── VISUALIZER_QUICKSTART.md      ← Static system docs
├── VISUALIZER_SYSTEMS_COMPARISON.md
├── IMPLEMENTATION_SUMMARY.md
│
├── cleaned_requests/             ← Your task data (13 JSON files)
│
└── visualizations/               ← Generated graphs (from Static system)
    ├── index.html
    ├── *_graph.html (13 files)
    └── README.md
```

---

## One-Liner Cheat Sheet

```bash
# Explore interactively (instant)
python visualize_dynamic.py

# OR generate archives (wait 3 min)
python visualize_decomposition.py

# Then open browser to the URL shown
```

---

## Remember

- Both systems work great
- Dynamic = instant + interactive
- Static = permanent + shareable
- Use both together = perfect!

---

## You're Ready! 🎉

```bash
# Type one of these:
python visualize_dynamic.py
# OR
python visualize_decomposition.py

# Then open the URL shown
# Click a task
# Explore!
```

**That's it. You're done. Go have fun exploring your task hierarchies!**

---

## Questions?

- **How do I use it?** → `README_VISUALIZERS.md`
- **How does Dynamic work?** → `DYNAMIC_VISUALIZER_GUIDE.md`
- **How does Static work?** → `VISUALIZER_QUICKSTART.md`
- **Which one should I use?** → `VISUALIZER_SYSTEMS_COMPARISON.md`

---

**Created**: 2026-02-21  
**Status**: Ready to Use ✅

**Now go explore your tasks!** 📊
