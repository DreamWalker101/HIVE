#!/usr/bin/env python3
"""
riri-project-done — signal RiRi that a project is complete.

When called from a Claude Code session (via Bash tool), it:
  1. Writes ~/.riri-project-done with the project name
  2. The Stop hook picks it up, runs case_study.py automatically
  3. case_study.py → Groq case study → ChromaDB → LinkedIn post

Usage:
  riri-project-done                   # uses cwd to infer project name
  riri-project-done "my-project"      # explicit name

Tip — drop this at the end of any Claude Code task:
  python3 ~/projects/riri/project_done.py
"""

import os, sys
from pathlib import Path

MARKER = Path.home() / ".riri-project-done"

def main():
    # Determine project name
    if len(sys.argv) > 1:
        proj = " ".join(sys.argv[1:]).strip()
    else:
        cwd   = Path.cwd()
        parts = cwd.parts
        proj  = "unknown"
        for marker_dir in ["projects", "Desktop", "home"]:
            if marker_dir in parts:
                idx = list(parts).index(marker_dir)
                if idx + 1 < len(parts):
                    proj = parts[idx + 1]
                    break
        if proj == "unknown":
            proj = cwd.name

    MARKER.write_text(proj)
    print(f"✅  Project-done marker set for '{proj}'")
    print(f"    RiRi will generate a case study + LinkedIn post when this session ends.")

if __name__ == "__main__":
    main()
