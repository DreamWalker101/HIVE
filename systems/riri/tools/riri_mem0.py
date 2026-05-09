"""
riri_mem0.py — Local structured memory for RiRi using Mem0 + Ollama + Qdrant.

Mem0 extracts *facts* from conversations and stores them as searchable memories.
Unlike LanceDB (raw semantic chunks), Mem0 builds a knowledge graph of what
actually happened: posts published, tasks completed, preferences, decisions.

Usage:
  from riri_mem0 import RiriMemory
  mem = RiriMemory()
  mem.add("Ahmed posted about AI on LinkedIn", agent_id="riri")
  results = mem.search("LinkedIn posts", agent_id="riri")

CLI:
  python3 riri_mem0.py add  "Ahmed posted about AI today"
  python3 riri_mem0.py search "recent posts"
  python3 riri_mem0.py all
  python3 riri_mem0.py context "what task is Ahmed working on"
"""

from __future__ import annotations

import json
import sys
import os
from typing import Any

import mem0

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MEM0_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "riri_memory",
            "host": "localhost",
            "port": 6333,
            "embedding_model_dims": 768,
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "gemma3:4b",
            "ollama_base_url": "http://localhost:11434",
            "temperature": 0,
            "max_tokens": 2000,
        },
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434",
            "embedding_dims": 768,
        },
    },
    "history_db_path": os.path.expanduser(
        "~/.local/share/riri/mem0_history.db"
    ),
}

USER_ID = "ahmed"
AGENT_ID = "riri"


# ---------------------------------------------------------------------------
# RiriMemory class
# ---------------------------------------------------------------------------


class RiriMemory:
    def __init__(self, config: dict | None = None):
        self._m = mem0.Memory.from_config(config or MEM0_CONFIG)

    # ---- Core operations --------------------------------------------------

    def add(self, text: str, agent_id: str = AGENT_ID, user_id: str = USER_ID, metadata: dict | None = None) -> list[dict]:
        """Extract facts from text and store them."""
        kwargs: dict[str, Any] = {"user_id": user_id, "agent_id": agent_id}
        if metadata:
            kwargs["metadata"] = metadata
        result = self._m.add(text, **kwargs)
        return result.get("results", [])

    def search(self, query: str, agent_id: str = AGENT_ID, user_id: str = USER_ID, limit: int = 10) -> list[dict]:
        """Semantic search for memories relevant to a query."""
        result = self._m.search(query, user_id=user_id, agent_id=agent_id, limit=limit)
        return result.get("results", [])

    def get_all(self, agent_id: str = AGENT_ID, user_id: str = USER_ID) -> list[dict]:
        """Return all stored memories (paginated up to 500)."""
        result = self._m.get_all(user_id=user_id, agent_id=agent_id)
        return result.get("results", [])

    def delete(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        try:
            self._m.delete(memory_id)
            return True
        except Exception:
            return False

    def delete_all(self, agent_id: str = AGENT_ID, user_id: str = USER_ID) -> None:
        """Wipe all memories — use with care."""
        self._m.delete_all(user_id=user_id, agent_id=agent_id)

    # ---- Context helpers --------------------------------------------------

    def context_block(self, query: str, limit: int = 8) -> str:
        """
        Return a formatted context block for injection into RiRi's system prompt.
        Searches for memories relevant to the query and formats them as a numbered list.
        """
        hits = self.search(query, limit=limit)
        if not hits:
            return ""
        lines = ["[Structured Memory — what I know about this topic:]"]
        for i, h in enumerate(hits, 1):
            mem_text = h.get("memory", "")
            if mem_text:
                lines.append(f"  {i}. {mem_text}")
        return "\n".join(lines)

    def recent_context(self, limit: int = 20) -> str:
        """
        Return all recent memories sorted by creation date, for cold-start context.
        """
        memories = self.get_all()
        # Sort newest first
        memories.sort(
            key=lambda x: x.get("created_at") or x.get("updated_at") or "",
            reverse=True,
        )
        memories = memories[:limit]
        if not memories:
            return ""
        lines = ["[Structured Memory — recent facts about Ahmed and RiRi:]"]
        for i, h in enumerate(memories, 1):
            mem_text = h.get("memory", "")
            ts = (h.get("created_at") or "")[:10]
            if mem_text:
                entry = f"  {i}. {mem_text}"
                if ts:
                    entry += f" [{ts}]"
                lines.append(entry)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_memories(memories: list[dict]) -> None:
    if not memories:
        print("No memories found.")
        return
    for m in memories:
        score = m.get("score")
        ts = (m.get("created_at") or "")[:16]
        score_str = f"  score={score:.3f}" if score else ""
        print(f"• {m.get('memory', '')}{score_str}  [{ts}]  id={m.get('id', '')[:8]}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="RiRi Mem0 — structured local memory")
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Extract facts from text and store")
    p_add.add_argument("text", help="Conversation or statement to ingest")

    p_search = sub.add_parser("search", help="Search memories by query")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)

    sub.add_parser("all", help="List all memories")
    sub.add_parser("recent", help="Show recent context block")

    p_context = sub.add_parser("context", help="Get context block for a query")
    p_context.add_argument("query")

    p_del = sub.add_parser("delete", help="Delete a memory by ID")
    p_del.add_argument("id")

    sub.add_parser("wipe", help="Delete ALL memories (irreversible)")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    print("Initializing mem0 (Ollama + Qdrant)...", file=sys.stderr)
    mem = RiriMemory()

    if args.cmd == "add":
        results = mem.add(args.text)
        print(f"Stored {len(results)} fact(s):")
        for r in results:
            ev = r.get("event", "")
            print(f"  [{ev}] {r.get('memory', '')}")

    elif args.cmd == "search":
        hits = mem.search(args.query, limit=args.limit)
        print(f"Found {len(hits)} result(s) for '{args.query}':")
        _print_memories(hits)

    elif args.cmd == "all":
        all_mem = mem.get_all()
        print(f"Total memories: {len(all_mem)}")
        _print_memories(all_mem)

    elif args.cmd == "recent":
        print(mem.recent_context())

    elif args.cmd == "context":
        print(mem.context_block(args.query))

    elif args.cmd == "delete":
        ok = mem.delete(args.id)
        print("Deleted." if ok else "Failed to delete.")

    elif args.cmd == "wipe":
        confirm = input("Type 'yes' to wipe ALL memories: ")
        if confirm.strip() == "yes":
            mem.delete_all()
            print("All memories wiped.")
        else:
            print("Aborted.")


if __name__ == "__main__":
    main()
