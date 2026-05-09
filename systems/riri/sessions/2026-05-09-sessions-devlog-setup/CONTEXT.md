---
date: 2026-05-09
title: Sessions Dev Log System + HIVE Git Fix
tags: [infra, tooling, git, nim]
files_changed:
  - sessions/INDEX.md                          (created — master log table)
  - sessions/2026-05-09-nim-model-catalog/     (created — see that entry)
  - sessions/2026-05-09-api-key-rotation/      (created — see that entry)
  - sessions/2026-05-09-sessions-devlog-setup/ (this entry)
  - .claude/commands/fk.md                     (created — /fk slash command)
  - .claude/commands/fkgit.md                  (created — /fkgit slash command)
  - .gitignore                                 (created — excludes __pycache__, output/, .claude/settings.json)
  - CLAUDE.md                                  (updated — sessions/INDEX.md added to session-start reading list)
  - riri.py                                    (fixed — removed hardcoded Groq key default)
---

## What happened

Built the RiRi development history system — a per-feature log that lives at `sessions/` so new Claude
sessions can orient instantly without reading everything. Also fixed the HIVE git structure and pushed
the full riri codebase to GitHub for the first time.

Also resolved the kimi-k2.6 tool call issue that prompted this session. See nim-model-catalog and
api-key-rotation entries for those details.

## Key decisions

**sessions/ format** — YAML frontmatter in CONTEXT.md (Claude parses fast without reading prose) +
compact INDEX.md table (~80 chars/row, 100 entries ≈ 2.5K tokens). Claude reads INDEX.md on session
start, drills into a folder only if relevant. No Obsidian/Mem0 needed for dev history — plain markdown
indexed by ChromaDB is sufficient and zero-overhead.

**/fk vs /fkgit split** — `/fk` writes the log only. `/fkgit` writes + commits + pushes to HIVE.
Commands live in `.claude/commands/` (project-level Claude Code slash commands). Claude generates
everything — title, slug, tags, summary, decisions — from the conversation history. Ahmed types nothing.

**HIVE git structure** — `systems/riri` was tracked as a symlink (mode 120000) pointing to
`/home/ahmed/projects/riri`. HIVE only stored the symlink blob, not the file contents. Fixed by:
removing symlink from git, moving actual dir into `HIVE/systems/riri`, creating reverse symlink
so `/home/ahmed/projects/riri` still works. Both paths resolve to same inode.

**secrets before push** — GitHub push protection caught a hardcoded Groq key in riri.py (was used as
`os.getenv()` default). Removed it. Also removed `.claude/settings.json` from git — it had an old
expired NVIDIA key baked into curl allowlist entries. Added to .gitignore. Rule: secrets only in
`~/.nanobot/secrets.env` and `~/.hermes/.env`, never in tracked files.

**HIVE repo made private** — `gh repo edit DreamWalker101/HIVE --visibility private`

## Context for next session (OpenDesign)

The previous chat session worked on OpenDesign model routing. Key things that changed:

- **kimi-k2.6 DOES support tool calls** — the 404 errors seen in OpenDesign were from an expired
  NVIDIA key, not a model limitation. With the new key, kimi-k2.6 passed tool call tests.
- **New NVIDIA key** is now in `~/.nanobot/secrets.env` and `~/.hermes/.env`. Hermes was restarted.
- **Recommended OD model for design tasks**: `deepseek-ai/deepseek-v4-pro` (verified tool calls,
  best at HTML/CSS/visual design generation per community reports)
- **Full model catalog** at `docs/models/README.md` — task→model routing table, verified tool support
- **Test script** at `tools/test_model_tools.py` — run with fresh NVIDIA_API_KEY to retest models
- **Hermes fallback chain** updated: nemotron v1 → v1.5 in `~/.hermes/config.yaml`
- OpenDesign docs: `docs/opendesign.md`, skill: `skills/opendesign/SKILL.md`
