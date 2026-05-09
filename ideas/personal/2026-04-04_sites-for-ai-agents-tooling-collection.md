---
title: "Sites for AI Agents — Tooling Collection Worth Exploring"
category: ideas
tags: [ideas, 2026-04-04]
source_reel: "https://www.instagram.com/p/DWqnJj2kvIF/?img_index=3{url}igsh=Nm41eGplNWc5N2V4"
source_platform: instagram
date_added: 2026-04-04
pipeline_run: run/2026-04-04T04-30-04
status: seed
---

# Sites for AI Agents — Tooling Collection Worth Exploring

## The Idea
A curated set of tools built specifically for AI agents is emerging fast. Tools like OneShot (screenshot-to-curl for agents), Feynman (local AI research agent), Rivet AgentOS (WebAssembly-based portable agent runtime), and Supabase docs-over-SSH suggest a new layer of infrastructure forming around agents. Ahmed should map and potentially build on top of — or contribute to — this ecosystem.

## What Sparked It
The post by @kalypsodesigns lists several agent-oriented tools across slides: OneShot for passing screenshots to agents via curl, LilAgents as Claude-powered dock companions, Feynman as a local open-source research agent, Rivet AgentOS as a portable 6ms coldstart WASM runtime, and Supabase serving docs over SSH so agents can `grep`/`cat` documentation like a filesystem.

## Why This Could Matter
These tools represent the emerging "agent-native" interface layer — moving away from web UIs toward bash, curl, and SSH as first-class agent surfaces. Building with or on top of these early could position Ahmed at the frontier of agentic tooling.

## Possible Next Steps
- [ ] Try OneShot (https://oneshot.zip) — test screenshot-to-curl workflow with Claude Code
- [ ] Explore Feynman (https://www.feynman.is) — run locally, see if it fits research workflows
- [ ] Read Rivet AgentOS docs and npm package `@rivet-dev/agent-os-core`
- [ ] Try `ssh supabase.sh` to see how docs-over-SSH feels for agent workflows
- [ ] Consider: could a similar docs-over-SSH pattern work for Ahmed's own projects?

## Raw Note
> read the picture for text

---
*Idea captured by claude-knowledge-pipeline | 2026-04-04*
