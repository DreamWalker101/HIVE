#!/usr/bin/env python3
"""
RiRi Case Study Generator
=========================
Triggered at project completion.  Reads the latest (or named) Claude Code
session from pipeline.db, writes a technical case study via Groq, indexes it
in ChromaDB, and posts a condensed version to LinkedIn.

Usage:
  python3 case_study.py                       # latest session
  python3 case_study.py --project riri        # filter by project name
  python3 case_study.py --no-linkedin         # skip LinkedIn post
  python3 case_study.py --no-chromadb         # skip ChromaDB indexing
  python3 case_study.py --dry-run             # preview only

Hook / programmatic trigger (from Claude Code session):
  touch ~/.riri-project-done                  # Stop hook checks this file
"""

import argparse, json, os, re, sqlite3, subprocess, sys, time
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
PIPELINE_DB  = Path.home() / ".local/share/riri/pipeline.db"
CASE_DIR     = Path.home() / "Desktop/case-studies"
RIRI_DIR     = Path.home() / "projects/riri"
RIRI_INDEX   = Path.home() / ".local/bin/riri-index"
SECRETS_FILE = Path.home() / ".nanobot/secrets.env"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


# ── Env ────────────────────────────────────────────────────────────────────────
def _load_env():
    for f in [SECRETS_FILE, Path.home() / "projects/claude-pipeline/.env"]:
        if f.exists():
            for line in f.read_text(errors="ignore").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()


# ── Pipeline DB ────────────────────────────────────────────────────────────────
def _pconn():
    c = sqlite3.connect(str(PIPELINE_DB), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def get_session(project: str = None) -> dict:
    if not PIPELINE_DB.exists():
        return {}
    with _pconn() as c:
        if project:
            row = c.execute(
                "SELECT * FROM sessions WHERE project LIKE ? "
                "ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 1",
                (f"%{project}%",)
            ).fetchone()
        else:
            row = c.execute(
                "SELECT * FROM sessions "
                "ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 1"
            ).fetchone()
    return dict(row) if row else {}


# ── Context builder ────────────────────────────────────────────────────────────
def build_context(session: dict) -> str:
    """Collect all available context about the session into a prompt string."""
    proj   = session.get("project", "unknown")
    cwd    = session.get("cwd", "")
    summ   = session.get("summary", "")
    files  = json.loads(session.get("files_changed", "[]") or "[]")
    cmds   = json.loads(session.get("cmds_run",     "[]") or "[]")
    errors = json.loads(session.get("errors",        "[]") or "[]")
    turns  = session.get("turn_count", 0)

    parts = [
        f"Project: {proj}",
        f"Directory: {cwd}",
        f"Session turns: {turns}",
    ]
    if summ:
        parts.append(f"What was done: {summ}")
    if files:
        parts.append(f"Files created/changed: {', '.join(files[:25])}")
    if cmds:
        skip = {"ls", "cat", "echo", "pwd", "which", "head", "tail"}
        sig  = [c for c in cmds if c.split()[0] not in skip][:12]
        if sig:
            parts.append("Key commands:\n  " + "\n  ".join(sig))
    if errors:
        parts.append("Errors hit (and fixed):\n  " + "\n  ".join(errors[:5]))

    # Pull in any .md files from the project dir (READMEs, task files, docs)
    if cwd:
        proj_path = Path(cwd)
        if proj_path.exists():
            md_texts = []
            for md in sorted(proj_path.rglob("*.md"))[:6]:
                if md.stat().st_size < 8000:
                    try:
                        txt = md.read_text(errors="ignore")[:1200]
                        md_texts.append(f"\n--- {md.relative_to(proj_path)} ---\n{txt}")
                    except Exception:
                        pass
            if md_texts:
                parts.append("\nProject docs:" + "".join(md_texts))

    return "\n".join(parts)


# ── Groq ───────────────────────────────────────────────────────────────────────
def groq(prompt: str, system: str = "", max_tokens: int = 1800) -> str:
    import urllib.request

    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY not found in secrets.env")

    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})

    body = json.dumps({
        "model":      GROQ_MODEL,
        "messages":   msgs,
        "temperature": 0.65,
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(
        GROQ_URL, data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type":  "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"].strip()


# ── Prompts ────────────────────────────────────────────────────────────────────
_CS_SYSTEM = (
    "You are a senior engineer writing a short technical case study about "
    "a personal project. First person. Specific — mention real file names, "
    "libraries, design decisions. No buzzwords or filler."
)

_CS_PROMPT = """\
Here is context from a Claude Code session. Write a technical case study.

{context}

Structure (use ## headers):
## What I Built
(2-3 sentences — what is it, what does it do)

## The Problem
(What gap or pain point triggered the build)

## Technical Approach
(Architecture, libraries, key design decisions, how pieces fit together)

## Key Implementation Details
(Most important files/functions and why they matter; any tricky problems solved)

## Outcome
(What works now, concrete capabilities, anything that surprised you)

## Lessons Learned
(1-2 specific takeaways from the build)

Keep under 650 words. Be concrete and technical."""

_LI_PROMPT = """\
Turn this case study into a LinkedIn post (max 1200 characters).

{case_study}

Format:
- First line: strong hook — a specific claim or question, no emojis at the start
- 2 sentences of context (the problem + what was built)
- 3-4 bullets (use • ) with the most interesting technical specifics
- One line on outcome or learning
- Last line: 3-4 hashtags only (e.g. #buildinpublic #python #ai #automation)

Tone: confident, technical, like a real engineer sharing work — not a press release."""


# ── Generators ─────────────────────────────────────────────────────────────────
def gen_case_study(context: str) -> str:
    return groq(_CS_PROMPT.format(context=context), system=_CS_SYSTEM, max_tokens=1800)

def gen_linkedin_post(case_study: str) -> str:
    return groq(_LI_PROMPT.format(case_study=case_study), max_tokens=700)


# ── Save + Index ───────────────────────────────────────────────────────────────
def save(proj: str, content: str) -> Path:
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", proj.lower()).strip("-")
    ts   = datetime.now().strftime("%Y%m%d-%H%M")
    path = CASE_DIR / f"{slug}-{ts}.md"
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ Saved → {path}")
    return path

def index_in_chromadb(path: Path):
    if RIRI_INDEX.exists():
        try:
            r = subprocess.run(
                [str(RIRI_INDEX), "--add", str(path)],
                capture_output=True, text=True, timeout=30
            )
            print(f"  ✅ ChromaDB indexed" + (f": {r.stdout.strip()}" if r.stdout.strip() else ""))
        except Exception as e:
            print(f"  ⚠️  ChromaDB: {e}")
    else:
        print("  ℹ️  riri-index not found — skipping ChromaDB")

def post_to_linkedin(text: str) -> bool:
    sys.path.insert(0, str(RIRI_DIR / "agents/linkedin"))
    try:
        from api import post_text
        result = post_text(text)
        if result.get("success"):
            print(f"  ✅ LinkedIn posted: {result.get('urn','')}")
            return True
        else:
            print(f"  ⚠️  LinkedIn API: {result.get('error','')}")
            return False
    except Exception as e:
        print(f"  ⚠️  LinkedIn error: {e}")
        return False


# ── Main pipeline ──────────────────────────────────────────────────────────────
def run(project: str = None, no_linkedin: bool = False,
        no_chromadb: bool = False, dry_run: bool = False) -> bool:

    print(f"\n{'='*55}")
    print(f"  RiRi Case Study Generator")
    print(f"{'='*55}")

    # 1. Load session
    print("🔍  Loading session…")
    session = get_session(project)
    if not session:
        label = f" for '{project}'" if project else ""
        print(f"❌  No session found{label}. Make sure pipeline.db has data.")
        return False

    proj = session.get("project", "unknown")
    ts   = datetime.fromtimestamp(
        session.get("ended_at") or session.get("started_at") or time.time()
    ).strftime("%Y-%m-%d %H:%M")
    print(f"    Project: {proj}  |  {session.get('turn_count',0)} turns  |  ended {ts}")

    # 2. Build context
    context = build_context(session)

    # 3. Generate case study
    print("✍️   Generating case study via Groq…")
    try:
        cs_body = gen_case_study(context)
    except Exception as e:
        print(f"❌  Groq error: {e}")
        return False

    date_str = datetime.now().strftime("%Y-%m-%d")
    full_md  = f"# Case Study: {proj.title()} ({date_str})\n\n{cs_body}\n"

    # 4. Generate LinkedIn post
    li_post = None
    if not no_linkedin:
        print("📝  Generating LinkedIn post…")
        try:
            li_post = gen_linkedin_post(cs_body)
        except Exception as e:
            print(f"⚠️   LinkedIn post gen failed: {e}")

    # 5. Dry-run preview
    if dry_run:
        print(f"\n{'─'*55}")
        print(full_md[:900])
        if li_post:
            print(f"\n{'─'*55}  LinkedIn:")
            print(li_post)
        print(f"{'─'*55}")
        print("  [dry-run] Nothing saved or posted.")
        return True

    # 6. Save
    path = save(proj, full_md)

    # 7. Index in ChromaDB
    if not no_chromadb:
        index_in_chromadb(path)

    # 8. Post to LinkedIn
    if li_post and not no_linkedin:
        print(f"\n  LinkedIn post ({len(li_post)} chars):")
        print(f"  ┌─{'─'*50}")
        for line in li_post.splitlines():
            print(f"  │ {line}")
        print(f"  └─{'─'*50}\n")

        posted = post_to_linkedin(li_post)
        if not posted:
            # Save as draft
            draft = path.with_suffix(".linkedin-draft.txt")
            draft.write_text(li_post, encoding="utf-8")
            print(f"  📄 Draft saved → {draft}")
    elif not no_linkedin and not li_post:
        print("  ⚠️  No LinkedIn post generated.")

    # 9. Toast notification
    notify_msg = f"Case study done: {proj}"
    try:
        subprocess.Popen(
            ["python3", str(RIRI_DIR / "notify.py"), notify_msg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

    print(f"\n  ✅ Done. Case study at: {path.name}")
    return True


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate case study from Claude session")
    ap.add_argument("--project",     default=None,          help="Project name filter")
    ap.add_argument("--no-linkedin", action="store_true",   help="Skip LinkedIn post")
    ap.add_argument("--no-chromadb", action="store_true",   help="Skip ChromaDB index")
    ap.add_argument("--dry-run",     action="store_true",   help="Preview only")
    args = ap.parse_args()

    ok = run(
        project=args.project,
        no_linkedin=args.no_linkedin,
        no_chromadb=args.no_chromadb,
        dry_run=args.dry_run,
    )
    sys.exit(0 if ok else 1)
