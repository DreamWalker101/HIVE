# HIVE Directory Structure

```
/home/ahmed/HIVE/
├── CLAUDE.md                          # Master brain file (read first)
├── STRUCTURE.md                       # This file
├── .claude/
│   ├── settings.json                  # Hook wiring (Anthropic spec)
│   └── commands/
│       ├── status.md                  # /project:status
│       ├── design.md                  # /project:design
│       ├── pipeline.md                # /project:pipeline
│       └── memory.md                  # /project:memory
├── hooks/                             # Executable bash hooks
│   ├── stop-log.sh                    # Fires after every turn
│   ├── prompt-log.sh                  # Logs user prompts
│   └── precompact-memory.sh           # Distills at ~95% context
├── memory/                            # Git-tracked session memory
│   ├── .git/                          # Initialized git repo
│   ├── SESSION_INSIGHTS.md            # Auto-populated by PreCompact
│   ├── findings.md                    # Key technical discoveries
│   ├── sessions.log                   # Session metadata log
│   └── prompts.log                    # User prompt log
├── systems/                           # Symlinks to live projects
│   ├── riri/                          # RiRi AI assistant (MCP tools, AGENTS.md)
│   ├── opendesign/                    # OpenDesign daemon (port 7456)
│   ├── claude-pipeline/               # URL → triage → index pipeline
│   ├── outreach-engine/               # Outreach automation
│   ├── openamnesia/                   # Session memory ingestion
│   └── CLI-Anything/                  # 52 agent-native CLIs
├── skills/                            # Symlinks to RiRi skills
│   ├── opendesign/                    # SKILL.md for design tasks
│   ├── nim-image/                     # SKILL.md for NIM FLUX
│   └── hermes/                        # SKILL.md for Hermes gateway
└── ideas/                             # Knowledge base (from claude-powers)
    ├── ai-tools/                      # AI tool discoveries
    ├── claude-agents/                 # Agent patterns & research
    ├── claude-superpowers/            # Advanced Claude capabilities
    ├── updates/                       # Model releases, AI news
    ├── README-claude-powers.md        # Knowledge base intro
    └── CHANGELOG-claude-powers.md     # Knowledge base updates
```

## Key Paths & Services

| Component | Location | Port |
|-----------|----------|------|
| Hermes gateway | ~/.hermes/ | 18789 |
| NIM API | https://integrate.api.nvidia.com/v1 | - |
| OpenDesign daemon | systems/opendesign/ | 7456 |
| NIM image proxy | ~projects/riri/tools/ | 7457 |
| ChromaDB index | ~/.local/share/riri/chroma/ | - |
| Pipeline database | ~/.local/share/riri/pipeline.db | - |
| OD project registry | ~/.od/riri-projects.json | - |

## Hook Execution Flow

```
Claude Code session starts
        ↓
User submits prompt
        ↓
    → UserPromptSubmit hook fires → prompt-log.sh logs to memory/prompts.log
        ↓
Claude processes → generates output
        ↓
    → Stop hook fires → stop-log.sh logs session metadata to memory/sessions.log
        ↓
[~95% context]
    → PreCompact hook fires → precompact-memory.sh distills transcript
        ↓
new session continues...
```

## Symlinked Projects (Read-Only)

All `systems/` and `skills/` directories are **symlinks** to live projects. Changes made inside symlinks persist in their source directories.

Source mapping:
- `systems/riri` → `/home/ahmed/projects/riri/`
- `systems/opendesign` → `/home/ahmed/Desktop/OpenDesign/open-design/`
- `systems/claude-pipeline` → `/home/ahmed/projects/claude-pipeline/`
- `systems/outreach-engine` → `/home/ahmed/projects/outreach-engine/`
- `systems/openamnesia` → `/home/ahmed/projects/openamnesia/`
- `systems/CLI-Anything` → `/home/ahmed/projects/CLI-Anything/`
- `skills/opendesign` → `/home/ahmed/projects/riri/skills/opendesign/`
- `skills/nim-image` → `/home/ahmed/projects/riri/skills/nim-image/`
- `skills/hermes` → `/home/ahmed/projects/riri/skills/hermes/`

## Getting Started

1. **Any Claude Code session from HIVE directory** automatically reads `CLAUDE.md`
2. **Read RiRi's brain** before RiRi tasks: `systems/riri/CLAUDE.md`
3. **Check memory** for past discoveries: `memory/findings.md` + `memory/SESSION_INSIGHTS.md`
4. **Use slash commands**: `/project:status`, `/project:design`, `/project:pipeline`, `/project:memory`

---

**HIVE initialized:** 2026-05-09  
**Memory git initialized:** master @ 409fd00
