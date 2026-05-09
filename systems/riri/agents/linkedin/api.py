#!/usr/bin/env python3
"""
LinkedIn REST API — clean text posting via OAuth access token.
No browser automation, no xdotool, zero ToS risk.

Prerequisites:
  1. Run auth.py once to get LINKEDIN_ACCESS_TOKEN in secrets.env
  2. python3 api.py "your post text"

API reference: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
"""

import json, os, sys, urllib.error, urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
SECRETS_FILE     = Path.home() / ".nanobot/secrets.env"
LINKEDIN_VERSION = "202503"
BASE              = "https://api.linkedin.com"


# ── Env loader ────────────────────────────────────────────────────────────────
def _load_env():
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()


# ── API helpers ───────────────────────────────────────────────────────────────
def _api(method: str, path: str, body=None, token: str = "") -> dict:
    """Generic LinkedIn REST call. Returns (status, data) or raises."""
    token = token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError(
            "No LINKEDIN_ACCESS_TOKEN found. Run auth.py first."
        )

    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization":             f"Bearer {token}",
            "Content-Type":              "application/json",
            "LinkedIn-Version":          LINKEDIN_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return {
                "status":  resp.status,
                "headers": dict(resp.headers),
                "body":    json.loads(raw) if raw.strip() else {},
            }
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {raw[:400]}")


def get_member_urn(token: str = "") -> str:
    """Return 'urn:li:person:<id>' for the authenticated user.

    Priority:
    1. LINKEDIN_MEMBER_URN env var (manual override — fastest, no API call)
    2. /v2/userinfo  (OpenID Connect — needs 'openid profile' scope)
    3. /v2/me        (legacy — needs 'r_liteprofile' scope)

    To use the manual override, add to ~/.nanobot/secrets.env:
        LINKEDIN_MEMBER_URN=urn:li:person:YOUR_NUMERIC_ID
    Find your numeric ID at: https://www.linkedin.com/in/[username]/ → view source → search 'id'
    """
    token = token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")

    # 1. Manual override — skip all API calls
    cached = os.getenv("LINKEDIN_MEMBER_URN", "")
    if cached:
        return cached

    # 2. Try OpenID Connect userinfo (needs openid + profile scope)
    try:
        req = urllib.request.Request(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        sub = data.get("sub", "")  # sub = numeric member ID
        if sub:
            urn = f"urn:li:person:{sub}"
            _cache_member_urn(urn)
            return urn
    except Exception:
        pass  # fall through to next method

    # 3. Try legacy /v2/me (needs r_liteprofile scope)
    try:
        result = _api("GET", "/v2/me", token=token)
        member_id = result["body"].get("id", "")
        if member_id:
            urn = f"urn:li:person:{member_id}"
            _cache_member_urn(urn)
            return urn
    except Exception:
        pass

    raise RuntimeError(
        "Could not determine LinkedIn member URN.\n"
        "Fix: Add 'Sign In with LinkedIn using OpenID Connect' product to your LinkedIn app "
        "(developer.linkedin.com → your app → Products tab), then run auth.py again.\n"
        "OR: Set LINKEDIN_MEMBER_URN=urn:li:person:YOUR_ID in ~/.nanobot/secrets.env"
    )


def _cache_member_urn(urn: str):
    """Save member URN to secrets.env so we don't need to look it up again."""
    try:
        lines = []
        found = False
        if SECRETS_FILE.exists():
            for line in SECRETS_FILE.read_text(errors="ignore").splitlines():
                k = line.split("=", 1)[0] if "=" in line else ""
                if k == "LINKEDIN_MEMBER_URN":
                    lines.append(f"LINKEDIN_MEMBER_URN={urn}")
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f"LINKEDIN_MEMBER_URN={urn}")
        SECRETS_FILE.write_text("\n".join(lines) + "\n")
    except Exception:
        pass  # non-fatal


# ── Main action ───────────────────────────────────────────────────────────────
def post_text(text: str, token: str = "") -> dict:
    """
    Publish a text post to the authenticated member's LinkedIn feed.

    Returns:
      {"success": True,  "urn": "urn:li:share:...", "status": 201}
      {"success": False, "error": "...", "status": <code>}
    """
    token = token or os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        return {
            "success": False,
            "error":   "No LINKEDIN_ACCESS_TOKEN. Run auth.py first.",
        }

    # 1. Get author URN
    try:
        author = get_member_urn(token)
    except Exception as e:
        return {"success": False, "error": f"member URN lookup failed: {e}"}

    # 2. Build payload (new Posts API format)
    payload = {
        "author":       author,
        "commentary":   text,
        "visibility":   "PUBLIC",
        "distribution": {
            "feedDistribution":            "MAIN_FEED",
            "targetEntities":              [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState":          "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    # 3. POST /rest/posts
    try:
        result  = _api("POST", "/rest/posts", body=payload, token=token)
        post_id = result["headers"].get("x-restli-id", "")
        if not post_id:
            return {"success": False, "error": f"API returned {result['status']} but no post ID in response headers. Raw headers: {dict(list(result['headers'].items())[:6])}"}
        post_url = f"https://www.linkedin.com/feed/update/{post_id}"
        return {
            "success": True,
            "urn":     post_id,
            "url":     post_url,
            "status":  result["status"],
            "author":  author,
        }
    except RuntimeError as e:
        return {"success": False, "error": str(e)}


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Post text to LinkedIn via REST API")
    parser.add_argument("text",    nargs="+",      help="Post content")
    parser.add_argument("--token", default="",     help="Override access token")
    parser.add_argument("--dry-run", action="store_true", help="Print payload, don't post")
    args = parser.parse_args()

    full_text = " ".join(args.text)

    if args.dry_run:
        print(f"[dry-run] Would post ({len(full_text)} chars):")
        print(full_text)
        sys.exit(0)

    result = post_text(full_text, token=args.token)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("success") else 1)
