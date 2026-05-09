#!/usr/bin/env python3
"""
RiRi Chroma MCP Server
Exposes ChromaDB project knowledge base as MCP tools for OpenClaw.

Tools:
  search_projects  — semantic search across all indexed project docs
  list_projects    — list all project names in the knowledge base
  get_pipeline_report — fetch recent Claude sessions from pipeline DB
"""

import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Add riri tools to path
RIRI_DIR = Path.home() / "projects/riri"
sys.path.insert(0, str(RIRI_DIR / "tools"))

CHROMA_PATH  = Path.home() / ".local/share/riri/chroma"
PIPELINE_DB  = Path.home() / ".local/share/riri/pipeline.db"
OLLAMA_URL   = "http://localhost:11434"
EMB_MODEL    = "nomic-embed-text"


def get_chroma_collection():
    import chromadb
    from chromadb.config import Settings
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
        emb_fn = OllamaEmbeddingFunction(
            url=f"{OLLAMA_URL}/api/embeddings",
            model_name=EMB_MODEL
        )
        return client.get_or_create_collection("riri_knowledge", embedding_function=emb_fn)
    except Exception:
        return client.get_or_create_collection("riri_knowledge")


def search_projects(query: str, n: int = 5, category: str = None) -> list[dict]:
    """Semantic search the knowledge base. Returns top N results."""
    try:
        col = get_chroma_collection()
        count = col.count()
        if count == 0:
            return [{"score": 0, "content": "Knowledge base is empty. Run: python3 ~/projects/riri/tools/index.py", "source": "system"}]
        where = {"type": "tool"} if category == "tools" else None
        results = col.query(
            query_texts=[query],
            n_results=min(n, count),
            where=where
        )
        out = []
        if results and results["documents"] and results["documents"][0]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
            dists = results["distances"][0] if results["distances"] else [0.5] * len(docs)
            for doc, meta, dist in zip(docs, metas, dists):
                out.append({
                    "score": round(1.0 - dist, 3),
                    "content": doc,
                    "source": meta.get("source", "?"),
                    "type": meta.get("type", "?"),
                })
        return out
    except Exception as e:
        return [{"score": 0, "content": f"Search error: {e}", "source": "error"}]


def list_projects() -> list[str]:
    """List all project directories that have been indexed."""
    try:
        col = get_chroma_collection()
        if col.count() == 0:
            return []
        results = col.get(limit=500, include=["metadatas"])
        projects = set()
        for meta in (results.get("metadatas") or []):
            src = meta.get("source", "")
            if "/projects/" in src:
                parts = src.split("/projects/")
                if len(parts) > 1:
                    projects.add(parts[1].split("/")[0])
        return sorted(projects)
    except Exception as e:
        return [f"Error: {e}"]


def get_pipeline_report(days: int = 7) -> str:
    """Fetch recent Claude coding sessions from the pipeline DB."""
    if not PIPELINE_DB.exists():
        return "Pipeline DB not found (no sessions yet)."
    try:
        cutoff = time.time() - days * 86400
        conn = sqlite3.connect(str(PIPELINE_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT project, summary, turn_count, files_changed, errors, "
            "ended_at, started_at FROM sessions "
            "WHERE COALESCE(ended_at, started_at) > ? "
            "ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 15",
            (cutoff,)
        ).fetchall()
        conn.close()
        if not rows:
            return f"No sessions in the last {days} days."
        lines = [f"Last {days} day(s) — {len(rows)} session(s):"]
        for r in rows:
            ts = datetime.fromtimestamp(r["ended_at"] or r["started_at"]).strftime("%m/%d %H:%M")
            proj = r["project"] or "?"
            summ = (r["summary"] or "in progress")[:80]
            n_f  = len(json.loads(r["files_changed"] or "[]"))
            n_t  = r["turn_count"] or 0
            lines.append(f"[{ts}] {proj} — {n_t} turns / {n_f} files: {summ}")
        return "\n".join(lines)
    except Exception as e:
        return f"DB error: {e}"


# ── MCP Server ────────────────────────────────────────────────────────────────
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio

app = Server("riri-chroma")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_projects",
            description="Semantic search across Ahmed's indexed project docs and tool knowledge base. Use this to find relevant project info, tool docs, or past work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "n": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                    "category": {"type": "string", "description": "Filter: 'tools' to search only tool docs", "default": None}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_projects",
            description="List all project names that have been indexed in the knowledge base.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_pipeline_report",
            description="Get a summary of recent Claude coding sessions (what Ahmed worked on).",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "How many days back to look (default 7)", "default": 7}
                }
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_projects":
        query = arguments.get("query", "")
        n = int(arguments.get("n", 5))
        category = arguments.get("category", None)
        results = search_projects(query, n=n, category=category)
        lines = []
        for r in results:
            lines.append(f"[score={r['score']}] {r['source']}\n{r['content'][:400]}")
        text = "\n\n---\n".join(lines) if lines else "No results found."
        return [TextContent(type="text", text=text)]

    elif name == "list_projects":
        projects = list_projects()
        text = "Indexed projects:\n" + "\n".join(f"  • {p}" for p in projects) if projects else "No projects indexed yet."
        return [TextContent(type="text", text=text)]

    elif name == "get_pipeline_report":
        days = int(arguments.get("days", 7))
        text = get_pipeline_report(days)
        return [TextContent(type="text", text=text)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
