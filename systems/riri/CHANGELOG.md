# RiRi Changelog

> Personal AI assistant built on OpenClaw 2026.4.23. NIM (meta/llama-3.3-70b-instruct) as primary LLM.

---

## v0.5 — 2026-04-30 · Continual Learning + WhatsApp Self-Chat Fix

### Added
- **openamnesia continual learning** — cloned `vincentkoc/openamnesia`, patched `ClaudeConnector` (slots/super() bug), built `riri_amnesia.py` wrapper that ingests Claude + Codex session JSONL → stores 32,554 events in SQLite → NIM-generates daily/weekly memory summaries → writes `.md` files to `~/.openclaw/workspace/memory/`
- **Memory cold-start hook** — AGENTS.md updated so RiRi runs `riri_amnesia.py context` on session start to load recent memory
- **Nightly memory cron** — 5:30am PKT runs full ingest+export pipeline
- **Cowork session ingestion** — openamnesia now also reads `~/.config/Claude/local-agent-mode-sessions/**/*.jsonl` (Cowork sessions)

### Fixed
- **WhatsApp self-chat not responding** — root cause: Baileys marks self-chat messages as `fromMe: true`, filtered by default. Fix: added `"selfChatMode": true` to WhatsApp channel config in `openclaw.json`
- **WhatsApp overnight disconnect** — added watchdog script (`riri-wa-watchdog.sh`) running every 30 mins, detects silent disconnect by checking log staleness, auto-restarts gateway. Also added clean 6am PKT daily restart (safe window: Ahmed works 8pm–5am PKT)

---

## v0.4 — 2026-04-29 · Plugin Stack + Memory

### Added
- **Plugin stack enabled** — tokenjuice (output compression), active-memory (pre-reply injection), skill-workshop (workflow capture), firecrawl (web scraping), memory-lancedb (LanceDB vector memory)
- **memory-lancedb** — configured with Ollama nomic-embed-text embeddings, DB at `~/.local/share/riri/lancedb`, `autoCapture + autoRecall` enabled
- **Plugin slot system** — discovered `plugins.slots.memory` key in OpenClaw types, used to override default memory-core with memory-lancedb
- **Morning briefing skill** — cron at 9am PKT, pipeline DB last 24h + pending approvals + KB insight → WhatsApp message to `+923415675181`

### Fixed
- **Plugin config schema** — all plugin-specific settings moved under `plugins.entries.<id>.config` (strict schema, direct keys rejected)
- **memory-lancedb slot conflict** — `plugins.slots.memory: "memory-lancedb"` added explicitly
- **Service file overwrite** — `openclaw doctor --fix` clobbered `EnvironmentFile`; restored with NIM key path
- **Gateway start-limit** — `systemctl --user reset-failed openclaw-gateway` after repeated crash/restart loop

---

## v0.3 — 2026-04-28 · WhatsApp Intelligence + Skills

### Added
- **WhatsApp channel** — connected via QR scan, `allowFrom: ["923415675181"]`, `dmPolicy: allowlist`
- **whatsapp-intelligence skill** — auto-routing: URL detection (regex), voice note transcription (faster-whisper large-v3), image analysis (NIM Gemma 3 12B), response rules (under 1500 chars, WA markdown, no `#` headers)
- **pipeline skill** — URL/text intake → `pipeline_intake.py` triage → RiRi synthesises with NIM → `write_insight` + `index_insight`
- **write-skill skill** — RiRi can draft + install new OpenClaw skills from description, patches dispatcher SKILL_REGISTRY
- **spawn_agent.py** — launches Claude Code (`claude --print`) or Codex CLI as subprocesses with streaming, approval gate for destructive keywords (delete/wipe/reset --hard etc.)
- **pipeline_intake.py** — conversational wrapper around claude-pipeline: `fetch_content()`, `triage()`, `write_insight()`, `index_insight()`, `build_synthesis_prompt()`

---

## v0.2 — 2026-04-27 · Video + Browser Policy

### Added
- **HyperFrames skill** — v0.4.31 → v0.4.39 installed, HTML/CSS/GSAP → MP4 via Puppeteer + FFmpeg, SKILL.md written covering `window.__timelines` GSAP requirement, NIM Flux.1-dev for image assets, LinkedIn output sizes
- **Remotion skill** — React/TSX → MP4 (v4.0.452 globally installed), SKILL.md written covering `useCurrentFrame`, `interpolate`, `spring`, `useVideoConfig`, `Sequence`, shared workspace at `~/projects/riri/remotion-comps/`
- **CLI-first browser policy** — AGENTS.md updated: Official CLI → Direct API → CLI-Anything → browser as last resort
- **AGENTS.md expanded** — video section, sub-agent launcher section, knowledge pipeline section, write-skill section, WhatsApp intelligence section, active plugins list

---

## v0.1 — 2026-04-26 · Foundation

### Added
- **OpenClaw 2026.4.23 gateway** — systemd user service, port 18789, NIM as primary LLM (`meta/llama-3.3-70b-instruct`)
- **NIM integration** — `NVIDIA_API_KEY` in secrets.env, OpenAI-compatible at `https://integrate.api.nvidia.com/v1`
- **Discord channel** — connected as `@Ahmed Pipeline`, user `622800747347574784` allowlisted
- **LinkedIn posting** — `tool_linkedin_post` via REST API, credentials in secrets.env
- **claude-pipeline integration** — `pipeline_intake.py` wraps scrape → triage → synthesis → ChromaDB index → Discord notify
- **Chroma DB** — semantic index of projects + tool docs
- **Evolution system** — `evolve.py` dual-agent critique loop, DMs Ahmed for approval before applying changes

---

## Roadmap
- [ ] Personal RiRi memorial agent (ex-skill / WhatsApp persona thread / Urdu TTS)
- [ ] clawdeck dashboard
- [ ] TOON format research (token-efficient alternative to JSON)
- [ ] Google Workspace OAuth
- [ ] Voice pipeline (Parakeet TDT v3 STT + F5-TTS)
- [ ] LinkedIn API for posting + case study infographic automation
