---
title: "Karpathy LLM Wiki: Compounding Knowledge Base via Claude Code Instead of RAG"
category: updates
tags: [claude, updates, claude-code, knowledge-base, rag, obsidian, wiki, agentic, knowledge-management]
confidence: high
source_reel: "https://www.instagram.com/reel/DWw08-WEqce/?igsh=MTY4Y3J4YXFhYmZ2ZQ=="
source_platform: instagram
verified_against:
  - "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
  - "https://analyticsindiamag.com/ai-news/andrej-karpathy-moves-beyond-rag-builds-llm-powered-personal-knowledge-bases"
date_added: 2026-04-10
claude_applicable: true
pipeline_run: run/2026-04-10T04-30-10
---

# Karpathy LLM Wiki: Compounding Knowledge Base via Claude Code Instead of RAG

## What Is This
Karpathy's LLM Wiki pattern (published April 4, 2026 as a GitHub gist) replaces RAG pipelines with a persistent, human-readable markdown wiki that an LLM compiles and maintains. Instead of re-embedding documents and re-discovering relationships on every query, you compile raw sources **once** into a structured wiki of backlinked markdown files. Each new source added makes the whole wiki smarter — knowledge compounds rather than resets.

The three components are: **raw sources** (immutable input documents), **wiki** (LLM-generated markdown with backlinks, summaries, entity/concept pages), and **schema** (a CLAUDE.md or AGENTS.md that tells the LLM how to operate on the wiki). There is no "OUTPUT" folder — the wiki itself is the output.

## Why It Matters
RAG has no memory: it re-discovers your knowledge from scratch on every query, so the system never gets smarter. The LLM Wiki flips this: the LLM acts as a research librarian that **authors** a persistent record. Adding source #50 enriches existing wiki pages via backlinks and contradicts/updates what was written from sources #1–49. For Ahmed building agent workflows or knowledge systems, this means you can replace an expensive vector DB + embedding pipeline with a folder of plain text files and a CLAUDE.md instruction set.

## How To Use It

**Minimal structure:**
```
/knowledge/
  raw/           ← dump everything here (articles, transcripts, PDFs → md)
  wiki/          ← LLM-generated and maintained markdown
    index.md     ← content-oriented catalog of all pages
    log.md       ← append-only log of wiki changes (never delete)
    [topics].md  ← one page per concept/entity/summary
  CLAUDE.md      ← schema: tells Claude how to compile and maintain wiki
```

**CLAUDE.md schema pattern (key instructions to include):**
```markdown
# Wiki Operations

## On new raw source added:
1. Read the new file in raw/
2. Check index.md for related existing pages
3. Update or create pages in wiki/ with summary, key entities, backlinks
4. Flag contradictions with existing pages inline using > ⚠️ CONFLICT: ...
5. Append a log entry to log.md

## Index format:
- Each page: `[title](path) — one-line description, related: [[page1]], [[page2]]`

## Never delete from log.md. Append only.
```

**Compile a wiki from existing raw sources with Claude Code:**
```bash
# In your project directory
claude "Read everything in raw/, then build wiki/ following CLAUDE.md.
Create index.md and log.md. Write one markdown page per major concept.
Add backlinks between related pages."
```

**Incremental update (add one new source):**
```bash
cp new_article.md raw/
claude "A new file was added to raw/. Update wiki/ per CLAUDE.md schema.
Backlink to related pages, flag any contradictions."
```

**Query the wiki (cheap, no embeddings):**
```bash
claude "Read wiki/index.md, then answer: [question].
Cite specific wiki pages."
```

## Business Adaptation
For non-research use cases, the video's suggestions are valid but the mechanism matters:
- **Separate vaults per domain** (personal / client / project) to prevent context bleed
- **Business sources**: export Slack channels as markdown, transcribe calls, paste meeting notes → dump into `raw/`
- **Agentic triggers**: watch `wiki/log.md` for specific topic updates, then fire downstream actions (e.g., "if wiki/competitors.md was updated today, draft a brief for the team")

```bash
# Watch log.md for topic triggers (simple version)
grep "competitors" wiki/log.md | tail -5
# Pipe into Claude to generate action
```

## Verified Claims
- ✅ Karpathy coined the term "vibe coding" — [Wikipedia: Vibe coding](https://en.wikipedia.org/wiki/Vibe_coding) (coined Feb 2, 2025)
- ⚠️ "4,000 GitHub stars" — undercounts reality; gist exceeded 5,000 stars within days of publishing (April 4, 2026) and reached ~12,675 total. The figure may have been accurate at recording time.
- ❌ "Three folders: RAW, WIKI, OUTPUT" — incorrect. Karpathy's actual three components are: **raw sources**, **wiki**, and **schema/config** (CLAUDE.md or AGENTS.md). No "OUTPUT" folder exists in the pattern. The wiki itself is the output.

## Sources
- [Karpathy LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Analytics India Mag — Karpathy Moves Beyond RAG](https://analyticsindiamag.com/ai-news/andrej-karpathy-moves-beyond-rag-builds-llm-powered-personal-knowledge-bases)
- [VentureBeat — LLM Knowledge Base Architecture](https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an)
- [Original Source](https://www.instagram.com/reel/DWw08-WEqce/?igsh=MTY4Y3J4YXFhYmZ2ZQ==)

---
*Auto-generated by claude-knowledge-pipeline | 2026-04-10*
