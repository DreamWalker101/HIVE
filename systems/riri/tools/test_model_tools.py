#!/usr/bin/env python3
"""
Test tool call support across NIM models.
Usage:
    python3 tools/test_model_tools.py                    # test priority list
    python3 tools/test_model_tools.py --model <model-id>  # test single model
    python3 tools/test_model_tools.py --all               # test everything
"""
import os
import sys
import json
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

NIM_BASE = "https://integrate.api.nvidia.com/v1"

PRIORITY_MODELS = [
    "deepseek-ai/deepseek-v4-pro",
    "deepseek-ai/deepseek-v4-flash",
    "qwen/qwen3-coder-480b-a35b-instruct",
    "qwen/qwen3-next-80b-a3b-instruct",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "meta/llama-4-maverick-17b-128e-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mistral-large-3-675b-instruct-2512",
    "mistralai/devstral-2-123b-instruct-2512",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "moonshotai/kimi-k2.6",
    "moonshotai/kimi-k2-instruct",
]

KNOWN_NO_TOOLS = {
    "moonshotai/kimi-k2-thinking",
    "qwen/qwen3-next-80b-a3b-thinking",
}

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_result",
        "description": "Return a computed result",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "description": "The result value"}
            },
            "required": ["value"],
        },
    },
}

def get_api_key():
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        for env_file in ["~/.nanobot/secrets.env", "~/.hermes/.env"]:
            path = os.path.expanduser(env_file)
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        if line.startswith("NVIDIA_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            break
            if key:
                break
    if not key:
        print("ERROR: NVIDIA_API_KEY not found. Set it or add to secrets.env")
        sys.exit(1)
    return key

def test_model(model_id: str, api_key: str, timeout: int = 20) -> dict:
    if model_id in KNOWN_NO_TOOLS:
        return {"model": model_id, "status": "skip", "reason": "known thinking-only model"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Call get_result with value 'test-ok'"}],
        "tools": [TOOL_SCHEMA],
        "tool_choice": "auto",
        "max_tokens": 150,
    }

    try:
        r = requests.post(
            f"{NIM_BASE}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        data = r.json()

        if r.status_code == 401 or r.status_code == 403:
            return {"model": model_id, "status": "auth_fail", "reason": data.get("detail", "auth error")}

        if r.status_code == 404:
            return {"model": model_id, "status": "not_found", "reason": "404"}

        if r.status_code != 200:
            return {"model": model_id, "status": "error", "reason": f"HTTP {r.status_code}: {data.get('detail', '')}"}

        choice = data.get("choices", [{}])[0]
        finish = choice.get("finish_reason", "")
        tool_calls = choice.get("message", {}).get("tool_calls")

        if tool_calls or finish == "tool_calls":
            called = tool_calls[0]["function"]["name"] if tool_calls else "unknown"
            return {"model": model_id, "status": "tools_ok", "reason": f"called {called}"}
        elif finish == "stop":
            content = choice.get("message", {}).get("content", "")[:80]
            return {"model": model_id, "status": "no_tools", "reason": f"text only: {content!r}"}
        else:
            return {"model": model_id, "status": "unknown", "reason": f"finish={finish}"}

    except requests.Timeout:
        return {"model": model_id, "status": "timeout", "reason": f">{timeout}s"}
    except Exception as e:
        return {"model": model_id, "status": "error", "reason": str(e)}

def fetch_all_models(api_key: str) -> list:
    r = requests.get(f"{NIM_BASE}/models", headers={"Authorization": f"Bearer {api_key}"})
    return [m["id"] for m in r.json().get("data", [])]

STATUS_EMOJI = {
    "tools_ok": "✅",
    "no_tools": "❌",
    "timeout": "⏱️",
    "auth_fail": "🔑",
    "not_found": "🚫",
    "error": "💥",
    "skip": "⏭️",
    "unknown": "❓",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Test a single model")
    parser.add_argument("--all", action="store_true", help="Test all NIM models")
    parser.add_argument("--timeout", type=int, default=20, help="Per-model timeout seconds")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.model:
        models = [args.model]
    elif args.all:
        print("Fetching full model list...")
        models = fetch_all_models(api_key)
        print(f"Found {len(models)} models\n")
    else:
        models = PRIORITY_MODELS

    print(f"Testing {len(models)} models (timeout={args.timeout}s, workers={args.workers})\n")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(test_model, m, api_key, args.timeout): m for m in models}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            emoji = STATUS_EMOJI.get(result["status"], "?")
            print(f"{emoji}  {result['model']:<55} {result['reason']}")

    print("\n--- Summary ---")
    by_status = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r["model"])

    for status, mlist in sorted(by_status.items()):
        emoji = STATUS_EMOJI.get(status, "?")
        print(f"\n{emoji} {status.upper()} ({len(mlist)}):")
        for m in sorted(mlist):
            print(f"   {m}")

    # Save results
    out_path = os.path.expanduser("~/projects/riri/docs/models/tool_test_results.json")
    with open(out_path, "w") as f:
        json.dump({"tested": results, "timestamp": __import__("datetime").datetime.now().isoformat()}, f, indent=2)
    print(f"\nResults saved to {out_path}")

if __name__ == "__main__":
    main()
