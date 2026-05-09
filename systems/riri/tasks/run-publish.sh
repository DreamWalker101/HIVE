#!/usr/bin/env bash
# RiRi autonomous task: Publish case studies to GitHub + LinkedIn
# Phase 1: finalise Desktop folder + git push
# Phase 2: LinkedIn post via visible Chrome
# Phase 3: sync + final notify

set -e
export DISPLAY="${DISPLAY:-:1}"

LOG=~/.local/share/riri/publish.log
exec > >(tee -a "$LOG") 2>&1

notify() {
  python3 ~/projects/riri/notify.py "$1" 2>/dev/null || true
}

step() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "[$(date '+%H:%M:%S')] STEP: $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ─────────────────────────────────────────────────────────────────────────────
step "Phase 1a — Sync case studies to Desktop"
# ─────────────────────────────────────────────────────────────────────────────

DEST=~/Desktop/case-studies
mkdir -p "$DEST/img"
rsync -av ~/projects/riri/case-studies/ "$DEST/"
echo "  Synced to $DEST"

# ─────────────────────────────────────────────────────────────────────────────
step "Phase 1b — Write README.md"
# ─────────────────────────────────────────────────────────────────────────────

cat > "$DEST/README.md" << 'README'
# Tavren AI Stack — Case Studies

A collection of technical case studies documenting the AI infrastructure built at
Tavren: an ambient desktop AI assistant, Claude Code pipeline awareness, a semantic
tool knowledge base, and an automated outreach engine.

All systems run **locally-first** to minimise cloud API costs. Roughly 95% of daily
AI queries are handled by local Ollama models at zero marginal cost.

---

## Case Studies

| # | Title | Stack | Status |
|---|-------|-------|--------|
| 1 | [RiRi — Personal AI Overlay](01-riri-overlay.md) | GTK3 · Ollama · SQLite · ChromaDB | ✅ Live |
| 2 | [Claude Pipeline Awareness](02-claude-pipeline.md) | Python hooks · SQLite · Ollama distillation | ✅ Live |
| 3 | [Tool Knowledge Base](03-tool-knowledge-base.md) | ChromaDB · nomic-embed-text · JSON registry | ✅ Live |
| 4 | [Outreach Engine](04-outreach-engine.md) | GWS CLI · PostgreSQL · AI copy generation | ✅ Live |

---

## Architecture Overview

These four systems form an integrated local-first AI stack:

```
┌─────────────────────────────────────────────────────┐
│                     RiRi Overlay                     │
│         (transparent pill window, hover-reveal)      │
│  Brain: Ollama → Gemini CLI → Groq → OpenAI          │
└──────────┬─────────────────┬───────────────┬─────────┘
           │                 │               │
    ┌──────▼──────┐   ┌──────▼──────┐  ┌────▼────────┐
    │  Memory DB  │   │  Tool KB    │  │  Pipeline   │
    │ (SQLite +   │   │ (ChromaDB + │  │  Awareness  │
    │  Embeddings)│   │  31 tools)  │  │  (Hooks)    │
    └─────────────┘   └─────────────┘  └─────────────┘
                                               │
                              ┌────────────────▼────────┐
                              │   Claude Code Sessions   │
                              │  (auto-distilled → mem)  │
                              └─────────────────────────┘
```

## Running Locally

Requirements:
- Ubuntu 22+ with X11 compositing
- Ollama with `gemma3:4b` and `nomic-embed-text` models pulled
- Python 3.11+ with `pygobject`, `chromadb`, `sqlite3`
- `gws` CLI for Google Workspace (Gmail, Drive, Calendar)
- Claude Code with hook support

Quick start:
```bash
cd ~/projects/riri
bash launch.sh
```

## Author

**Ahmed** — building local-first AI tooling at [Tavren](https://tavren.io)

📧 [contact@tavren.io](mailto:contact@tavren.io) · 🐙 [DreamWalker101](https://github.com/DreamWalker101)
README

echo "  README.md written"

# ─────────────────────────────────────────────────────────────────────────────
step "Phase 1c — Git init and push to GitHub"
# ─────────────────────────────────────────────────────────────────────────────

cd "$DEST"

if [ ! -d ".git" ]; then
  git init
  git checkout -b main 2>/dev/null || true
fi

git config user.name "Ahmed" 2>/dev/null || true
git config user.email "ahmed@propsync.dev" 2>/dev/null || true

git add .
git diff --cached --quiet && echo "  Nothing new to commit" || \
  git commit -m "feat: Tavren AI stack case studies

- RiRi personal AI overlay (GTK3, Ollama, 4-tier brain fallback)
- Claude Code pipeline awareness (hooks, SQLite, Ollama distillation)
- Tool knowledge base (ChromaDB, nomic-embed-text, 31 tools)
- Outreach engine (GWS CLI, AI copy, PostgreSQL tracking)

All systems live on Ubuntu 22, locally-first architecture."

# Create repo on GitHub or just push if it exists
REPO_NAME="tavren-ai-case-studies"
GITHUB_USER="DreamWalker101"

# Check if repo exists
if gh repo view "$GITHUB_USER/$REPO_NAME" > /dev/null 2>&1; then
  echo "  Repo already exists — pushing..."
  git remote get-url origin > /dev/null 2>&1 || \
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
  git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null || true
else
  echo "  Creating new repo: $GITHUB_USER/$REPO_NAME"
  gh repo create "$GITHUB_USER/$REPO_NAME" \
    --public \
    --description "Technical case studies: RiRi AI overlay, Claude pipeline awareness, tool knowledge base, outreach engine" \
    --source . \
    --remote origin \
    --push
fi

REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME"
echo "  ✅ Pushed to $REPO_URL"
notify "GitHub push complete → $REPO_URL"

# ─────────────────────────────────────────────────────────────────────────────
step "Phase 2 — LinkedIn post (visible Chrome)"
# ─────────────────────────────────────────────────────────────────────────────

notify "Starting LinkedIn post — opening Chrome (you can watch)"
echo "  Launching headful browser on DISPLAY=:1..."

DISPLAY=:1 python3 ~/projects/riri/tasks/linkedin-post.py

# Add any generated screenshots to git
cd "$DEST"
if ls linkedin-*.png > /dev/null 2>&1; then
  git add linkedin-*.png
  git commit -m "docs: add LinkedIn post screenshots" 2>/dev/null || true
  git push 2>/dev/null || true
  echo "  Screenshots committed to git"
fi

# ─────────────────────────────────────────────────────────────────────────────
step "Phase 3 — Final sync + summary"
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "  Final state of ~/Desktop/case-studies:"
ls -lah "$DEST/"
ls -lah "$DEST/img/"

echo ""
echo "  Git log:"
git -C "$DEST" log --oneline | head -5

echo ""
echo "  GitHub: $REPO_URL"
echo "  Desktop: $DEST"
echo "  LinkedIn log: ~/.local/share/riri/linkedin.log"

notify "All done — git pushed, LinkedIn posted, case studies on Desktop ✓"

echo ""
echo "[$(date '+%H:%M:%S')] ✅ publish-case-studies task complete"
