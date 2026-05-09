# NIM API Reference — RiRi's LLM Backend

Everything about NVIDIA's NIM (Inference Microservices) as used by RiRi.

## Basics

**Endpoint:** `https://integrate.api.nvidia.com/v1`
**Format:** OpenAI-compatible (drop-in replacement)
**Auth:** Bearer token in `Authorization` header
**API Key:** `$NVIDIA_API_KEY` (in `~/.nanobot/secrets.env` or `~/.hermes/.env`)

## Authentication

```bash
# Set key from secrets
export NVIDIA_API_KEY="$(grep NVIDIA_API_KEY ~/.nanobot/secrets.env | cut -d= -f2)"

# Test connectivity
curl -s https://integrate.api.nvidia.com/v1/models \
  -H "Authorization: Bearer $NVIDIA_API_KEY" | jq '.data | length'
# Should return number of available models
```

## Chat Completions Endpoint

**Endpoint:** `/v1/chat/completions`
**Method:** POST
**Format:** OpenAI-compatible

### Request

```python
import requests

response = requests.post(
    "https://integrate.api.nvidia.com/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "moonshotai/kimi-k2.6",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain async/await in Python."},
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
        "top_p": 0.9,
    }
)

print(response.json()["choices"][0]["message"]["content"])
```

### Response

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1715291234,
  "model": "moonshotai/kimi-k2.6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Async/await is..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 123,
    "completion_tokens": 456,
    "total_tokens": 579
  }
}
```

## Confirmed Working Models

**Tested 2026-05-01 on RiRi:**

| Model ID | Latency | Context | Use Case | Status |
|---|---|---|---|---|
| `moonshotai/kimi-k2.6` | ~20s | 1M | **Primary**: complex reasoning, long context | ✅ Working |
| `moonshotai/kimi-k2-instruct` | ~18s | 128K | Long-context alternative | ✅ Working |
| `moonshotai/kimi-k2-thinking` | ~25s | 128K | Extended thinking mode | ✅ Working |
| `qwen/qwen3-next-80b-a3b-instruct` | 1.2s | 32K | **Fallback 1**: general purpose, fast | ✅ Working |
| `nvidia/llama-3.3-nemotron-super-49b-v1` | 1.5s | 32K | **Fallback 2**: reasoning, structured output | ✅ Working |
| `qwen/qwen3.5-122b-a10b` | 1.9s | 32K | **Fallback 3**: long-form content, writing quality | ✅ Working |
| `qwen/qwen3-coder-480b-a35b-instruct` | 2.5s | 32K | Code generation, SVG, complex markup | ✅ Working |
| `meta/llama-3.3-70b-instruct` | 0.8s | 32K | **Fallback 4**: fastest, versatile | ✅ Working |

## Broken Models (DO NOT USE)

| Model ID | Issue | Reason |
|---|---|---|
| `minimaxai/minimax-m2.7` | Timeout on tool calls | Unstable implementation |
| `minimaxai/minimax-m2.5` | Timeout on tool calls | Unstable implementation |
| `deepseek-ai/deepseek-v3.2` | Timeout | Service issue |
| `google/gemma-3-27b-it` | Timeout | Service issue |
| `mistralai/mistral-large-2-instruct` | 404 Not Found | Not on this plan |

## Model Selection Strategy

### Default (in Hermes)

Hermes uses `moonshotai/kimi-k2.6` as primary. If timeout, falls back to fallback chain.

### For Specific Tasks (use nim_infer)

```python
# Complex code generation / refactoring
nim_infer(
    model="qwen/qwen3-coder-480b-a35b-instruct",
    prompt="Refactor this Python class to async/await...",
    max_tokens=2000
)

# Deep reasoning / architecture decisions
nim_infer(
    model="nvidia/llama-3.3-nemotron-super-49b-v1",
    prompt="Design a data pipeline that handles...",
    max_tokens=3000
)

# Long-form writing
nim_infer(
    model="qwen/qwen3.5-122b-a10b",
    prompt="Write a detailed case study about...",
    max_tokens=4000
)

# When you need speed
nim_infer(
    model="meta/llama-3.3-70b-instruct",
    prompt="List 10 quick tips for...",
    max_tokens=500
)
```

## Image Generation (FLUX Models)

**Endpoint:** `/v1/genai/<model-name>` (internal NIM endpoint)
**Note:** Accessed via NIM image proxy (port 7457) for OpenDesign compatibility

### Direct API (via proxy)

```python
import requests
import base64

response = requests.post(
    "http://localhost:7457/v1/images/generations",
    headers={"Content-Type": "application/json"},
    json={
        "model": "flux.1-dev",
        "prompt": "A sleek logo for an AI company",
        "size": "1024x1024",
        "n": 1,
        "response_format": "b64_json",
    }
)

data = response.json()["data"][0]["b64_json"]
image_bytes = base64.b64decode(data)
with open("logo.png", "wb") as f:
    f.write(image_bytes)
```

### Available FLUX Models

Via proxy (at `localhost:7457`):

| Model Name | Steps | Speed | Quality | Use Case |
|---|---|---|---|---|
| `flux-schnell` | 4 | ⚡⚡⚡ Fast | Good | Quick previews, thumbnails |
| `flux.1-dev` | 20 | ⚡ Moderate | Excellent | LinkedIn assets, final output |
| `flux-kontext-dev` | 20 | ⚡ Moderate | Excellent | Image editing / inpainting |

### Valid Dimensions

FLUX supports widths and heights independently. Valid values:
```
768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344 (pixels)
```

Examples:
- `1024x1024` ✅
- `1280x1024` ✅
- `768x768` ✅
- `1200x1200` ⚠️ Clamped to nearest valid (1216)
- `1024x2048` ⚠️ Clamped

### Response Format

**Default: `b64_json`** (base64-encoded PNG)
```json
{
  "created": 1715291234,
  "data": [
    {
      "b64_json": "iVBORw0KGgoAAAANSUhEUgAAA..."
    }
  ],
  "model": "black-forest-labs/flux.1-dev"
}
```

**Alternative: `url`** (returns file:// URL)
```json
{
  "created": 1715291234,
  "data": [
    {
      "url": "file:///tmp/flux-output.png"
    }
  ],
  "model": "black-forest-labs/flux.1-dev"
}
```

## Kimi K2.6 Specifics

Ahmed explicitly chose Kimi K2.6 as primary model.

### Context Window

- **Size:** 1,000,000 tokens (1M)
- **Use for:** Very large codebases, multi-file reasoning, complex architecture decisions, full-session context
- **Latency:** ~20 seconds (longer than other models, but necessary for 1M context)

### Model IDs

```
moonshotai/kimi-k2.6           # Latest Kimi, recommended
moonshotai/kimi-k2-instruct    # Standard K2
moonshotai/kimi-k2-thinking    # With extended thinking
```

### Thinking Mode

Kimi K2 supports optional thinking/reasoning:
```json
{
  "model": "moonshotai/kimi-k2-thinking",
  "messages": [...],
  "temperature": 1.0,  # Thinking requires temp 1.0
}
```

### When to Use Kimi

- Analyzing large codebases (>50K tokens)
- Multi-file refactoring decisions
- Deep architectural analysis
- Complex multi-step reasoning
- When context is the bottleneck

### When NOT to Use Kimi

- Simple questions → use qwen3-next-80b (1.2s)
- Time-sensitive tasks → use meta/llama-3.3-70b (0.8s)
- Quick code snippets → use qwen3-coder-480b (2.5s)

## Routing in Hermes Config

**File:** `~/.hermes/config.yaml`

```yaml
model:
  default: nim/moonshotai/kimi-k2.6
  fallbacks:
    - nim/qwen/qwen3-next-80b-a3b-instruct
    - nim/nvidia/llama-3.3-nemotron-super-49b-v1
    - nim/qwen/qwen3.5-122b-a10b
    - nim/meta/llama-3.3-70b-instruct
    - groq/llama-3.3-70b-versatile
    - ollama/qwen2.5-coder:7b

custom_providers:
  - name: nim
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
    api_mode: chat_completions
```

### How Routing Works

1. **User message arrives** at Hermes
2. **Hermes routes to default model:** `nim/moonshotai/kimi-k2.6`
3. **If timeout/error → try fallback 1:** `nim/qwen3-next-80b`
4. **If timeout/error → try fallback 2:** `nim/nemotron-super-49b`
5. **Continue down chain** until success or exhaust all options

### Custom Provider Configuration

The `custom_providers` entry tells litellm:
- When you see `nim/model-name` → use this provider
- Base URL: NIM endpoint
- API key: NVIDIA key
- Mode: OpenAI chat completions API

## Using NIM via Hermes CLI

**Direct call (Hermes):**

```bash
hermes acp --model nim/qwen/qwen3-coder-480b-a35b-instruct \
  --prompt "Refactor this to async: $(cat my_class.py)"
```

**Or via MCP tool:**

```python
nim_infer(
    model="qwen/qwen3-coder-480b-a35b-instruct",
    prompt="Refactor this to async: ...",
    system="You are a Python expert.",
    max_tokens=2000
)
```

## Rate Limiting & Quotas

**Note:** RiRi's plan on NIM includes generous quotas for:
- Chat completions (text-in-text-out)
- Image generation (FLUX models)

**If you hit limits:**
1. Check your NIM plan at `https://console.nvidia.com/app/`
2. Request increase if quota exhausted
3. Fall back to Groq or Ollama while waiting

## Testing NIM Connectivity

```bash
# List available models
curl -s https://integrate.api.nvidia.com/v1/models \
  -H "Authorization: Bearer $NVIDIA_API_KEY" | jq '.data | length'

# Test chat completions
curl -X POST https://integrate.api.nvidia.com/v1/chat/completions \
  -H "Authorization: Bearer $NVIDIA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta/llama-3.3-70b-instruct",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 100
  }' | jq '.choices[0].message.content'

# Test image generation (via proxy)
curl -X POST http://localhost:7457/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux.1-schnell",
    "prompt": "A test image",
    "size": "1024x1024",
    "n": 1,
    "response_format": "b64_json"
  }' | jq '.data[0].b64_json | length'
```

## Troubleshooting

### "Model not found"

```bash
# Check model availability
curl -s https://integrate.api.nvidia.com/v1/models \
  -H "Authorization: Bearer $NVIDIA_API_KEY" | jq '.data[].id' | grep kimi

# If empty → model not on your plan
# Contact NIM support or check console.nvidia.com
```

### "Authorization failed"

```bash
# Verify key is set
echo $NVIDIA_API_KEY

# Check it's not empty/whitespace
echo "$NVIDIA_API_KEY" | wc -c  # Should be >50 chars

# Verify location
grep NVIDIA_API_KEY ~/.nanobot/secrets.env
grep NVIDIA_API_KEY ~/.hermes/.env
```

### "Timeout (model not responding)"

1. **Check NIM service status:** Usually temporary
2. **Try faster fallback:** Use `nim/meta/llama-3.3-70b-instruct` (0.8s)
3. **Switch to Groq:** `groq/llama-3.3-70b-versatile`
4. **Try local Ollama:** `ollama/qwen2.5-coder:7b` (if available)

### "Image generation failing"

```bash
# Check proxy is running
curl -s http://localhost:7457/health

# Check NIM API key is loaded in proxy
tail /tmp/nim-image-proxy.log | grep -i "key\|error"

# Restart proxy
pkill -f nim_image_proxy
python3 ~/projects/riri/tools/nim_image_proxy.py &
```

### "Too many requests"

NIM enforces rate limits. If hit:
1. Wait a few seconds before retrying
2. Check your quota at console.nvidia.com
3. Contact NVIDIA support for increase

---

**Last updated:** 2026-05-09
**NIM Status:** Active (tested 2026-05-01)
