#!/usr/bin/env python3
"""
RiRi Agent Loop — ReAct-style reasoning with tool execution.

Architecture:
  User message
       ↓
  Dispatcher (gemma3:4b local, ~200ms, no API cost)
  → classifies intent, selects 2-3 relevant skills
       ↓
  Fetcher sub-agent (pure Python, no LLM, no API cost)
  → Chroma semantic search, Magika file detection, skills.sh discovery
       ↓
  RiRi (NIM Llama 3.3 70B)
  → receives: message + pre-fetched knowledge + only relevant tool schemas
  → reasons and acts — never floods context with all tools

Model priority:
  1. NVIDIA NIM (meta/llama-3.3-70b-instruct) — free, powerful
  2. Local Ollama gemma3:12b — offline last resort, vision support
"""

import json, os, re, sys, time, urllib.request
from pathlib import Path

RIRI_DIR   = Path.home() / "projects/riri"
OLLAMA_URL = "http://localhost:11434"
NIM_URL    = "https://integrate.api.nvidia.com/v1"
BRAIN      = "gemma3:12b"   # local vision fallback
MAX_STEPS  = 10             # prevent infinite loops

sys.path.insert(0, str(RIRI_DIR / "core"))
sys.path.insert(0, str(RIRI_DIR))
from tools import call_tool, TOOL_DESCRIPTIONS

# Import dispatcher + fetcher (non-fatal if unavailable)
try:
    from dispatcher import dispatch, format_for_context
    from fetcher    import fetch, format_results as format_fetch
    DISPATCH_AVAILABLE = True
except ImportError:
    DISPATCH_AVAILABLE = False

# ── Env ────────────────────────────────────────────────────────────────────────
def _load_env():
    for f in [Path.home() / ".nanobot/secrets.env",
              Path.home() / "projects/claude-pipeline/.env"]:
        if f.exists():
            for line in f.read_text(errors="ignore").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
_load_env()


# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM = f"""You are RiRi, Ahmed's personal AI assistant running on his computer.
You can take real actions on his system using tools.

AVAILABLE TOOLS:
{TOOL_DESCRIPTIONS}

HOW TO USE TOOLS — follow this format exactly:
THOUGHT: <your reasoning about what to do next>
ACTION: <tool_name>
INPUT: <JSON dict of args>

After seeing the tool result, continue with another THOUGHT/ACTION/INPUT or end with:
FINAL: <your reply to Ahmed>

RULES:
- Always THINK before acting
- Use the simplest tool for the job
- For "write case study and post" tasks: use case_study tool (it handles everything)
- For GitHub tasks: use github_push tool
- For system tasks: use shell tool
- Be concise in FINAL reply — Ahmed wants results, not explanations
- If a tool fails, try a different approach or explain why

Ahmed's common requests:
- "fetch project X, write case study, post to LinkedIn" → case_study(project=X)
- "push [project] to github" → github_push(repo=path, message=...)
- "what did I work on recently" → search_memory(query=...)
- "post this to linkedin: ..." → linkedin_post(text=...)
"""


# ── LLM backends ──────────────────────────────────────────────────────────────
def _ollama(prompt: str, image_b64: str = None) -> str:
    """Call local Ollama with gemma3:12b. Supports vision if image_b64 provided."""
    payload = {
        "model":  BRAIN,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 800},
    }
    if image_b64:
        payload["images"] = [image_b64]

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read()).get("response", "").strip()


def _nim(messages: list) -> str:
    """Call NVIDIA NIM — primary LLM (free, powerful, OpenAI-compat)."""
    key = os.getenv("NVIDIA_API_KEY", "")
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY")
    body = json.dumps({
        "model":       "meta/llama-3.3-70b-instruct",
        "messages":    messages,
        "temperature": 0.3,
        "max_tokens":  800,
    }).encode()
    req = urllib.request.Request(
        f"{NIM_URL}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def _groq(messages: list) -> str:
    """Call Groq API — fast fallback."""
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("no GROQ_API_KEY")
    body = json.dumps({
        "model":       "llama-3.3-70b-versatile",
        "messages":    messages,
        "temperature": 0.3,
        "max_tokens":  800,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def _llm(history: list, image_b64: str = None, system_override: str = None) -> str:
    """
    Call the best available LLM.
    Priority: NIM → local Ollama (vision only).
    system_override: use a custom system prompt (e.g. one enriched with fetched context)
    history = list of {"role": "user"|"assistant", "content": str}
    """
    sys_prompt = system_override or SYSTEM

    # Build a single prompt string for Ollama (completion API)
    prompt_parts = [sys_prompt, ""]
    for msg in history:
        role = "Ahmed" if msg["role"] == "user" else "RiRi"
        prompt_parts.append(f"{role}: {msg['content']}")
    prompt_parts.append("RiRi:")
    prompt = "\n".join(prompt_parts)

    msgs = [{"role": "system", "content": sys_prompt}] + history

    # 1. NIM — primary (text only; skip for vision)
    if not image_b64:
        try:
            return _nim(msgs)
        except Exception as e:
            _log_error(f"NIM failed: {e}")

    # 2. Local Ollama — offline fallback + vision support
    return _ollama(prompt, image_b64=image_b64)


def _log_error(msg: str):
    """Write errors to ~/.riri/error.log"""
    try:
        log = Path.home() / ".riri/error.log"
        log.parent.mkdir(exist_ok=True)
        with open(log, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] agent_loop: {msg}\n")
    except Exception:
        pass


# ── ReAct parser ──────────────────────────────────────────────────────────────
def _parse_action(text: str):
    """
    Extract ACTION + INPUT from LLM output.
    Returns (tool_name, args_dict) or (None, None) if FINAL reached.
    """
    # Check for FINAL
    final_match = re.search(r"FINAL:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return "FINAL", final_match.group(1).strip()

    # Check for ACTION
    action_match = re.search(r"ACTION:\s*(\w+)", text, re.IGNORECASE)
    input_match  = re.search(r"INPUT:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)

    if not action_match:
        return None, None

    tool = action_match.group(1).strip()
    args = {}
    if input_match:
        try:
            args = json.loads(input_match.group(1))
        except json.JSONDecodeError:
            # Try to extract key=value if JSON fails
            raw = input_match.group(1)
            for m in re.finditer(r'"(\w+)"\s*:\s*"([^"]*)"', raw):
                args[m.group(1)] = m.group(2)
    return tool, args


# ── Main agent loop ────────────────────────────────────────────────────────────
def run(user_message: str, image_b64: str = None, file_path: str = None) -> str:
    """
    Process a user message through the dispatcher → fetcher → RiRi pipeline.

    Args:
      user_message: plain text request from the user
      image_b64:    optional base64 screenshot/image for vision tasks
      file_path:    optional path to an uploaded file (Magika detects type)
    """
    # ── Step 1: Dispatch (gemma3:4b local, ~200ms, no API cost) ────────────────
    dispatch_result = None
    fetch_result    = None
    context_block   = ""

    if DISPATCH_AVAILABLE:
        try:
            dispatch_result = dispatch(user_message, file_path=file_path)
            _log_error(f"dispatch: intent={dispatch_result.get('intent')} "
                       f"skills={dispatch_result.get('skills')} "
                       f"needs_fetch={dispatch_result.get('needs_fetch')}")
        except Exception as e:
            _log_error(f"Dispatcher failed (non-fatal): {e}")

    # ── Step 2: Fetch (pure Python, no LLM, no API cost) ───────────────────────
    if DISPATCH_AVAILABLE and dispatch_result and dispatch_result.get("needs_fetch"):
        try:
            fetch_result = fetch(
                queries        = dispatch_result.get("fetch_queries", []),
                file_path      = file_path,
                skill_search   = dispatch_result.get("fetch_skill_search"),
                search_hooks   = dispatch_result.get("intent") in ("system", "action"),
                search_pipeline_db = dispatch_result.get("intent") in ("retrieval", "content"),
            )
            context_block = format_fetch(fetch_result)
        except Exception as e:
            _log_error(f"Fetcher failed (non-fatal): {e}")

    # ── Step 3: Build system prompt with pre-fetched context ───────────────────
    system_with_context = SYSTEM
    if context_block.strip():
        system_with_context = (
            SYSTEM
            + "\n\n## Pre-fetched context (from knowledge base — use this, don't re-search):\n"
            + context_block
        )

    history = [{"role": "user", "content": user_message}]
    steps   = 0

    while steps < MAX_STEPS:
        steps += 1

        # LLM step — pass image only on first call (context)
        img = image_b64 if steps == 1 else None
        try:
            response = _llm(history, image_b64=img,
                            system_override=system_with_context if steps == 1 else None)
        except Exception as e:
            return f"❌ LLM error: {e}"

        history.append({"role": "assistant", "content": response})

        # Parse what the LLM wants to do
        tool, args = _parse_action(response)

        if tool == "FINAL":
            return args or response  # the final answer

        if tool is None:
            # No valid action found — treat the whole response as the final answer
            # (LLM might have answered directly without using tools)
            clean = re.sub(r"THOUGHT:.*?\n", "", response, flags=re.DOTALL).strip()
            return clean or response

        # Execute tool
        tool_result = call_tool(tool, args or {})
        result_text = tool_result.get("output", "")
        status      = "✓" if tool_result["ok"] else "✗"

        # For screenshot tool, grab the image for the next LLM call
        if tool == "screenshot" and tool_result.get("image_b64"):
            image_b64 = tool_result["image_b64"]

        # Feed result back into history
        observation = f"OBSERVATION [{tool} {status}]: {result_text}"
        history.append({"role": "user", "content": observation})

    return "⚠️ Max steps reached. Last response: " + (history[-2].get("content","")[:200])


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="RiRi agent — ask anything")
    ap.add_argument("message",  nargs="+",         help="Your request")
    ap.add_argument("--image",  default=None,       help="Path to image file to include")
    ap.add_argument("--screenshot", action="store_true", help="Auto-take screenshot first")
    args = ap.parse_args()

    msg = " ".join(args.message)
    img = None

    if args.screenshot:
        import subprocess, base64, tempfile
        p = tempfile.mktemp(suffix=".png")
        subprocess.run(["scrot", p], capture_output=True)
        if Path(p).exists():
            img = base64.b64encode(Path(p).read_bytes()).decode()
            print("📸 Screenshot attached")
    elif args.image:
        img = base64.b64encode(Path(args.image).read_bytes()).decode()

    print(f"💬 {msg}\n" + "─"*50)
    reply = run(msg, image_b64=img)
    print(reply)
