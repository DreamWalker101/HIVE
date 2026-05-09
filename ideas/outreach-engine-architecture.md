# Outreach Engine — System Architecture

## What it is
A local-first B2B cold outreach system for Tavren. Discovers leads via Google Places, audits websites via PageSpeed Insights, generates personalised emails via Groq, sends via Zoho SMTP.

## Stack
- FastAPI backend on port 8765
- SQLite database at `data/outreach.db`
- Single-file SPA at `static/index.html` (Tailwind CDN, no build step)
- CLI at `cli.py` for agent/terminal control

## Key files
| File | Purpose |
|---|---|
| `app/main.py` | FastAPI routes + pipeline orchestration |
| `app/database.py` | SQLite schema (runs, businesses, campaigns, settings, contacted_emails) |
| `app/scraper.py` | Google Places lead discovery |
| `app/auditor.py` | PageSpeed Insights audit |
| `app/emailer.py` | Groq email gen + Zoho SMTP |
| `static/index.html` | Dashboard SPA |
| `cli.py` | CLI: status/start/stop/run/leads/stats/set/campaigns |

## Pipeline flow
1. Scrape: Google Places → businesses table
2. Deduplicate: check contacted_emails table
3. Audit: PSI score (research mode only)
4. Generate: Groq → personalised email subject + body
5. Send: Zoho SMTP → mark as sent, record in contacted_emails

## Agents in Paperclip
- **Outreach Operator** (1d2501da) — runs campaigns via CLI
- **Outreach Coder** (0cc4ee58) — implements changes to codebase
- **HR Ops** (1d770c1a) — tracks performance + agent registry

## ChromaDB index
Collection: `codebase` at `/home/ahmed/projects/chroma-db`
166 chunks, 8 files indexed. Re-index after major changes:
```
python3 -c "..." # see claude-powers indexing snippet
```

## Config
All keys in `/home/ahmed/projects/outreach-engine/.env`
- GROQ_API_KEY, GOOGLE_PLACES_API_KEY, GOOGLE_PSI_API_KEY
- ZOHO_EMAIL=hammad@tavren.io, ZOHO_APP_PASSWORD
