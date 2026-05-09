#!/bin/bash
# Stop hook — fires after every Claude turn. Logs session metadata.
INPUT=$(cat)
LOG="$HOME/HIVE/memory/sessions.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_ID=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id','unknown'))" 2>/dev/null)
CWD=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cwd',''))" 2>/dev/null)
mkdir -p "$(dirname "$LOG")"
echo "[$TIMESTAMP] session=$SESSION_ID cwd=$CWD" >> "$LOG"
