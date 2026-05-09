#!/usr/bin/env python3
"""
RiRi Dispatcher
───────────────
Lightweight intent classifier that runs BEFORE the main LLM.
Uses gemma3:4b locally — no API cost, ~200ms, no network required.

What it does:
  1. Classifies the user's message into an intent
  2. Selects only the 2-3 relevant skill schemas to load
  3. Decides if a retrieval fetch is needed and what to search for

This prevents token flooding — instead of sending 50+ tool schemas
to the main model, only 2-3 relevant ones are passed.

Usage:
  from dispatcher import dispatch
  result = dispatch("write a case study for my riri project")
  # → {"intent": "content", "skills": ["case-study"], "fetch": {"queries": ["riri project"]}}
"""

import json
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
DISPATCHER_MODEL = "gemma3:4b"  # local, fast, free

# ── Skill registry (compact — just names + one-line descriptions) ──────────────
# This is what the dispatcher sees — NOT the full schemas. ~300 tokens total.
SKILL_REGISTRY = {
    "case-study":       "generate a case study or LinkedIn post from a project",
    "pipeline-report":  "show what Ahmed worked on recently, session history, activity",
    "evolve":           "run RiRi self-improvement cycle, review herself, evolution plan",
    "browse":           "open a URL, browse the web, take screenshots, fill forms",
    "shell":            "run a shell command, execute code, manage files, git operations",
    "linkedin-post":    "post content to LinkedIn directly",
    "github":           "push to GitHub, commit code, manage repositories",
    "search-memory":    "search past conversations, what was discussed before",
    "search-projects":  "semantic search across project files and knowledge base",
    "find-skills":      "discover and install new community skills from skills.sh",
    "google-workspace": "Gmail, Calendar, Google Drive, Sheets operations",
    "whatsapp":         "send WhatsApp messages",
    "voice":            "transcribe audio, text to speech",
    "image":            "describe, analyse, or generate images",
    "cli-anything":     "use any of the 52 CLI-Anything tools (blender, gimp, comfyui, etc)",
}

INTENT_TYPES = {
    "conversation": "casual chat, questions, opinions, explanations — no tools needed",
    "retrieval":    "find something: search projects, past work, tools, knowledge base",
    "content":      "create something: case study, post, write-up, documentation",
    "action":       "do something on the system: run command, push git, open browser",
    "social":       "post to LinkedIn, manage social content",
    "workspace":    "Gmail, Calendar, Drive, Sheets",
    "system":       "manage RiRi herself: evolve, settings, skills, voice",
}

DISPATCHER_SYSTEM = f"""You are a dispatcher for RiRi, an AI personal assistant.
Your ONLY job: read a message and output a JSON object. Nothing else.

AVAILABLE SKILLS:
{json.dumps(SKILL_REGISTRY, indent=2)}

INTENT TYPES:
{json.dumps(INTENT_TYPES, indent=2)}

Output exactly this JSON format, no other text:
{{
  "intent": "<one of the intent types>",
  "skills": ["<skill-name>", "<skill-name>"],
  "needs_fetch": true or false,
  "fetch_queries": ["<search term>"],
  "fetch_skill_search": "<search term for skills.sh if no local skill matches, else null>",
  "has_file": false,
  "reasoning": "<one sentence>"
}}

Rules:
- skills: pick at most 3, only the ones actually needed
- needs_fetch: true if message references past work, projects, files, or knowledge base
- fetch_queries: 1-3 short search terms for semantic search
- conversation intent: skills=[], needs_fetch=false
- If unsure: lean toward fewer skills, not more"""


def dispatch(message: str, file_path: str = None) -> dict:
    """
    Classify a message and return routing instructions.
    Falls back to a safe default if Ollama is unavailable.
    """
    user_prompt = f'Message: "{message}"'
    if file_path:
        user_prompt += f'\nFile attached: {file_path}'

    try:
        payload = {
            "model":  DISPATCHER_MODEL,
            "prompt": f"{DISPATCHER_SYSTEM}\n\n{user_prompt}\n\nJSON:",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 300},
        }
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = json.loads(r.read()).get("response", "").strip()

        # Extract JSON from response (model might add prose around it)
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
            # Validate and fill defaults
            return {
                "intent":              result.get("intent", "conversation"),
                "skills":              result.get("skills", [])[:3],
                "needs_fetch":         bool(result.get("needs_fetch", False)),
                "fetch_queries":       result.get("fetch_queries", [])[:3],
                "fetch_skill_search":  result.get("fetch_skill_search"),
                "has_file":            bool(file_path or result.get("has_file", False)),
                "file_path":           file_path,
                "reasoning":           result.get("reasoning", ""),
            }
    except Exception as e:
        # Dispatcher failure is non-fatal — fall back to safe default
        pass

    # Safe fallback: pass everything through with minimal assumptions
    return {
        "intent":             "conversation",
        "skills":             [],
        "needs_fetch":        False,
        "fetch_queries":      [],
        "fetch_skill_search": None,
        "has_file":           bool(file_path),
        "file_path":          file_path,
        "reasoning":          "dispatcher unavailable, using fallback",
    }


def format_for_context(dispatch_result: dict, fetch_result: dict = None) -> str:
    """
    Format dispatch + fetch results into a compact context block
    to prepend to the main LLM's system prompt.
    Keeps it tight — this goes into the main model's context.
    """
    lines = []

    # Intent signal (helps RiRi understand what Ahmed wants)
    intent = dispatch_result.get("intent", "")
    if intent and intent != "conversation":
        lines.append(f"[Intent: {intent}]")

    # Fetched knowledge
    if fetch_result:
        chunks = fetch_result.get("chunks", [])
        if chunks:
            lines.append("[Relevant knowledge retrieved:]")
            for c in chunks[:3]:  # max 3 chunks to stay lean
                score  = c.get("score", 0)
                source = Path(c.get("source", "?")).name
                text   = c.get("content", "")[:300]
                if score > 0.5:
                    lines.append(f"  [{source}] {text}")

        file_type = fetch_result.get("file_type")
        if file_type:
            lines.append(f"[File detected: {file_type.get('type', '?')} ({file_type.get('mime', '?')})]")

        skills_found = fetch_result.get("skills", [])
        if skills_found:
            lines.append("[Community skills found:]")
            for s in skills_found[:2]:
                lines.append(f"  {s.get('name')}: {s.get('cmd')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "what did I work on this week"
    print(f"Dispatching: '{msg}'")
    result = dispatch(msg)
    print(json.dumps(result, indent=2))
