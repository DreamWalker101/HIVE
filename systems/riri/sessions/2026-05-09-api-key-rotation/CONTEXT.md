---
date: 2026-05-09
title: API Key Rotation + Hermes Config Update
tags: [infra, nim, hermes, config]
files_changed:
  - ~/.nanobot/secrets.env          (NVIDIA_API_KEY rotated)
  - ~/.hermes/.env                  (NVIDIA_API_KEY + OD_OPENAI_API_KEY rotated)
  - ~/.hermes/config.yaml           (nemotron-super-49b-v1 → v1.5 in fallback chain)
---

## What happened

Old NVIDIA key (`nvapi-eTMem...h-is`) was expired — causing 403 on all NIM completions endpoints.
User provided new key (`nvapi-Eatx...kxv`). Updated both secrets files and restarted Hermes.

## Key decisions

**Two places to update** — `secrets.env` (used by MCP tools / riri_tools_mcp.py) and `.hermes/.env`
(used by Hermes gateway + OD proxy). Both must stay in sync. Also `OD_OPENAI_API_KEY` in `.env`
is a separate var for the NIM image proxy — updated that too.

**nemotron v1 → v1.5** — took the opportunity to upgrade the Hermes fallback chain from
`llama-3.3-nemotron-super-49b-v1` to `v1.5` which is the current version. Drop-in replacement,
no other config changes needed.

**Hermes restart** — `systemctl --user restart hermes-gateway` required after `.env` changes.
Gateway came up clean in <3s.

## Context for next session

If NIM starts 403ing again: generate a new key at console.nvidia.com, update both files above,
restart Hermes. Takes ~2 minutes.
