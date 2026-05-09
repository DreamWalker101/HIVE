#!/usr/bin/env bash
pkill -f "python3.*riri.py" 2>/dev/null
sleep 0.3
mkdir -p ~/.local/share/riri
export DISPLAY="${DISPLAY:-:1}"
# Load API keys
[ -f ~/projects/outreach-engine/.env ] && export $(grep -v '^#' ~/projects/outreach-engine/.env | xargs) 2>/dev/null
nohup python3 ~/projects/riri/riri.py >> ~/.local/share/riri/stdout.log 2>&1 &
echo "RiRi started (PID $!)"
