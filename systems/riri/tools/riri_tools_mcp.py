#!/usr/bin/env python3
"""
RiRi Tools MCP Server
Exposes LinkedIn posting, HyperFrames rendering, notifications and memory
as native MCP tools — no bash exec approval needed, reliable tool calling.

Tools:
  linkedin_post        — publish text post, returns real URL
  linkedin_delete      — delete a post by URN
  hyperframes_render   — create + render an HTML composition to MP4
  riri_notify          — send Ahmed a proactive WhatsApp message
  riri_memory_context  — fetch recent openamnesia memory summaries
  mem0_recall          — semantic search structured memory (Mem0 + Qdrant)
  mem0_store           — store new facts into structured memory
"""

import asyncio
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RIRI_DIR    = Path.home() / "projects/riri"
SECRETS     = Path.home() / ".nanobot/secrets.env"
OUTPUT_DIR  = RIRI_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Secrets ──────────────────────────────────────────────────────────────────

def _load_secrets():
    if SECRETS.exists():
        for line in SECRETS.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_secrets()


# ── LinkedIn ──────────────────────────────────────────────────────────────────

LI_BASE    = "https://api.linkedin.com"
LI_VERSION = "202503"

def _li_headers() -> dict:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("No LINKEDIN_ACCESS_TOKEN in secrets.env")
    return {
        "Authorization":             f"Bearer {token}",
        "Content-Type":              "application/json",
        "LinkedIn-Version":          LI_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }

def _li_get_member_urn() -> str:
    cached = os.getenv("LINKEDIN_MEMBER_URN", "")
    if cached:
        return cached
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {os.getenv('LINKEDIN_ACCESS_TOKEN','')}"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    sub = data.get("sub", "")
    if not sub:
        raise RuntimeError("Could not get LinkedIn member ID from /v2/userinfo")
    return f"urn:li:person:{sub}"

def linkedin_post(text: str) -> dict:
    """Publish a text post. Returns {success, url, urn} or {success:False, error}."""
    try:
        author = _li_get_member_urn()
        payload = json.dumps({
            "author":       author,
            "commentary":   text,
            "visibility":   "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState":          "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }).encode()
        req = urllib.request.Request(
            f"{LI_BASE}/rest/posts",
            data=payload, method="POST",
            headers=_li_headers(),
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            post_id = dict(r.headers).get("x-restli-id", "")
            if not post_id:
                return {"success": False, "error": f"API returned {r.status} but no post ID — headers: {dict(list(r.headers.items())[:5])}"}
            url = f"https://www.linkedin.com/feed/update/{post_id}"
            return {"success": True, "urn": post_id, "url": url}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        return {"success": False, "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def linkedin_delete(urn: str) -> dict:
    try:
        encoded = urllib.parse.quote(urn, safe="")
        req = urllib.request.Request(
            f"{LI_BASE}/rest/posts/{encoded}",
            method="DELETE", headers=_li_headers(),
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return {"success": True, "status": r.status}
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── HyperFrames ───────────────────────────────────────────────────────────────

def hyperframes_render(slug: str, html_content: str, duration: int = 4, fps: int = 30) -> dict:
    """
    Create a HyperFrames project from html_content and render to MP4.
    Returns {success, path, size_kb} or {success:False, error, lint_output}.
    html_content must be a complete index.html using the correct HyperFrames structure.
    """
    import shutil, tempfile
    proj_dir = Path(tempfile.mkdtemp(prefix=f"hf_{slug}_"))
    try:
        # Write project files
        meta = {"id": slug, "name": slug, "createdAt": "2026-01-01T00:00:00.000Z"}
        (proj_dir / "meta.json").write_text(json.dumps(meta))
        hf_cfg = {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}
        }
        (proj_dir / "hyperframes.json").write_text(json.dumps(hf_cfg))
        (proj_dir / "index.html").write_text(html_content)
        (proj_dir / "compositions").mkdir(exist_ok=True)
        (proj_dir / "assets").mkdir(exist_ok=True)

        nvm_setup = "source ~/.nvm/nvm.sh && nvm use 22 --silent 2>/dev/null && "

        # Lint first
        lint = subprocess.run(
            f"{nvm_setup} npx hyperframes@0.4.39 lint {proj_dir} --json",
            shell=True, executable="/bin/bash",
            capture_output=True, text=True, timeout=30
        )
        lint_out = lint.stdout + lint.stderr
        try:
            lint_data = json.loads(lint.stdout)
            errors = [x for x in lint_data if x.get("severity") == "error"]
            if errors:
                return {"success": False, "error": "Lint errors — fix before rendering", "lint_output": json.dumps(errors[:5])}
        except Exception:
            pass  # lint JSON parse failed, continue

        # Render
        output_path = OUTPUT_DIR / f"{slug}.mp4"
        render = subprocess.run(
            f"{nvm_setup} npx hyperframes@0.4.39 render {proj_dir} -o {output_path} --fps {fps}",
            shell=True, executable="/bin/bash",
            capture_output=True, text=True, timeout=180
        )
        render_out = (render.stdout + render.stderr)[-1000:]

        # Verify output
        if not output_path.exists():
            return {"success": False, "error": "Render produced no output file", "render_log": render_out}
        size = output_path.stat().st_size
        if size < 10_000:
            content = output_path.read_text(errors="replace")[:200]
            return {"success": False, "error": f"Output is only {size} bytes — not a real MP4. Content: {content}", "render_log": render_out}

        file_check = subprocess.run(f"file {output_path}", shell=True, capture_output=True, text=True)
        if "ISO Media" not in file_check.stdout and "MP4" not in file_check.stdout:
            return {"success": False, "error": f"Output is not a valid MP4: {file_check.stdout}", "render_log": render_out}

        return {"success": True, "path": str(output_path), "size_kb": round(size / 1024, 1)}
    finally:
        shutil.rmtree(proj_dir, ignore_errors=True)


# ── Notify ────────────────────────────────────────────────────────────────────

def nim_infer(model: str, prompt: str, system: str = "", max_tokens: int = 1500, temperature: float = 0.3) -> dict:
    """
    Call any NIM model directly for a specialist subtask.
    Use this for tasks that benefit from a different model than the primary agent:
      - qwen/qwen3-coder-480b-a35b-instruct  → complex code generation / debugging
      - nvidia/nemotron-3-super-120b-a12b     → deep reasoning, architecture decisions
      - nvidia/nemotron-3-nano-omni-30b-a3b-reasoning → step-by-step analysis
      - qwen/qwen3.5-122b-a10b               → long-form content writing, quality text
    Returns {success, content, model, tokens_used} or {success:False, error}.
    """
    secrets: dict = {}
    if SECRETS.exists():
        for line in SECRETS.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip()
    api_key = secrets.get("NVIDIA_API_KEY", os.getenv("NVIDIA_API_KEY", ""))
    if not api_key:
        return {"success": False, "error": "No NVIDIA_API_KEY in secrets.env"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            return {
                "success": True,
                "content": content,
                "model": model,
                "tokens_used": usage.get("total_tokens", 0),
            }
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode()[:300]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def riri_status() -> str:
    """Run the riri-status.sh script and return formatted status output."""
    result = subprocess.run(
        ["/home/ahmed/.local/bin/riri-status.sh"],
        capture_output=True, text=True, timeout=15
    )
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        err = result.stderr[:200]
        return f"Status check failed (exit {result.returncode}): {err}"
    return out


def riri_notify(type_: str, message: str) -> dict:
    """Send Ahmed a proactive WhatsApp message. type: done|error|approval|update"""
    result = subprocess.run(
        ["/home/ahmed/.local/bin/riri-notify.sh", type_, message],
        capture_output=True, text=True, timeout=15
    )
    return {"sent": result.returncode == 0, "output": (result.stdout + result.stderr)[:200]}


# ── Memory context ────────────────────────────────────────────────────────────

def riri_memory_context(max_chars: int = 3000) -> str:
    memory_dir = Path.home() / ".openclaw/workspace/memory"
    files = sorted(memory_dir.glob("*.md"), reverse=True)[:3]
    if not files:
        return "(no memory files yet)"
    per = max_chars // max(len(files), 1)
    return "\n\n---\n\n".join(f.read_text(encoding="utf-8")[:per] for f in files)


# ── Mem0 structured memory ───────────────────────────────────────────────────

_mem0_instance = None

def _get_mem0():
    global _mem0_instance
    if _mem0_instance is None:
        try:
            sys.path.insert(0, str(RIRI_DIR / "tools"))
            from riri_mem0 import RiriMemory
            _mem0_instance = RiriMemory()
        except Exception as e:
            return None, str(e)
    return _mem0_instance, None

def mem0_recall(query: str, limit: int = 8) -> dict:
    """Search structured memories relevant to a query."""
    mem, err = _get_mem0()
    if err:
        return {"success": False, "error": err}
    try:
        hits = mem.search(query, limit=limit)
        return {
            "success": True,
            "count": len(hits),
            "memories": [
                {"text": h.get("memory", ""), "score": round(h.get("score", 0), 3), "date": (h.get("created_at") or "")[:10]}
                for h in hits
            ],
            "context_block": mem.context_block(query, limit=limit),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def mem0_store(text: str) -> dict:
    """Extract facts from text and persist them to structured memory."""
    mem, err = _get_mem0()
    if err:
        return {"success": False, "error": err}
    try:
        results = mem.add(text)
        return {
            "success": True,
            "stored": len(results),
            "facts": [{"event": r.get("event"), "text": r.get("memory", "")} for r in results],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}




# ── OpenDesign ────────────────────────────────────────────────────────────────

OD_DAEMON_URL   = "http://localhost:7456"
OD_PROXY_URL    = "http://localhost:7457"   # NIM image proxy
OD_PROJECT_ROOT = Path.home() / "Desktop/OpenDesign/open-design"
OD_DATA_DIR     = OD_PROJECT_ROOT / ".od"
OD_NODE_BIN     = Path.home() / ".nvm/versions/node/v24.14.1/bin/node"
OD_DAEMON_BIN   = OD_PROJECT_ROOT / "apps/daemon/dist/cli.js"
OD_DAEMON_LOG   = Path("/tmp/od-daemon.log")
OD_PROXY_LOG    = Path("/tmp/nim-image-proxy.log")
OD_REGISTRY     = OD_DATA_DIR / "riri-projects.json"   # task→project_id memory

# Task type → OpenDesign skill ID
OD_TASK_SKILL = {
    # Infographics / dashboards / data
    "infographic":   "dashboard",
    "dashboard":     "dashboard",
    "data-viz":      "dashboard",
    "chart":         "dashboard",
    "report":        "finance-report",
    "finance":       "finance-report",
    # Web / UI prototypes
    "web":           "web-prototype",
    "ui":            "web-prototype",
    "prototype":     "web-prototype",
    "app":           "web-prototype",
    "landing":       "saas-landing",
    "saas":          "saas-landing",
    "waitlist":      "waitlist-page",
    "pricing":       "pricing-page",
    "kanban":        "kanban-board",
    # Mobile
    "mobile":        "mobile-app",
    "mobile-app":    "mobile-app",
    # Presentations / decks
    "deck":          "html-ppt",
    "slides":        "html-ppt",
    "presentation":  "html-ppt",
    "pitch":         "html-ppt-pitch-deck",
    "weekly":        "html-ppt-weekly-report",
    # Social / content
    "social":        "social-carousel",
    "social-media":  "social-carousel",
    "blog":          "blog-post",
    "article":       "blog-post",
    "email":         "email-marketing",
    "newsletter":    "email-marketing",
    "docs":          "docs-page",
    # Visual assets
    "image":         "image-poster",
    "poster":        "image-poster",
    "visual":        "image-poster",
    "svg":           "web-prototype",
    "wireframe":     "wireframe-sketch",
    # Video / animation
    "video":         "hyperframes",
    "animation":     "motion-frames",
    "frames":        "motion-frames",
    # Misc
    "invoice":       "invoice",
    "okrs":          "team-okrs",
    "magazine":      "magazine-poster",
    "sprite":        "sprite-animation",
}

# Task type → NIM model (for AGENTS.md routing context and nim_infer subtasks)
OD_TASK_MODEL = {
    "infographic":  "nvidia/llama-3.3-nemotron-super-49b-v1",   # reasoning + data
    "dashboard":    "nvidia/llama-3.3-nemotron-super-49b-v1",
    "data-viz":     "nvidia/llama-3.3-nemotron-super-49b-v1",
    "chart":        "nvidia/llama-3.3-nemotron-super-49b-v1",
    "report":       "nvidia/llama-3.3-nemotron-super-49b-v1",
    "svg":          "qwen/qwen3-coder-480b-a35b-instruct",       # code-heavy SVG
    "wireframe":    "qwen/qwen3-next-80b-a3b-instruct",          # design-first
    "web":          "qwen/qwen3-next-80b-a3b-instruct",
    "ui":           "qwen/qwen3-next-80b-a3b-instruct",
    "prototype":    "qwen/qwen3-next-80b-a3b-instruct",
    "landing":      "qwen/qwen3-next-80b-a3b-instruct",
    "mobile":       "qwen/qwen3-next-80b-a3b-instruct",
    "deck":         "qwen/qwen3-next-80b-a3b-instruct",
    "slides":       "qwen/qwen3-next-80b-a3b-instruct",
    "presentation": "qwen/qwen3-next-80b-a3b-instruct",
    "social":       "qwen/qwen3-next-80b-a3b-instruct",
    "video":        "qwen/qwen3-next-80b-a3b-instruct",
    "animation":    "qwen/qwen3-coder-480b-a35b-instruct",
}


def _od_is_running() -> bool:
    """Check if OD daemon is responding on port 7456."""
    try:
        req = urllib.request.Request(f"{OD_DAEMON_URL}/api/skills", method="GET")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def _od_find_node24() -> str:
    """Return path to Node 24 binary."""
    if OD_NODE_BIN.exists():
        return str(OD_NODE_BIN)
    result = subprocess.run(
        "source ~/.nvm/nvm.sh && nvm which 24 2>/dev/null",
        shell=True, executable="/bin/bash", capture_output=True, text=True
    )
    p = result.stdout.strip()
    if p and Path(p).exists():
        return p
    return ""


def _od_proxy_is_running() -> bool:
    """Check if the NIM image proxy is responding on port 7457."""
    try:
        req = urllib.request.Request(f"{OD_PROXY_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _od_start_proxy() -> dict:
    """Start the NIM image proxy server at port 7457."""
    proxy_script = Path(__file__).parent / "nim_image_proxy.py"
    if not proxy_script.exists():
        return {"ok": False, "error": f"Proxy script not found at {proxy_script}"}
    venv_python = Path.home() / ".hermes/hermes-agent/venv/bin/python"
    python_bin = str(venv_python) if venv_python.exists() else sys.executable
    proc = subprocess.Popen(
        [python_bin, str(proxy_script)],
        stdout=open(str(OD_PROXY_LOG), "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    import time
    for _ in range(20):
        time.sleep(0.3)
        if _od_proxy_is_running():
            return {"ok": True, "pid": proc.pid}
    return {"ok": False, "pid": proc.pid, "error": "Proxy started but not responding"}


def _od_configure_media_nim() -> dict:
    """Tell the OD daemon to use the NIM image proxy for image generation."""
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        if SECRETS.exists():
            for line in SECRETS.read_text(errors="ignore").splitlines():
                if "NVIDIA_API_KEY=" in line and not line.startswith("#"):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        return {"ok": False, "error": "NVIDIA_API_KEY not found"}
    try:
        _od_api("PUT", "/api/media/config", {
            "openai": {
                "apiKey": api_key,
                "baseUrl": OD_PROXY_URL,
            }
        })
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _od_start_daemon() -> dict:
    """Start OD daemon + NIM image proxy in background. Returns {ok, pid, error}."""
    node_bin = _od_find_node24()
    if not node_bin:
        return {"ok": False, "error": "Node 24 not found — run: nvm install 24"}
    if not OD_DAEMON_BIN.exists():
        return {"ok": False, "error": f"OD daemon not built at {OD_DAEMON_BIN}"}

    proc = subprocess.Popen(
        [node_bin, str(OD_DAEMON_BIN), "--no-open"],
        cwd=str(OD_PROJECT_ROOT),
        env={**os.environ, "OD_PORT": "7456"},
        stdout=open(str(OD_DAEMON_LOG), "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    import time
    for _ in range(24):
        time.sleep(0.5)
        if _od_is_running():
            # Also start proxy if not running
            if not _od_proxy_is_running():
                _od_start_proxy()
            # Configure OD to use proxy for image gen
            _od_configure_media_nim()
            return {"ok": True, "pid": proc.pid}

    return {"ok": False, "pid": proc.pid, "error": "Daemon started but not responding after 12s"}


# ── Project registry (RiRi remembers OD projects across sessions) ─────────────

def _registry_load() -> dict:
    """Load the project registry {task_slug: {project_id, skill, updated_at}}."""
    try:
        if OD_REGISTRY.exists():
            return json.loads(OD_REGISTRY.read_text())
    except Exception:
        pass
    return {}


def _registry_save(reg: dict):
    OD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OD_REGISTRY.write_text(json.dumps(reg, indent=2))


def _registry_get(task_slug: str) -> str:
    """Return existing project_id for this task slug, or empty string."""
    reg = _registry_load()
    entry = reg.get(task_slug, {})
    pid = entry.get("project_id", "")
    # Verify the project still exists in the OD daemon
    if pid:
        try:
            _od_api("GET", f"/api/projects/{pid}")
            return pid
        except Exception:
            pass
    return ""


def _registry_set(task_slug: str, project_id: str, skill: str):
    import time as _time
    reg = _registry_load()
    reg[task_slug] = {
        "project_id": project_id,
        "skill": skill,
        "updated_at": int(_time.time()),
    }
    _registry_save(reg)


def _od_api(method: str, path: str, body: dict = None) -> dict:
    """Make a request to the OD daemon API."""
    url = f"{OD_DAEMON_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"OD API {method} {path} → HTTP {e.code}: {body_text}")


def opendesign_run(
    task_type: str,
    prompt: str,
    skill: str = "",
    project_id: str = "",
    output_dir: str = "",
    timeout_seconds: int = 300,
) -> dict:
    """
    Run an OpenDesign task via the local daemon using Hermes as the agent.

    task_type: infographic|dashboard|web|ui|landing|mobile|deck|slides|social|image|poster|
               video|animation|wireframe|svg|blog|email|docs|report|kanban|invoice|okrs
    prompt:    What to create (be specific — dimensions, brand colors, content, tone)
    skill:     Override OD skill ID (optional, auto-mapped from task_type if blank)
    project_id: Reuse an existing project (optional, creates new if blank)
    output_dir: Copy output files here (optional)
    timeout_seconds: Max wait time for the run (default 300s)

    Returns {success, files, project_id, skill_used, nim_model, project_dir, error?}

    NIM model routing (what Hermes uses internally per task):
      infographic/dashboard/chart/report → nvidia/llama-3.3-nemotron-super-49b-v1
      svg/animation                      → qwen/qwen3-coder-480b-a35b-instruct
      web/ui/landing/deck/mobile/visual  → qwen/qwen3-next-80b-a3b-instruct (default)
    """
    import time, uuid as _uuid

    # 1. Ensure daemon is running
    if not _od_is_running():
        start_result = _od_start_daemon()
        if not start_result["ok"]:
            return {"success": False, "error": f"Could not start OD daemon: {start_result.get('error')}"}
    # Also ensure proxy is running (start lazily if daemon was already up)
    if not _od_proxy_is_running():
        _od_start_proxy()
        _od_configure_media_nim()

    # 2. Resolve skill
    task_key = task_type.lower().strip()
    skill_id = skill or OD_TASK_SKILL.get(task_key, "web-prototype")
    nim_model = OD_TASK_MODEL.get(task_key, "qwen/qwen3-next-80b-a3b-instruct")

    # 3. Create or reuse project — check registry first for continuity
    if not project_id:
        project_id = _registry_get(task_key)

    if not project_id:
        pid = f"riri-{task_key}-{str(_uuid.uuid4())[:8]}"
        proj_name = f"RiRi — {task_type.title()}"
        proj = _od_api("POST", "/api/projects", {
            "id": pid,
            "name": proj_name,
            "skillId": skill_id,
        })
        project_id = proj.get("id", pid)
        _registry_set(task_key, project_id, skill_id)
    else:
        # Verify project exists
        try:
            _od_api("GET", f"/api/projects/{project_id}")
        except Exception as e:
            # Registry stale — create fresh
            project_id = ""
            pid = f"riri-{task_key}-{str(_uuid.uuid4())[:8]}"
            proj = _od_api("POST", "/api/projects", {
                "id": pid, "name": f"RiRi — {task_type.title()}", "skillId": skill_id,
            })
            project_id = proj.get("id", pid)
            _registry_set(task_key, project_id, skill_id)

    # 4. Get conversation ID
    convs = _od_api("GET", f"/api/projects/{project_id}/conversations")
    conv_list = convs.get("conversations", [])
    if not conv_list:
        return {"success": False, "error": f"No conversations found in project {project_id}"}
    conversation_id = conv_list[0]["id"]

    # 5. Submit run
    run_body = {
        "agentId": "hermes",
        "message": prompt,
        "projectId": project_id,
        "conversationId": conversation_id,
        "skillId": skill_id,
    }
    run_resp = _od_api("POST", "/api/runs", run_body)
    run_id = run_resp.get("runId")
    if not run_id:
        return {"success": False, "error": f"No runId in response: {run_resp}"}

    # 6. Poll for completion
    deadline = time.time() + timeout_seconds
    status = "running"
    while time.time() < deadline:
        run_status = _od_api("GET", f"/api/runs/{run_id}")
        status = run_status.get("status", "running")
        if status in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(2)

    if status not in ("succeeded", "failed", "cancelled"):
        return {
            "success": False,
            "error": f"Run timed out after {timeout_seconds}s (last status: {status})",
            "run_id": run_id,
            "project_id": project_id,
        }

    if status == "failed":
        run_status = _od_api("GET", f"/api/runs/{run_id}")
        return {
            "success": False,
            "error": f"Run failed: {run_status.get('error', 'unknown error')}",
            "run_id": run_id,
            "project_id": project_id,
            "skill_used": skill_id,
        }

    # 7. Find output files
    project_dir = OD_DATA_DIR / "projects" / project_id
    output_files = []

    # Check API files endpoint
    try:
        files_resp = _od_api("GET", f"/api/projects/{project_id}/files")
        api_files = files_resp.get("files", [])
        for f in api_files:
            fname = f.get("name", "")
            fpath = project_dir / fname
            if fpath.exists():
                output_files.append(str(fpath))
    except Exception:
        pass

    # Also scan project dir directly for HTML files
    if project_dir.exists():
        for fpath in sorted(project_dir.glob("*.html")):
            if str(fpath) not in output_files:
                output_files.append(str(fpath))
        # Index.html is the primary output
        index = project_dir / "index.html"
        if index.exists() and str(index) not in output_files:
            output_files.insert(0, str(index))

    # 8. Copy to output_dir if requested
    if output_dir and output_files:
        import shutil
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        copied = []
        for f in output_files:
            dest = out_path / Path(f).name
            shutil.copy2(f, dest)
            copied.append(str(dest))
        output_files = copied

    # Keep registry fresh with latest project_id
    _registry_set(task_key, project_id, skill_id)

    return {
        "success": True,
        "files": output_files,
        "project_id": project_id,
        "project_dir": str(project_dir),
        "run_id": run_id,
        "skill_used": skill_id,
        "nim_model": nim_model,
        "status": status,
    }


def nim_generate_image(
    prompt: str,
    model: str = "black-forest-labs/flux.1-schnell",
    width: int = 1024,
    height: int = 1024,
    steps: int = 4,
    output_path: str = ""
) -> dict:
    """Generate an image via NIM FLUX API and save it to disk.
    
    Available models: black-forest-labs/flux.1-schnell (fast), black-forest-labs/flux.1-dev (quality),
                      black-forest-labs/flux.1-kontext-dev (image editing).
    Valid sizes: 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344 (width and height independently).
    Steps: 4 for schnell (fast), 20-30 for dev (quality).
    """
    import os, base64, urllib.request, json as _json, time
    from pathlib import Path

    NIM_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
    if not NIM_API_KEY:
        return {"success": False, "error": "NVIDIA_API_KEY not set"}

    # Clamp dimensions to valid NIM values
    VALID_DIMS = [768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344]
    width = min(VALID_DIMS, key=lambda x: abs(x - width))
    height = min(VALID_DIMS, key=lambda x: abs(x - height))

    endpoint = f"https://ai.api.nvidia.com/v1/genai/{model}"
    payload = _json.dumps({
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": 0 if "schnell" in model else 3.5,
        "seed": 0,
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {NIM_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "riri-tools/1.0",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = _json.load(r)
    except Exception as e:
        return {"success": False, "error": str(e)}

    if "artifacts" not in data:
        return {"success": False, "error": f"Unexpected response: {list(data.keys())}"}

    img_b64 = data["artifacts"][0]["base64"]
    img_bytes = base64.b64decode(img_b64)

    if not output_path:
        output_dir = Path.home() / "projects/riri/output/images"
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        output_path = str(output_dir / f"nim_image_{ts}.png")

    with open(output_path, "wb") as f:
        f.write(img_bytes)

    return {
        "success": True,
        "path": output_path,
        "model": model,
        "width": width,
        "height": height,
        "size_bytes": len(img_bytes),
    }


# ── MCP Server ────────────────────────────────────────────────────────────────

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("riri-tools")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="linkedin_post",
            description="Publish a text post to Ahmed's LinkedIn. Returns the real post URL. Use this instead of bash. Never fake a URL — only use the url field from the result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Post content (150-220 words, first-person, builder tone)"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="linkedin_delete",
            description="Delete a LinkedIn post by URN (e.g. urn:li:share:...).",
            inputSchema={
                "type": "object",
                "properties": {
                    "urn": {"type": "string", "description": "The post URN to delete"}
                },
                "required": ["urn"]
            }
        ),
        Tool(
            name="hyperframes_render",
            description="Create an animated MP4 infographic from an HTML composition using HyperFrames. Handles project setup, lint, render, and verification automatically. Returns the file path on success.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug":         {"type": "string",  "description": "Filename slug, e.g. 'linkedin-post-1'"},
                    "html_content": {"type": "string",  "description": "Complete index.html content using HyperFrames structure (data-composition-id, class=clip, window.__timelines object)"},
                    "duration":     {"type": "integer", "description": "Video duration in seconds (default 4)", "default": 4},
                    "fps":          {"type": "integer", "description": "Frame rate (default 30)", "default": 30}
                },
                "required": ["slug", "html_content"]
            }
        ),
        Tool(
            name="nim_infer",
            description=(
                "Call a specialist NIM model directly for a subtask. "
                "Use when the primary model isn't optimal:\n"
                "• qwen/qwen3-coder-480b-a35b-instruct → complex code, architecture, debugging\n"
                "• nvidia/nemotron-3-super-120b-a12b → deep reasoning, multi-step analysis\n"
                "• nvidia/nemotron-3-nano-omni-30b-a3b-reasoning → structured step-by-step thinking\n"
                "• qwen/qwen3.5-122b-a10b → long-form quality content writing\n"
                "• moonshotai/kimi-k2-instruct → very long context tasks (1M tokens)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model":       {"type": "string", "description": "Full NIM model ID (e.g. qwen/qwen3-coder-480b-a35b-instruct)"},
                    "prompt":      {"type": "string", "description": "User message / task"},
                    "system":      {"type": "string", "description": "Optional system prompt", "default": ""},
                    "max_tokens":  {"type": "integer", "description": "Max output tokens (default 1500)", "default": 1500},
                    "temperature": {"type": "number",  "description": "Temperature 0-1 (default 0.3)", "default": 0.3},
                },
                "required": ["model", "prompt"]
            }
        ),
        Tool(
            name="riri_status",
            description="Get full system status: gateway health, WhatsApp/Discord state, last message timestamps, active model, LanceDB/Qdrant/Ollama state. Call this when Ahmed asks '/status', 'what are you doing', 'are you running', or any system health question.",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="riri_notify",
            description="Send Ahmed a proactive WhatsApp message. Use for: task completion, errors, approval requests, progress updates. Never go silent on async tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type":    {"type": "string", "enum": ["done", "error", "approval", "update"], "description": "Message type"},
                    "message": {"type": "string", "description": "The message to send"}
                },
                "required": ["type", "message"]
            }
        ),
        Tool(
            name="riri_memory_context",
            description="Fetch recent memory summaries of Ahmed's work sessions. Use on cold-start or when needing context about past work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_chars": {"type": "integer", "description": "Max characters to return (default 3000)", "default": 3000}
                }
            }
        ),
        Tool(
            name="mem0_recall",
            description=(
                "Search structured memory for facts relevant to a query. "
                "Use this at the start of any task to recall what happened before — "
                "e.g. 'LinkedIn posts this week', 'Ahmed preferences', 'last HyperFrames render'. "
                "Returns a context_block ready to use."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in memory"},
                    "limit": {"type": "integer", "description": "Max memories to return (default 8)", "default": 8}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="mem0_store",
            description=(
                "Store new facts into structured memory. "
                "Call this after completing tasks — posts published, decisions made, preferences noted. "
                "Mem0 extracts discrete facts automatically from natural language."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Conversation summary or fact statement to ingest"}
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="opendesign_run",
            description=(
                "Run an OpenDesign visual task using Hermes as the agent. "
                "USE THIS whenever Ahmed asks for: infographics, dashboards, UI prototypes, landing pages, "
                "mobile apps, slide decks, presentations, social carousels, posters, SVGs, "
                "HTML animations, wireframes, or any visual design asset. "
                "OpenDesign is purpose-built for visual output — always prefer it over hand-coding HTML for design work. "
                "task_type options: infographic|dashboard|data-viz|chart|report|web|ui|prototype|app|landing|saas|"
                "mobile|deck|slides|presentation|pitch|social|image|poster|visual|svg|wireframe|"
                "video|animation|frames|blog|email|docs|invoice|okrs|kanban|magazine|waitlist|pricing\n"
                "NIM model used internally by skill:\n"
                "  infographic/dashboard/chart/report → nemotron-super-49b (reasoning + data)\n"
                "  svg/animation                      → qwen3-coder-480b (code-heavy)\n"
                "  web/ui/landing/deck/mobile/visual  → qwen3-next-80b (primary design model)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "Type of design task. Maps to OpenDesign skill. Examples: 'infographic', 'landing', 'deck', 'social', 'wireframe', 'video', 'svg'"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of what to create. Include: content, style, colors, dimensions, target audience, tone. Be specific."
                    },
                    "skill": {
                        "type": "string",
                        "description": "Override the OpenDesign skill ID directly (optional). Leave blank to auto-map from task_type.",
                        "default": ""
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Reuse an existing project ID to continue/iterate on a design (optional).",
                        "default": ""
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Copy output files to this directory (optional). Default: files stay in OD project dir.",
                        "default": ""
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Max wait time in seconds (default 300). Increase for complex visual tasks.",
                        "default": 300
                    },
                },
                "required": ["task_type", "prompt"]
            }
        ),
        Tool(
            name="nim_generate_image",
            description=(
                "Generate an image using NIM FLUX API and save it to disk. "
                "Use for: UI mockups, illustrations, icons, design assets, or any visual content Ahmed needs. "
                "Models: 'black-forest-labs/flux.1-schnell' (fast, 4 steps), "
                "'black-forest-labs/flux.1-dev' (quality, 20+ steps), "
                "'black-forest-labs/flux.1-kontext-dev' (image editing). "
                "Returns the file path of the saved image."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Detailed image description"},
                    "model": {
                        "type": "string",
                        "description": "NIM model ID (default: flux.1-schnell)",
                        "default": "black-forest-labs/flux.1-schnell"
                    },
                    "width": {"type": "integer", "description": "Width in px (768-1344, default 1024)", "default": 1024},
                    "height": {"type": "integer", "description": "Height in px (768-1344, default 1024)", "default": 1024},
                    "steps": {"type": "integer", "description": "Inference steps (4 for schnell, 20 for dev)", "default": 4},
                    "output_path": {"type": "string", "description": "Optional custom save path", "default": ""},
                },
                "required": ["prompt"]
            }
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "linkedin_post":
        result = linkedin_post(arguments["text"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "linkedin_delete":
        result = linkedin_delete(arguments["urn"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "hyperframes_render":
        result = hyperframes_render(
            slug=arguments["slug"],
            html_content=arguments["html_content"],
            duration=int(arguments.get("duration", 4)),
            fps=int(arguments.get("fps", 30)),
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "nim_infer":
        result = nim_infer(
            model=arguments["model"],
            prompt=arguments["prompt"],
            system=arguments.get("system", ""),
            max_tokens=int(arguments.get("max_tokens", 1500)),
            temperature=float(arguments.get("temperature", 0.3)),
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "riri_status":
        text = riri_status()
        return [TextContent(type="text", text=text)]

    elif name == "riri_notify":
        result = riri_notify(arguments["type"], arguments["message"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "riri_memory_context":
        text = riri_memory_context(int(arguments.get("max_chars", 3000)))
        return [TextContent(type="text", text=text)]

    elif name == "mem0_recall":
        result = mem0_recall(arguments["query"], int(arguments.get("limit", 8)))
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "mem0_store":
        result = mem0_store(arguments["text"])
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "opendesign_run":
        result = opendesign_run(
            task_type=arguments["task_type"],
            prompt=arguments["prompt"],
            skill=arguments.get("skill", ""),
            project_id=arguments.get("project_id", ""),
            output_dir=arguments.get("output_dir", ""),
            timeout_seconds=int(arguments.get("timeout_seconds", 300)),
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "nim_generate_image":
        result = nim_generate_image(
            arguments["prompt"],
            arguments.get("model", "black-forest-labs/flux.1-schnell"),
            int(arguments.get("width", 1024)),
            int(arguments.get("height", 1024)),
            int(arguments.get("steps", 4)),
            arguments.get("output_path", ""),
        )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
