#!/usr/bin/env python3
"""
RiRi Tool Knowledge Indexer
Indexes all tool docs, command examples, and project docs into ChromaDB.
RiRi queries this at runtime to find the right tool for any task.

Usage:
  python3 index.py              # full index (tools + projects)
  python3 index.py --tools      # only tool registry
  python3 index.py --projects   # only project docs
  python3 index.py --query "send an email"   # test semantic search
  python3 index.py --add "path/to/doc.md"   # add a single doc
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

# ── ChromaDB setup ────────────────────────────────────────────────────────────
CHROMA_PATH  = Path.home() / ".local/share/riri/chroma"
REGISTRY     = Path(__file__).parent / "registry.json"
PROJECTS_DIR = Path.home() / "projects"
CLAUDE_POWERS = Path.home() / "claude-powers"

# Embedding via Ollama nomic-embed-text
OLLAMA_URL   = "http://localhost:11434"
EMB_MODEL    = "nomic-embed-text"


def get_chroma():
    import chromadb
    from chromadb.config import Settings
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_collection(client, name: str = "riri_knowledge"):
    """Get or create the knowledge collection with Ollama embeddings."""
    try:
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
        emb_fn = OllamaEmbeddingFunction(
            url=f"{OLLAMA_URL}/api/embeddings",
            model_name=EMB_MODEL
        )
    except Exception:
        emb_fn = None

    return client.get_or_create_collection(
        name=name,
        embedding_function=emb_fn,
        metadata={"description": "RiRi tool and project knowledge base"}
    )


# ── Indexing functions ────────────────────────────────────────────────────────

def index_tool_registry(col) -> int:
    """Index every tool from registry.json as a searchable chunk."""
    with open(REGISTRY) as f:
        registry = json.load(f)

    docs, ids, metas = [], [], []
    for cat_name, cat in registry["categories"].items():
        for tool_name, tool in cat["tools"].items():
            # Build rich text chunk
            examples = "\n".join(f"  $ {e}" for e in tool.get("examples", []))
            auth_note = tool.get("auth_note", "")
            chunk = (
                f"Tool: {tool_name}\n"
                f"Category: {cat_name} — {cat['description']}\n"
                f"Binary: {tool.get('bin', tool_name)}\n"
                f"Description: {tool['description']}\n"
                f"Examples:\n{examples}"
            )
            if auth_note:
                chunk += f"\nNote: {auth_note}"

            uid = f"tool_{cat_name}_{tool_name}"
            docs.append(chunk)
            ids.append(uid)
            metas.append({
                "type":     "tool",
                "category": cat_name,
                "name":     tool_name,
                "bin":      tool.get("bin", tool_name)
            })

    # Upsert in batches of 50
    for i in range(0, len(docs), 50):
        col.upsert(documents=docs[i:i+50], ids=ids[i:i+50], metadatas=metas[i:i+50])

    print(f"  ✅ Indexed {len(docs)} tools")
    return len(docs)


def index_markdown_file(col, path: Path, source: str = "doc") -> bool:
    """Chunk a markdown file and index it."""
    try:
        text = path.read_text(errors="ignore")
    except Exception as e:
        print(f"  ⚠ skip {path.name}: {e}")
        return False

    if len(text) < 50:
        return False

    # Chunk by ~800 chars with 150 overlap
    CHUNK, OVERLAP = 800, 150
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i+CHUNK])
        i += CHUNK - OVERLAP

    docs, ids, metas = [], [], []
    for idx, chunk in enumerate(chunks):
        uid = f"{source}_{path.stem}_{idx}"
        docs.append(chunk)
        ids.append(uid)
        metas.append({
            "type":   source,
            "file":   str(path),
            "chunk":  idx,
            "name":   path.stem
        })

    try:
        for i in range(0, len(docs), 50):
            col.upsert(documents=docs[i:i+50], ids=ids[i:i+50], metadatas=metas[i:i+50])
        return True
    except Exception as e:
        print(f"  ⚠ index error {path.name}: {e}")
        return False


def index_project_docs(col) -> int:
    """Index all markdown docs from projects/ and claude-powers/."""
    count = 0
    dirs = []
    if PROJECTS_DIR.exists():
        dirs.append(PROJECTS_DIR)
    if CLAUDE_POWERS.exists():
        dirs.append(CLAUDE_POWERS)
    # Also include RiRi's own AGENTS.md
    riri_dir = Path(__file__).parent.parent
    dirs.append(riri_dir)

    for base in dirs:
        for md in base.rglob("*.md"):
            # Skip node_modules, .git, venv etc.
            if any(p in md.parts for p in ["node_modules", ".git", "venv", "__pycache__", ".tmp"]):
                continue
            if index_markdown_file(col, md, source="project_doc"):
                count += 1
                sys.stdout.write(f"\r  indexing docs... {count}")
                sys.stdout.flush()

    print(f"\n  ✅ Indexed {count} doc files")
    return count


def index_agents_md(col) -> int:
    """Specifically index all AGENTS.md files from Paperclip."""
    paperclip_base = Path.home() / ".paperclip/instances/default/companies"
    count = 0
    for agents_md in paperclip_base.rglob("AGENTS.md"):
        if index_markdown_file(col, agents_md, source="agents_doc"):
            count += 1
    print(f"  ✅ Indexed {count} AGENTS.md files")
    return count


# ── Query ─────────────────────────────────────────────────────────────────────

def query(text: str, n: int = 5, category: str = None) -> list[dict]:
    """Semantic search the knowledge base."""
    client = get_chroma()
    col    = get_collection(client)

    where = {"type": "tool"} if category == "tools" else None
    results = col.query(
        query_texts=[text],
        n_results=min(n, col.count()),
        where=where
    )

    out = []
    docs  = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({
            "content":  doc[:300],
            "type":     meta.get("type"),
            "name":     meta.get("name") or meta.get("file", ""),
            "score":    round(1 - dist, 3)   # convert distance → similarity
        })
    return out


def query_tools(task: str, n: int = 3) -> str:
    """
    Return a formatted string of relevant tools for a given task.
    Used by riri.py to inject tool hints into the brain prompt.
    """
    results = query(task, n=n, category="tools")
    if not results:
        return ""
    lines = ["[Relevant tools from knowledge base]"]
    for r in results:
        lines.append(r["content"].split("\n")[0] + "  →  " + "\n".join(r["content"].split("\n")[1:3]))
    return "\n".join(lines)


# ── Stats ─────────────────────────────────────────────────────────────────────

def stats():
    client = get_chroma()
    col    = get_collection(client)
    total  = col.count()
    print(f"Knowledge base: {total} chunks")
    # Sample distribution
    if total > 0:
        sample = col.get(limit=500)
        types = {}
        for m in sample["metadatas"]:
            t = m.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        for t, n in sorted(types.items(), key=lambda x: -x[1]):
            print(f"  {t}: {n}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RiRi knowledge indexer")
    parser.add_argument("--tools",    action="store_true", help="Index tool registry only")
    parser.add_argument("--projects", action="store_true", help="Index project docs only")
    parser.add_argument("--agents",   action="store_true", help="Index AGENTS.md files")
    parser.add_argument("--all",      action="store_true", help="Full reindex (default)")
    parser.add_argument("--query",    type=str,            help="Test semantic search")
    parser.add_argument("--add",      type=str,            help="Add a single file")
    parser.add_argument("--stats",    action="store_true", help="Show index stats")
    args = parser.parse_args()

    if args.stats:
        stats()
        return

    if args.query:
        results = query(args.query, n=5)
        print(f"\nTop results for: '{args.query}'\n")
        for r in results:
            print(f"[{r['score']:.3f}] ({r['type']}) {r['name']}")
            print(f"  {r['content'][:200]}\n")
        return

    if args.add:
        client = get_chroma()
        col    = get_collection(client)
        ok = index_markdown_file(col, Path(args.add), source="custom")
        print("Added." if ok else "Failed.")
        return

    # Index
    client = get_chroma()
    col    = get_collection(client)
    print("Indexing RiRi knowledge base...")

    do_all = args.all or not (args.tools or args.projects or args.agents)

    if args.tools or do_all:
        print("\n[1/3] Tool registry...")
        index_tool_registry(col)

    if args.projects or do_all:
        print("\n[2/3] Project docs...")
        index_project_docs(col)

    if args.agents or do_all:
        print("\n[3/3] Agent instructions...")
        index_agents_md(col)

    print(f"\nDone. Total chunks: {col.count()}")


if __name__ == "__main__":
    main()
