# Skill: Hermes Runtime — Gateway & LLM Router

Reference for managing Hermes Agent, the gateway that powers RiRi.

## What is Hermes?

**Hermes Agent v0.12.0** is the runtime that:

- Receives messages from Discord/WhatsApp
- Routes to MCP tools (function calls)
- Routes to LLM (with model selection + fallbacks)
- Manages session state
- Runs on port 18789

**Installation:** `~/.hermes/`
**Configuration:** `~/.hermes/config.yaml`
**Environment:** `~/.hermes/.env`

## Configuration (config.yaml)

**Location:** `~/.hermes/config.yaml`

**Key sections:**

```yaml
model:
  default: nim/moonshotai/kimi-k2.6              # Primary model
  fallbacks:
    - nim/qwen/qwen3-next-80b-a3b-instruct       # Fallback 1
    - nim/nvidia/llama-3.3-nemotron-super-49b-v1 # Fallback 2
    - nim/qwen/qwen3.5-122b-a10b                 # Fallback 3
    - nim/meta/llama-3.3-70b-instruct             # Fallback 4
    - groq/llama-3.3-70b-versatile                # Fallback 5 (Groq)
    - ollama/qwen2.5-coder:7b                     # Fallback 6 (Local)

providers:
  groq:
    base_url: https://api.groq.com/openai/v1
    api_key: ${GROQ_API_KEY}

custom_providers:
  - name: nim
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
    api_mode: chat_completions

toolsets:
  - hermes-cli

agent:
  max_turns: 90                   # Max conversation turns before reset
  gateway_timeout: 1800           # 30 minutes

mcp:
  - name: riri-tools
    command: python3
    args:
      - /home/ahmed/projects/riri/tools/riri_tools_mcp.py
    env:
      PYTHONPATH: /home/ahmed/projects/riri/tools
```

## Environment Variables (config.yaml reads from .env)

**Location:** `~/.hermes/.env`

**Required variables:**

```bash
NVIDIA_API_KEY=nvapi-...     # NIM endpoint auth
GROQ_API_KEY=gsk_...         # Groq fallback
DISCORD_TOKEN=...             # Discord messaging
# ... other channel tokens
```

**To add/update:**

```bash
# Edit directly
nano ~/.hermes/.env

# Or append
echo "NVIDIA_API_KEY=nvapi-..." >> ~/.hermes/.env

# Reload (after restart)
systemctl --user restart hermes-gateway
```

## Starting & Stopping

### Check Status

```bash
systemctl --user status hermes-gateway
# Shows if running, uptime, recent logs
```

### Start

```bash
systemctl --user start hermes-gateway
# Or:
hermes gateway start
```

### Stop

```bash
systemctl --user stop hermes-gateway
```

### Restart

```bash
systemctl --user restart hermes-gateway
# Clear session state, reload config, restart
```

### View Logs (Live)

```bash
journalctl --user -u hermes-gateway -f
# Follow logs in real-time (Ctrl+C to exit)
```

## Logs

### Error Log

```bash
cat ~/.hermes/logs/errors.log
tail -f ~/.hermes/logs/errors.log
```

### Gateway Log

```bash
cat ~/.hermes/logs/gateway.log
tail -f ~/.hermes/logs/gateway.log
```

### Full Journal (systemd)

```bash
journalctl --user -u hermes-gateway -n 100 -p err
# Last 100 error-level entries
```

## Gateway Commands

Hermes CLI interface (via systemd socket):

```bash
# Gateway status
hermes gateway status

# Start/stop/restart
hermes gateway start
hermes gateway stop
hermes gateway restart

# Check which models are available
hermes models list

# Show active model routing
hermes config show

# Test LLM connection
hermes test-llm --model nim/qwen/qwen3-next-80b-a3b-instruct
```

## Model Routing & Fallback Chain

### How It Works

1. **User sends message** to Discord
2. **Hermes receives** on port 18789
3. **Routes to default model:** `nim/moonshotai/kimi-k2.6`
4. **If timeout/error** → try fallback 1: `nim/qwen/qwen3-next-80b-a3b-instruct`
5. **If timeout/error** → try fallback 2: `nim/nvidia/llama-3.3-nemotron-super-49b-v1`
6. **Continue down chain** until success or exhaust all

### Changing Default Model

Edit `~/.hermes/config.yaml`:

```yaml
model:
  default: nim/qwen/qwen3-next-80b-a3b-instruct  # Faster, less context
  # or
  default: nim/nvidia/llama-3.3-nemotron-super-49b-v1  # Reasoning
```

Then restart:
```bash
systemctl --user restart hermes-gateway
```

### Adding Fallback Models

```yaml
model:
  default: nim/moonshotai/kimi-k2.6
  fallbacks:
    - nim/qwen/qwen3-next-80b-a3b-instruct
    - <new-model>  # Add here
    - nim/nvidia/llama-3.3-nemotron-super-49b-v1
```

## Custom Providers

### NIM Provider (Already Configured)

```yaml
custom_providers:
  - name: nim
    base_url: https://integrate.api.nvidia.com/v1
    api_key: ${NVIDIA_API_KEY}
    api_mode: chat_completions
```

**What this means:**
- When you see `nim/model-name` → use this provider
- Base URL is NIM endpoint
- Auth via `$NVIDIA_API_KEY` env var
- API compatible with OpenAI chat completions

### Groq Provider (Fallback)

```yaml
providers:
  groq:
    base_url: https://api.groq.com/openai/v1
    api_key: ${GROQ_API_KEY}
```

**Usage:** Models like `groq/llama-3.3-70b-versatile` automatically route to Groq.

### Local Ollama Provider

```yaml
custom_providers:
  - name: ollama
    base_url: http://localhost:11434
    api_key: ""  # No auth needed
    api_mode: chat_completions
```

**Usage:** Models like `ollama/qwen2.5-coder:7b` route to local Ollama.

## Port 18789 (Gateway Listener)

Hermes listens on `127.0.0.1:18789` for:

1. **Discord integration** — receives messages
2. **WhatsApp integration** — receives messages
3. **OpenDesign daemon** (ACP mode) — design task requests
4. **MCP tool responses** — from tools spawned as subprocesses

**To verify it's listening:**

```bash
lsof -i :18789
# Should show "hermes-agent" process

# Or test connectivity
curl -s http://localhost:18789/health
# Returns: {"status": "ok"} (or similar)
```

## MCP Toolsets

Hermes dispatches tools via MCP (Model Context Protocol).

### RiRi Tools

```yaml
mcp:
  - name: riri-tools
    command: python3
    args:
      - /home/ahmed/projects/riri/tools/riri_tools_mcp.py
    env:
      PYTHONPATH: /home/ahmed/projects/riri/tools
```

**Spawns:** Python subprocess running `riri_tools_mcp.py`
**Inherits env:** `~/.hermes/.env` + `~/.nanobot/secrets.env`
**Tools exposed:** linkedin_post, hyperframes_render, opendesign_run, mem0_recall, mem0_store, etc.

### Adding New MCP Tools

1. Create script at `~/path/to/my_tool.py`
2. Add to `config.yaml`:
   ```yaml
   mcp:
     - name: my-tool
       command: python3
       args:
         - ~/path/to/my_tool.py
   ```
3. Restart: `systemctl --user restart hermes-gateway`
4. Tool is now available to RiRi

## Session Management

### Max Turns

```yaml
agent:
  max_turns: 90  # Max conversation turns before reset
```

After 90 back-and-forth exchanges, Hermes resets the session.

### Timeout

```yaml
agent:
  gateway_timeout: 1800  # 30 minutes
```

If no activity for 30 minutes, session auto-closes.

### View Active Sessions

```bash
hermes session list
# Shows: session_id, started_at, turn_count, context_used
```

### Clear Session (Manual)

```bash
hermes session clear
# Or: systemctl --user restart hermes-gateway (full restart)
```

## Performance Tuning

### Increase Context Window (for long conversations)

Currently using Kimi K2.6 (1M context). Context is rarely exhausted.

If needed, check:
```bash
hermes session info
# Shows: context_used, context_limit
```

### Optimize for Speed (when Kimi is slow)

Change default to faster model:
```yaml
model:
  default: nim/qwen/qwen3-next-80b-a3b-instruct  # 1.2s latency
  # instead of kimi-k2.6 (~20s latency)
```

### Optimize for Quality (when fallback too simple)

Add more capable fallbacks:
```yaml
fallbacks:
  - nim/qwen/qwen3-coder-480b-a35b-instruct  # Code-heavy tasks
  - nim/qwen/qwen3.5-122b-a10b               # Long-form writing
```

## ACP Mode (for OpenDesign)

When OD daemon connects to Hermes, it uses **ACP mode** (Agent Communication Protocol):

```
OD daemon (port 7456)
    ↓ ACP JSON-RPC
Hermes (port 18789)
    ↓ selects model
NIM (LLM)
    ↓
Returns design
```

This is automatic—no manual configuration needed. Just ensure:
1. Hermes is running (`systemctl --user status hermes-gateway`)
2. Port 18789 is open
3. NIM API key is set

## Troubleshooting

### "Gateway not responding"

```bash
# Check if running
systemctl --user status hermes-gateway

# Restart
systemctl --user restart hermes-gateway

# Check logs for errors
journalctl --user -u hermes-gateway -n 50 -p err
```

### "Model timeout"

1. Check NIM service status
2. Try fallback model: edit config.yaml, move faster model to top
3. Check internet connectivity

### "Tool call failing"

```bash
# Check MCP tools are loaded
hermes tools list

# Restart to reload tools
systemctl --user restart hermes-gateway

# Check tool logs
tail -f ~/.hermes/logs/errors.log | grep riri-tools
```

### "Port 18789 already in use"

```bash
# Find what's using it
lsof -i :18789

# Kill the process
kill -9 <PID>

# Or restart cleanly
systemctl --user stop hermes-gateway
sleep 2
systemctl --user start hermes-gateway
```

### "ANTHROPIC_API_KEY breaking NIM routing"

If `ANTHROPIC_API_KEY` is set, litellm hijacks nim/ model routing.

**Fix:** Unset it
```bash
unset ANTHROPIC_API_KEY

# Or in environment file, comment it out
nano ~/.hermes/.env
# ANTHROPIC_API_KEY=...  (commented)
```

Then restart gateway:
```bash
systemctl --user restart hermes-gateway
```

## Quick Reference Commands

```bash
# Status
systemctl --user status hermes-gateway

# Restart
systemctl --user restart hermes-gateway

# Logs
journalctl --user -u hermes-gateway -f

# Check port
lsof -i :18789

# Test LLM
hermes test-llm --model nim/meta/llama-3.3-70b-instruct

# List available models
hermes models list
```

---

**Related Documentation:**
- `/home/ahmed/.hermes/config.yaml` — Full configuration
- `/home/ahmed/.hermes/.env` — Environment variables
- `/home/ahmed/projects/riri/docs/architecture.md` — System architecture
- `/home/ahmed/projects/riri/docs/nim.md` — NIM models reference

**Last updated:** 2026-05-09
**Version:** Hermes 0.12.0 (OpenClaw migration 2026-05-08)
