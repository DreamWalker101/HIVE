#!/usr/bin/env python3
"""
RiRi Composio Tools — thin wrapper for common "dumb task" integrations.
Requires COMPOSIO_API_KEY in ~/.nanobot/secrets.env

One-time setup per service:
  python3 composio_tools.py setup linkedin
  python3 composio_tools.py setup googledocs
  python3 composio_tools.py setup notion

Usage:
  from composio_tools import run_action
  run_action("GOOGLESHEETS_CREATE_SPREADSHEET", {"title": "My Sheet"})
"""

import json, os, sys
from pathlib import Path

SECRETS = Path.home() / ".nanobot/secrets.env"

def _load_env():
    if SECRETS.exists():
        for line in SECRETS.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()


def run_action(action: str, params: dict = None, entity_id: str = "default") -> dict:
    """
    Execute a Composio action.

    Examples:
      run_action("GOOGLEDOCS_CREATE_DOCUMENT", {"title": "Case Study"})
      run_action("NOTION_CREATE_PAGE", {"title": "RiRi Update", "content": "..."})
      run_action("GITHUB_CREATE_OR_UPDATE_FILE", {"owner": "...", "repo": "...", "path": "README.md", "content": "..."})
    """
    try:
        from composio import ComposioToolSet, Action
        toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY", ""))
        action_enum = getattr(Action, action, None)
        if not action_enum:
            return {"success": False, "error": f"Action {action} not found"}
        result = toolset.execute_action(action=action_enum, params=params or {})
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_available_actions(app: str) -> list:
    """List all available actions for an app (e.g. 'googledocs', 'notion', 'linkedin')"""
    try:
        from composio import ComposioToolSet, App, Action
        toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY", ""))
        app_enum = getattr(App, app.upper(), None)
        if not app_enum:
            return []
        actions = toolset.get_actions(app=app_enum)
        return [action.value for action in actions]
    except Exception as e:
        return [f"error: {e}"]


def setup_integration(app: str):
    """Authenticate with an app (opens browser for OAuth)."""
    import subprocess
    subprocess.run(["composio", "add", app])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: composio_tools.py setup <app>")
        print("       composio_tools.py list <app>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "setup" and len(sys.argv) > 2:
        setup_integration(sys.argv[2])
    elif cmd == "list" and len(sys.argv) > 2:
        actions = list_available_actions(sys.argv[2])
        print(f"\nActions for {sys.argv[2]}:")
        for a in actions:
            print(f"  {a}")
    else:
        print("Commands: setup <app>, list <app>")
