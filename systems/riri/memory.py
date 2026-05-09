"""
RiRi Memory System
- Short-term: in-session history (handled in riri.py)
- Long-term: SQLite + nomic-embed-text semantic search
- Session compaction: distill sessions into facts after N exchanges
"""
import json, sqlite3, time, threading, subprocess
from pathlib import Path

DB_PATH   = Path.home() / ".local/share/riri/memory.db"
OLLAMA    = "http://localhost:11434"
EMB_MODEL = "nomic-embed-text"
CHAT_MODEL = "gemma3:4b"  # fast local model

_lock = threading.Lock()


# ── DB setup ─────────────────────────────────────────────────────────────────

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            content   TEXT    NOT NULL,
            embedding TEXT,           -- JSON float array
            tags      TEXT,
            source    TEXT DEFAULT 'user',
            created_at REAL  DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS facts (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            updated_at REAL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            summary    TEXT,
            turn_count INTEGER DEFAULT 0,
            created_at REAL    DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS cmd_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            cmd        TEXT NOT NULL,
            exit_code  INTEGER,
            used_at    REAL DEFAULT (unixepoch())
        );
        """)
    # Seed initial facts
    set_fact("owner", "Ahmed")
    set_fact("owner_email", "contact@tavren.io")
    set_fact("work_email", "hammad@tavren.io")


# ── Embeddings ────────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float] | None:
    try:
        import urllib.request
        body = json.dumps({"model": EMB_MODEL, "prompt": text}).encode()
        req  = urllib.request.Request(
            f"{OLLAMA}/api/embeddings",
            data=body, method="POST",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())["embedding"]
    except Exception:
        return None

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = sum(x*x for x in a) ** 0.5
    nb  = sum(x*x for x in b) ** 0.5
    return dot / (na * nb + 1e-9)


# ── Memory CRUD ───────────────────────────────────────────────────────────────

def remember(content: str, tags: str = "", source: str = "user") -> int:
    """Store a memory with semantic embedding."""
    with _lock:
        emb  = _embed(content)
        emb_s = json.dumps(emb) if emb else None
        with _conn() as c:
            cur = c.execute(
                "INSERT INTO memories (content, embedding, tags, source) VALUES (?,?,?,?)",
                (content, emb_s, tags, source)
            )
            return cur.lastrowid

def recall(query: str, k: int = 5, min_score: float = 0.60) -> list[dict]:
    """Return top-k semantically similar memories."""
    qemb = _embed(query)
    with _conn() as c:
        rows = c.execute(
            "SELECT id, content, tags, created_at, embedding FROM memories ORDER BY created_at DESC LIMIT 200"
        ).fetchall()

    results = []
    for row in rows:
        if qemb and row["embedding"]:
            try:
                remb  = json.loads(row["embedding"])
                score = _cosine(qemb, remb)
            except Exception:
                score = 0.0
        else:
            # Fallback: keyword match
            score = 0.5 if query.lower() in row["content"].lower() else 0.0

        if score >= min_score:
            results.append({
                "id":      row["id"],
                "content": row["content"],
                "tags":    row["tags"],
                "score":   round(score, 3),
                "age_h":   round((time.time() - row["created_at"]) / 3600, 1)
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]

def recall_text(query: str, k: int = 5) -> str:
    """Return recalled memories as a formatted string for prompt injection."""
    mems = recall(query, k)
    if not mems:
        return ""
    lines = [f"[Memory] {m['content']}" for m in mems]
    return "\n".join(lines)


# ── Facts (structured KV) ────────────────────────────────────────────────────

def set_fact(key: str, value: str):
    with _conn() as c:
        c.execute(
            "INSERT INTO facts(key,value,updated_at) VALUES(?,?,unixepoch()) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=unixepoch()",
            (key, value)
        )

def get_fact(key: str) -> str | None:
    with _conn() as c:
        row = c.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

def all_facts() -> dict:
    with _conn() as c:
        rows = c.execute("SELECT key, value FROM facts").fetchall()
        return {r["key"]: r["value"] for r in rows}


# ── Command log ───────────────────────────────────────────────────────────────

def log_cmd(cmd: str, exit_code: int):
    with _conn() as c:
        c.execute("INSERT INTO cmd_log(cmd, exit_code) VALUES(?,?)", (cmd, exit_code))

def proven_cmds(limit: int = 10) -> list[str]:
    """Commands that reliably succeeded."""
    with _conn() as c:
        rows = c.execute(
            "SELECT cmd, COUNT(*) as n, SUM(exit_code=0)*1.0/COUNT(*) as sr "
            "FROM cmd_log GROUP BY cmd HAVING sr > 0.8 AND n >= 2 "
            "ORDER BY n DESC LIMIT ?", (limit,)
        ).fetchall()
        return [r["cmd"] for r in rows]


# ── Session compaction ────────────────────────────────────────────────────────

def compact_session(history: list[dict]) -> str:
    """
    Distill a conversation history into facts + a summary.
    Uses local Ollama to generate the distillation.
    Stores results in DB. Returns summary string.
    """
    if len(history) < 2:
        return ""

    convo = "\n".join(
        f"{'Ahmed' if h['role']=='user' else 'RiRi'}: {h['text']}"
        for h in history[-30:]   # last 30 turns max
    )

    prompt = (
        "Analyze this conversation between Ahmed and his AI assistant RiRi.\n\n"
        f"{convo}\n\n"
        "Output JSON with exactly these fields:\n"
        '{"summary": "2-3 sentence session summary", '
        '"facts": ["fact 1", "fact 2", ...], '
        '"preferences": {"key": "value"}, '
        '"commands_worked": ["cmd1", "cmd2"]}\n'
        "Facts are things Ahmed mentioned about himself, his projects, or preferences. "
        "Keep each fact under 20 words."
    )

    try:
        result = subprocess.run(
            ["ollama", "run", CHAT_MODEL, prompt],
            capture_output=True, text=True, timeout=60
        )
        raw = result.stdout.strip()
        # Extract JSON
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return raw[:200]
        data = json.loads(m.group())
    except Exception as e:
        return f"(compaction failed: {e})"

    summary = data.get("summary", "")
    facts   = data.get("facts", [])
    prefs   = data.get("preferences", {})
    cmds    = data.get("commands_worked", [])

    # Store
    for fact in facts:
        if fact.strip():
            remember(fact, tags="session-fact", source="compaction")
    for k, v in prefs.items():
        set_fact(k, str(v))
    for cmd in cmds:
        log_cmd(cmd, 0)  # mark as successful

    with _conn() as c:
        c.execute(
            "INSERT INTO sessions(summary, turn_count) VALUES(?,?)",
            (summary, len(history))
        )

    return summary


# ── Recent context builder ────────────────────────────────────────────────────

def build_context_block(query: str) -> str:
    """
    Build a context block to prepend to every Hermes prompt.
    Includes relevant memories + key facts.
    """
    facts  = all_facts()
    recall = recall_text(query, k=4)

    lines = []
    if facts:
        key_facts = ["owner", "owner_email", "current_project", "preferred_model", "timezone"]
        for k in key_facts:
            if k in facts:
                lines.append(f"Fact — {k}: {facts[k]}")
    if recall:
        lines.append(recall)

    return "\n".join(lines) if lines else ""


# ── CLI for debugging ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    init_db()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "remember" and len(sys.argv) > 2:
        mid = remember(" ".join(sys.argv[2:]))
        print(f"Stored memory #{mid}")

    elif cmd == "recall" and len(sys.argv) > 2:
        mems = recall(" ".join(sys.argv[2:]))
        for m in mems:
            print(f"[{m['score']:.2f}] {m['content']}")

    elif cmd == "facts":
        for k, v in all_facts().items():
            print(f"  {k}: {v}")

    elif cmd == "stats":
        with _conn() as c:
            print("Memories:", c.execute("SELECT COUNT(*) FROM memories").fetchone()[0])
            print("Facts:   ", c.execute("SELECT COUNT(*) FROM facts").fetchone()[0])
            print("Sessions:", c.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
            print("Cmd log: ", c.execute("SELECT COUNT(*) FROM cmd_log").fetchone()[0])
    else:
        print("Usage: memory.py [remember <text>|recall <query>|facts|stats]")
