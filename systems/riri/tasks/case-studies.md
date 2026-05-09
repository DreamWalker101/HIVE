# TASK: Generate Case Studies for Tavren AI Stack

**Priority**: High
**Owner**: RiRi (autonomous execution)
**Output directory**: ~/projects/riri/case-studies/

---

## OBJECTIVE

Create 4 polished case study documents (Markdown + visual diagrams) covering the core systems built at Tavren. Each case study should:
- Be saved as a `.md` file with embedded ASCII/Mermaid diagrams
- Include an SVG architecture diagram generated via Python
- Be indexed into the ChromaDB knowledge base via `riri-index --add`
- Be around 600-900 words of actual substance (not filler)

---

## CASE STUDIES TO PRODUCE

### 1. RiRi — Personal AI Overlay
**File**: `~/projects/riri/case-studies/01-riri-overlay.md`

Cover:
- The problem: no ambient AI assistant that stays out of the way but is always reachable
- Solution: transparent GTK3 pill window, hover-reveal at top-center of screen, spring-fade opacity animation
- Architecture: 4-tier brain fallback chain (Ollama gemma3:4b → Gemini CLI → Groq llama-3.3-70b → OpenAI), tier indicator label, colour-coded (green/blue/amber/red)
- Memory system: SQLite at ~/.local/share/riri/memory.db, nomic-embed-text 768d embeddings via Ollama, cosine similarity recall, session compaction
- IPC: Unix socket /tmp/riri.sock for notify/expand/hide/ask commands
- Include this architecture diagram (Mermaid):
  ```
  graph TD
    User -->|hover trigger| RiRi_Window
    RiRi_Window -->|query| BrainFallback
    BrainFallback --> Ollama_local
    BrainFallback --> Gemini_CLI
    BrainFallback --> Groq_API
    BrainFallback --> OpenAI_API
    RiRi_Window -->|recall context| MemoryDB[(SQLite + Embeddings)]
    Pipeline -->|session facts| MemoryDB
  ```
- Key technical choices and why (GTK3 RGBA visual for transparency, Ollama-first for zero-cost inference)
- Outcome: always-on VA, no context switching required, free 95%+ of queries

### 2. Claude Pipeline Awareness
**File**: `~/projects/riri/case-studies/02-claude-pipeline.md`

Cover:
- The problem: no visibility into what Claude Code actually did across sessions — files changed, commands run, bugs fixed
- Solution: hooks into Claude Code's SessionStart / PostToolUse / Stop lifecycle events via ~/.claude/settings.json
- Architecture:
  - SessionStart → log session to pipeline.db with cwd + project
  - PostToolUse → buffer SIGNAL_TOOLS (Bash, Write, Edit, WebFetch, Task…) into tool_events table; track files_changed, cmds_run, errors per session
  - Stop → read .jsonl transcript → parse user+assistant+tool turns → Ollama distillation → structured JSON (summary, key_changes, problems_solved, still_todo, important_facts) → store in RiRi memory DB
- Include data flow diagram (Mermaid):
  ```
  graph LR
    Claude_Code -->|JSON via stdin| Hook_Script
    Hook_Script -->|SessionStart| pipeline_db[(pipeline.db)]
    Hook_Script -->|PostToolUse| pipeline_db
    Hook_Script -->|Stop| Ollama_Distill
    Ollama_Distill -->|structured facts| memory_db[(memory.db)]
    RiRi -->|query: what did Claude do?| memory_db
  ```
- Queryable from RiRi: "what did Claude work on yesterday?", "what files changed in outreach-engine?"
- Outcome: full audit trail of all AI work, searchable via natural language

### 3. Tool Knowledge Base (ChromaDB + Registry)
**File**: `~/projects/riri/case-studies/03-tool-knowledge-base.md`

Cover:
- The problem: RiRi (and the brain) doesn't know what CLI tools are available or how to use them
- Solution: structured tool registry (JSON) + ChromaDB semantic indexing
- Registry: 31 tools across 11 categories — web_search (ddgs, trafilatura, yt-dlp), browser_automation (browser-use, chrome), google_workspace (gws), ai_models (ollama, gemini, gsd), devops_git (gh, git, vercel, neonctl), outreach_engine, document_processing (docling, pdfplumber), media (ffmpeg, ImageMagick), data (jq, chroma), system_services, ml_training (huggingface-cli, unsloth, accelerate)
- Indexing: nomic-embed-text via Ollama, 800-char chunks with 150-char overlap, upserted into ChromaDB PersistentClient
- How RiRi uses it: `_tool_hints(task)` function queries ChromaDB at query time, injects top-3 relevant tool docs into brain context — so the brain knows to use `gws gmail` for email tasks, `ddgs` for web search, etc.
- Stats: 3,310 total chunks — 31 tool docs + 747 project markdown files + 12 AGENTS.md files
- Include category breakdown table
- Outcome: brain auto-selects the right CLI tool without hallucinating tool names

### 4. Outreach Engine
**File**: `~/projects/riri/case-studies/04-outreach-engine.md`

Cover:
- The problem: manual outreach is slow and doesn't scale; needed automated, personalised cold outreach
- What it does: pull leads → generate personalised email copy with AI → send via Gmail (gws) → track replies + status
- Architecture overview — use `ls ~/projects/outreach-engine/` and `cat ~/projects/outreach-engine/README.md` (if exists) to get accurate details. If no README, infer from the file structure.
- Key integrations: GWS CLI for sending, likely Neon/Postgres for lead tracking
- Run `outreach status` to get live stats and include them
- Run `outreach stats` for campaign metrics
- Outcome: automated personalised outreach at scale

---

## VISUAL GENERATION

For each case study, also generate a simple SVG architecture diagram using Python (matplotlib or svgwrite) and save it as `~/projects/riri/case-studies/img/<name>.svg`. Keep diagrams clean — boxes and arrows, no clutter.

Use Python + matplotlib if svgwrite isn't available:
```bash
pip install svgwrite --break-system-packages 2>/dev/null || true
```

---

## INDEXING

After writing all 4 case studies, run:
```bash
riri-index --add ~/projects/riri/case-studies/01-riri-overlay.md
riri-index --add ~/projects/riri/case-studies/02-claude-pipeline.md
riri-index --add ~/projects/riri/case-studies/03-tool-knowledge-base.md
riri-index --add ~/projects/riri/case-studies/04-outreach-engine.md
```

---

## NOTIFICATION

When done, notify RiRi:
```bash
python3 ~/projects/riri/notify.py "Case studies complete — 4 docs indexed in knowledge base"
```

---

## EXECUTION NOTES

- Use `bash` for reading actual file structures, running `outreach` CLI, getting real data
- Do NOT make up statistics — if a number isn't known, check the actual system
- The case studies should read like internal technical documentation, not marketing copy
- If the outreach engine README doesn't exist, write a brief architecture inference section based on files found
- Write all docs in clean markdown with proper headers, no excessive bullet nesting
