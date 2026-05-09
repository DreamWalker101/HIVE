# NIM Model Directory

Full catalog: `catalog.json` — 137 models, last fetched 2026-05-09.

## Quick Task → Model

| Task | Best Model | Fallback | Notes |
|---|---|---|---|
| **Design / HTML / CSS / UI** | `deepseek-ai/deepseek-v4-pro` | `qwen/qwen3-coder-480b-a35b-instruct` | V4 Pro best at design code |
| **Infographic / Dashboard** | `deepseek-ai/deepseek-v4-pro` | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | Replace old nemotron with V4 Pro |
| **SVG / Animation code** | `qwen/qwen3-coder-480b-a35b-instruct` | `mistralai/devstral-2-123b-instruct-2512` | Biggest code model on NIM |
| **Web / Prototype / SaaS** | `qwen/qwen3-next-80b-a3b-instruct` | `deepseek-ai/deepseek-v4-flash` | Fast + reliable tool calls |
| **General / Chat** | `qwen/qwen3-next-80b-a3b-instruct` | `meta/llama-3.3-70b-instruct` | Speed matters here |
| **Long-form writing / Deck** | `qwen/qwen3.5-122b-a10b` | `writer/palmyra-creative-122b` | Writing quality |
| **Complex reasoning** | `nvidia/llama-3.1-nemotron-ultra-253b-v1` | `qwen/qwen3.5-397b-a17b` | When depth > speed |
| **Code generation** | `qwen/qwen3-coder-480b-a35b-instruct` | `mistralai/devstral-2-123b-instruct-2512` | Code specialists |
| **Fast fallback** | `meta/llama-3.3-70b-instruct` | `openai/gpt-oss-20b` | <1s latency |
| **Large context** | `moonshotai/kimi-k2.6` | `meta/llama-4-maverick-17b-128e-instruct` | 1M ctx (Kimi: no tool calls) |
| **Vision / Image analysis** | `meta/llama-3.2-90b-vision-instruct` | `nvidia/nemotron-nano-12b-v2-vl` | Multimodal input |
| **Chart → data extraction** | `google/deplot` | `meta/llama-3.2-90b-vision-instruct` | deplot specialized for this |

---

## Tool Call Support

**Verified YES** (tested 2026-05-09 with live key):
- `deepseek-ai/deepseek-v4-pro` ✅
- `qwen/qwen3-coder-480b-a35b-instruct` ✅
- `qwen/qwen3-next-80b-a3b-instruct` ✅
- `nvidia/llama-3.3-nemotron-super-49b-v1.5` ✅
- `meta/llama-3.3-70b-instruct` ✅
- `mistralai/mistral-large-3-675b-instruct-2512` ✅
- `openai/gpt-oss-120b` ✅
- `openai/gpt-oss-20b` ✅
- `moonshotai/kimi-k2.6` ✅ (previously appeared broken due to expired key)

**Verified NO:**
- `meta/llama-4-maverick-17b-128e-instruct` — returns tool schema as text, not actual calls
- `moonshotai/kimi-k2-thinking` — thinking mode only
- `qwen/qwen3-next-80b-a3b-thinking` — thinking mode only

**Not available on this plan:**
- `nvidia/llama-3.1-nemotron-ultra-253b-v1` — 404

**Degraded / Timeout:**
- `deepseek-ai/deepseek-v4-flash` — timed out at 20s (may work with longer timeout)
- `moonshotai/kimi-k2-instruct` — timed out at 20s
- `mistralai/devstral-2-123b-instruct-2512` — temporarily degraded on NIM infra

**Untested:**
- `nvidia/nemotron-3-super-120b-a12b`
- `qwen/qwen3.5-397b-a17b`
- `mistralai/magistral-small-2506`
- `google/gemma-4-31b-it`
- `stepfun-ai/step-3.5-flash`
- `z-ai/glm-5.1`

---

## Hermes Fallback Chain (Current — validated 2026-05-09)

Current config in `~/.hermes/config.yaml` is fine. Kimi K2.6 DOES support tool calls (was broken by stale key, not model limitation).

```yaml
model:
  default: nim/moonshotai/kimi-k2.6               # 1M ctx + tools verified
  fallbacks:
    - nim/qwen/qwen3-next-80b-a3b-instruct         # fast + tools ✅
    - nim/nvidia/llama-3.3-nemotron-super-49b-v1.5 # reasoning ✅ (upgraded from v1)
    - nim/qwen/qwen3.5-122b-a10b                   # writing quality
    - nim/meta/llama-3.3-70b-instruct              # fastest ✅
    - groq/llama-3.3-70b-versatile                 # off-NIM
    - ollama/qwen2.5-coder:7b                       # local last resort
```

Optional upgrades to consider:
- Add `nim/deepseek-ai/deepseek-v4-pro` as fallback #2 for design-heavy sessions
- Add `nim/openai/gpt-oss-120b` as general fallback (surprisingly good)

---

## OpenDesign Task Routing (Updated)

Replaces the routing table in `riri_tools_mcp.py`:

| OD Task Type | Model | Why |
|---|---|---|
| infographic, dashboard, data-viz, chart, report | `deepseek-ai/deepseek-v4-pro` | Best at data layout + visual design |
| web, ui, app, prototype, landing, saas | `deepseek-ai/deepseek-v4-pro` | Strong HTML/CSS generation |
| mobile | `qwen/qwen3-next-80b-a3b-instruct` | Fast, good for component code |
| deck, slides, pitch | `qwen/qwen3.5-122b-a10b` | Writing quality for decks |
| svg, animation, motion | `qwen/qwen3-coder-480b-a35b-instruct` | Largest code model |
| social, blog, email | `qwen/qwen3.5-122b-a10b` | Writing quality |
| image, poster | `deepseek-ai/deepseek-v4-flash` | Fast for single-image prompts |
| wireframe | `qwen/qwen3-next-80b-a3b-instruct` | Speed matters for iteration |
| invoice, kanban, okrs | `meta/llama-3.3-70b-instruct` | Structured output, fast |

---

## Models to Test Next

Priority for tool-call verification (when fresh API key available):

1. `openai/gpt-oss-120b` — unknown origin, worth evaluating
2. `deepseek-ai/deepseek-v4-pro` — confirm tool calls work before using in OD
3. `deepseek-ai/deepseek-v4-flash` — confirm tool calls work
4. `meta/llama-4-maverick-17b-128e-instruct` — Llama 4 with 1M ctx
5. `mistralai/devstral-2-123b-instruct-2512` — code/design tasks
6. `nvidia/llama-3.1-nemotron-ultra-253b-v1` — large reasoning model

Run test script:
```bash
cd ~/projects/riri && python3 tools/test_model_tools.py
```

---

## Broken / Do Not Use

| Model | Issue |
|---|---|
| `minimaxai/minimax-m2.7` | Timeout on tool calls |
| `minimaxai/minimax-m2.5` | Timeout on tool calls |
| `deepseek-ai/deepseek-v3.2` | Timeout |
| `google/gemma-3-27b-it` | Timeout |
| `mistralai/mistral-large-2-instruct` | 404 Not on plan |
| `moonshotai/kimi-k2.6` | No tool calls (use for chat-only) |
