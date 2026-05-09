#!/usr/bin/env python3
"""
RiRi Tool Registry — every action RiRi can take on the computer.

Each tool is a plain function that takes a dict of args and returns
{"ok": bool, "output": str}. The agent loop calls these and feeds the
output back to the LLM.

Tools:
  shell          — run any shell command
  read_file      — read a file
  write_file     — write/overwrite a file
  browse         — browser-use LLM agent (vision-driven)
  linkedin_post  — post text to LinkedIn via REST API
  github_push    — git add + commit + push in a repo
  case_study     — generate case study + LinkedIn post
  notify         — desktop toast notification
  search_memory  — search ChromaDB past sessions
  screenshot     — take a desktop screenshot → base64 (for vision)
"""

import base64, json, os, subprocess, sys
from pathlib import Path

RIRI_DIR = Path.home() / "projects/riri"

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


# ── Helpers ────────────────────────────────────────────────────────────────────
def _ok(output: str) -> dict:
    return {"ok": True, "output": str(output)[:2000]}

def _err(msg: str) -> dict:
    return {"ok": False, "output": f"ERROR: {msg}"}

def _run(cmd, cwd=None, timeout=30) -> tuple[int, str]:
    r = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


# ── Tool implementations ───────────────────────────────────────────────────────

def tool_shell(args: dict) -> dict:
    """Run a shell command. Args: {command: str, cwd: str (optional)}"""
    cmd = args.get("command", "").strip()
    cwd = args.get("cwd", None)
    if not cmd:
        return _err("No command provided")
    try:
        code, out = _run(cmd, cwd=cwd, timeout=60)
        status = "✓" if code == 0 else f"✗ exit {code}"
        return _ok(f"[{status}]\n{out[:1500]}")
    except subprocess.TimeoutExpired:
        return _err("Command timed out after 60s")
    except Exception as e:
        return _err(str(e))


def tool_read_file(args: dict) -> dict:
    """Read a file. Args: {path: str, lines: int (optional, default 100)}"""
    path = Path(args.get("path", "")).expanduser()
    limit = int(args.get("lines", 100))
    try:
        text = path.read_text(errors="ignore")
        lines = text.splitlines()
        snippet = "\n".join(lines[:limit])
        note = f"\n... ({len(lines)} total lines, showing first {limit})" if len(lines) > limit else ""
        return _ok(snippet + note)
    except Exception as e:
        return _err(str(e))


def tool_write_file(args: dict) -> dict:
    """Write content to a file. Args: {path: str, content: str}"""
    path = Path(args.get("path", "")).expanduser()
    content = args.get("content", "")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return _ok(f"Written {len(content)} chars to {path}")
    except Exception as e:
        return _err(str(e))


def tool_linkedin_post(args: dict) -> dict:
    """Post text to LinkedIn. Args: {text: str}"""
    text = args.get("text", "").strip()
    if not text:
        return _err("No text to post")
    sys.path.insert(0, str(RIRI_DIR / "agents/linkedin"))
    try:
        from api import post_text
        result = post_text(text)
        if result.get("success"):
            url = result.get("url", "")
            urn = result.get("urn", "")
            return _ok(f"Posted to LinkedIn ✓\nURL: {url}\nURN: {urn}")
        return _err(f"LinkedIn post FAILED: {result.get('error', 'unknown error')}")
    except Exception as e:
        return _err(str(e))


def tool_github_push(args: dict) -> dict:
    """
    Git add + commit + push in a repo.
    Args: {repo: str (path), message: str, files: list (optional, default all)}
    """
    repo = Path(args.get("repo", ".")).expanduser()
    msg  = args.get("message", "RiRi: update")
    files = args.get("files", ["."])
    try:
        add_targets = " ".join(f'"{f}"' for f in files)
        _, out1 = _run(f"git add {add_targets}", cwd=repo)
        code, out2 = _run(f'git commit -m "{msg}"', cwd=repo)
        if code != 0 and "nothing to commit" in out2:
            return _ok("Nothing to commit — repo already up to date")
        _, out3 = _run("git push", cwd=repo, timeout=30)
        return _ok(f"Committed & pushed.\n{out2}\n{out3}")
    except Exception as e:
        return _err(str(e))


def tool_case_study(args: dict) -> dict:
    """
    Generate a case study from the latest Claude session and post to LinkedIn.
    Args: {project: str (optional), no_linkedin: bool, no_chromadb: bool}
    """
    cmd = [sys.executable, str(RIRI_DIR / "case_study.py")]
    if args.get("project"):
        cmd += ["--project", args["project"]]
    if args.get("no_linkedin"):
        cmd += ["--no-linkedin"]
    if args.get("no_chromadb"):
        cmd += ["--no-chromadb"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return _ok((r.stdout + r.stderr).strip()[:1500])
    except subprocess.TimeoutExpired:
        return _err("Case study timed out (3 min)")
    except Exception as e:
        return _err(str(e))


def tool_browse(args: dict) -> dict:
    """
    Run a browser-use vision agent for a task.
    Args: {task: str, steps: int (default 15)}
    """
    import asyncio
    task  = args.get("task", "").strip()
    steps = int(args.get("steps", 15))
    if not task:
        return _err("No task specified")
    sys.path.insert(0, str(RIRI_DIR / "agents/browser"))
    try:
        from agent import run_task
        result = asyncio.run(run_task(task, max_steps=steps, timeout=120))
        if result["success"]:
            return _ok(f"Done ({result['steps']} steps)\n{result['result']}")
        return _err(result.get("error", "unknown"))
    except Exception as e:
        return _err(str(e))


def tool_notify(args: dict) -> dict:
    """Show a desktop toast notification. Args: {message: str}"""
    msg = args.get("message", "RiRi")
    try:
        subprocess.Popen(
            [sys.executable, str(RIRI_DIR / "notify.py"), msg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return _ok(f"Notified: {msg}")
    except Exception as e:
        return _err(str(e))


def tool_search_memory(args: dict) -> dict:
    """Search past Claude sessions in ChromaDB. Args: {query: str, n: int}"""
    query = args.get("query", "")
    n     = int(args.get("n", 5))
    sys.path.insert(0, str(RIRI_DIR))
    try:
        from memory import recall
        results = recall(query, n=n)
        if not results:
            return _ok("No matching memories found")
        lines = [f"[{i+1}] {r.get('text','')[:200]}" for i, r in enumerate(results)]
        return _ok("\n".join(lines))
    except Exception as e:
        return _err(str(e))


def tool_screenshot(args: dict) -> dict:
    """
    Take a desktop screenshot and return as base64.
    Args: {save_path: str (optional)}
    Useful for passing to the vision model to see what's on screen.
    """
    import tempfile
    path = args.get("save_path") or tempfile.mktemp(suffix=".png")
    try:
        subprocess.run(["scrot", path], capture_output=True, timeout=5)
        if not Path(path).exists():
            subprocess.run(["import", "-window", "root", path],
                           capture_output=True, timeout=5)
        if Path(path).exists():
            b64 = base64.b64encode(Path(path).read_bytes()).decode()
            return {"ok": True, "output": f"Screenshot saved: {path}", "image_b64": b64}
        return _err("Screenshot failed — scrot and import both unavailable")
    except Exception as e:
        return _err(str(e))


# ── Registry ───────────────────────────────────────────────────────────────────
TOOLS = {
    "shell":          tool_shell,
    "read_file":      tool_read_file,
    "write_file":     tool_write_file,
    "linkedin_post":  tool_linkedin_post,
    "github_push":    tool_github_push,
    "case_study":     tool_case_study,
    "browse":         tool_browse,
    "notify":         tool_notify,
    "search_memory":  tool_search_memory,
    "screenshot":     tool_screenshot,
}

TOOL_DESCRIPTIONS = """
shell(command, cwd?)          — run any bash command on the computer
read_file(path, lines?)       — read a file (default first 100 lines)
write_file(path, content)     — create or overwrite a file
linkedin_post(text)           — publish a text post to LinkedIn feed
github_push(repo, message, files?) — git add + commit + push
case_study(project?, no_linkedin?, no_chromadb?) — generate AI case study from last session
browse(task, steps?)          — vision-based browser agent (e.g. "go to X and do Y")
notify(message)               — show a desktop toast notification
search_memory(query, n?)      — search past sessions and project history
screenshot()                  — capture the current screen (for vision tasks)
""".strip()


def call_tool(name: str, args: dict) -> dict:
    fn = TOOLS.get(name)
    if not fn:
        return _err(f"Unknown tool '{name}'. Available: {', '.join(TOOLS)}")
    try:
        return fn(args)
    except Exception as e:
        return _err(f"{name} crashed: {e}")
