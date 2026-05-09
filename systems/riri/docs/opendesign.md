# OpenDesign Integration — Complete Guide

Everything about how RiRi uses OpenDesign for visual design tasks.

## What is OpenDesign?

OpenDesign is a **visual design tool** that uses AI (via Hermes) as the design agent. You give it a prompt, it generates HTML/CSS/SVG prototypes. RiRi uses it for:

- Infographics, dashboards, data visualizations
- UI mockups, web prototypes, landing pages
- Slide decks, presentations, pitch decks
- Social media carousels, posters
- Wireframes, blog layouts, email templates
- Video frame sequences (for HyperFrames)

## Installation & Paths

**Installation directory:** `~/Desktop/OpenDesign/open-design/`

**Verify installation:**
```bash
ls -la ~/Desktop/OpenDesign/open-design/apps/daemon/dist/cli.js
# Should exist and be executable
```

**Requires:** Node.js v24.14.1 (check with `nvm list`)

```bash
nvm install 24  # If not installed
nvm use 24
```

## Two Ways to Use OpenDesign

### 1. Desktop GUI (Ahmed's Manual Use)

**Start:**
```bash
bash ~/.local/bin/opendesign-start.sh
```

**What the launcher script does:**
1. Unsets `ANTHROPIC_API_KEY` (prevents litellm hijacking)
2. Loads `~/.hermes/.env` + `~/.nanobot/secrets.env`
3. Starts OD daemon (Node 24, port 7456)
4. Starts NIM image proxy (port 7457)
5. Configures OD to use NIM proxy for image generation
6. Opens browser to `http://localhost:7456`

**In OpenDesign UI:**
1. Create/open a project
2. Select skill (dashboard, web-prototype, html-ppt, etc.)
3. Write design prompt
4. Go to Settings → AI Provider → **NVIDIA NIM**
5. Base URL: `https://integrate.api.nvidia.com/v1`
6. Model: `moonshotai/kimi-k2.6` (or other NIM model)
7. API key: paste `$NVIDIA_API_KEY`
8. Click Generate

**Desktop icon:** `~/Desktop/OpenDesign.desktop`

### 2. RiRi's MCP Tool (Programmatic)

**MCP tool:** `opendesign_run()`

```python
opendesign_run(
    task_type="infographic",    # from OD_TASK_SKILL table
    prompt="Create a 3-column dashboard showing...",
    skill="",                   # optional: override skill ID
    project_id="",              # optional: reuse existing project
    output_dir="",              # optional: copy output here
    timeout_seconds=300,
)
```

**Return value:**
```python
{
    "success": True,
    "files": ["/path/to/index.html", "/path/to/style.css", ...],
    "project_id": "riri-infographic-abc123",
    "project_dir": "~/Desktop/OpenDesign/open-design/.od/projects/riri-infographic-abc123/",
    "skill_used": "dashboard",
    "nim_model": "nvidia/llama-3.3-nemotron-super-49b-v1",
}
```

**What it does automatically:**
- Starts OD daemon if not running
- Starts NIM image proxy if not running
- Looks up project registry to reuse existing project
- Creates new project if first time for this task type
- Submits design task to Hermes (MCP mode)
- Polls until complete (up to 5 minutes)
- Returns file paths

---

## Daemon Management

### Check if Running

```bash
curl -s http://localhost:7456/api/skills | jq 'length'
# Returns: 35 (number of available skills)
# 0 or error → daemon not running
```

### Manual Start

```bash
source ~/.nvm/nvm.sh && nvm use 24
cd ~/Desktop/OpenDesign/open-design
OD_PORT=7456 nohup node apps/daemon/dist/cli.js --no-open > /tmp/od-daemon.log 2>&1 &
```

### Manual Stop

```bash
pkill -f "cli.js"
```

### Logs

```bash
tail -f /tmp/od-daemon.log
```

### Common Errors

**"Node 24 not found"**
```bash
nvm install 24
```

**"Cannot connect to daemon"**
1. Check logs: `tail /tmp/od-daemon.log`
2. Check port: `lsof -i :7456`
3. Kill lingering process: `pkill -9 -f "cli.js"`
4. Restart: See above

**"Daemon crashed with SQLite error"**
- Node 22 won't work (missing native bindings)
- Must use Node 24.14.1+
- Check: `node --version` should be `v24.14.x`

---

## Project Registry

**Location:** `~/.od/riri-projects.json`

**Purpose:** Maps task types to OpenDesign project IDs, so RiRi remembers projects across sessions.

**Format:**
```json
{
  "infographic": {
    "project_id": "riri-infographic-abc123def",
    "skill": "dashboard",
    "updated_at": 1715291234
  },
  "web": {
    "project_id": "riri-web-xyz789",
    "skill": "web-prototype",
    "updated_at": 1715291234
  }
}
```

**How it works:**
1. When you call `opendesign_run(task_type="infographic", ...)`
2. RiRi checks registry for existing "infographic" project
3. If found and still exists in OD, reuse it
4. If not found, create new project, store ID in registry
5. Next time you ask for an infographic, it reuses the same project

**Manual reset (start fresh):**
```bash
rm ~/.od/riri-projects.json
# Next task will create new project
```

---

## NIM Image Proxy (Port 7457)

**Script:** `~/projects/riri/tools/nim_image_proxy.py`

### Why It Exists

OpenDesign expects OpenAI image generation format:
```json
POST /v1/images/generations
{
  "model": "dall-e-3",
  "prompt": "...",
  "size": "1024x1024",
  "n": 1,
  "response_format": "b64_json"
}
```

NIM FLUX API has a different format:
```json
POST https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev
{
  "prompt": "...",
  "width": 1024,
  "height": 1024,
  "steps": 20,
  "cfg_scale": 3.5
}
```

**Proxy bridges the gap:** translates OpenAI format → NIM format.

### Check if Running

```bash
curl -s http://localhost:7457/health
# {"ok": true, "service": "nim-image-proxy"}
```

### Manual Start

```bash
python3 ~/projects/riri/tools/nim_image_proxy.py
```

### Logs

```bash
tail -f /tmp/nim-image-proxy.log
```

### Models Supported

List available models:
```bash
curl -s http://localhost:7457/v1/models | jq '.data[].id'
```

Available models in proxy (from code):

| Input Name | Maps to NIM | Steps |
|---|---|---|
| `flux-schnell`, `flux.1-schnell` | `black-forest-labs/flux.1-schnell` | 4 |
| `flux-dev`, `flux.1-dev` | `black-forest-labs/flux.1-dev` | 20 |
| `flux-kontext-pro`, `flux-kontext-dev` | `black-forest-labs/flux.1-kontext-dev` | 20 |
| `flux-pro`, `flux-1.1-pro` | `black-forest-labs/flux.1-dev` | 20 |
| `dall-e-3`, `dall-e-2` | `black-forest-labs/flux.1-schnell` | 4 |

### Configuration in OD Daemon

The launcher script (or `opendesign_run()`) calls:
```bash
curl -X PUT http://localhost:7456/api/media/config \
  -H "Content-Type: application/json" \
  -d '{"openai":{"apiKey":"$NVIDIA_API_KEY","baseUrl":"http://localhost:7457"}}'
```

This tells OD: "When you request image generation, use the local proxy at :7457 instead of calling OpenAI."

---

## Task Type → Skill Routing Table

**Full mapping (35 task types):**

| Task Type | OD Skill | NIM Model | Use Case |
|---|---|---|---|
| `infographic` | `dashboard` | `nemotron-super-49b` | Data visualization |
| `dashboard` | `dashboard` | `nemotron-super-49b` | Dashboard/analytics |
| `data-viz` | `dashboard` | `nemotron-super-49b` | Data chart |
| `chart` | `dashboard` | `nemotron-super-49b` | Chart generation |
| `report` | `finance-report` | `nemotron-super-49b` | Finance/report layout |
| `finance` | `finance-report` | `nemotron-super-49b` | Finance document |
| `web` | `web-prototype` | `qwen3-next-80b` | Website prototype |
| `ui` | `web-prototype` | `qwen3-next-80b` | UI mockup |
| `prototype` | `web-prototype` | `qwen3-next-80b` | Prototype |
| `app` | `web-prototype` | `qwen3-next-80b` | Web app |
| `landing` | `saas-landing` | `qwen3-next-80b` | Landing page |
| `saas` | `saas-landing` | `qwen3-next-80b` | SaaS site |
| `waitlist` | `waitlist-page` | `qwen3-next-80b` | Waitlist page |
| `pricing` | `pricing-page` | `qwen3-next-80b` | Pricing page |
| `kanban` | `kanban-board` | `qwen3-next-80b` | Kanban board |
| `mobile` | `mobile-app` | `qwen3-next-80b` | Mobile app mockup |
| `mobile-app` | `mobile-app` | `qwen3-next-80b` | Mobile UI |
| `deck` | `html-ppt` | `qwen3-next-80b` | Presentation slide |
| `slides` | `html-ppt` | `qwen3-next-80b` | Slide deck |
| `presentation` | `html-ppt` | `qwen3-next-80b` | Presentation |
| `pitch` | `html-ppt-pitch-deck` | `qwen3-next-80b` | Pitch deck |
| `weekly` | `html-ppt-weekly-report` | `qwen3-next-80b` | Weekly report |
| `social` | `social-carousel` | `qwen3-next-80b` | Social media |
| `social-media` | `social-carousel` | `qwen3-next-80b` | Social carousel |
| `blog` | `blog-post` | `qwen3-next-80b` | Blog post layout |
| `article` | `blog-post` | `qwen3-next-80b` | Article |
| `email` | `email-marketing` | `qwen3-next-80b` | Email template |
| `newsletter` | `email-marketing` | `qwen3-next-80b` | Newsletter |
| `docs` | `docs-page` | `qwen3-next-80b` | Documentation |
| `image` | `image-poster` | `qwen3-next-80b` | Image/poster |
| `poster` | `image-poster` | `qwen3-next-80b` | Poster design |
| `visual` | `image-poster` | `qwen3-next-80b` | Visual asset |
| `svg` | `web-prototype` | `qwen3-coder-480b` | SVG code |
| `wireframe` | `wireframe-sketch` | `qwen3-next-80b` | Wireframe |
| `video` | `hyperframes` | `qwen3-next-80b` | Video frame |
| `animation` | `motion-frames` | `qwen3-coder-480b` | Animation code |
| `frames` | `motion-frames` | `qwen3-coder-480b` | Frame sequence |
| `invoice` | `invoice` | `qwen3-next-80b` | Invoice template |
| `okrs` | `team-okrs` | `qwen3-next-80b` | OKR board |
| `magazine` | `magazine-poster` | `qwen3-next-80b` | Magazine layout |
| `sprite` | `sprite-animation` | `qwen3-next-80b` | Sprite sheet |

**Model IDs (full):**
- `nemotron-super-49b` → `nim/nvidia/llama-3.3-nemotron-super-49b-v1`
- `qwen3-next-80b` → `nim/qwen/qwen3-next-80b-a3b-instruct`
- `qwen3-coder-480b` → `nim/qwen/qwen3-coder-480b-a35b-instruct`

---

## How RiRi Calls OpenDesign

### Example: Create an Infographic

```python
# In RiRi MCP context:
opendesign_run(
    task_type="infographic",
    prompt="""
    Create a 3-column infographic dashboard showing:
    - Column 1: Monthly revenue trend (line chart)
    - Column 2: Customer acquisition by source (pie chart)
    - Column 3: Key metrics summary (cards)

    Colors: Dark theme, accent color #2563eb (blue)
    Audience: Executive summary
    """,
)
```

### What Happens Internally

1. **Check daemon:** Is OD running on port 7456?
   - If no → start it (Node 24 binary)
2. **Check proxy:** Is NIM image proxy running on port 7457?
   - If no → start it (Python script)
3. **Resolve skill:** `task_type="infographic"` → look up `OD_TASK_SKILL["infographic"]` → `"dashboard"`
4. **Resolve model:** `OD_TASK_MODEL["infographic"]` → `"nvidia/llama-3.3-nemotron-super-49b-v1"`
5. **Check registry:** Is there an existing "infographic" project?
   - If yes and still valid → reuse project_id
   - If no → create new project_id (UUID)
6. **Submit to OD API:**
   ```
   POST http://localhost:7456/api/runs
   {
     "projectId": "riri-infographic-...",
     "skillId": "dashboard",
     "prompt": "Create a 3-column infographic...",
     "model": "moonshotai/kimi-k2.6"  # or task-specific model
   }
   ```
7. **OD daemon receives** → connects to Hermes (port 18789) in ACP mode
8. **Hermes routes to NIM** with selected model (nemotron for data-heavy tasks)
9. **NIM returns design HTML/CSS/SVG**
10. **OD renders & saves** to project directory
11. **Poll /api/runs/{runId}** until `status === "complete"`
12. **Collect output files** from `~/.od/projects/riri-infographic-.../`
13. **Save project_id to registry** (so next infographic reuses same project)
14. **Return success + file paths** to caller

---

## Output Files

**Location:** `~/Desktop/OpenDesign/open-design/.od/projects/<project_id>/`

**Typical files:**
- `index.html` — Main prototype (open in browser)
- `style.css` — Stylesheet
- `script.js` — Interactions (if any)
- `config.json` — Project metadata
- `media/` — Generated images (if OD used image gen)

**To view output:**
```bash
# Open in browser
open ~/Desktop/OpenDesign/open-design/.od/projects/riri-infographic-abc123/index.html

# Or copy to RiRi output dir
cp ~/Desktop/OpenDesign/open-design/.od/projects/riri-infographic-abc123/index.html \
   ~/projects/riri/output/infographic.html
```

**Video pipeline (HyperFrames):**

If OD generated frame sequence for video, feed HTML to HyperFrames:
```python
hyperframes_render(
    slug="my_video",
    html_content=open("index.html").read(),
    output_path="~/projects/riri/output/video.mp4",
    width=1080, height=1080, duration=5
)
```

---

## Hermes ↔ OpenDesign Connection

OD daemon connects to Hermes in **ACP mode** (Agent Communication Protocol):

```
OD daemon (port 7456)
    ↓
Connect to Hermes (port 18789)
    ↓
Send design task via ACP JSON-RPC
    ↓
Hermes routes to LLM (NIM with selected model)
    ↓
LLM generates HTML/CSS/SVG
    ↓
OD receives output
    ↓
Renders to browser / saves project
```

**In `~/.hermes/config.yaml`:**
```yaml
model:
  default: nim/moonshotai/kimi-k2.6
  fallbacks: [...]

custom_providers:
  - name: nim
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
    api_mode: chat_completions
```

When OD submits a task with `model: "moonshotai/kimi-k2.6"`, Hermes routes it to NIM.

---

## Critical: ANTHROPIC_API_KEY Must Be Unset

The launcher script includes this critical line:

```bash
unset ANTHROPIC_API_KEY
unset ANTHROPIC_BASE_URL
```

**Why?**

If `ANTHROPIC_API_KEY` is set in the environment, litellm (inside Hermes) will **override** the `nim/` prefix routing and try to use Anthropic's API instead. This breaks NIM model selection.

The script ensures that:
1. OD daemon runs without ANTHROPIC_API_KEY
2. Hermes respects `nim/` model prefixes
3. NIM models route correctly

**Check:** Before launching OD, verify `ANTHROPIC_API_KEY` is not set:
```bash
env | grep ANTHROPIC
# Should return nothing
```

---

## Troubleshooting

### "Daemon not responding"

```bash
# Check logs
tail /tmp/od-daemon.log

# Check Node version
node --version  # Should be v24.14.1

# Restart
pkill -f "cli.js"
sleep 2
bash ~/.local/bin/opendesign-start.sh
```

### "Image generation failing in OD"

```bash
# Check proxy is running
curl -s http://localhost:7457/health

# Check NIM API key
echo $NVIDIA_API_KEY

# Restart proxy
pkill -f "nim_image_proxy"
python3 ~/projects/riri/tools/nim_image_proxy.py &
```

### "OD can't connect to Hermes"

1. Check Hermes is running: `systemctl --user status hermes-gateway`
2. Check port 18789 is listening: `lsof -i :18789`
3. Check NIM provider in config: `cat ~/.hermes/config.yaml | grep -A 5 "nim"`
4. Restart gateway: `systemctl --user restart hermes-gateway`

### "Project not reusing (creating duplicate every time)"

```bash
# Check registry
cat ~/.od/riri-projects.json | jq '.infographic'

# If missing, create one task manually in GUI
# Or manually add to registry:
# {
#   "infographic": {
#     "project_id": "riri-infographic-abc123",
#     "skill": "dashboard",
#     "updated_at": <unix timestamp>
#   }
# }
```

### "Model keeps timing out"

Try a faster fallback model:
```python
opendesign_run(
    task_type="infographic",
    prompt="...",
    skill="dashboard",  # force skill
    # Don't specify model — let it use qwen3-next-80b fallback
)
```

---

## When to Use OD vs NIM Image Gen vs HyperFrames

| Task | Tool | Why |
|---|---|---|
| Simple standalone image (logo, icon, banner) | `nim_generate_image()` | Fast, no overhead |
| Complex multi-element design (dashboard, poster, page) | `opendesign_run()` | Layout, reasoning, iterative |
| 2–8 second branded animation | `HyperFrames` (with OD HTML) | Video output, lightweight |
| Multi-scene, data-driven video | `Remotion` (React/TSX) | Full composability |
| Quick social media carousel | `opendesign_run(task_type="social")` | Template-based, fast |

---

**Last updated:** 2026-05-09
