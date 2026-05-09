# TASK: Publish Case Studies — Git + LinkedIn

**Dispatched by**: Claude (plan only — system executes)
**Executed by**: RiRi autonomous task runner
**Priority**: High
**Cost target**: Zero — use gh CLI (local), browser-use (local Chromium), no paid APIs

---

## Phase 1 — Finalise Desktop Folder + Git Repo

### 1a. Ensure Desktop folder is clean and titled correctly
Directory: `~/Desktop/case-studies/`
Required files:
- `README.md` (write this — see spec below)
- `01-riri-overlay.md`
- `02-claude-pipeline.md`
- `03-tool-knowledge-base.md`
- `04-outreach-engine.md`
- `img/01-riri-brain-chain.svg`
- `img/02-pipeline-flow.svg`
- `img/03-tool-kb.svg`

Sync from source:
```bash
rsync -av ~/projects/riri/case-studies/ ~/Desktop/case-studies/
```

### 1b. Write README.md
File: `~/Desktop/case-studies/README.md`

Content spec:
```
# Tavren AI Stack — Case Studies

A collection of technical case studies documenting the AI infrastructure built at
Tavren: an ambient desktop AI assistant, Claude Code pipeline awareness, a semantic
tool knowledge base, and an automated outreach engine.

All systems run locally-first to minimise cloud API costs.

---

## Case Studies

| # | Title | Stack | Status |
|---|-------|-------|--------|
| 1 | [RiRi — Personal AI Overlay](01-riri-overlay.md) | GTK3, Ollama, SQLite, ChromaDB | Live |
| 2 | [Claude Pipeline Awareness](02-claude-pipeline.md) | Python hooks, SQLite, Ollama | Live |
| 3 | [Tool Knowledge Base](03-tool-knowledge-base.md) | ChromaDB, nomic-embed-text | Live |
| 4 | [Outreach Engine](04-outreach-engine.md) | GWS CLI, PostgreSQL, AI copy | Live |

---

## Architecture Overview

These systems form an integrated local-first AI stack:

- **RiRi** sits at the top — a transparent overlay that is always reachable, never intrusive
- **Pipeline awareness** feeds every Claude Code session into RiRi's memory automatically
- **Tool KB** gives RiRi's brain accurate knowledge of every available CLI tool
- **Outreach Engine** is an example of an autonomous business workflow driven by the stack

## Running Locally

All components require:
- Ubuntu 22+ with X11/Wayland compositing
- Ollama running with `gemma3:4b` and `nomic-embed-text` models
- Python 3.11+ with pygobject, chromadb, sqlite3
- `gws` CLI for Google Workspace integration

## Author

Ahmed — [tavren.io](https://tavren.io) · [contact@tavren.io](mailto:contact@tavren.io)
```

### 1c. Init git and push to GitHub
```bash
cd ~/Desktop/case-studies
git init
git add .
git commit -m "feat: initial case studies for Tavren AI stack

Covers RiRi overlay, Claude pipeline awareness, tool knowledge base,
and outreach engine — all running local-first on Ubuntu 22."

# Create public repo on DreamWalker101's GitHub
gh repo create DreamWalker101/tavren-ai-case-studies \
  --public \
  --description "Technical case studies: RiRi AI overlay, Claude pipeline, tool KB, outreach engine" \
  --source . \
  --push
```

If repo already exists, just push:
```bash
git remote add origin https://github.com/DreamWalker101/tavren-ai-case-studies.git 2>/dev/null || true
git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null
```

---

## Phase 2 — LinkedIn Post via Visible Browser

### Post content (copy this exactly)
```
Built an ambient local-first AI stack over the last few weeks. Here's what's running:

🧠 RiRi — a transparent AI overlay that lives at the top of the screen. Invisible at idle, appears on hover. 4-tier brain fallback: local Ollama → Gemini CLI → Groq → OpenAI, so ~95% of queries are free.

📡 Claude Code Pipeline Awareness — hooks into every Claude Code session. When a session ends, a local model distills what was built, what was fixed, and what's still todo — all queryable via natural language.

🗂️ Tool Knowledge Base — ChromaDB + nomic-embed-text semantic index of all CLI tools. When RiRi gets a task, it looks up the right tool automatically. No more hallucinated commands.

📧 Outreach Engine — automated personalised cold outreach via real Gmail (OAuth, not SMTP). AI-generated copy per lead, full status tracking.

All of this runs on a single Ubuntu workstation. The goal was maximum capability at minimum cloud spend — and it mostly works.

Case studies: https://github.com/DreamWalker101/tavren-ai-case-studies

#AI #LocalAI #BuildInPublic #Automation #Python
```

### Browser automation — HEADFUL (visible to Ahmed)
Use Python + selenium or browser-use with `DISPLAY=:1` (not headless).

Script approach: Launch Google Chrome in app mode pointing at LinkedIn, navigate to post creation, paste the content, submit.

```bash
DISPLAY=:1 python3 ~/projects/riri/tasks/linkedin-post.py
```

The linkedin-post.py script:
- Opens Chrome headfully (Ahmed can see it)
- Goes to https://www.linkedin.com/feed/
- If not logged in: wait up to 120 seconds (Ahmed logs in manually in the visible window)
- Find "Start a post" button → click
- Paste the post content
- Find "Post" button → click
- Take screenshot → save to ~/Desktop/case-studies/linkedin-screenshot.png
- Notify RiRi: "LinkedIn post published ✓"

---

## Phase 3 — Final Sync + Notification

```bash
# Make sure Desktop folder is final
rsync -av ~/projects/riri/case-studies/ ~/Desktop/case-studies/

# Add LinkedIn screenshot to git if it was captured
cd ~/Desktop/case-studies
git add linkedin-screenshot.png 2>/dev/null || true
git commit -m "docs: add LinkedIn publish screenshot" 2>/dev/null || true
git push 2>/dev/null || true

# Notify RiRi
python3 ~/projects/riri/notify.py "Case studies published to GitHub + LinkedIn ✓"
```

---

## EXECUTION NOTES

- **Cost**: zero — gh CLI (local auth), Chrome (local), no LLM calls needed for this task
- **Browser**: MUST be headful (`DISPLAY=:1`) — Ahmed watches the LinkedIn step
- **If LinkedIn fails**: save the post content to `~/Desktop/linkedin-post-draft.txt` and notify RiRi
- **Git**: repo name = `tavren-ai-case-studies`, visibility = public
- **Do NOT use `--headless`** anywhere in the browser script
