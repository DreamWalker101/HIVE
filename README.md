# HIVE — Ahmed's AI System Hub

**Status:** ✅ Live and initialized 2026-05-09

HIVE is the **central command hub** for Ahmed's entire AI system. It's a fully-wired Anthropic Claude Code project that:

- **Reads automatically** when any Claude Code session is started from `/home/ahmed/HIVE`
- **Logs everything** via three Anthropic hooks: Stop, PreCompact, UserPromptSubmit
- **Persists memory** in git-tracked files for continuity across sessions
- **Routes to RiRi** (AI assistant), OpenDesign (design daemon), pipelines, and all subsystems
- **Provides slash commands** for status checks, design triggers, knowledge pipeline, and memory search

## Quick Start

### Start a Session from HIVE
```bash
cd /home/ahmed/HIVE
claude --print "what you want to do"
```

The `CLAUDE.md` file loads automatically. This document contains:
- System overview
- Key paths (Hermes, NIM, OD, ChromaDB, etc.)
- Model routing (primary: kimi-k2.6, 1M context)
- Hook descriptions
- Slash command reference

### Check System Status
```bash
/project:status
```

Returns:
- Hermes gateway running? (port 18789)
- OpenDesign daemon running? (port 7456)
- NIM image proxy running? (port 7457)
- Current Hermes default model
- Last 3 memory entries

### Before Any RiRi Task
```bash
cat systems/riri/CLAUDE.md
```

RiRi is Ahmed's personal AI assistant. This file contains:
- Complete personality profile (AGENTS.md)
- All MCP tools and workflows
- Architecture diagrams
- Model routing for RiRi-specific tasks
- How to post to LinkedIn, generate images, render videos, etc.

### Search Memory
```bash
/project:memory <topic>
```

Searches across:
- `memory/SESSION_INSIGHTS.md` (PreCompact distillations)
- `memory/prompts.log` (user prompts)
- `memory/findings.md` (technical discoveries)
- `systems/riri/AGENTS.md` (RiRi personality)

## Directory Structure

```
HIVE/
├── CLAUDE.md                   # Master brain (read first)
├── STRUCTURE.md                # Visual tree + service mapping
├── INIT_REPORT.md              # Initialization details
├── README.md                   # This file
├── .claude/
│   ├── settings.json           # Hook wiring (Anthropic spec)
│   └── commands/               # Slash commands
│       ├── status.md
│       ├── design.md
│       ├── pipeline.md
│       └── memory.md
├── hooks/                      # Executable bash (all chmod +x)
│   ├── stop-log.sh            # Fires after every turn
│   ├── prompt-log.sh          # Captures user prompts
│   └── precompact-memory.sh   # Distills at ~95% context
├── memory/                     # Git-tracked persistent memory
│   ├── .git/
│   ├── SESSION_INSIGHTS.md    # Auto-populated by PreCompact
│   ├── findings.md            # 35+ technical discoveries
│   ├── sessions.log           # Session metadata
│   └── prompts.log            # User prompts (searchable)
├── systems/                    # Symlinks to live projects
│   ├── riri/                   # RiRi AI assistant
│   ├── opendesign/             # Design daemon (port 7456)
│   ├── claude-pipeline/        # URL → triage → index
│   ├── openamnesia/            # Memory ingestion
│   ├── outreach-engine/        # Outreach automation
│   └── CLI-Anything/           # 52 agent CLIs
├── skills/                     # Symlinks to RiRi skills
│   ├── opendesign/
│   ├── nim-image/
│   └── hermes/
└── ideas/                      # Knowledge base (from claude-powers)
    ├── ai-tools/               # 7 AI tool discoveries
    ├── claude-agents/          # 5 agent patterns
    ├── claude-superpowers/     # 2 power-user guides
    ├── updates/                # 8 AI news items
    └── README-claude-powers.md
```

## Key Files

| File | Purpose |
|------|---------|
| **CLAUDE.md** | Main brain file. Loaded by Claude Code. Start here. |
| **STRUCTURE.md** | Directory tree with paths and service ports. |
| **INIT_REPORT.md** | Full initialization details and checklist. |
| **memory/findings.md** | Technical discoveries (NIM, Hermes, hooks, models). Searchable. |
| **memory/SESSION_INSIGHTS.md** | Session distillations. Auto-populated by PreCompact hook. |
| **.claude/settings.json** | Hook wiring per Anthropic spec. |
| **.claude/commands/*.md** | Slash command definitions. |

## Hooks Explained

HIVE automatically logs session metadata, prompts, and transcript summaries using Anthropic's hook system.

### Stop Hook
Fires after every Claude turn. Logs session ID and working directory.
```bash
hooks/stop-log.sh
→ memory/sessions.log
```

### UserPromptSubmit Hook
Fires when user submits a prompt. Logs the prompt (first 300 chars, newlines stripped).
```bash
hooks/prompt-log.sh
→ memory/prompts.log
```
Searchable: `grep -i "topic" memory/prompts.log`

### PreCompact Hook
Fires at ~95% context usage. Captures transcript path and prepares distillation.
```bash
hooks/precompact-memory.sh
→ memory/SESSION_INSIGHTS.md
```

All three hooks are wired in `.claude/settings.json` per [Anthropic's hook spec](https://docs.anthropic.com/claude/reference/claude-code-hooks).

## Model Routing

### Primary Model: Kimi K2.6
- **Model ID:** `moonshotai/kimi-k2.6` (via NIM)
- **Context:** 1M tokens
- **Use:** Long-context reasoning, multi-file analysis, complex decisions

### Fallback Chain
From `~/.hermes/config.yaml`:
1. `nim/qwen/qwen3-next-80b-a3b-instruct` — general purpose
2. `nim/nvidia/llama-3.3-nemotron-super-49b-v1` — reasoning
3. `nim/qwen/qwen3.5-122b-a10b` — long-form writing
4. `nim/meta/llama-3.3-70b-instruct` — fast fallback
5. `groq/llama-3.3-70b-versatile` — Groq fallback
6. `ollama/qwen2.5-coder:7b` — local last resort

## Services & Ports

| Service | Location | Port |
|---------|----------|------|
| **Hermes gateway** | `~/.hermes/` | 18789 |
| **NIM LLM API** | https://integrate.api.nvidia.com/v1 | - |
| **OpenDesign daemon** | `systems/opendesign/` | 7456 |
| **NIM image proxy** | `~projects/riri/tools/` | 7457 |
| **ChromaDB** | `~/.local/share/riri/chroma/` | - |
| **Qdrant (Mem0)** | `localhost:6333` | 6333 |
| **Ollama** | `localhost:11434` | 11434 |

## Adding to Memory

### Manual Entry
```bash
cd memory
echo "## Session — $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> SESSION_INSIGHTS.md
echo "- Key finding about X: ..." >> SESSION_INSIGHTS.md
git add -A
git commit -m "insight: topic description"
```

### After a Task
The PreCompact hook will auto-populate SESSION_INSIGHTS.md with transcript location. Manually:
```bash
cat memory/SESSION_INSIGHTS.md
# Add bullet points under the latest session entry
git add -A && git commit -m "insights: session summary"
```

## Environment Variables

Required for full functionality:

```bash
# At ~/.nanobot/secrets.env or ~/.hermes/.env
NVIDIA_API_KEY=...              # NIM, image gen, OpenDesign
LINKEDIN_ACCESS_TOKEN=...       # LinkedIn posting
DISCORD_TOKEN=...               # Discord integration
GROQ_API_KEY=...                # Groq fallback
```

Hermes loads these before starting the gateway.

## Slash Commands Reference

### /project:status
System health check. Reports:
- Hermes gateway status
- OpenDesign daemon status
- NIM image proxy status
- Hermes default model
- Last 3 memory entries

### /project:design
Trigger OpenDesign task via RiRi MCP. Prompts for:
- Design type (infographic, dashboard, social post, etc.)
- Description
- Project name

### /project:pipeline
Run knowledge pipeline on URL or text:
1. Fetch content
2. Triage
3. Synthesize with NIM
4. Index to ChromaDB
5. Notify Ahmed

### /project:memory <topic>
Search across memory files:
```
/project:memory NIM routing
→ grep -i "NIM routing" memory/findings.md
→ grep -i "NIM routing" memory/SESSION_INSIGHTS.md
→ grep -i "NIM routing" systems/riri/AGENTS.md
```

## Symlinks (Live Projects)

All `systems/` and `skills/` directories are **symlinks**. Changes made inside persist in source directories:

```
systems/riri → /home/ahmed/projects/riri/
systems/opendesign → /home/ahmed/Desktop/OpenDesign/open-design/
systems/claude-pipeline → /home/ahmed/projects/claude-pipeline/
systems/outreach-engine → /home/ahmed/projects/outreach-engine/
systems/openamnesia → /home/ahmed/projects/openamnesia/
systems/CLI-Anything → /home/ahmed/projects/CLI-Anything/

skills/opendesign → /home/ahmed/projects/riri/skills/opendesign/
skills/nim-image → /home/ahmed/projects/riri/skills/nim-image/
skills/hermes → /home/ahmed/projects/riri/skills/hermes/
```

## Knowledge Base (ideas/)

Populated from `/home/ahmed/claude-powers/`:

- **ai-tools/** — 7 documents on AI tools (Claude Code, OMI, PDF-X, Takumi, Fireworks, Magika, etc.)
- **claude-agents/** — 5 documents on agent patterns (tiered routing, autoresearch, progressive disclosure, skill trust, npx-skills CLI)
- **claude-superpowers/** — 2 power-user guides (Stop hook memory, PreCompact hook distillation)
- **updates/** — 8 AI news items and research findings

Searchable:
```bash
grep -r "agent pattern" ideas/claude-agents/
grep -r "NIM" ideas/
grep -r "hook" ideas/claude-superpowers/
```

## Troubleshooting

### Hooks Not Firing?
Check that `.claude/settings.json` is valid:
```bash
cat .claude/settings.json
# Should have Stop, PreCompact, UserPromptSubmit sections
```

Check hook logs:
```bash
tail -10 memory/sessions.log
tail -10 memory/prompts.log
```

### Session Not Loading CLAUDE.md?
Ensure Claude Code session started from `/home/ahmed/HIVE`:
```bash
cd /home/ahmed/HIVE
pwd  # Should show /home/ahmed/HIVE
claude --print "test"
```

### Need RiRi Context?
Always read before RiRi tasks:
```bash
cat systems/riri/CLAUDE.md
cat systems/riri/AGENTS.md  # Full 538-line brain
```

### Memory Not Persisting?
Check git status:
```bash
cd memory
git status
git log --oneline
```

Commit new findings manually:
```bash
git add -A && git commit -m "insight: description"
```

## Next Steps

1. **Test a session:** `cd /home/ahmed/HIVE && claude --print "check system health"`
2. **Review hooks:** `cat .claude/settings.json`
3. **Check memory:** `cat memory/findings.md`
4. **Read RiRi brain:** `cat systems/riri/CLAUDE.md`
5. **Try slash commands:** `/project:status`

---

**HIVE v1.0 — Initialized 2026-05-09**  
Ready to serve as Ahmed's central AI system hub.
