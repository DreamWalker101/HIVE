# RiRi System Architecture

Complete diagram of how all components fit together.

## High-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                    HERMES AGENT v0.12.0 (Gateway)                   │
│                          Port 18789                                  │
│                    Default: kimi-k2.6 (1M ctx)                       │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  MCP Tool Dispatcher                                        │   │
│   │  • riri-tools (LinkedIn, HyperFrames, notifications, mem0) │   │
│   │  • opendesign_run (design automation)                       │   │
│   │  • nim_infer (specialist model calls)                       │   │
│   │  • get_pipeline_report (project history)                    │   │
│   │  • spawn_agent (Claude/Codex subprocesses)                  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  LLM Router (litellm integration)                           │   │
│   │  • nim/* → https://integrate.api.nvidia.com/v1             │   │
│   │  • groq/* → https://api.groq.com/openai/v1                 │   │
│   │  • ollama/* → http://localhost:11434                        │   │
│   │  Fallback chain: Kimi → Qwen3 → Nemotron → Groq → Ollama   │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
       │                    │                    │
       │                    │                    │
   DISCORD           WHATSAPP            MESSAGE CHANNELS
   (port 18789)      (via Hermes)        (MCP responses)
       │                    │                    │
       └────────────────────┴────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
      NIM                   NVIDIA APIs
   (LLM backend)
        │
    ├─ Chat completions: /v1/chat/completions
    ├─ FLUX image: /v1/genai/black-forest-labs/flux.1-{schnell|dev|kontext}
    └─ Embeddings: (for Mem0 via proxy)
```

## Component Details

### 1. Hermes Gateway (Port 18789)

**Path:** `~/.hermes/`
**Config:** `~/.hermes/config.yaml`
**Env:** `~/.hermes/.env`
**Version:** 0.12.0 (OpenClaw migration, 2026-05-08)

**Responsibilities:**
- Accept messages from Discord/WhatsApp
- Route to MCP tools (dispatch function calls)
- Route to LLM (with selected model + fallbacks)
- Manage session state

**Key config entries:**
```yaml
model:
  default: nim/moonshotai/kimi-k2.6
  fallbacks: [nim/qwen3-next-80b, nim/nemotron-super-49b, ...]

custom_providers:
  - name: nim
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}

toolsets:
  - hermes-cli

agent:
  max_turns: 90
  gateway_timeout: 1800
```

**Start/stop:**
```bash
systemctl --user start hermes-gateway
systemctl --user stop hermes-gateway
systemctl --user restart hermes-gateway
systemctl --user status hermes-gateway
journalctl --user -u hermes-gateway -f  # live logs
```

**Logs:**
- Error log: `~/.hermes/logs/errors.log`
- Gateway log: `~/.hermes/logs/gateway.log`

---

### 2. NIM (NVIDIA Inference Microservices)

**Endpoint:** `https://integrate.api.nvidia.com/v1`
**Auth:** Bearer `$NVIDIA_API_KEY`
**Format:** OpenAI-compatible

**Primary models (tested 2026-05-01):**

| Model | Latency | Purpose |
|---|---|---|
| `moonshotai/kimi-k2.6` | ~20s | **Primary**: 1M context, complex reasoning |
| `qwen/qwen3-next-80b-a3b-instruct` | 1.2s | Default fallback: fast, reliable |
| `nvidia/llama-3.3-nemotron-super-49b-v1` | 1.5s | Reasoning, structured output |
| `qwen/qwen3.5-122b-a10b` | 1.9s | Long-form content |
| `meta/llama-3.3-70b-instruct` | 0.8s | Fast fallback |

**Image generation (FLUX models):**

Via NIM proxy at `localhost:7457` (translates OpenAI → NIM format):

| Model | Steps | Use Case |
|---|---|---|
| `black-forest-labs/flux.1-schnell` | 4 | Fast preview, quick asset generation |
| `black-forest-labs/flux.1-dev` | 20 | Quality output, LinkedIn assets |
| `black-forest-labs/flux.1-kontext-dev` | 20 | Image editing / inpainting |

**Broken models (DO NOT USE):**
- `minimaxai/minimax-m2.7` / `m2.5` — timeout
- `deepseek-ai/deepseek-v3.2` — timeout
- `google/gemma-3-27b-it` — timeout
- `mistralai/mistral-large-2` — 404

---

### 3. OpenDesign Daemon (Port 7456)

**Path:** `~/Desktop/OpenDesign/open-design/`
**Daemon binary:** `apps/daemon/dist/cli.js`
**Requires:** Node.js v24.14.1

**What it does:**
- Exposes REST API for design tasks
- Accepts prompts, skill IDs, asset uploads
- Uses a connected LLM (Hermes via ACP mode) as the design agent
- Outputs HTML/CSS/SVG prototypes
- Manages project state (SQLite)

**Start manually:**
```bash
source ~/.nvm/nvm.sh && nvm use 24
cd ~/Desktop/OpenDesign/open-design
OD_PORT=7456 node apps/daemon/dist/cli.js --no-open
```

**Or via desktop launcher:**
```bash
bash ~/.local/bin/opendesign-start.sh
```

**Health check:**
```bash
curl -s http://localhost:7456/api/skills | jq length
# Should return number of available skills
```

**Logs:** `/tmp/od-daemon.log`

**Project registry:** `~/.od/riri-projects.json`
- Maps `task_slug` → `{project_id, skill, updated_at}`
- Used for project continuity (reuse across sessions)

---

### 4. NIM Image Proxy (Port 7457)

**Script:** `~/projects/riri/tools/nim_image_proxy.py`
**Purpose:** Bridge between OpenDesign (OpenAI format) and NIM FLUX API

**Request path:**
```
OpenDesign (OpenAI format)
    ↓
POST /v1/images/generations {model, prompt, size, n, response_format}
    ↓
nim_image_proxy (port 7457)
    ↓
Translate to NIM format + call API
    ↓
POST https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev
    ↓
Return OpenAI response {data: [{b64_json}]}
```

**Model mapping (in proxy):**

| Input | Maps to | Steps |
|---|---|---|
| `flux-schnell`, `flux.1-schnell` | `black-forest-labs/flux.1-schnell` | 4 |
| `flux-dev`, `flux.1-dev` | `black-forest-labs/flux.1-dev` | 20 |
| `flux-kontext-pro`, `flux-kontext-dev` | `black-forest-labs/flux.1-kontext-dev` | 20 |
| `dalle-3`, `dalle-2` | → schnell (alias) | 4 |

**Start manually:**
```bash
python3 ~/projects/riri/tools/nim_image_proxy.py
```

**Check health:**
```bash
curl -s http://localhost:7457/health
# {"ok": true, "service": "nim-image-proxy"}
```

**List available models:**
```bash
curl -s http://localhost:7457/v1/models | jq '.data[].id'
```

**Logs:** `/tmp/nim-image-proxy.log`

---

### 5. ChromaDB (Vector Semantic Index)

**Path:** `~/.local/share/riri/chroma/`
**Purpose:** Semantic search across projects, tool docs, documentation

**Indexed content:**
- Project README files
- API docs
- AGENTS.md
- Skill documentation
- Tool source (riri_tools_mcp.py snippets)
- Past session summaries (from openamnesia)

**Query from CLI:**
```bash
python3 ~/projects/riri/tools/index.py --query "thing you're looking for"
```

**Rebuild index:**
```bash
python3 ~/projects/riri/tools/index.py --rebuild
# Re-scans ~/projects/ + ~/.hermes/workspace/skills/ + docs/
```

---

### 6. Mem0 + Qdrant (Structured Memory)

**Qdrant:** `localhost:6333`
**Storage:** `~/.local/share/riri/qdrant/`
**Purpose:** Store discrete facts (not raw text): "Ahmed published 3 posts on April 30", "Ahmed prefers short builder-tone posts"

**MCP tools:**

```python
mem0_recall(query="LinkedIn posts this week")
# Returns: list of matching facts + injectable context block

mem0_store(text="Ahmed published post about X. URL: ...")
# Call after completing tasks
```

**CLI (debug/inspect):**
```bash
python3 ~/projects/riri/tools/riri_mem0.py search "LinkedIn posts"
python3 ~/projects/riri/tools/riri_mem0.py recent
python3 ~/projects/riri/tools/riri_mem0.py all
```

**Auto-start:** Qdrant runs on reboot. Check:
```bash
curl -s http://localhost:6333/health | jq .
```

---

### 7. openamnesia (Session Summarization)

**Path:** `~/projects/openamnesia/`
**Purpose:** Ingest Claude/Codex session logs → generate narrative memory summaries

**What it ingests:**
- Claude Code session logs: `~/.claude/projects/**/*.jsonl`
- Cowork sessions: `~/.config/Claude/local-agent-mode-sessions/**/*.jsonl`
- Codex logs: `~/.codex/**/*.jsonl`

**Outputs:** `~/.hermes/workspace/memory/*.md` (one per day/week)

**Auto-pipeline:**
- Runs nightly at **5:30am PKT**
- Ingests last 24h of sessions
- Generates summaries with NIM
- Extracts facts → Mem0
- Writes .md files

**Manual run:**
```bash
export $(grep -v '^#' ~/.nanobot/secrets.env | xargs -d '\n')
cd ~/projects/openamnesia
.venv/bin/python riri_amnesia.py context
```

**Load memory on session start:**
```bash
# This should run automatically in RiRi init
~/.local/bin/riri-memory-run.sh
```

---

### 8. RiRi MCP Tools (riri_tools_mcp.py)

**Path:** `~/projects/riri/tools/riri_tools_mcp.py`
**Spawned by:** Hermes MCP dispatcher
**Env:** Inherits `~/.hermes/.env` + `~/.nanobot/secrets.env`

**Exposed tools:**

| Tool | Purpose |
|---|---|
| `linkedin_post(text)` | Publish a text post, return URL |
| `linkedin_delete(urn)` | Delete a post by URN |
| `hyperframes_render(slug, html_content, ...)` | Render HTML → MP4 via Puppeteer + FFmpeg |
| `riri_notify(level, message)` | Send WhatsApp notification (done/error/approval/update) |
| `mem0_recall(query)` | Search structured memory |
| `mem0_store(text)` | Store new fact |
| `opendesign_run(task_type, prompt, ...)` | Design task automation (see below) |
| `nim_generate_image(prompt, model, width, height)` | Generate image via NIM FLUX + proxy |
| `nim_infer(model, prompt, system, max_tokens)` | Call specialist NIM models |
| `get_pipeline_report(days)` | Query pipeline.db for project history |

**Key functions:**

```python
# OpenDesign task runner
opendesign_run(
    task_type="infographic",        # from OD_TASK_SKILL table
    prompt="...",                   # detailed description
    skill="",                       # override skill ID (optional)
    project_id="",                  # reuse project (optional)
    output_dir="",                  # copy output here (optional)
    timeout_seconds=300,
)
# Returns: {success, files, project_id, project_dir, skill_used, nim_model}

# Image generation
nim_generate_image(
    prompt="...",
    model="black-forest-labs/flux.1-schnell",  # or flux.1-dev
    width=1024, height=1024,
    output_path=""  # auto-saves to ~/projects/riri/output/images/
)
```

**OD task routing table (OD_TASK_SKILL dict, 35 entries):**

```python
# Infographics / dashboards
"infographic" → "dashboard"
"dashboard" → "dashboard"
"data-viz" → "dashboard"
"chart" → "dashboard"
"report" → "finance-report"

# Web / UI
"web" → "web-prototype"
"ui" → "web-prototype"
"landing" → "saas-landing"
"saas" → "saas-landing"

# Mobile
"mobile" → "mobile-app"

# Presentations
"deck" → "html-ppt"
"slides" → "html-ppt"
"pitch" → "html-ppt-pitch-deck"

# Social / content
"social" → "social-carousel"
"blog" → "blog-post"
"email" → "email-marketing"

# Visual
"image" → "image-poster"
"poster" → "image-poster"
"svg" → "web-prototype"
"wireframe" → "wireframe-sketch"

# Video / animation
"video" → "hyperframes"
"animation" → "motion-frames"

# Misc
"invoice" → "invoice"
"kanban" → "kanban-board"
"okrs" → "team-okrs"
```

---

### 9. Pipeline Database (Project History)

**Path:** `~/.local/share/riri/pipeline.db` (SQLite)
**Purpose:** Log of every Claude coding session, what Ahmed worked on, outcomes

**Schema:**
```sql
sessions (
    id,
    project,
    summary,
    started_at,
    ended_at,
    context_tokens,
    output_tokens,
    tool_calls,
)
```

**Query example:**
```bash
sqlite3 ~/.local/share/riri/pipeline.db \
  "SELECT project, summary, ended_at FROM sessions ORDER BY ended_at DESC LIMIT 10;"
```

**MCP tool:**
```python
get_pipeline_report(days=7)
# Returns table of last N days' work
```

---

## Message Flow: Discord → Hermes → NIM → Tool

### Simple case: "Post to LinkedIn"

```
Discord: "Post to LinkedIn: Check out my new project..."
    ↓
Hermes gateway (recv on port 18789)
    ↓
Route to MCP: linkedin_post tool
    ↓
riri_tools_mcp.py: linkedin_post()
    ├─ GET /v2/userinfo → get Ahmed's LinkedIn ID
    ├─ POST /rest/posts → publish
    └─ Return {success: true, url: "...", urn: "..."}
    ↓
Hermes formats response
    ↓
Discord: "✅ *RiRi* — Posted. URL: https://linkedin.com/feed/..."
```

### Complex case: "Create an infographic"

```
Discord: "Make an infographic showing our product metrics..."
    ↓
Hermes gateway
    ↓
Route to MCP: opendesign_run tool
    ↓
riri_tools_mcp.py: opendesign_run(task_type="infographic", prompt="...")
    ├─ Check if OD daemon is running → if not, start it
    ├─ Check if NIM proxy is running → if not, start it
    ├─ Look up project registry for "infographic" task
    ├─ Create/reuse project
    ├─ Call OD API: POST /api/runs
    │   {
    │     projectId: "riri-infographic-...",
    │     skillId: "dashboard",
    │     prompt: "...",
    │     model: "nim/nvidia/llama-3.3-nemotron-super-49b-v1"
    │   }
    ├─ OD daemon receives request
    │   └─ Connects to Hermes (ACP mode, port 18789)
    │   └─ Sends design prompt to Hermes
    │       → Hermes routes to NIM with nemotron-super-49b
    │       → NIM returns design HTML/CSS
    │   └─ OD renders to browser, saves to project dir
    │
    ├─ Poll /api/runs/{runId} until complete
    ├─ Collect output files
    ├─ Save project_id to registry
    └─ Return {success, files, project_id}
    ↓
Hermes formats response + attaches HTML file
    ↓
Discord: "✅ *RiRi* — Infographic created. Files: [download links...]"
```

### Image generation path

```
prompt: "Generate a LinkedIn cover image..."
    ↓
Call MCP: nim_generate_image(prompt, model="flux.1-dev")
    ↓
riri_tools_mcp.py: nim_generate_image()
    ├─ Load NVIDIA_API_KEY from env
    ├─ POST http://localhost:7457/v1/images/generations
    │   {model: "flux.1-dev", prompt: "...", size: "1024x1024"}
    ├─ NIM proxy receives
    │   ├─ Map "flux.1-dev" → "black-forest-labs/flux.1-dev"
    │   ├─ POST https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev
    │   │   {prompt: "...", width: 1024, height: 1024, steps: 20}
    │   ├─ NIM returns {artifacts: [{base64: "..."}]}
    │   └─ Proxy returns OpenAI format: {data: [{b64_json: "..."}]}
    ├─ Decode base64 PNG
    ├─ Save to ~/projects/riri/output/images/
    └─ Return {success, path}
    ↓
Discord: "✅ *RiRi* — Image saved: ~/projects/riri/output/images/..."
```

---

## Startup Sequence (Boot)

1. **Systemd starts Hermes gateway** (`systemctl --user start hermes-gateway`)
   - Loads `~/.hermes/config.yaml`
   - Loads `~/.hermes/.env` (NVIDIA_API_KEY, etc.)
   - Starts port 18789 listener

2. **Qdrant starts** (auto via systemd, if configured)
   - Listens on port 6333
   - Loads existing vector store from `~/.local/share/riri/qdrant/`

3. **Ollama starts** (auto via systemd, if configured)
   - Loads embedding models (nomic-embed-text, qwen2.5-coder)

4. **OpenDesign daemon is dormant** until first use
   - Will auto-start when `opendesign_run()` is called
   - Or via `bash ~/.local/bin/opendesign-start.sh`

5. **NIM image proxy is dormant** until first use
   - Will auto-start when image generation requested
   - Or when OD daemon starts

6. **Memory pipeline runs at 5:30am PKT**
   - Ingests last 24h of Claude/Codex sessions
   - Generates summaries, stores facts
   - Writes to `~/.hermes/workspace/memory/`

---

## Shutdown & Restart

**Full restart:**
```bash
# Stop gateway
systemctl --user stop hermes-gateway

# Kill lingering processes
pkill -f "cli.js"          # OD daemon
pkill -f "nim_image_proxy" # NIM proxy
pkill -f "hermes acp"      # OD Hermes connection

# Restart
systemctl --user start hermes-gateway
# Or: hermes gateway restart
```

**Restart just OD:**
```bash
pkill -f "cli.js"
sleep 2
bash ~/.local/bin/opendesign-start.sh
```

**Reset image proxy:**
```bash
pkill -f "nim_image_proxy"
sleep 2
python3 ~/projects/riri/tools/nim_image_proxy.py &
```

---

## Error Investigation

**Check what's running:**
```bash
# Gateway
systemctl --user status hermes-gateway

# Daemons
curl -s http://localhost:7456/api/skills && echo "OD daemon: OK"
curl -s http://localhost:7457/health && echo "NIM proxy: OK"
curl -s http://localhost:6333/health && echo "Qdrant: OK"

# Ollama
curl -s http://localhost:11434/api/tags && echo "Ollama: OK"
```

**Check logs:**
```bash
# Gateway errors
cat ~/.hermes/logs/errors.log
journalctl --user -u hermes-gateway -n 50

# OD daemon
tail -f /tmp/od-daemon.log

# NIM proxy
tail -f /tmp/nim-image-proxy.log

# Pipeline/memory
tail -f ~/.local/share/riri/pipeline.db  # (binary, use sqlite3)
cat ~/.hermes/workspace/memory/latest.md
```

**Common issues:**

| Issue | Check |
|---|---|
| "OD daemon not responding" | Is Node 24 installed? `nvm list` should show v24.14.1 |
| "NIM_API_KEY not found" | Is it in `~/.nanobot/secrets.env` or `~/.hermes/.env`? |
| "Flask port in use" | `lsof -i :7456` or `:7457` to find process, kill it |
| "Memory not loading" | Check `~/.hermes/workspace/memory/` exists, memory files are recent |
| "Model timeout" | Try fallback model, check NIM service status |

---

**Last updated:** 2026-05-09
