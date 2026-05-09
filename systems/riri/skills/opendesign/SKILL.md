# Skill: OpenDesign — Visual Design Automation

How RiRi uses OpenDesign to create infographics, UI mockups, decks, and more.

## When to Use OpenDesign

Anytime Ahmed asks for something visual, reach for `opendesign_run()` first:

- **Data visualizations:** Infographics, dashboards, charts
- **Web/UI:** Prototypes, landing pages, mobile mockups
- **Presentations:** Slide decks, pitch decks, weekly reports
- **Social:** Carousels, posters, editorial
- **Documents:** Blog layouts, emails, invoices
- **Wireframes & assets:** Low-fi sketches, icon grids
- **Video frames:** Frame sequences for HyperFrames

## MCP Tool: opendesign_run()

### Signature

```python
opendesign_run(
    task_type: str,           # infographic|dashboard|web|ui|deck|slides|...
    prompt: str,              # Detailed description of what to create
    skill: str = "",          # Optional: override skill ID
    project_id: str = "",     # Optional: reuse existing project
    output_dir: str = "",     # Optional: copy output here
    timeout_seconds: int = 300,  # Max wait time
) → dict
```

### Parameters

**task_type** (required)
- Type of design task
- Mapped to OD skill automatically via `OD_TASK_SKILL` table (35 task types)
- Examples: `infographic`, `dashboard`, `web`, `ui`, `landing`, `deck`, `slides`, `social`, `blog`, `wireframe`
- See `/home/ahmed/projects/riri/docs/opendesign.md` for full list

**prompt** (required)
- Detailed description of what to create
- Include: dimensions, brand colors, content, tone, target audience
- Be specific — the more detail, the better
- Example: "Create a 3-column dashboard with dark theme, accent color #2563eb, showing revenue trend (line chart), customer acquisition (pie chart), and KPIs (cards). Executive audience."

**skill** (optional)
- Override the auto-mapped skill ID
- Only use if you know the OD skill name explicitly
- Leave blank to auto-map from task_type

**project_id** (optional)
- Reuse an existing OpenDesign project
- If blank, RiRi checks registry and creates new if needed
- Use when you want to update/iterate on previous output

**output_dir** (optional)
- Copy output files to this directory
- Example: `~/projects/riri/output/`
- If blank, files stay in OD project dir

**timeout_seconds** (optional, default 300)
- Max wait for task completion
- Increase for complex designs (max ~600s)
- Decrease if you want faster feedback (min 60s)

### Return Value

```python
{
    "success": True,
    "files": [
        "/path/to/index.html",
        "/path/to/style.css",
        "/path/to/script.js",
        ...
    ],
    "project_id": "riri-infographic-abc123",
    "project_dir": "~/Desktop/OpenDesign/open-design/.od/projects/riri-infographic-abc123/",
    "skill_used": "dashboard",
    "nim_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
}

# On error:
{
    "success": False,
    "error": "Daemon not responding after 12s",
}
```

## Usage Examples

### Example 1: Create a Dashboard

```python
opendesign_run(
    task_type="dashboard",
    prompt="""
    Create a data analytics dashboard with dark theme.

    Layout:
    - Top row: 4 KPI cards (revenue, users, engagement, retention)
    - Middle row: Line chart (monthly revenue) and pie chart (user distribution)
    - Bottom row: Data table with sorting/filtering

    Colors: Dark background (#1a1a1a), accent blue (#0066ff), text white
    Interactivity: Hover effects on cards, clickable chart elements
    Target: Product team daily standup
    """,
)
```

### Example 2: Create a Web Prototype

```python
opendesign_run(
    task_type="web",
    prompt="""
    Design a SaaS landing page for a project management tool.

    Sections:
    1. Hero (headline, CTA)
    2. Features grid (6 features with icons)
    3. Pricing cards (3 tiers)
    4. Testimonials carousel
    5. CTA footer

    Style: Modern, minimalist, use Interstellar Blue (#2563eb) accent
    Responsive: Desktop + mobile views
    """,
)
```

### Example 3: Create a Pitch Deck

```python
opendesign_run(
    task_type="pitch",
    prompt="""
    Create a 10-slide pitch deck for investor meeting.

    Slides:
    1. Title (company name, tagline)
    2. Problem
    3. Solution
    4. Market opportunity
    5. Business model
    6. Traction
    7. Team
    8. Financials (3-year projection)
    9. Call to action
    10. Contact

    Brand: Bold, clean typography, use company colors (primary: #2563eb, secondary: #f97316)
    """,
)
```

### Example 4: Create a Social Media Carousel

```python
opendesign_run(
    task_type="social",
    prompt="""
    Design a 5-slide LinkedIn carousel about AI trends in 2026.

    Slide 1: Title slide (eye-catching)
    Slide 2: Trend #1 with icon + brief text
    Slide 3: Trend #2 with icon + brief text
    Slide 4: Trend #3 with icon + brief text
    Slide 5: Call to action (follow for more insights)

    Dimensions: 1080x1350px (Instagram/LinkedIn standard)
    Style: Modern, gradient backgrounds, readable sans-serif font
    """,
)
```

## What Happens Internally

1. **Check daemon:** Is OD running on port 7456?
   - No → start it (Node 24, auto-waits ~15s)
2. **Check proxy:** Is NIM image proxy running on port 7457?
   - No → start it
3. **Map task type:** Look up `OD_TASK_SKILL["infographic"]` → `"dashboard"`
4. **Check registry:** Is there an existing project for this task type?
   - Yes → reuse project_id
   - No → create new with UUID
5. **Submit to OD API:** POST `/api/runs` with skill + prompt + model
6. **OD daemon connects to Hermes** (port 18789, ACP mode)
7. **Hermes routes to NIM** with task-specific model (nemotron for data, qwen3 for design)
8. **NIM generates design** (HTML/CSS/SVG)
9. **OD renders & saves** to project directory
10. **Poll for completion** (up to 5 minutes)
11. **Return file paths** to caller
12. **Save project_id in registry** for next time

## Project Continuity (Registry)

RiRi remembers projects across sessions via `~/.od/riri-projects.json`:

```json
{
  "infographic": {
    "project_id": "riri-infographic-abc123",
    "skill": "dashboard",
    "updated_at": 1715291234
  }
}
```

**How to use:**
- First call: `opendesign_run(task_type="infographic", ...)` → creates project, saves to registry
- Second call: `opendesign_run(task_type="infographic", ...)` → reuses same project, iterates
- Different task: `opendesign_run(task_type="web", ...)` → creates new project for "web" tasks

**Manual control:**
```python
# Force new project (don't reuse)
opendesign_run(task_type="infographic", project_id="new", prompt="...")

# Reuse specific project
opendesign_run(task_type="infographic", project_id="riri-infographic-abc123", prompt="...")

# Reset registry (start fresh)
import os
os.remove(os.path.expanduser("~/.od/riri-projects.json"))
```

## Available Task Types & Skills

See `/home/ahmed/projects/riri/docs/opendesign.md` for full table (35 task types).

Quick reference:

| Task | Skill | Best For |
|---|---|---|
| `infographic`, `dashboard` | `dashboard` | Data visualization |
| `web`, `ui`, `landing` | `web-prototype` | Web design |
| `mobile` | `mobile-app` | Mobile UI |
| `deck`, `slides`, `pitch` | `html-ppt` | Presentations |
| `social` | `social-carousel` | Social media |
| `blog`, `email` | `blog-post`, `email-marketing` | Content layout |
| `svg`, `animation` | `web-prototype`, `motion-frames` | Code-heavy |
| `wireframe` | `wireframe-sketch` | Low-fi mockup |

## Model Routing

OD automatically picks the best NIM model for your task:

| Task Category | Model | Latency |
|---|---|---|
| Data/infographic/dashboard | `nemotron-super-49b` (reasoning) | ~1.5s per iteration |
| Web/UI/design | `qwen3-next-80b` (design strength) | ~1.2s |
| Code/SVG/animation | `qwen3-coder-480b` (code gen) | ~2.5s |

(Actual time depends on OD rendering + Hermes routing + NIM inference)

## Tips & Best Practices

### 1. Be Specific in Prompts

❌ Bad:
```
"Make an infographic"
```

✅ Good:
```
"Create a 1200x800px infographic with dark theme showing quarterly revenue growth.
Include: 3-column layout, left column line chart (revenue trend), middle column
stat cards (YoY growth %), right column supporting text. Colors: white text on #1a1a1a,
accent #2563eb. Audience: executive summary."
```

### 2. Specify Dimensions

- **Web:** Usually 1920x1080 or responsive
- **Social:** 1080x1350 (Instagram), 1200x627 (LinkedIn)
- **Dashboard:** 1200x800 or full-viewport
- **Deck:** 1920x1080 per slide

### 3. Include Brand/Color Info

```
"Use dark theme: background #1a1a1a, primary accent #2563eb,
secondary #f97316, text #ffffff. Font: sans-serif (Helvetica or similar)."
```

### 4. Set Expectations for Interactivity

```
"Include hover effects on cards, clickable elements that highlight,
smooth transitions between states."
```

### 5. Iterate, Don't Recreate

Instead of starting over:
```python
# Call 1: Initial design
opendesign_run(task_type="dashboard", prompt="Create dashboard with...")

# Call 2: Refine (reuses same project)
opendesign_run(
    task_type="dashboard",
    prompt="Update the dashboard: change colors to dark theme, move KPIs to top..."
)
```

## Output Files

After successful run, files are in:
```
~/Desktop/OpenDesign/open-design/.od/projects/<project_id>/
```

**Typical structure:**
```
index.html        — Main prototype (open in browser)
style.css         — Stylesheet
script.js         — Interactions/animations
config.json       — Project metadata
media/            — Generated images (if OD used image gen)
```

**To view:**
```bash
# Open in browser
open ~/Desktop/OpenDesign/open-design/.od/projects/riri-infographic-abc123/index.html

# Or copy to RiRi output
cp -r ~/Desktop/OpenDesign/open-design/.od/projects/riri-infographic-abc123/index.html ~/projects/riri/output/
```

## Integration with Video Pipelines

If OD generated frames for video:

```python
# Get HTML output from OD
od_result = opendesign_run(task_type="video", prompt="...")

# Feed to HyperFrames
html_file = od_result["files"][0]  # index.html
html_content = open(html_file).read()

hyperframes_render(
    slug="my_video",
    html_content=html_content,
    output_path="~/projects/riri/output/video.mp4",
    width=1080, height=1080, duration=5
)
```

## Troubleshooting

### "Daemon not responding"

```bash
# Check logs
tail /tmp/od-daemon.log

# Restart
pkill -f "cli.js"
bash ~/.local/bin/opendesign-start.sh
```

### "Image generation in OD failing"

```bash
# Check proxy
curl -s http://localhost:7457/health

# Restart
pkill -f "nim_image_proxy"
python3 ~/projects/riri/tools/nim_image_proxy.py &
```

### "Model timeout (Nemotron / Qwen taking >30s)"

Increase timeout:
```python
opendesign_run(
    task_type="dashboard",
    prompt="...",
    timeout_seconds=600  # 10 minutes for complex tasks
)
```

### "Project not reusing"

Check registry:
```bash
cat ~/.od/riri-projects.json | jq '.dashboard'
# If empty, create one task manually
```

---

**Related Documentation:**
- `/home/ahmed/projects/riri/docs/opendesign.md` — Daemon, proxy, architecture
- `/home/ahmed/projects/riri/docs/nim.md` — NIM model reference
- `/home/ahmed/projects/riri/CLAUDE.md` — Architecture overview

**Last updated:** 2026-05-09
