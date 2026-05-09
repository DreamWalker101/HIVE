# HIVE — Ahmed's AI System Hub

You are operating inside HIVE, Ahmed's central AI system directory.
RiRi is his personal AI assistant. Everything here is personal — not client work.

## Read First
- systems/riri/CLAUDE.md — RiRi full brain (do this before any RiRi task)
- memory/SESSION_INSIGHTS.md — distilled past session memory
- memory/findings.md — key technical discoveries

## What HIVE Contains
- systems/riri/ — RiRi AI assistant (MCP tools, NIM proxy, ChromaDB, AGENTS.md)
- systems/opendesign/ — OpenDesign daemon (port 7456, Node 24)
- systems/claude-pipeline/ — URL fetch → triage → index pipeline
- systems/outreach-engine/ — outreach automation
- systems/openamnesia/ — session memory ingestion
- systems/CLI-Anything/ — 52 agent-native CLIs
- ideas/ — research finds, AI tool discoveries, agent patterns
- skills/ — how to use each capability (read SKILL.md before using)
- hooks/ — Claude Code hooks (Stop, PreCompact, UserPromptSubmit)
- memory/ — git-tracked persistent session memory

## Key Paths
- Secrets: ~/.nanobot/secrets.env
- Hermes config: ~/.hermes/config.yaml (default model: nim/moonshotai/kimi-k2.6)
- Hermes env: ~/.hermes/.env (NVIDIA_API_KEY here)
- ChromaDB: ~/.local/share/riri/chroma
- Pipeline DB: ~/.local/share/riri/pipeline.db
- OD project registry: ~/.od/riri-projects.json
- NIM proxy: ~/projects/riri/tools/nim_image_proxy.py (port 7457)
- OD launcher: ~/.local/bin/opendesign-start.sh

## Model Routing (Hermes / NIM)
Default: nim/moonshotai/kimi-k2.6 (1M context)
Fallbacks: nim/qwen/qwen3-next-80b-a3b-instruct → nim/nvidia/llama-3.3-nemotron-super-49b-v1 → nim/meta/llama-3.3-70b-instruct → groq → ollama

## Active Hooks (wired in .claude/settings.json)
- Stop → hooks/stop-log.sh (logs session metadata to memory/)
- PreCompact → hooks/precompact-memory.sh (distills transcript to memory/SESSION_INSIGHTS.md)
- UserPromptSubmit → hooks/prompt-log.sh (logs prompts to memory/prompts.log)

## Slash Commands
/project:status — system health check
/project:design — trigger OpenDesign via RiRi MCP
/project:pipeline — run knowledge pipeline on a URL
/project:memory — search session memory
