#!/bin/bash
# UserPromptSubmit hook — logs each user prompt for grep memory
INPUT=$(cat)
LOG="$HOME/HIVE/memory/prompts.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PROMPT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('prompt','')[:300].replace(chr(10),' '))" 2>/dev/null)
mkdir -p "$(dirname "$LOG")"
echo "[$TIMESTAMP] $PROMPT" >> "$LOG"
