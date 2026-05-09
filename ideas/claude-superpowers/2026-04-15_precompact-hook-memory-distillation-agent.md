---
title: "PreCompact Hook as Memory Distillation Trigger: Background Agent Reads Full Transcript Before Context Is Lost"
category: claude-superpowers
tags: [claude, claude-superpowers, hooks, precompact, memory, sub-agent, persistent-memory, git, context-management]
confidence: medium
source_reel: "https://www.instagram.com/reel/DW_wEu9jQt7/?igsh=MTRjOWIzdDd6dTdzeA=="
source_platform: instagram
verified_against:
  - "https://code.claude.com/docs/en/hooks"
  - "https://github.com/anthropics/claude-code/issues/15946"
  - "https://github.com/anthropics/claude-code/issues/27969"
date_added: 2026-04-15
claude_applicable: true
pipeline_run: run/2026-04-15T02-30-12
---

# PreCompact Hook as Memory Distillation Trigger: Background Agent Reads Full Transcript Before Context Is Lost

## What Is This
Claude Code's `PreCompact` hook fires just before automatic context compaction (~95% context used). Wiring a background `agent`-type hook here lets you spawn a sub-agent that reads the full conversation transcript (via `transcript_path`) and distills it into structured insights stored in persistent memory files — before the conversation history is compressed or lost.

This is analogous to sleep consolidation: converting the "working memory" of a long session into permanent long-term storage.

## Why It Matters
Auto-compaction silently destroys conversation history detail. By the time PreCompact fires, the full uncompressed transcript is still on disk and available. A background agent that reads it and writes distilled insights to `~/.claude/memory/` (or a git-tracked repo) creates durable, session-independent knowledge. The Git backend adds a time dimension: you can see how your understanding of a codebase evolved across weeks.

This is distinct from the Stop hook logging pattern (which logs metadata every turn). PreCompact fires once per session near its natural end, making it ideal for holistic insight extraction rather than turn-by-turn logging.

## How To Use It

### 1. Wire an agent-type PreCompact hook

```json
// ~/.claude/settings.json
{
  "hooks": {
    "PreCompact": [
      {
        "type": "agent",
        "prompt": "You have access to the conversation transcript at the path provided in transcript_path. Read the full transcript, identify the 3-5 most important insights, decisions, or patterns discovered in this session, and append them as structured markdown to ~/.claude/memory/SESSION_INSIGHTS.md with today's date. Ask the user first with the AskUserQuestion tool whether they want to save a memory before proceeding.",
        "tools": ["Read", "Write", "Edit", "AskUserQuestion"],
        "background": true
      }
    ]
  }
}
```

### 2. The agent flow

1. `PreCompact` fires at ~95% context usage
2. Background agent asks user (via `AskUserQuestion`): "Save a memory of this session?"
3. If yes: agent reads `transcript_path` → distills → appends to memory file
4. If no: agent exits cleanly

### 3. Git-track your memory for time-dimension

```bash
cd ~/.claude/memory
git init
echo "*.md" > .gitignore-except
git add SESSION_INSIGHTS.md
git commit -m "session insights $(date +%Y-%m-%d)"
```

Add a PostToolUse hook on Write (filtered to memory path) to auto-commit each insight save.

### 4. Alternative: Stop hook with transcript size check

Since PreCompact is at ~95% (not configurable to 80%), you can use Stop hook + a custom threshold:

```bash
#!/bin/bash
# ~/.claude/hooks/check-context.sh
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('transcript_path',''))")

if [ -n "$TRANSCRIPT" ]; then
  SIZE=$(wc -c < "$TRANSCRIPT" 2>/dev/null || echo 0)
  # ~200KB ≈ 80% of a typical 200K-token context
  if [ "$SIZE" -gt 200000 ]; then
    # trigger memory save logic here
    echo '{"decision": "block", "reason": "Triggering memory save at 80% estimated context"}'
  fi
fi
```

This is a heuristic workaround until native context-threshold hooks ship.

## Verified Claims
- ✅ `PreCompact` hook exists and fires before auto-compaction — [Claude Code Hooks Docs](https://code.claude.com/docs/en/hooks)
- ✅ `agent`-type hooks can spawn background sub-agents with tool access including `Read`, `Write`, `AskUserQuestion` — [Hooks Reference](https://code.claude.com/docs/en/hooks)
- ✅ `transcript_path` is available in hook context, giving agents access to the full conversation — [Hooks Reference](https://code.claude.com/docs/en/hooks)
- ✅ `AskUserQuestion` is a real tool Claude Code exposes — confirmed via docs
- ❌ "Hook triggers at 80% context" — **incorrect as a native feature**. No native percentage-threshold hook exists. PreCompact fires at ~95%. Feature requests for configurable thresholds (e.g., 80%) are open but unimplemented as of April 2026. — [GitHub Issue #15946](https://github.com/anthropics/claude-code/issues/15946), [Issue #27969](https://github.com/anthropics/claude-code/issues/27969)
- ⚠️ "Constantly monitoring" — hooks are event-driven, not polling. Stop hook fires per-turn; PreCompact fires once near context exhaustion. Neither is "constant monitoring" in the traditional sense.

## Sources
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Feature Request: Context Threshold Hooks (closed as duplicate)](https://github.com/anthropics/claude-code/issues/15946)
- [Feature Request: Expose context % to hooks](https://github.com/anthropics/claude-code/issues/27969)
- [Original Source](https://www.instagram.com/reel/DW_wEu9jQt7/?igsh=MTRjOWIzdDd6dTdzeA==)

---
*Auto-generated by claude-knowledge-pipeline | 2026-04-15*
