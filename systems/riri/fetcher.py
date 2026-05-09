#!/usr/bin/env python3
"""
RiRi Fetcher Sub-Agent
──────────────────────
The dumb retrieval worker. No LLM involved — pure deterministic fetching.
RiRi delegates all retrieval here so her context stays clean.

Does three things:
  1. Semantic search in ChromaDB (projects, tools, hooks, case studies)
  2. File type detection via Magika (for any file that comes in)
  3. Community skill discovery via skills.sh (npx skills find)

Called by dispatcher.py when needs_fetch=True.
Called directly by agent_loop.py before the main LLM turn.

Usage:
  from fetcher import fetch
  result = fetch(
      queries=["riri project architecture"],
      file_path="/tmp/uploaded.pdf",
      skill_search="generate diagrams"
  )
"""

import json
import subprocess
import sys
from pathlib import Path

HOME         = Path.home()
CHROMA_PATH  = HOME / ".local/share/riri/chroma"
OLLAMA_URL   = "http://localhost:11434"
EMB_MODEL    = "nomic-embed-text"


# ── Chroma search ──────────────────────────────────────────────────────────────
def _search_chroma(queries: list[str], n_per_query: int = 4) -> list[dict]:
    """
    Semantic search across the ChromaDB knowledge base.
    Returns deduplicated top results across all queries.
    """
    if not queries:
        return []
    try:
        import chromadb
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))

        try:
            from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
            emb_fn = OllamaEmbeddingFunction(
                url=f"{OLLAMA_URL}/api/embeddings",
                model_name=EMB_MODEL
            )
            col = client.get_or_create_collection("riri_knowledge", embedding_function=emb_fn)
        except Exception:
            col = client.get_or_create_collection("riri_knowledge")

        if col.count() == 0:
            return []

        seen_ids = set()
        results  = []
        n        = min(n_per_query, col.count())

        for query in queries:
            try:
                r = col.query(query_texts=[query], n_results=n)
                if not r or not r.get("documents") or not r["documents"][0]:
                    continue
                docs  = r["documents"][0]
                metas = r["metadatas"][0] if r.get("metadatas") else [{}] * len(docs)
                dists = r["distances"][0]  if r.get("distances")  else [0.5] * len(docs)
                ids   = r["ids"][0]        if r.get("ids")         else [str(i) for i in range(len(docs))]

                for doc, meta, dist, doc_id in zip(docs, metas, dists, ids):
                    if doc_id in seen_ids:
                        continue
                    seen_ids.add(doc_id)
                    score = round(1.0 - dist, 3)
                    if score > 0.4:  # only keep reasonably relevant results
                        results.append({
                            "score":   score,
                            "content": doc,
                            "source":  meta.get("source", "?"),
                            "type":    meta.get("type", "?"),
                        })
            except Exception:
                continue

        # Sort by score, return top 6 overall
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:6]

    except Exception as e:
        return [{"score": 0, "content": f"Chroma error: {e}", "source": "error", "type": "error"}]


# ── Magika file detection ──────────────────────────────────────────────────────
def _detect_file_type(file_path: str) -> dict | None:
    """
    Use Magika to detect file type. Returns None if file doesn't exist.
    """
    if not file_path:
        return None
    path = Path(file_path)
    if not path.exists():
        return None
    try:
        from magika import Magika
        m      = Magika()
        result = m.identify_path(path)
        out    = result.output   # ContentTypeInfo
        return {
            "type":        out.label,
            "mime":        out.mime_type,
            "group":       out.group,
            "confidence":  round(result.score, 3),
            "description": out.description,
        }
    except Exception as e:
        # Fallback: guess from extension
        suffix = path.suffix.lower().lstrip(".")
        return {
            "type":        suffix or "unknown",
            "mime":        f"application/{suffix}" if suffix else "application/octet-stream",
            "group":       "unknown",
            "confidence":  0.0,
            "description": f"Extension-based guess (magika error: {e})",
        }


# ── Skills.sh discovery ────────────────────────────────────────────────────────
def _search_skills_sh(query: str) -> list[dict]:
    """
    Search the community skills marketplace via npx skills find.
    Returns list of found skills with name, command, and description.
    """
    if not query:
        return []
    try:
        result = subprocess.run(
            ["npx", "--yes", "skills", "find", query, "--json"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = json.loads(result.stdout)
            # Normalise different possible formats
            skills = raw if isinstance(raw, list) else raw.get("skills", raw.get("results", []))
            return [
                {
                    "name":    s.get("name", s.get("title", "?")),
                    "cmd":     s.get("install", s.get("command", s.get("cmd", "?"))),
                    "url":     s.get("url", s.get("link", "")),
                    "stars":   s.get("stars", 0),
                    "installs":s.get("installs", 0),
                }
                for s in skills[:3]
            ]
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    # Fallback: text output
    try:
        result = subprocess.run(
            ["npx", "--yes", "skills", "find", query],
            capture_output=True, text=True, timeout=20
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
        if lines:
            return [{"name": query, "cmd": "npx skills find " + query,
                     "url": "https://skills.sh", "raw_output": "\n".join(lines[:5])}]
    except Exception:
        pass

    return []


# ── Claude hooks search ────────────────────────────────────────────────────────
def _search_local_hooks(query: str) -> list[dict]:
    """
    Search Ahmed's local claude-powers directory for relevant hooks and skills.
    Fast grep-based search, no LLM needed.
    """
    powers_dir = HOME / "claude-powers"
    if not powers_dir.exists():
        return []

    results = []
    query_lower = query.lower()
    query_words = set(query_lower.split())

    for md in powers_dir.rglob("*.md"):
        if md.name in ("README.md", "CHANGELOG.md", "rejected.md"):
            continue
        try:
            content = md.read_text(errors="ignore")
            content_lower = content.lower()
            # Score by word overlap
            matches = sum(1 for w in query_words if w in content_lower and len(w) > 3)
            if matches >= 2:
                title = md.stem.replace("-", " ").replace("_", " ")
                for line in content.splitlines():
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                snippet = " ".join(content.split()[:30])
                results.append({
                    "score":   matches / max(len(query_words), 1),
                    "title":   title,
                    "path":    str(md),
                    "snippet": snippet,
                    "category": md.parent.name,
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]


# ── Pipeline DB search ─────────────────────────────────────────────────────────
def _search_pipeline(query: str) -> list[dict]:
    """
    Search Ahmed's Claude session history for relevant past work.
    Keyword match against project names and summaries.
    """
    import sqlite3, time
    db_path = HOME / ".local/share/riri/pipeline.db"
    if not db_path.exists():
        return []
    try:
        query_lower = query.lower()
        conn   = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows   = conn.execute(
            "SELECT project, summary, ended_at, files_changed FROM sessions "
            "ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 50"
        ).fetchall()
        conn.close()

        results = []
        for r in rows:
            proj = (r["project"] or "").lower()
            summ = (r["summary"] or "").lower()
            if query_lower in proj or query_lower in summ:
                from datetime import datetime
                ts = datetime.fromtimestamp(r["ended_at"] or 0).strftime("%m/%d") if r["ended_at"] else "?"
                results.append({
                    "score":   1.0 if query_lower in proj else 0.6,
                    "content": f"[{ts}] {r['project']}: {(r['summary'] or '')[:150]}",
                    "source":  "pipeline.db",
                    "type":    "session",
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:4]
    except Exception:
        return []


# ── Main fetch function ────────────────────────────────────────────────────────
def fetch(
    queries: list[str] = None,
    file_path: str = None,
    skill_search: str = None,
    search_hooks: bool = False,
    search_pipeline_db: bool = False,
) -> dict:
    """
    Run all applicable retrieval operations in parallel (well, sequentially but fast).
    Returns structured results for RiRi to reason over.

    Args:
      queries:           list of semantic search terms for ChromaDB
      file_path:         path to a file to detect type via Magika
      skill_search:      search term for skills.sh community marketplace
      search_hooks:      whether to search local claude-powers hooks/skills
      search_pipeline_db:whether to search pipeline session history

    Returns dict with keys: chunks, file_type, skills, hooks, sessions
    """
    result = {
        "chunks":    [],
        "file_type": None,
        "skills":    [],
        "hooks":     [],
        "sessions":  [],
    }

    # 1. Chroma semantic search
    if queries:
        result["chunks"] = _search_chroma(queries)

    # 2. File type detection
    if file_path:
        result["file_type"] = _detect_file_type(file_path)

    # 3. Skills.sh community search
    if skill_search:
        result["skills"] = _search_skills_sh(skill_search)

    # 4. Local hooks/powers search
    if search_hooks and queries:
        combined_query = " ".join(queries[:2])
        result["hooks"] = _search_local_hooks(combined_query)

    # 5. Pipeline history search
    if search_pipeline_db and queries:
        for q in queries[:2]:
            result["sessions"].extend(_search_pipeline(q))

    return result


def format_results(fetch_result: dict, max_chars: int = 1200) -> str:
    """
    Format fetch results into a compact string for injection into LLM context.
    Stays under max_chars to avoid bloating the main model's context.
    """
    lines = []

    # Knowledge base chunks
    for c in fetch_result.get("chunks", []):
        if c.get("score", 0) > 0.5:
            src  = Path(c.get("source", "?")).name
            text = c.get("content", "")[:200]
            lines.append(f"[KB:{src}] {text}")

    # Pipeline sessions
    for s in fetch_result.get("sessions", []):
        lines.append(f"[History] {s.get('content', '')[:150]}")

    # File type
    ft = fetch_result.get("file_type")
    if ft:
        lines.append(f"[File] {ft['type']} — {ft['description']} (confidence: {ft['confidence']})")

    # Hooks/powers
    for h in fetch_result.get("hooks", []):
        lines.append(f"[Power:{h['category']}] {h['title']}: {h['snippet'][:100]}")

    # Community skills
    for s in fetch_result.get("skills", []):
        lines.append(f"[Skill] {s['name']}: {s.get('cmd', '')}")

    result = "\n".join(lines)
    # Trim to budget
    if len(result) > max_chars:
        result = result[:max_chars] + "\n[... truncated]"
    return result


if __name__ == "__main__":
    import sys
    queries      = sys.argv[1:] if len(sys.argv) > 1 else ["riri architecture agent"]
    skill_search = sys.argv[-1] if len(sys.argv) > 2 else None

    print(f"Fetching for: {queries}")
    result = fetch(queries=queries, skill_search=skill_search,
                   search_hooks=True, search_pipeline_db=True)
    print(f"\nChroma chunks:  {len(result['chunks'])}")
    print(f"Sessions found: {len(result['sessions'])}")
    print(f"Skills found:   {len(result['skills'])}")
    print(f"Hooks found:    {len(result['hooks'])}")
    print(f"File type:      {result['file_type']}")
    print("\n--- Formatted output ---")
    print(format_results(result))
