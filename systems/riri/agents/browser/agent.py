#!/usr/bin/env python3
"""
RiRi Browser Agent — LLM-driven browser automation via browser-use + Playwright.
Give it a high-level task in plain English; it figures out the clicks itself.

Architecture:
  browser-use Agent → LLM (GPT-4o / Groq vision) → Playwright → screenshot loop

Usage (CLI):
  python3 agent.py "go to linkedin.com/feed and post: hello world"
  python3 agent.py "open google.com and search for python tutorials"

Discord trigger:
  !browse go to my LinkedIn and post: "hello from RiRi"

The agent uses the EXISTING Chrome session if --attach is passed,
otherwise launches a fresh Chromium instance.
"""

import argparse, asyncio, json, os, sys
from pathlib import Path

RIRI_DIR     = Path.home() / "projects/riri"
SECRETS_FILE = Path.home() / ".nanobot/secrets.env"
DIAG_DIR     = Path.home() / ".local/share/riri/browser-diag"
DIAG_DIR.mkdir(parents=True, exist_ok=True)


def _load_env():
    for f in [SECRETS_FILE, Path.home() / "projects/claude-pipeline/.env"]:
        if f.exists():
            for line in f.read_text(errors="ignore").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()


def _get_llm(model_override: str = None):
    """
    Return the best available LLM for browser-use.
    Priority: OpenAI → Groq (free) → Anthropic → Ollama local (no vision)

    Quick free setup: get key at console.groq.com →
      echo 'GROQ_API_KEY=<key>' >> ~/.nanobot/secrets.env
    """
    if model_override:
        # Explicit override e.g. "ollama:gemma3:12b" or "groq:llama-3.2-90b-vision-preview"
        provider, _, model = model_override.partition(":")
        if provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(model=model or "gemma3:12b", temperature=0)
        if provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model=model or "llama-3.2-90b-vision-preview", temperature=0)

    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o", temperature=0)

    if os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.2-90b-vision-preview", temperature=0)

    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)

    # Local Ollama fallback — no vision, but can navigate via DOM text
    try:
        from langchain_ollama import ChatOllama
        print("⚠️  No cloud key — using local Ollama (gemma3:12b, no vision). "
              "Add GROQ_API_KEY to ~/.nanobot/secrets.env for free vision support.")
        return ChatOllama(model="gemma3:12b", temperature=0)
    except Exception:
        pass

    raise RuntimeError(
        "No LLM available. Quick fix (free): console.groq.com → "
        "add GROQ_API_KEY=<key> to ~/.nanobot/secrets.env"
    )


async def run_task(task: str, max_steps: int = 15, timeout: int = 120) -> dict:
    """
    Run a browser task. Returns:
      {"success": True/False, "result": "...", "steps": N, "error": "..."}
    """
    from browser_use import Agent, Browser, BrowserConfig

    try:
        llm = _get_llm()
    except RuntimeError as e:
        return {"success": False, "error": str(e), "result": "", "steps": 0}

    # Launch fresh Chromium (headed so user can see what's happening)
    browser = Browser(
        config=BrowserConfig(
            headless=False,
            chrome_instance_path=None,   # use bundled Chromium
            extra_chromium_args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
    )

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        max_actions_per_step=5,
    )

    try:
        result = await asyncio.wait_for(
            agent.run(max_steps=max_steps),
            timeout=timeout
        )
        # browser-use AgentHistoryList
        final = str(result.final_result() or "Task completed")
        steps = len(result.history) if hasattr(result, 'history') else 0
        return {"success": True, "result": final[:500], "steps": steps}

    except asyncio.TimeoutError:
        return {"success": False, "error": f"Timed out after {timeout}s", "result": "", "steps": 0}
    except Exception as e:
        return {"success": False, "error": str(e)[:300], "result": "", "steps": 0}
    finally:
        try:
            await browser.close()
        except Exception:
            pass


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("task", nargs="+", help="Task description in plain English")
    ap.add_argument("--steps",   type=int, default=15,  help="Max steps (default 15)")
    ap.add_argument("--timeout", type=int, default=120, help="Timeout seconds (default 120)")
    args = ap.parse_args()

    task = " ".join(args.task)
    print(f"🌐 Task: {task}")

    result = asyncio.run(run_task(task, max_steps=args.steps, timeout=args.timeout))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)
