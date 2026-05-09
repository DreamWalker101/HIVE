#!/usr/bin/env python3
"""
RiRi Evolution Engine
─────────────────────
Two observer agents analyse RiRi's recent behaviour from different angles.
They cross-critique each other. A synthesiser produces an improvement plan.
The plan is staged and sent to Ahmed via Discord for approval — nothing is
applied automatically.

Usage:
  python3 ~/projects/riri/evolve.py              # run full evolution cycle
  python3 ~/projects/riri/evolve.py --dry-run    # just print, don't DM
  python3 ~/projects/riri/evolve.py --apply <id> # apply an approved plan

Triggered by:
  - Discord: "riri evolve" or "riri review yourself"
  - Cron: nightly at 2am
  - Manual: python3 ~/projects/riri/evolve.py
"""

import argparse
import json
import os
import re
import sqlite3
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
HOME         = Path.home()
SECRETS_ENV  = HOME / ".nanobot/secrets.env"
PIPELINE_DB  = HOME / ".local/share/riri/pipeline.db"
AGENTS_MD    = HOME / ".openclaw/workspace/AGENTS.md"
MEMORY_DIR   = HOME / ".riri/memory"
PLANS_DIR    = HOME / ".riri/evolution-plans"
AUDIT_LOG    = HOME / ".riri/audit.log"
CONVO_LOG    = HOME / ".claude/conversation-log.md"
PLANS_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# ── Env ────────────────────────────────────────────────────────────────────────
def _load_env():
    if SECRETS_ENV.exists():
        for line in SECRETS_ENV.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()


# ── LLM calls ─────────────────────────────────────────────────────────────────
def _call_nim(system: str, user: str, model: str = "meta/llama-3.3-70b-instruct") -> str:
    key = os.getenv("NVIDIA_API_KEY", "")
    if not key:
        raise RuntimeError("NVIDIA_API_KEY missing")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "temperature": 0.4,
        "max_tokens": 1200,
    }).encode()
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def _call_groq(system: str, user: str) -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    body = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user}
        ],
        "temperature": 0.4,
        "max_tokens": 1200,
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def _llm(system: str, user: str, model: str = "nim") -> str:
    """Call best available LLM — NIM primary, NIM fallback model secondary."""
    # Determine which NIM model to use
    nim_model = "meta/llama-3.3-70b-instruct"
    if model and model not in ("nim", "groq") and not model.startswith("nim/"):
        nim_model = model  # e.g. "qwen/qwen2.5-72b-instruct"

    try:
        return _call_nim(system, user, model=nim_model)
    except Exception as e:
        print(f"  [NIM/{nim_model} failed: {e}] → trying fallback NIM model")

    # Fallback: try the other NIM model
    fallback_model = ("qwen/qwen2.5-72b-instruct"
                      if nim_model == "meta/llama-3.3-70b-instruct"
                      else "meta/llama-3.3-70b-instruct")
    try:
        return _call_nim(system, user, model=fallback_model)
    except Exception as e:
        raise RuntimeError(f"All LLMs failed: {e}")


# ── Data gathering ─────────────────────────────────────────────────────────────
def _gather_context(days: int = 3) -> str:
    """Pull recent session data, audit log tail, and memory notes."""
    parts = []

    # Pipeline sessions
    if PIPELINE_DB.exists():
        try:
            cutoff = time.time() - days * 86400
            conn = sqlite3.connect(str(PIPELINE_DB))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT project, summary, turn_count, files_changed, errors, "
                "ended_at, started_at FROM sessions "
                "WHERE COALESCE(ended_at, started_at) > ? "
                "ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 20",
                (cutoff,)
            ).fetchall()
            conn.close()
            if rows:
                lines = [f"RECENT CLAUDE SESSIONS (last {days} days):"]
                for r in rows:
                    ts   = datetime.fromtimestamp(r["ended_at"] or r["started_at"]).strftime("%m/%d %H:%M")
                    proj = r["project"] or "?"
                    summ = (r["summary"] or "in progress")[:120]
                    n_f  = len(json.loads(r["files_changed"] or "[]"))
                    n_err= len(json.loads(r["errors"] or "[]"))
                    lines.append(f"[{ts}] {proj} — {r['turn_count']} turns / {n_f} files / {n_err} errors: {summ}")
                parts.append("\n".join(lines))
        except Exception as e:
            parts.append(f"(pipeline DB error: {e})")

    # Recent audit log (RiRi's own actions)
    if AUDIT_LOG.exists():
        tail = AUDIT_LOG.read_text(errors="ignore").splitlines()[-50:]
        if tail:
            parts.append("RIRI'S RECENT TOOL CALLS (audit log tail):\n" + "\n".join(tail))

    # Recent memory notes
    mem_files = sorted(MEMORY_DIR.glob("*.md"))[-5:]
    if mem_files:
        notes = []
        for f in mem_files:
            notes.append(f"=== {f.name} ===\n" + f.read_text(errors="ignore")[:400])
        parts.append("RIRI'S RECENT MEMORY NOTES:\n" + "\n\n".join(notes))

    # Conversation log tail (if exists)
    if CONVO_LOG.exists():
        tail = CONVO_LOG.read_text(errors="ignore").splitlines()[-80:]
        if tail:
            parts.append("RECENT DISCORD CONVERSATION LOG (tail):\n" + "\n".join(tail))

    return "\n\n" + ("=" * 60) + "\n\n".join(parts) if parts else "(no recent data available)"


# ── Observer A: Engineer lens ──────────────────────────────────────────────────
OBSERVER_A_SYSTEM = """You are Observer A — the Engineering Critic for RiRi, an AI personal assistant.

Your job: analyse RiRi's recent session data from a TECHNICAL perspective.
Look for: tool failures, repeated errors, slow workflows, missing capabilities, inefficient patterns.

Output format (use exactly these headers):
STRENGTHS:
- bullet points of what's working technically

WEAKNESSES:
- bullet points of technical failures, errors, inefficiencies

MISSING CAPABILITIES:
- things RiRi tried but couldn't do, or should be able to do but can't

IMPROVEMENT SUGGESTIONS:
- specific, actionable technical fixes (max 5, ranked by impact)

Be honest, specific, and ruthless. No fluff."""


OBSERVER_B_SYSTEM = """You are Observer B — the User Experience Critic for RiRi, an AI personal assistant.

Your job: analyse RiRi's recent session data from AHMED'S perspective.
Look for: gaps between what Ahmed asked for vs what he got, communication issues, tasks that felt clunky, things Ahmed kept repeating, missed opportunities to be more helpful.

Output format (use exactly these headers):
WHAT WORKED FOR AHMED:
- bullet points

WHAT FRUSTRATED AHMED (or would have):
- bullet points of UX failures, communication gaps, missed intent

PATTERNS IN AHMED'S REQUESTS:
- recurring themes, what Ahmed actually cares about

IMPROVEMENT SUGGESTIONS:
- specific changes to RiRi's behaviour, personality, or skills (max 5, ranked by impact)

Be honest and specific. Think from Ahmed's point of view, not the machine's."""


# ── Cross-critique ─────────────────────────────────────────────────────────────
CRITIQUE_A_SYSTEM = """You are Observer A reviewing Observer B's UX critique of RiRi.

You're a technical engineer. Your job is to challenge B's suggestions:
- Which UX suggestions are technically infeasible or risky?
- Where is B wrong or missing technical context?
- Which of B's suggestions are actually good and you'd endorse?
- What did B miss?

Be concise and direct. Format:
CHALLENGES TO B:
- points where you disagree and why

ENDORSEMENTS:
- B's suggestions you agree are valid

ADDITIONS:
- things B missed that matter"""


CRITIQUE_B_SYSTEM = """You are Observer B reviewing Observer A's technical critique of RiRi.

You're a UX/user advocate. Your job is to challenge A's suggestions:
- Which technical fixes would actually hurt the user experience?
- Where is A solving the wrong problem?
- Which of A's suggestions are genuinely good and user-beneficial?
- What did A miss about what Ahmed actually wants?

Be concise and direct. Format:
CHALLENGES TO A:
- points where you disagree and why

ENDORSEMENTS:
- A's suggestions you agree are valid and user-beneficial

ADDITIONS:
- things A missed that matter for Ahmed"""


# ── Synthesiser ───────────────────────────────────────────────────────────────
SYNTHESISER_SYSTEM = """You are the RiRi Improvement Synthesiser.

You receive: two independent critiques (A=technical, B=UX), plus their cross-critiques of each other.
Your job: produce a concrete, prioritised improvement plan for RiRi.

Rules:
- Only include changes that both observers (or their cross-critiques) agree on, OR changes with very high impact
- Be specific: "add X tool" not "improve capabilities"
- Flag HIGH/MEDIUM/LOW impact for each item
- For AGENTS.md changes: write the exact text to add/replace
- For code changes: describe specifically what file and what to change
- For skill additions: describe the skill

Output format:
IMPROVEMENT PLAN — [date]
Overall assessment: [one sentence on RiRi's current state]

PROPOSED CHANGES:
1. [HIGH/MEDIUM/LOW] Title
   What: specific change
   Why: reason from the critiques
   Where: AGENTS.md / evolve.py / skill file / openclaw.json / etc.

(up to 6 changes, ranked by impact)

WHAT'S WORKING — DON'T TOUCH:
- list things both observers said are working fine

DEFERRED (good ideas but not now):
- list suggestions that need more thought"""


def run_evolution(dry_run: bool = False) -> dict:
    """Run the full evolution cycle. Returns the plan dict."""
    print("🔍 Gathering RiRi's recent session data...")
    context = _gather_context(days=3)

    print("🅰  Observer A (Engineering lens) analysing...")
    obs_a = _llm(OBSERVER_A_SYSTEM, f"Analyse this data:\n{context}", model="nim")

    # Observer B uses a different NIM model for genuine diversity of perspective
    print("🅱  Observer B (User lens) analysing...")
    obs_b = _llm(OBSERVER_B_SYSTEM, f"Analyse this data:\n{context}",
                 model="qwen/qwen2.5-72b-instruct")

    print("🔄 Cross-critique: A reviews B...")
    cross_a = _llm(
        CRITIQUE_A_SYSTEM,
        f"Observer B's critique:\n{obs_b}\n\nOriginal data:\n{context[:1000]}",
        model="nim"
    )

    print("🔄 Cross-critique: B reviews A...")
    cross_b = _llm(
        CRITIQUE_B_SYSTEM,
        f"Observer A's critique:\n{obs_a}\n\nOriginal data:\n{context[:1000]}",
        model="qwen/qwen2.5-72b-instruct"
    )

    print("⚗️  Synthesising improvement plan...")
    synthesis_input = f"""OBSERVER A (Technical):
{obs_a}

OBSERVER B (UX/User):
{obs_b}

A's CROSS-CRITIQUE OF B:
{cross_a}

B's CROSS-CRITIQUE OF A:
{cross_b}"""

    plan_text = _llm(SYNTHESISER_SYSTEM, synthesis_input, model="nim")

    # Save the plan
    plan_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    plan = {
        "id":          plan_id,
        "created_at":  datetime.now().isoformat(),
        "status":      "pending_approval",
        "observer_a":  obs_a,
        "observer_b":  obs_b,
        "cross_a":     cross_a,
        "cross_b":     cross_b,
        "plan":        plan_text,
    }

    plan_file = PLANS_DIR / f"plan-{plan_id}.json"
    plan_file.write_text(json.dumps(plan, indent=2))
    print(f"📋 Plan saved: {plan_file}")

    if not dry_run:
        _notify_discord(plan_id, plan_text)

    return plan


def _notify_discord(plan_id: str, plan_text: str):
    """Send the improvement plan to Ahmed on Discord for approval."""
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    user_id = "622800747347574784"
    if not token:
        print("No DISCORD_BOT_TOKEN — skipping Discord notification")
        return

    # Get DM channel
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me/channels",
            data=json.dumps({"recipient_id": user_id}).encode(),
            headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            channel_id = json.loads(r.read())["id"]
    except Exception as e:
        print(f"Discord DM channel error: {e}")
        return

    # Trim plan to Discord limit
    plan_preview = plan_text[:1600] if len(plan_text) > 1600 else plan_text
    message = (
        f"**RiRi Evolution Plan** `{plan_id}`\n\n"
        f"{plan_preview}\n\n"
        f"---\n"
        f"Reply with:\n"
        f"• `riri apply {plan_id}` — apply all changes\n"
        f"• `riri apply {plan_id} 1,3` — apply only items 1 and 3\n"
        f"• `riri skip {plan_id}` — discard this plan"
    )

    try:
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            data=json.dumps({"content": message}).encode(),
            headers={"Authorization": f"Bot {token}", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10):
            print(f"✅ Plan sent to Ahmed on Discord")
    except Exception as e:
        print(f"Discord send error: {e}")


def apply_plan(plan_id: str, items: list[int] = None):
    """Apply an approved plan (all items or specific numbers)."""
    plan_file = PLANS_DIR / f"plan-{plan_id}.json"
    if not plan_file.exists():
        print(f"Plan {plan_id} not found")
        return

    plan = json.loads(plan_file.read_text())
    plan_text = plan["plan"]

    print(f"📋 Applying plan {plan_id}...")

    # Write to memory as applied
    mem_entry = MEMORY_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(mem_entry, "a") as f:
        f.write(f"\n\n## Evolution Plan Applied — {plan_id}\n")
        f.write(f"Applied at: {datetime.now().isoformat()}\n")
        f.write(f"Items: {items or 'all'}\n\n")
        f.write(plan_text[:500])

    # Update plan status
    plan["status"] = "applied"
    plan["applied_at"] = datetime.now().isoformat()
    plan["applied_items"] = items or "all"
    plan_file.write_text(json.dumps(plan, indent=2))

    # The actual changes are described in plain English in the plan.
    # RiRi (OpenClaw) handles the execution when Ahmed approves via Discord.
    print(f"✅ Plan {plan_id} marked as applied. Memory note written.")
    print("\nPlan content (for RiRi to execute):")
    print(plan_text)


def list_pending():
    """List plans waiting for approval."""
    plans = sorted(PLANS_DIR.glob("plan-*.json"))
    pending = []
    for f in plans:
        try:
            p = json.loads(f.read_text())
            if p.get("status") == "pending_approval":
                pending.append((p["id"], p["created_at"][:16], p["plan"][:100]))
        except Exception:
            pass
    if not pending:
        print("No pending evolution plans.")
    else:
        print(f"{len(pending)} pending plan(s):")
        for pid, created, preview in pending:
            print(f"  {pid} ({created}) — {preview}...")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="RiRi Evolution Engine")
    ap.add_argument("--dry-run",  action="store_true", help="Run but don't DM Ahmed")
    ap.add_argument("--apply",    metavar="PLAN_ID",   help="Apply an approved plan")
    ap.add_argument("--items",    metavar="1,2,3",     help="Apply specific items only")
    ap.add_argument("--list",     action="store_true", help="List pending plans")
    args = ap.parse_args()

    if args.list:
        list_pending()
    elif args.apply:
        items = [int(x) for x in args.items.split(",")] if args.items else None
        apply_plan(args.apply, items)
    else:
        plan = run_evolution(dry_run=args.dry_run)
        print("\n" + "="*60)
        print("IMPROVEMENT PLAN:")
        print("="*60)
        print(plan["plan"])
