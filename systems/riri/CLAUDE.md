# RiRi — Master Entry Point for Claude Code

**Start here.** This document contains everything a new Claude Code session needs to understand the RiRi system from first principles.

## What is RiRi?

RiRi is Ahmed's **personal AI assistant** living on his machine. It's not a search engine or a chatbot—it's the person who *handles things*. RiRi:

- Runs **24/7** via Hermes Agent gateway on port 18789
- Executes real tasks: posts to LinkedIn, generates videos, renders designs, manages projects
- Operates across **Discord, WhatsApp, and MCP tools**
- Has **structured memory** (Mem0 + Qdrant) and **session summaries** (openamnesia)
- Handles **design** (OpenDesign), **video** (HyperFrames/Remotion), **images** (NIM FLUX), and **code**
- Knows Ahmed's personality, preferences, and project history

## Who Ahmed Is

Ahmed is a developer building hobby projects, running personal socials (LinkedIn, Instagram), and experimenting with AI systems. He does **not** do client work. His work is personal: building things he finds interesting, documenting learnings, sharing on socials.

### Read These First — Every Session

1. **AGENTS.md** (538 lines) — Ahmed's full RiRi brain. Contains personality, capabilities, model routing, every tool, every workflow.
   - File: `/home/ahmed/.hermes/workspace/AGENTS.md`
   - **Must read before starting any task**

2. **CHANGELOG.md** — version history of RiRi features.
   - File: `/home/ahmed/projects/riri/CHANGELOG.md`

3. **sessions/INDEX.md** — dev log of every feature/change built in Claude Code sessions.
   - File: `/home/ahmed/projects/riri/sessions/INDEX.md`
   - Scan the table (one row per feature). Only open a session folder if the task is related.
   - Use `/fk` to log current session work. Use `/fkgit` to log + push to GitHub.

## Architecture at a Glance

```
┌─ Hermes Gateway (port 18789) ─────────────────────┐
│  Default model: moonshotai/kimi-k2.6 (1M context) │
│  Fallbacks: Qwen3-next-80b → Nemotron → ...       │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    Discord         WhatsApp        MCP Tools
    (primary)       (secondary)     (Hermes slot)
        │              │              │
        └──────────────┼──────────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
   NIM              ChromaDB           OpenDesign
(LLM backend)     (semantic KB)       (design daemon)
    │                  │                  │
    ├─ FLUX.1          ├─ Projects        ├─ Port 7456
    │  (image gen)     │  + tools         │
    ├─ Qwen3/Nemotron  │  + docs          └─ NIM proxy
    └─ Kimi K2.6       └─ Chroma DB         (port 7457)
                           (~/.local/
                            share/riri/
                            chroma/)
```

### Core Infrastructure

| Component | What it does | Where |
|---|---|---|
| **Hermes Agent v0.12.0** | LLM gateway, MCP dispatcher, model router | `~/.hermes/` |
| **NIM (NVIDIA)** | LLM completions + FLUX image generation | `https://integrate.api.nvidia.com/v1` |
| **OpenDesign daemon** | Design tool (infographics, UI, decks) | `~/Desktop/OpenDesign/open-design/`, port 7456 |
| **NIM image proxy** | Translates OpenAI format → NIM FLUX | `localhost:7457` |
| **ChromaDB** | Semantic index (projects, tools, docs) | `~/.local/share/riri/chroma/` |
| **Mem0 + Qdrant** | Structured memory (facts, not text) | `localhost:6333` / `~/.local/share/riri/qdrant/` |
| **openamnesia** | Session summarizer → memory files | `~/.hermes/workspace/memory/` |
| **Ollama** | Local embeddings + LLM fallback | `localhost:11434` |
| **RiRi MCP tools** | LinkedIn, HyperFrames, notifications, memory | `/home/ahmed/projects/riri/tools/riri_tools_mcp.py` |

## Critical Files & Paths

| Path | Purpose |
|---|---|
| **`/home/ahmed/.hermes/config.yaml`** | Hermes config: NIM provider, model routing, fallbacks, MCP toolsets |
| **`/home/ahmed/.hermes/.env`** | Hermes env: NVIDIA_API_KEY |
| **`/home/ahmed/.nanobot/secrets.env`** | All API keys: NVIDIA, LinkedIn, Discord, Groq, etc. |
| **`~/.local/share/riri/chroma/`** | ChromaDB vector index |
| **`~/.local/share/riri/qdrant/`** | Qdrant (Mem0) vector store |
| **`~/.od/riri-projects.json`** | OpenDesign project registry (maps task → project_id) |
| **`/tmp/od-daemon.log`** | OD daemon logs |
| **`/tmp/nim-image-proxy.log`** | NIM image proxy logs |
| **`~/.hermes/logs/errors.log`** | Hermes error log |
| **`~/.hermes/logs/gateway.log`** | Hermes gateway log |
| **`~/.hermes/workspace/memory/*.md`** | Session summaries from openamnesia |
| **`/home/ahmed/projects/riri/tools/`** | MCP tools (riri_tools_mcp.py, nim_image_proxy.py, index.py, etc.) |
| **`/home/ahmed/projects/riri/output/`** | Generated videos, images, files |

## Model Routing Table

### Primary Model: Kimi K2.6

Ahmed explicitly chose `moonshotai/kimi-k2.6` on NIM as the **primary long-context model**:
- 1M token context window
- Best for multi-file reasoning, large codebases, complex decisions
- Model ID on NIM: `moonshotai/kimi-k2.6`
- Hermes config default: `nim/moonshotai/kimi-k2.6`

### Fallback Chain (in order)

From `~/.hermes/config.yaml`:

```yaml
model:
  default: nim/moonshotai/kimi-k2.6
  fallbacks:
    - nim/qwen/qwen3-next-80b-a3b-instruct          # Primary general model (1.2s)
    - nim/nvidia/llama-3.3-nemotron-super-49b-v1    # Reasoning
    - nim/qwen/qwen3.5-122b-a10b                    # Long-form writing
    - nim/meta/llama-3.3-70b-instruct                # Fast fallback (0.8s)
    - groq/llama-3.3-70b-versatile                   # Groq fallback
    - ollama/qwen2.5-coder:7b                        # Last resort (local)
```

### Task-Specific Model Routing

For design/video tasks via OpenDesign:

| Task Type | Model | Why |
|---|---|---|
| infographic, dashboard, data-viz, chart, report | `nemotron-super-49b` | Reasoning for data layout |
| web, ui, app, prototype, landing, saas, mobile, deck, slides | `qwen3-next-80b` | Design strength |
| svg, animation, motion | `qwen3-coder-480b` | Code generation |

See **`docs/opendesign.md`** for full OD routing table (35 task types mapped).

## Environment Variables (Critical!)

**Load from `/home/ahmed/.nanobot/secrets.env` OR `/home/ahmed/.hermes/.env`:**

```bash
NVIDIA_API_KEY=<key>              # Required for NIM, image gen, OpenDesign
LINKEDIN_ACCESS_TOKEN=<token>     # LinkedIn posting
LINKEDIN_MEMBER_URN=<cached>      # LinkedIn user ID (auto-populated)
GROQ_API_KEY=<key>                # Fallback LLM
DISCORD_TOKEN=<token>             # Discord messaging
```

**Hermes sets environment for MCP tools:**
```bash
# Hermes loads ~/.hermes/.env before starting gateway
# RiRi tools inherit these + secrets.env
```

## Two Separate OpenDesign Use Cases

### 1. Desktop GUI (Ahmed's Manual Use)

**Path:** `~/Desktop/OpenDesign/open-design/`

**Start command:**
```bash
bash ~/.local/bin/opendesign-start.sh
```

**What it does:**
- Starts OD daemon (Node 24, port 7456)
- Starts NIM image proxy (port 7457)
- Opens OD in browser
- **Critical:** Script unsets `ANTHROPIC_API_KEY` so litellm NIM routing works

**Ahmed's setup:** Uses NVIDIA NIM tab (5th pill in OD settings)
- Base URL: `https://integrate.api.nvidia.com/v1`
- Model: `moonshotai/kimi-k2.6` (can override in dropdown)
- API key: `NVIDIA_API_KEY`

### 2. RiRi's MCP Tool (Programmatic)

**Tool:** `opendesign_run()` in riri_tools_mcp.py

**What it does:**
- Auto-starts daemon + proxy if not running
- Submits design task to Hermes (MCP)
- Hermes runs design using task-specific NIM model
- Returns HTML output files + project_id
- Reuses projects via registry for continuity

**Calling it:**
```python
opendesign_run(
    task_type="infographic",
    prompt="Create a 3-column data visualization showing...",
    project_id="",  # auto-create or reuse
    output_dir="~/projects/riri/output/"
)
```

## Documentation Structure

After reading **AGENTS.md**, consult these files for specific subsystems:

| File | Read for |
|---|---|
| **`docs/architecture.md`** | Full system diagram (text/ASCII) + data flow |
| **`docs/opendesign.md`** | OD daemon, project registry, task routing table, launcher script |
| **`docs/nim.md`** | NIM API reference, confirmed models, broken models, image generation |
| **`docs/hermes.md`** (if exists) | Hermes config, model routing, custom providers |
| **`skills/opendesign/SKILL.md`** | How RiRi invokes design tasks, examples |
| **`skills/nim-image/SKILL.md`** | Image generation via NIM FLUX + proxy |
| **`skills/hermes/SKILL.md`** | Hermes runtime, logging, restart procedures |

## Quick Reference — Common Tasks

### Check RiRi Status
```bash
riri_status()  # MCP tool
# or
~/.local/bin/riri-status.sh
```

### Search Project Knowledge
```bash
python3 ~/projects/riri/tools/index.py --query "thing you're looking for"
```

### Recall Structured Memory
```python
mem0_recall(query="thing you want to find")
mem0_store(text="new fact to record")
```

### Generate an Image (via NIM FLUX)
```python
nim_generate_image(
    prompt="...",
    model="black-forest-labs/flux.1-schnell",
    width=1024, height=1024
)
```

### Create a Design (via OpenDesign)
```python
opendesign_run(
    task_type="infographic",
    prompt="..."
)
```

### Post to LinkedIn
```python
linkedin_post(text="..., Ahmed has been working on...")
```

### Send a Notification (WhatsApp)
```python
riri_notify(
    level="done",  # or "error", "approval", "update"
    message="Task complete. Files saved to ~/projects/riri/output/"
)
```

### Render a Video (HyperFrames)
```python
hyperframes_render(
    slug="my_video",
    html_content="<html>...</html>",
    output_path="~/projects/riri/output/video.mp4",
    width=1080, height=1080, duration=5
)
```

## Message Identity & Tone (Discord)

Every RiRi Discord message **starts with a status glyph**:

```
✅ *RiRi*              Task completed
❌ *RiRi*              Error occurred
⏳ *RiRi* — needs your call    Needs approval
◈ *RiRi*               Normal reply / progress update
```

Tone:
- Natural, direct, no corporate speak
- Don't explain what you're doing—just do it and report results
- Keep Discord messages under 2000 chars (split if needed)
- No markdown headers in chat (plain paragraphs)
- If something fails, say what failed and what you tried; don't apologize

## What NOT to Do

- Don't ask for permission to run basic commands
- Don't add disclaimers to LinkedIn posts unless asked
- Don't suggest Ahmed "manually" do something RiRi can do
- Don't repeat what Ahmed just said back to him
- Don't go silent on async tasks—use `riri_notify()` for proactive updates

## The Only Rule That Matters

**Read AGENTS.md before starting any task.** It's 538 lines of context—Ahmed's complete brain. Everything else is reference documentation.

---

**Last updated:** 2026-05-09
**RiRi version:** 0.5 (openamnesia + continual learning)
**Hermes version:** 0.12.0 (migrated from OpenClaw)
