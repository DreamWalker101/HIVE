#!/bin/bash
# PreCompact hook — fires at ~95% context. Distills transcript to memory.
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('transcript_path',''))" 2>/dev/null)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
MEMORY_FILE="$HOME/HIVE/memory/SESSION_INSIGHTS.md"

mkdir -p "$(dirname "$MEMORY_FILE")"

if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  echo "" >> "$MEMORY_FILE"
  echo "## Session — $TIMESTAMP" >> "$MEMORY_FILE"
  echo "transcript: $TRANSCRIPT" >> "$MEMORY_FILE"
  echo "---" >> "$MEMORY_FILE"
  echo "_Distill insights from this transcript manually or via: claude --print 'Read $TRANSCRIPT and summarize the 5 key findings into bullet points' >> $MEMORY_FILE_" >> "$MEMORY_FILE"
fi
