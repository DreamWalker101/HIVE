#!/usr/bin/env python3
"""
pipeline_intake.py — RiRi's conversational pipeline integration.

Wraps the claude-pipeline's triage + fetch logic so RiRi can process
URLs or raw text sent through any channel (Discord, WhatsApp, etc.)
without running the full cron pipeline.

Flow:
  1. fetch_content(url_or_text)  → raw transcript text
  2. triage(transcript, note)    → {score, category, reason}
  3. RiRi (NIM) does synthesis   → insight markdown content
  4. write_insight(content, cat) → writes to ~/claude-powers/<cat>/
  5. index_insight(filepath)     → ChromaDB via embed_and_index.py

Usage from RiRi / skill:
  python3 ~/projects/riri/pipeline_intake.py <url_or_text> [--note "..."] [--dry-run]
"""

import sys
import os
import json
import re
import subprocess
import argparse
from datetime import date
from pathlib import Path

# Reuse the existing pipeline's triage and blog scraper
PIPELINE_DIR = Path.home() / "projects" / "claude-pipeline"
KB_PATH      = Path.home() / "claude-powers"
IDEAS_PATH   = Path.home() / "ahmed-ideas"
CHROMA_SCRIPT = PIPELINE_DIR / "embed_and_index.py"

sys.path.insert(0, str(PIPELINE_DIR))


# ── Content fetch ──────────────────────────────────────────────────

def _is_url(text: str) -> bool:
    return bool(re.match(r"https?://", text.strip()))


def fetch_content(url_or_text: str) -> dict:
    """
    Returns {"transcript": str, "media_type": str, "source": str}
    media_type: "blog" | "text" | "unsupported"
    """
    text = url_or_text.strip()

    if not _is_url(text):
        # Raw text / paste — use directly
        return {"transcript": text, "media_type": "text", "source": "(direct input)"}

    url = text

    # Try blog scraper first (handles most articles)
    try:
        from blog_scraper import is_blog_url
        if is_blog_url(url):
            result = subprocess.run(
                [sys.executable, str(PIPELINE_DIR / "blog_scraper.py"), url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return {"transcript": result.stdout.strip(), "media_type": "blog", "source": url}
    except Exception:
        pass

    # Fallback: trafilatura directly
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text_content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            if text_content and len(text_content.split()) > 30:
                return {"transcript": text_content, "media_type": "blog", "source": url}
    except ImportError:
        pass

    # Last fallback: curl
    try:
        r = subprocess.run(
            ["curl", "-sL", "--max-time", "15", url],
            capture_output=True, text=True, timeout=20
        )
        if r.returncode == 0 and r.stdout:
            # Strip HTML tags roughly
            clean = re.sub(r"<[^>]+>", " ", r.stdout)
            clean = re.sub(r"\s+", " ", clean).strip()
            if len(clean.split()) > 30:
                return {"transcript": clean[:8000], "media_type": "blog", "source": url}
    except Exception:
        pass

    return {"transcript": "", "media_type": "unsupported", "source": url}


# ── Triage ─────────────────────────────────────────────────────────

def triage(transcript: str, note: str = "") -> dict:
    """
    Score content using Ollama triage.
    Returns {"score": int, "category": str, "reason": str}
    Falls back gracefully if Ollama unavailable.
    """
    try:
        # Write transcript to temp file for triage.py
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(transcript)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, str(PIPELINE_DIR / "triage.py"), tmp_path, note or "(no note)"],
            capture_output=True, text=True, timeout=60
        )
        os.unlink(tmp_path)

        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        pass

    # Fallback: neutral score so RiRi can decide manually
    return {"score": 5, "category": "updates", "reason": "Triage unavailable — manual review"}


# ── Write insight ──────────────────────────────────────────────────

def write_insight(markdown_content: str, category: str, title_slug: str) -> Path:
    """
    Write a synthesised insight markdown file to ~/claude-powers/<category>/.
    Returns the path written.
    """
    if category == "ideas":
        target_dir = IDEAS_PATH / "ideas"
    else:
        target_dir = KB_PATH / category

    target_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    filename = f"{today}_{title_slug}.md"
    filepath = target_dir / filename

    filepath.write_text(markdown_content)
    return filepath


# ── Index to Chroma ────────────────────────────────────────────────

def index_insight(filepath: Path) -> bool:
    """
    Call embed_and_index.py to add the file to ChromaDB.
    Returns True on success.
    """
    if not CHROMA_SCRIPT.exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(CHROMA_SCRIPT), str(filepath)],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


# ── Synthesis prompt builder (for RiRi / NIM to fill) ─────────────

SYNTHESIS_PROMPT = """You are processing content to extract knowledge for Ahmed's personal knowledge base.

SOURCE: {source}
TRIAGE: Category={category}, Score={score}/10, Reason={reason}
DATE: {today}
USER NOTE: {note}

TRANSCRIPT / CONTENT:
{transcript}

YOUR TASKS:

1. FACT-CHECK — identify the 3 most specific claims. For each:
   - Search to verify against official docs, GitHub, or authoritative sources
   - Mark: VERIFIED / UNVERIFIED / INCORRECT

2. EXTRACT INSIGHTS — find 1-3 genuinely actionable, non-obvious insights.
   Skip: promotional content, generic advice, things every developer knows.
   Include: specific patterns, concrete techniques, code, benchmarks, novel workflows.

3. WRITE INSIGHT — produce a markdown file using this exact structure:

---
title: "Full Descriptive Title"
category: {category}
tags: [relevant, tags, here]
confidence: high
source: "{source}"
date_added: {today}
riri_processed: true
---

# Full Descriptive Title

## What Is This
[2-3 sentences explaining the concept]

## Why It Matters
[Why should Ahmed care? What does this enable?]

## How To Use It
[Concrete steps or code. Be specific.]

## Verified Claims
- VERIFIED: [claim] — [source]
- UNVERIFIED: [claim]
- INCORRECT: [wrong claim] → correct: [correction]

## Sources
- {source}

---

After writing, output ONLY the following JSON so the pipeline can save the file:
{{"title_slug": "short-kebab-case-slug", "content": "<full markdown as a single string>"}}
"""


def build_synthesis_prompt(fetch_result: dict, triage_result: dict, note: str) -> str:
    return SYNTHESIS_PROMPT.format(
        source=fetch_result["source"],
        category=triage_result["category"],
        score=triage_result["score"],
        reason=triage_result["reason"],
        today=date.today().isoformat(),
        note=note or "(no note)",
        transcript=fetch_result["transcript"][:6000],
    )


# ── CLI entrypoint ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RiRi pipeline intake")
    parser.add_argument("input", help="URL or raw text to process")
    parser.add_argument("--note", default="", help="Ahmed's note / intent")
    parser.add_argument("--dry-run", action="store_true", help="Triage only, do not write or index")
    parser.add_argument("--threshold", type=int, default=3, help="Minimum score to proceed (default: 3)")
    args = parser.parse_args()

    print(f"[intake] Fetching content...", file=sys.stderr)
    fetch_result = fetch_content(args.input)

    if not fetch_result["transcript"]:
        print(json.dumps({"error": "Could not extract content", "source": fetch_result["source"]}))
        sys.exit(1)

    word_count = len(fetch_result["transcript"].split())
    print(f"[intake] Got {word_count} words ({fetch_result['media_type']}) from {fetch_result['source']}", file=sys.stderr)

    print(f"[intake] Triaging...", file=sys.stderr)
    triage_result = triage(fetch_result["transcript"], args.note)

    output = {
        "source": fetch_result["source"],
        "media_type": fetch_result["media_type"],
        "word_count": word_count,
        "score": triage_result["score"],
        "category": triage_result["category"],
        "reason": triage_result["reason"],
        "passes": triage_result["score"] >= args.threshold,
        "threshold": args.threshold,
        "synthesis_prompt": None,
        "transcript_preview": fetch_result["transcript"][:500],
    }

    if output["passes"] and not args.dry_run:
        output["synthesis_prompt"] = build_synthesis_prompt(fetch_result, triage_result, args.note)

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
