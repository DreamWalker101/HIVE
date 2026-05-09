#!/usr/bin/env python3
"""
RiRi notification dispatcher.
Launches toast.py in the background — fire-and-forget.

Usage: python3 notify.py "message"
       riri-notify "message"          (if symlinked)
"""
import os, subprocess, sys

RIRI_DIR = os.path.expanduser("~/projects/riri")
TOAST_PY = os.path.join(RIRI_DIR, "toast.py")


def send(msg: str):
    # Ignore legacy overlay control commands
    if msg.strip() in ("expand", "hide", "collapse"):
        return
    # Strip legacy prefix
    if msg.startswith("notify:"):
        msg = msg[7:]
    if not msg.strip():
        return
    try:
        subprocess.Popen(
            ["python3", TOAST_PY, msg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")},
        )
    except Exception as e:
        # Silent — notifications are best-effort
        print(f"[notify] {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: notify.py <message>")
        sys.exit(1)
    send(" ".join(sys.argv[1:]))
