# Changelog

## [run/2026-04-27T22-42-08] — 2026-04-27

### Added
- `updates/2026-04-27_digital-brain-session-handoff-pattern.md` — Explicit session-start prompting pattern for external knowledge vaults + `~/.claude/projects/` as raw session history store
  - Source: https://www.instagram.com/reel/DXerbfCDkNL/?igsh=bXlyNXpsMGlzY2Zj
  - Confidence: medium
  - Note: Core Obsidian/digital-brain concept was previously skipped (2026-04-25) as redundant. This run captures the one concrete new detail: `~/.claude/projects/` session JSON storage + explicit session-start prompt pattern not previously documented.

### Stats
- Insights extracted: 1
- Claims verified: 2 verified, 2 unverified (visual UI is third-party; Obsidian has no official integration)

---

## [run/2026-04-25T12-30-10] — 2026-04-25

### Skipped
- No files written — content was surface-level promotion of "Obsidian as digital brain for Claude Code".
  The core pattern (Claude reading external files for cross-session continuity) is already fully covered by:
  - `updates/2026-04-10_stop-hook-persistent-conversation-log-grep-memory.md` (automated hook-based memory)
  - `claude-superpowers/2026-04-15_precompact-hook-memory-distillation-agent.md` (PreCompact distillation)
  - `claude-agents/2026-04-23_progressive-disclosure-claudemd-as-context-trunk.md` (CLAUDE.md navigation trunk)
  No technical implementation was shown in the video; mechanism is identical to @file references to memory files.
  - Source: https://www.instagram.com/reel/DXerbfCDkNL/?igsh=bXlyNXpsMGlzY2Zj

### Stats
- Insights extracted: 0
- Claims verified: 2 ✅, 1 ⚠️

---

## [run/2026-04-25T09-41-53] — 2026-04-25

### Added
- `claude-agents/2026-04-25_npx-skills-cli-agent-skills-discovery-and-installation.md` — `npx skills` CLI for discovering/installing agent skills from skills.sh (91K+ skills, real leaderboard, `npx skills find [query]` + `-g -y` flags for headless install)
  - Source: https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md#find-skills
  - Confidence: high
- `claude-agents/2026-04-25_agent-skill-trust-criteria-install-count-source-reputation.md` — 3-factor trust framework for evaluating agent skills before installing: ≥1K installs, official source orgs (vercel-labs/anthropics/microsoft), GitHub stars on source repo
  - Source: https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md#find-skills
  - Confidence: high

### Stats
- Insights extracted: 2
- Claims verified: 3 ✅, 1 ⚠️, 0 ❌

---

## [run/2026-04-25T09-30-06] — 2026-04-25

### Added
- `ai-tools/2026-04-25_magika-ai-file-type-detection-python-api.md` — Google's Magika Python API for AI file routing pipelines: `identify_bytes/path/stream()` returning label+MIME+group+score at ~5ms/file regardless of file size, with per-content-type confidence thresholds
  - Source: https://github.com/google/magika
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 3 ✅, 0 ⚠️, 0 ❌

---

## [run/2026-04-23T01-33-47] — 2026-04-23

### Added
- `claude-agents/2026-04-23_progressive-disclosure-claudemd-as-context-trunk.md` — Use CLAUDE.md as a navigation trunk that points to branch files/skills/workflows rather than a content dump; agents load only what's needed per task (progressive disclosure pattern)
  - Source: https://www.instagram.com/reel/DXcKltHExY_/?igsh=eTI0NndmdW9iYWd2
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 2 verified, 1 partially incorrect (system prompt mutability)

---

## [run/2026-04-19T00-56-20] — 2026-04-19

### Added
- `ai-tools/2026-04-19_agent-council-multi-perspective-decision-making-skill.md` — Claude Code skill that spins up 5 adversarial advisors (Contrarian, First Principles, Expansionist, Outsider, Executor) + peer review + chairman synthesis to counter Claude's sycophancy in decision-making
  - Source: https://www.instagram.com/reel/DXPjubKkyDI/?igsh=MWVwb2l3Z3NhbDFjZQ==
  - Confidence: high
- `claude-skills/2026-04-19_impeccable-skill-design-commands.md` — Impeccable: third-party Claude Code skill with 18 commands (/audit, /polish, /bolder, etc.) and 25 deterministic design rules to eliminate AI slop UI patterns
  - Source: https://www.instagram.com/reel/DXJ-SweDOmC/?igsh=aWZmZ2xsemRkcDY4
  - Confidence: high

### Stats
- Insights extracted: 2
- Claims verified: 3 ✅, 0 ⚠️, 1 ❌ (corrected)

---


## [run/2026-04-17T01-30-09] — 2026-04-17

### Added
- `ai-tools/2026-04-17_fireworks-tech-graph-claude-code-svg-png-diagrams.md` — Claude Code skill that converts natural language into publication-ready SVG+PNG technical diagrams with AI/Agent domain knowledge baked in
  - Source: https://www.instagram.com/reel/DXKJ7lRRflf/?igsh=MXBjODgxaXJzem15Zg==
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 2 ✅, 1 ⚠️

---

## [run/2026-04-16T05-30-05] — 2026-04-16

### Added
- `ai-tools/2026-04-16_omi-open-source-ai-passive-capture-second-brain.md` — OMI is an open-source ambient capture system (screen + audio + wearable) with a plugin SDK that can pipe episodic memory into external agents like Claude
  - Source: https://www.instagram.com/reel/DXKqkS6jLO7/?igsh=MjlsNWF1YTNjc2tv
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 3 ✅, 2 ⚠️

---

## [run/2026-04-16T02-00-06] — 2026-04-16

### Added
- `ai-tools/2026-04-16_takumi-jsx-to-image-animation-for-llms.md` — Takumi renders React/JSX to images, animations, and video frames with a dedicated "For LLMs" documentation tab for agent consumption
  - Source: https://www.instagram.com/p/DXJmHD1Enhh/?img_index=4 (image post, 7 slides)
  - Confidence: medium
- `ai-tools/2026-04-16_pdfx-react-pdf-components-mcp-integration.md` — PDFx is a React PDF component toolkit with an MCP server integration and AI-ready docs, init via `npx pdfx-cli init`
  - Source: https://www.instagram.com/p/DXJmHD1Enhh/?img_index=4 (image post, 7 slides)
  - Confidence: medium

### Also noted (not written — insufficient AI angle)
- DomainStack (domainstack.io) — domain server inspection tool, 231 GitHub stars
- Screenshot Studio (screenshot-studio.com) — template-based device mockup creator, 638 stars
- MapCN (mapcn.dev) — React map components on MapLibre + Tailwind, 7k GitHub stars
- 72pt — iOS font/typeface browser app, now in public beta

### Stats
- Insights extracted: 2
- Claims verified: 0 against Anthropic docs (all tools are unrelated to Anthropic); 3 claims marked ⚠️ unverified per tool

---

## [run/2026-04-15T02-30-12] — 2026-04-15

### Added
- `claude-superpowers/2026-04-15_precompact-hook-memory-distillation-agent.md` — PreCompact hook wired to a background agent that reads the full transcript and distills session insights into persistent memory files before auto-compaction destroys context
  - Source: https://www.instagram.com/reel/DW_wEu9jQt7/?igsh=MTRjOWIzdDd6dTdzeA==
  - Confidence: medium (core architecture is valid; 80% threshold claim is incorrect — PreCompact fires at ~95%; native configurable thresholds are unimplemented feature requests)

### Stats
- Insights extracted: 1
- Claims verified: 4 verified, 2 uncertain/corrected (80% threshold claim ❌, "constantly monitoring" claim ⚠️)

---

## [run/2026-04-12T02-30-09] — 2026-04-12

### Added
- `claude-agents/2026-04-12_autoresearch-claude-code-skill-self-improving-agents.md` — Installable Claude Code skill (uditgoenka/autoresearch) that ports Karpathy's AutoResearch into 10 slash commands for autonomous self-improving agent loops on any measurable metric
  - Source: https://www.instagram.com/reel/DW_wFDyiI0J/?igsh=MWZiY3N1aHI2cHlveA==
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 3 verified, 2 unverified (product names)

---

## [run/2026-04-08T22-09-20] — 2026-04-08

### Added
- `updates/2026-04-08_self-evolving-claude-agents-hook-loop.md` — 4-hook architecture (SessionStart + PostToolUse + Stop + gate) that logs every run, detects recurring failures, and auto-writes rules to `.claude/rules/` so agents learn from past mistakes without manual intervention
  - Source: https://www.instagram.com/p/DW4A22ijJ15/?igsh=MTRzdGQ2ZHE5Z2lvOA== (image post, 8 slides)
  - Confidence: high

---

## [run/2026-04-07T03-44-16] — 2026-04-07

### Added
- `updates/2026-04-07_output-compression-via-behavioral-instructions.md` — ~50–65% output token reduction via explicit behavioral rules in system prompt/CLAUDE.md; verified real effect, debunks the misleading BEFORE/AFTER code token counts in the original doc
  - Source: discord-upload-1490792022502670347-PULSE-TOKEN-EFFICIENCY-COMPACTOR.md
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 2 verified, 2 uncertain, 1 corrected

---

## [run/2026-04-04T04-30-04] — 2026-04-04

### Added
- `ai-tools/2026-04-04_claude-code-playground-skill-visual-design-builder.md` — Playground plugin turns Claude Code into a visual design builder: generates interactive HTML UI with controls, you tweak visually, copy the generated prompt, paste back to Claude to implement
  - Source: https://www.instagram.com/reel/DWmM8C-DsiC/?igsh=NjIyOTJsZWd2MHox
  - Confidence: high

### Stats
- Insights extracted: 1
- Claims verified: 2 verified, 2 uncertain, 1 corrected

---

## [run/2026-04-02T01-21-28] — 2026-04-02

### Added
- `updates/2026-04-02_claude-code-loop-recurring-scheduled-tasks.md` — Claude Code's native `/loop` slash command for session-scoped recurring/scheduled tasks with cron support
  - Source: https://www.instagram.com/reel/DWXGFvEAc5q/?igsh=YnY4bTRweWFmeWh1
  - Confidence: high
- `updates/2026-04-02_karpathy-autoresearch-pattern-business-optimization.md` — Karpathy AutoResearch pattern adapted for self-optimizing agent loops on any measurable business metric
  - Source: https://www.instagram.com/reel/DWXGFvEAc5q/?igsh=YnY4bTRweWFmeWh1
  - Confidence: high

### Stats
- Insights extracted: 2
- Claims verified: 3/3 (2 fully verified, 1 verified with qualification)

---
