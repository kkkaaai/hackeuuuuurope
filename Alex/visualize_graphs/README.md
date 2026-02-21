# Task Decomposition Visualizer - Main Directory

Welcome! All visualization tools and documentation are now organized here.

## 📁 Structure

```
visualize_graphs/
├── visualize_decomposition.py     (Static generation script)
├── visualize_dynamic.py            (Dynamic web server script)
├── visualizations/                 (Generated HTML output)
│   ├── index.html                 (Master dashboard)
│   ├── *_graph.html               (Individual graphs x13)
│   └── README.md
└── Documentation/
    ├── START_HERE.md              (Quick start guide)
    ├── README_VISUALIZERS.md      (System overview)
    ├── DYNAMIC_VISUALIZER_GUIDE.md
    ├── VISUALIZER_QUICKSTART.md
    ├── CREATE_VISUALIZATIONS.md
    ├── VISUALIZER_SYSTEMS_COMPARISON.md
    ├── VISUALIZATION_SUMMARY.md
    └── IMPLEMENTATION_SUMMARY.md
```

## 🚀 Quick Start

### Option 1: Dynamic System (Instant)
```bash
cd visualize_graphs
python visualize_dynamic.py
# Then open: http://localhost:8889
```

### Option 2: Static System (Pre-generated)
```bash
# Already generated! Just open:
visualizations/index.html
```

## 📖 Documentation

Start with **`START_HERE.md`** for a 5-minute overview.

Then choose:
- **Dynamic system?** → `DYNAMIC_VISUALIZER_GUIDE.md`
- **Static system?** → `VISUALIZER_QUICKSTART.md`
- **Which to use?** → `VISUALIZER_SYSTEMS_COMPARISON.md`

## ✨ What You Get

- ✅ Interactive task decomposition graphs
- ✅ Color-coded complexity (green → orange → red)
- ✅ Zoomable and pannable interface
- ✅ Hover tooltips with full task details
- ✅ Two visualization approaches:
  - **Dynamic**: Web interface, instant startup
  - **Static**: Portable HTML, shareable

## 🔗 Key Files

| File | Purpose |
|------|---------|
| `visualize_dynamic.py` | Run this for web interface (instant) |
| `visualize_decomposition.py` | Run this to generate static files (2-3 min) |
| `visualizations/index.html` | View generated graphs here |

## 💡 Tips

- Dynamic system: Best for exploration
- Static system: Best for sharing/archiving
- Use both together for maximum flexibility
- All scripts run from this directory

## 🎯 Next Steps

1. Read `START_HERE.md` (5 minutes)
2. Run one of the scripts
3. Open the visualization
4. Explore your task hierarchies!

---

**For detailed help**, see the documentation files in this directory.
