#!/usr/bin/env python3
"""
NIM Image Proxy — port 7457
Translates OpenAI /v1/images/generations requests to NIM FLUX API,
so OpenDesign (and any OpenAI-compatible image client) can use NIM
FLUX models transparently.

OD sends:  POST /v1/images/generations {model, prompt, n, size, response_format}
Proxy:     POST https://ai.api.nvidia.com/v1/genai/<nim-model> {prompt, width, height, steps}
Returns:   {created, data: [{b64_json|url}]}

Also served:
  GET /health        → 200 {"ok": true}
  GET /v1/models     → list of supported image models
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = int(os.environ.get("NIM_PROXY_PORT", "7457"))

# OD model name → NIM model endpoint segment
MODEL_MAP = {
    # Schnell (fast, 4 steps)
    "flux-schnell":              "black-forest-labs/flux.1-schnell",
    "flux.1-schnell":            "black-forest-labs/flux.1-schnell",
    "flux-1-schnell":            "black-forest-labs/flux.1-schnell",
    "black-forest-labs/flux.1-schnell": "black-forest-labs/flux.1-schnell",
    # Dev (quality, 20+ steps)
    "flux-dev":                  "black-forest-labs/flux.1-dev",
    "flux.1-dev":                "black-forest-labs/flux.1-dev",
    "flux-1-dev":                "black-forest-labs/flux.1-dev",
    "black-forest-labs/flux.1-dev": "black-forest-labs/flux.1-dev",
    # Kontext (image editing)
    "flux-kontext-pro":          "black-forest-labs/flux.1-kontext-dev",
    "flux-kontext-dev":          "black-forest-labs/flux.1-kontext-dev",
    "flux.1-kontext-dev":        "black-forest-labs/flux.1-kontext-dev",
    # Pro (maps to dev — closest NIM equivalent)
    "flux-pro":                  "black-forest-labs/flux.1-dev",
    "flux-1.1-pro":              "black-forest-labs/flux.1-dev",
    "flux-1-pro":                "black-forest-labs/flux.1-dev",
    # DALL-E pass-through aliases → schnell
    "dall-e-3":                  "black-forest-labs/flux.1-schnell",
    "dall-e-2":                  "black-forest-labs/flux.1-schnell",
    "gpt-image-2":               "black-forest-labs/flux.1-schnell",
}

DEFAULT_NIM_MODEL = "black-forest-labs/flux.1-schnell"

# Valid NIM dimensions (width and height independently)
VALID_DIMS = [768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344]

# Default steps per model
MODEL_STEPS = {
    "black-forest-labs/flux.1-schnell": 4,
    "black-forest-labs/flux.1-dev": 20,
    "black-forest-labs/flux.1-kontext-dev": 20,
}


def _clamp_dim(v: int) -> int:
    return min(VALID_DIMS, key=lambda x: abs(x - v))


def _parse_size(size_str: str) -> tuple[int, int]:
    """Parse '1024x1024' → (1024, 1024), clamped to valid NIM dims."""
    try:
        w, h = size_str.lower().split("x")
        return _clamp_dim(int(w)), _clamp_dim(int(h))
    except Exception:
        return 1024, 1024


def _load_nim_key() -> str:
    key = os.environ.get("NVIDIA_API_KEY", "")
    if key:
        return key
    secrets = Path.home() / ".nanobot/secrets.env"
    if secrets.exists():
        for line in secrets.read_text(errors="ignore").splitlines():
            if "NVIDIA_API_KEY=" in line and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    hermes_env = Path.home() / ".hermes/.env"
    if hermes_env.exists():
        for line in hermes_env.read_text(errors="ignore").splitlines():
            if "NVIDIA_API_KEY=" in line and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    return ""


def nim_generate(nim_model: str, prompt: str, width: int, height: int,
                 steps: int, api_key: str) -> str:
    """Call NIM FLUX API. Returns base64-encoded PNG string."""
    endpoint = f"https://ai.api.nvidia.com/v1/genai/{nim_model}"
    payload = json.dumps({
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": 0 if "schnell" in nim_model else 3.5,
        "seed": 0,
    }).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "riri-nim-proxy/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read())
    if "artifacts" not in data or not data["artifacts"]:
        raise RuntimeError(f"No artifacts in NIM response: {list(data.keys())}")
    return data["artifacts"][0]["base64"]


MODELS_LIST = {
    "object": "list",
    "data": [
        {"id": k, "object": "model", "owned_by": "nvidia-nim"}
        for k in MODEL_MAP
    ],
}


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Quiet logging — only errors go to stderr
        pass

    def _send_json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/health", "/healthz"):
            self._send_json(200, {"ok": True, "service": "nim-image-proxy"})
        elif self.path.startswith("/v1/models"):
            self._send_json(200, MODELS_LIST)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/images/generations":
            self._send_json(404, {"error": "only /v1/images/generations is supported"})
            return

        # Read body
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)
        except Exception:
            self._send_json(400, {"error": "invalid JSON"})
            return

        prompt = body.get("prompt", "")
        if not prompt:
            self._send_json(400, {"error": "prompt is required"})
            return

        # Resolve model
        req_model = body.get("model", "")
        nim_model = MODEL_MAP.get(req_model, MODEL_MAP.get(req_model.lower(), DEFAULT_NIM_MODEL))

        # Resolve dimensions
        size_str = body.get("size", "1024x1024")
        width, height = _parse_size(size_str)

        # Resolve steps
        steps = body.get("steps", MODEL_STEPS.get(nim_model, 4))

        # Get API key (check Authorization header first, then env)
        auth = self.headers.get("Authorization", "")
        api_key = auth.replace("Bearer ", "").strip() if auth else ""
        if not api_key or len(api_key) < 10:
            api_key = _load_nim_key()
        if not api_key:
            self._send_json(401, {"error": "NVIDIA_API_KEY not configured"})
            return

        # Call NIM
        try:
            b64 = nim_generate(nim_model, prompt, width, height, steps, api_key)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")[:400]
            print(f"[nim-proxy] NIM error {e.code}: {err_body}", file=sys.stderr)
            self._send_json(502, {"error": f"NIM API error {e.code}: {err_body}"})
            return
        except Exception as e:
            print(f"[nim-proxy] Error: {e}", file=sys.stderr)
            self._send_json(502, {"error": str(e)})
            return

        # Return in OpenAI format
        n = int(body.get("n", 1))
        resp_format = body.get("response_format", "b64_json")

        if resp_format == "url":
            # Save to temp file and return a file:// URL
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir="/tmp")
            tmp.write(base64.b64decode(b64))
            tmp.close()
            data_item = {"url": f"file://{tmp.name}"}
        else:
            data_item = {"b64_json": b64}

        self._send_json(200, {
            "created": int(time.time()),
            "data": [data_item] * n,
            "model": nim_model,
        })


def main():
    api_key = _load_nim_key()
    if not api_key:
        print("[nim-proxy] WARNING: NVIDIA_API_KEY not found — image gen will fail", file=sys.stderr)

    server = HTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"[nim-proxy] Listening on port {PORT} (NIM FLUX image proxy)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
