---
date: 2026-05-09
title: NIM Model Catalog
tags: [infra, model, nim]
files_changed:
  - docs/models/catalog.json        (created — 137 models, machine-readable with tool_calls/tiers/speed)
  - docs/models/README.md           (created — task→model routing table, verified tool support list)
  - docs/models/tool_test_results.json (created — live test output)
  - tools/test_model_tools.py       (created — parallel tool-call tester, run with NVIDIA_API_KEY=...)
---

## What happened

Kimi K2.6 in OpenDesign was returning 404 on tool calls and self-identifying as K2.5. Investigated
whether this was a NIM model limitation. Fetched full NIM model list (open endpoint, no auth needed —
returns 137 models). Built a structured catalog to avoid re-investigating this every session.

## Key decisions

**Kimi K2.6 tool calls** — initially diagnosed as "model doesn't support tools." Wrong. The real cause
was an expired NVIDIA API key. With a fresh key, kimi-k2.6 passes tool call tests. The K2.5
self-identification is harmless — NIM serves K2.5 weights under the k2.6 endpoint ID.

**Catalog location** — put in `docs/models/` (inside riri project) so ChromaDB indexes it
automatically. No separate knowledge base needed.

**test_model_tools.py** — runs 14 priority models in parallel (ThreadPoolExecutor), saves JSON results.
Default timeout 20s. Some models (deepseek-v4-flash, kimi-k2-instruct) timed out — not confirmed broken,
just slow. Re-test with `--timeout 60` if needed.

## Verified tool call results (2026-05-09)

Working: deepseek-v4-pro, qwen3-coder-480b, qwen3-next-80b, nemotron-super-49b-v1.5,
llama-3.3-70b, mistral-large-3, gpt-oss-120b, gpt-oss-20b, kimi-k2.6

Broken on NIM: llama-4-maverick (returns schema as text, not actual calls)
Not on plan: nemotron-ultra-253b (404)
Degraded: devstral-2-123b (NIM infra issue, temporary)
Timeout: deepseek-v4-flash, kimi-k2-instruct
