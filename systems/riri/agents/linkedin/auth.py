#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 — one-time token fetch.
Run this ONCE to authorise RiRi to post on your behalf.
Saves LINKEDIN_ACCESS_TOKEN to ~/.nanobot/secrets.env (valid ~60 days).

BEFORE running:
  1. Go to https://developer.linkedin.com/apps → your app → Auth tab
  2. Under "Authorized Redirect URLs for your app" click [+ Add redirect URL]
  3. Enter:  http://localhost:8080/callback
  4. Save, then run:  python3 auth.py
"""

import base64, json, os, secrets, sys, urllib.parse, urllib.request, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SECRETS_FILE  = Path.home() / ".nanobot/secrets.env"
SCOPE         = "openid profile w_member_social"  # openid+profile for /v2/userinfo, w_member_social to post
AUTH_URL      = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL     = "https://www.linkedin.com/oauth/v2/accessToken"

import socket as _socket
def _free_port(preferred: int = 8080) -> int:
    """Return preferred port if free, else any available ephemeral port."""
    for port in [preferred, 8888, 9090, 7777, 0]:
        try:
            s = _socket.socket()
            s.bind(("127.0.0.1", port))
            p = s.getsockname()[1]
            s.close()
            return p
        except OSError:
            continue
    raise RuntimeError("No free port found")


def _load_env():
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌  LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not found in secrets.env")
    sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_member_urn(id_token: str) -> str:
    """Decode the JWT id_token to extract the 'sub' (member ID) without any API call."""
    try:
        parts = id_token.split(".")
        if len(parts) < 2:
            return ""
        payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        sub = data.get("sub", "")
        return f"urn:li:person:{sub}" if sub else ""
    except Exception:
        return ""


def _save_member_urn(urn: str):
    lines, found = [], False
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(errors="ignore").splitlines():
            k = line.split("=", 1)[0] if "=" in line else ""
            if k == "LINKEDIN_MEMBER_URN":
                lines.append(f"LINKEDIN_MEMBER_URN={urn}"); found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"LINKEDIN_MEMBER_URN={urn}")
    SECRETS_FILE.write_text("\n".join(lines) + "\n")


def _save_token(token: str, expires_in: int):
    lines = []
    found = False
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(errors="ignore").splitlines():
            k = line.split("=", 1)[0] if "=" in line else ""
            if k == "LINKEDIN_ACCESS_TOKEN":
                lines.append(f"LINKEDIN_ACCESS_TOKEN={token}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"LINKEDIN_ACCESS_TOKEN={token}")
    SECRETS_FILE.write_text("\n".join(lines) + "\n")
    days = expires_in // 86400
    print(f"✅  Token saved → {SECRETS_FILE}")
    print(f"⏱️   Expires in {days} days (~{days//30} months) — re-run auth.py when it expires")


# ── OAuth callback server ─────────────────────────────────────────────────────
_state     = secrets.token_urlsafe(16)
_auth_code = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        p      = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(p.query)

        if "error" in params:
            msg = params["error"][0].encode()
            self.send_response(400); self.end_headers()
            self.wfile.write(b"<h2>Auth error: " + msg + b"</h2>")
            return

        if params.get("state", [""])[0] != _state:
            self.send_response(400); self.end_headers()
            self.wfile.write(b"<h2>State mismatch - try again</h2>")
            return

        _auth_code = params.get("code", [""])[0]
        self.send_response(200); self.end_headers()
        self.wfile.write(
            b"<h2 style='font-family:sans-serif;color:green'>"
            b"&#x2705; RiRi is authorised! Close this tab.</h2>"
        )

    def log_message(self, *_):
        pass   # suppress HTTP logs


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global _auth_code

    port         = _free_port()
    redirect_uri = f"http://localhost:{port}/callback"

    # Step 1 — open LinkedIn auth page
    qs = urllib.parse.urlencode({
        "response_type": "code",
        "client_id":     CLIENT_ID,
        "redirect_uri":  redirect_uri,
        "scope":         SCOPE,
        "state":         _state,
    })
    url = f"{AUTH_URL}?{qs}"

    if port != 8080:
        print(f"⚠️   Port 8080 in use — using {port} instead.")
        print(f"    Make sure '{redirect_uri}' is in your LinkedIn app's")
        print(f"    Authorized Redirect URLs (Auth tab).\n")

    print(f"\n🌐  Opening LinkedIn in your browser…")
    print(f"    (if nothing opens, visit manually:)\n    {url}\n")
    webbrowser.open(url)

    # Step 2 — wait for callback
    print(f"⏳  Waiting for you to click 'Allow' in LinkedIn…")
    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    while not _auth_code:
        server.handle_request()
    server.server_close()
    print(f"✅  Got authorization code")

    # Step 3 — exchange code for token
    print("🔄  Exchanging code for access token…")
    body = urllib.parse.urlencode({
        "grant_type":    "authorization_code",
        "code":          _auth_code,
        "redirect_uri":  redirect_uri,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    req = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
    except urllib.request.HTTPError as e:
        print(f"❌  Token exchange failed: HTTP {e.code}")
        print(e.read().decode())
        sys.exit(1)

    token      = data.get("access_token", "")
    expires_in = data.get("expires_in", 0)
    id_token   = data.get("id_token", "")

    if not token:
        print("❌  No access_token in response:", data)
        sys.exit(1)

    _save_token(token, expires_in)

    # Extract member ID from id_token JWT (no extra API call needed)
    if id_token:
        member_urn = _extract_member_urn(id_token)
        if member_urn:
            _save_member_urn(member_urn)
            print(f"👤  Member URN cached: {member_urn}")

    print("\n🎉  All done! Run:  python3 api.py 'your post text'")


if __name__ == "__main__":
    main()
