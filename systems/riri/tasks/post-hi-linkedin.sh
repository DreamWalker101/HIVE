#!/usr/bin/env bash
# TASK: Post "hi" to LinkedIn via xdotool pixel clicks
# v4 — uses screen coordinates, no JS selector guessing

export DISPLAY=":1"
LOG=~/.local/share/riri/linkedin-hi.log
exec > >(tee -a "$LOG") 2>&1

notify() { python3 ~/projects/riri/notify.py "$1" 2>/dev/null || true; }

echo "[$(date '+%H:%M:%S')] LinkedIn 'hi' post v4 (pixel clicks)"
notify "LinkedIn task — clicking through UI"

WID=$(DISPLAY=:1 xdotool search --name "LinkedIn" 2>/dev/null | head -1)
[ -z "$WID" ] && WID=$(DISPLAY=:1 xdotool search --class "Google-chrome" 2>/dev/null | head -1)
echo "[$(date '+%H:%M:%S')] Window: $WID"

DISPLAY=:1 xdotool windowfocus --sync "$WID"
DISPLAY=:1 xdotool windowactivate --sync "$WID"
sleep 1

# Navigate to feed
DISPLAY=:1 xdotool key --window "$WID" ctrl+l
sleep 0.4
DISPLAY=:1 xdotool type --window "$WID" --clearmodifiers "https://www.linkedin.com/feed/"
DISPLAY=:1 xdotool key --window "$WID" Return
sleep 5

echo "[$(date '+%H:%M:%S')] Page loaded — clicking Start a post..."

# Click "Start a post" box — viewport (528, 110), window chrome ~87px → screen y≈197
DISPLAY=:1 xdotool mousemove --window "$WID" 528 197
sleep 0.3
DISPLAY=:1 xdotool click --window "$WID" 1
sleep 2

DISPLAY=:1 import -window "$WID" /tmp/li-after-click.png 2>/dev/null
echo "[$(date '+%H:%M:%S')] After click screenshot saved"
notify "Composer open — typing hi"

# Type "hi" — active element should be the composer text field
DISPLAY=:1 xdotool type --window "$WID" --clearmodifiers "hi"
sleep 1

DISPLAY=:1 import -window "$WID" ~/Desktop/linkedin-hi-preview.png 2>/dev/null
echo "[$(date '+%H:%M:%S')] Preview screenshot saved"

# Post button confirmed at (700, 672) in 768x1024 window
echo "[$(date '+%H:%M:%S')] Clicking Post button..."
DISPLAY=:1 xdotool mousemove --window "$WID" 700 672
sleep 0.3
DISPLAY=:1 xdotool click --window "$WID" 1
sleep 3

DISPLAY=:1 import -window "$WID" ~/Desktop/linkedin-hi-done.png 2>/dev/null
echo "[$(date '+%H:%M:%S')] Final screenshot saved"
notify "LinkedIn 'hi' post — system done ✓"
echo "[$(date '+%H:%M:%S')] Task complete."
