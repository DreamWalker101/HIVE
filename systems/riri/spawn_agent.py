#!/usr/bin/env python3
"""
spawn_agent.py — RiRi's sub-agent launcher.

Spawns Claude Code or Codex CLI for complex coding tasks that benefit
from a full agentic coding session. RiRi hands off the task, streams
output, and returns a summary.

Usage:
  python3 ~/projects/riri/spawn_agent.py claude "refactor auth.py to use JWT" --cwd ~/projects/myapp
  python3 ~/projects/riri/spawn_agent.py codex  "add unit tests for utils.py"  --cwd ~/projects/myapp
  python3 ~/projects/riri/spawn_agent.py claude "what does this file do?" --cwd ~/projects/myapp --safe

Flags:
  --cwd     Working directory for the agent (default: current dir)
  --safe    Suggest-only mode (no file writes) — for review/analysis tasks
  --timeout Max seconds to wait (default: 300)
"""

import sys
import os
import subprocess
import argparse
import shutil
from pathlib import Path


AGENTS = {
    "claude": {
        "description": "Claude Code — multi-file agentic coding, refactors, complex implementations",
        "check": "claude",
    },
    "codex": {
        "description": "OpenAI Codex CLI — quick focused changes, GPT-4o/5 powered",
        "check": "codex",
    },
}

# Destructive keywords that require approval before spawning
DESTRUCTIVE_PATTERNS = [
    "delete", "remove", "drop", "truncate", "rm ", "wipe", "reset --hard",
    "overwrite all", "replace all", "rewrite everything",
]


def check_available(agent: str) -> bool:
    return shutil.which(AGENTS[agent]["check"]) is not None


def needs_approval(task: str) -> bool:
    task_lower = task.lower()
    return any(p in task_lower for p in DESTRUCTIVE_PATTERNS)


def build_command(agent: str, task: str, cwd: str, safe: bool) -> list[str]:
    if agent == "claude":
        cmd = ["claude", "--dangerously-skip-permissions", "--print", task]
        if safe:
            # Safe mode: don't skip permissions, suggest only
            cmd = ["claude", "--print", task]
        return cmd

    elif agent == "codex":
        approval_mode = "suggest" if safe else "auto-edit"
        return ["codex", "--approval-mode", approval_mode, task]

    raise ValueError(f"Unknown agent: {agent}")


def run_agent(agent: str, task: str, cwd: str, safe: bool, timeout: int) -> dict:
    """
    Spawn the agent and stream its output.
    Returns {"success": bool, "output": str, "agent": str, "task": str}
    """
    if not check_available(agent):
        return {
            "success": False,
            "output": f"{agent} CLI not found. Check PATH or install it.",
            "agent": agent,
            "task": task,
        }

    cmd = build_command(agent, task, cwd, safe)
    work_dir = Path(cwd).expanduser().resolve() if cwd else Path.cwd()

    print(f"[spawn] Launching {agent.upper()} in {work_dir}", file=sys.stderr)
    print(f"[spawn] Task: {task}", file=sys.stderr)
    print(f"[spawn] Mode: {'SAFE/suggest' if safe else 'FULL'}", file=sys.stderr)
    print(f"[spawn] Command: {' '.join(cmd)}", file=sys.stderr)
    print("─" * 60, file=sys.stderr)

    output_lines = []
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in iter(proc.stdout.readline, ""):
            print(line, end="", flush=True)  # stream to stdout
            output_lines.append(line)

        proc.wait(timeout=timeout)
        success = proc.returncode == 0

    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append(f"\n[spawn] TIMEOUT after {timeout}s — agent killed.")
        success = False
    except FileNotFoundError:
        output_lines.append(f"[spawn] ERROR: {agent} CLI not found in PATH.")
        success = False
    except Exception as e:
        output_lines.append(f"[spawn] ERROR: {e}")
        success = False

    return {
        "success": success,
        "output": "".join(output_lines),
        "agent": agent,
        "task": task,
        "cwd": str(work_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="RiRi sub-agent launcher")
    parser.add_argument("agent", choices=list(AGENTS.keys()), help="Agent to use: claude or codex")
    parser.add_argument("task", help="Task description for the agent")
    parser.add_argument("--cwd", default=".", help="Working directory (default: current)")
    parser.add_argument("--safe", action="store_true", help="Suggest-only mode, no file writes")
    parser.add_argument("--timeout", type=int, default=300, help="Max seconds (default: 300)")
    parser.add_argument("--force", action="store_true", help="Skip destructive action check")
    args = parser.parse_args()

    # Approval gate for destructive tasks
    if needs_approval(args.task) and not args.safe and not args.force:
        print(f"[spawn] APPROVAL REQUIRED — task contains destructive keywords.")
        print(f"[spawn] Task: {args.task}")
        print(f"[spawn] Re-run with --safe (suggest only) or --force to proceed.")
        sys.exit(2)

    result = run_agent(
        agent=args.agent,
        task=args.task,
        cwd=args.cwd,
        safe=args.safe,
        timeout=args.timeout,
    )

    print("─" * 60, file=sys.stderr)
    print(f"[spawn] Done. Success: {result['success']}", file=sys.stderr)
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
