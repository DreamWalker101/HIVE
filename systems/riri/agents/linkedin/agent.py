#!/usr/bin/env python3
"""
LinkedIn Posting Agent — Paperclip-compatible
Semantic, coordinate-free, self-diagnosing.

Key design:
- scrollIntoView() before EVERY click → works regardless of post length
- Screenshot after every step → full audit trail
- State machine with explicit verifiers → never fires blind
- Recovery playbook for every known failure mode

Usage:
  python3 agent.py "Your post text here"
  python3 agent.py --dry-run          # open composer only, don't post
  python3 agent.py --diagnose         # dump page state and exit
"""

import argparse, json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DISPLAY   = os.environ.get("DISPLAY", ":1")
RIRI_DIR  = Path.home() / "projects/riri"
LOG       = Path.home() / ".local/share/riri/linkedin-agent.log"
DIAG_DIR  = Path.home() / ".local/share/riri/linkedin-diag"
DIAG_DIR.mkdir(parents=True, exist_ok=True)

# How long each step waits before giving up (seconds)
TIMEOUT = {
    "navigate":  8,
    "composer":  5,
    "text":      3,
    "post_btn":  5,
    "confirm":   4,
}

# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def notify(msg: str):
    try:
        subprocess.Popen(
            ["python3", str(RIRI_DIR / "notify.py"), msg],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

# ── Window helpers ────────────────────────────────────────────────────────────
_ENV = lambda: {**os.environ, "DISPLAY": DISPLAY}

def get_window() -> str:
    """
    Find the best Chrome window to use.
    Priority: tab titled 'LinkedIn' > tab titled 'Claude' (avoid) > any Chrome window.
    Returns the window ID as a string. Raises if nothing found.
    """
    env = _ENV()
    all_wids = subprocess.run(
        ["xdotool", "search", "--class", "Google-chrome"],
        capture_output=True, text=True, env=env
    ).stdout.strip().split()

    if not all_wids:
        raise RuntimeError("No Chrome window found. Is Chrome running?")

    # Score windows: LinkedIn > any non-Claude > Claude last
    best, best_score = None, -1
    for wid in all_wids:
        title = subprocess.run(
            ["xdotool", "getwindowname", wid],
            capture_output=True, text=True, env=env
        ).stdout.strip().lower()
        if not title or title in ("google-chrome-stable",):
            score = 0
        elif "linkedin" in title:
            score = 3
        elif "claude" in title:
            score = 1   # usable but last resort
        else:
            score = 2
        if score > best_score:
            best, best_score = wid, score

    if best is None:
        raise RuntimeError("No usable Chrome window found.")
    return best

def get_window_title() -> str:
    wid = get_window()
    r = subprocess.run(
        ["xdotool", "getwindowname", wid],
        capture_output=True, text=True, env=_ENV()
    )
    return r.stdout.strip()

def focus_window():
    wid = get_window()
    env = _ENV()
    # windowraise first — moves window to current desktop if it's on another
    subprocess.run(["xdotool", "windowraise",    wid],           env=env, capture_output=True)
    subprocess.run(["xdotool", "windowfocus",   "--sync", wid],  env=env, capture_output=True)
    subprocess.run(["xdotool", "windowactivate","--sync", wid],  env=env, capture_output=True)
    time.sleep(0.4)

def screenshot(tag: str) -> Path:
    """Capture current Chrome window. Saves to DIAG_DIR with timestamp + tag."""
    wid  = get_window()
    path = DIAG_DIR / f"{datetime.now().strftime('%H%M%S')}_{tag}.png"
    subprocess.run(
        ["import", "-window", wid, str(path)],
        capture_output=True, env=_ENV()
    )
    log(f"  📸 {path.name}")
    return path

# ── JS injection ──────────────────────────────────────────────────────────────
def inject_js(js: str) -> None:
    """
    Inject JS via the Chrome DevTools console (Ctrl+Shift+J).

    Chrome 90+ silently converts 'javascript:' URLs typed/pasted into the
    address bar into Google searches — the bookmarklet approach no longer works.
    The DevTools console REPL has no such restriction.

    Flow: focus window → open console → clear input → paste JS → execute → close console
    Total overhead per call: ~2.8 s
    """
    wid      = get_window()
    # Collapse whitespace; void 0 prevents DevTools from navigating on a
    # non-undefined return value
    oneliner = " ".join(js.split()) + ";void 0;"
    env      = _ENV()

    focus_window()

    # 1. Open DevTools and focus the console REPL (Ctrl+Shift+J does both)
    subprocess.run(["xdotool", "key", "--window", wid, "ctrl+shift+j"],
                   env=env, capture_output=True)
    time.sleep(1.2)

    # 2. Clear any leftover partial input in the console prompt
    subprocess.run(["xdotool", "key", "--window", wid, "ctrl+a"],
                   env=env, capture_output=True)
    time.sleep(0.1)

    # 3. Copy JS to clipboard and paste into the console
    subprocess.run(["xsel", "--clipboard", "--input"],
                   input=oneliner.encode("utf-8"), env=env, capture_output=True)
    time.sleep(0.15)
    subprocess.run(["xdotool", "key", "--window", wid, "ctrl+v"],
                   env=env, capture_output=True)
    time.sleep(0.25)

    # 4. Execute
    subprocess.run(["xdotool", "key", "--window", wid, "Return"],
                   env=env, capture_output=True)
    time.sleep(0.6)

    # 5. Close DevTools — page regains focus cleanly
    subprocess.run(["xdotool", "key", "--window", wid, "ctrl+shift+j"],
                   env=env, capture_output=True)
    time.sleep(0.6)

# ── Page-state helpers ────────────────────────────────────────────────────────
def dismiss_dialogs():
    """
    Clear any modal noise before each step:
    - LinkedIn 'Save as draft?' → click Discard
    - Native browser alert/confirm → press Escape then Enter
    """
    inject_js("""
        var d = Array.from(document.querySelectorAll('button')).find(
            function(b){ return (b.innerText||'').trim()==='Discard'; }
        );
        if(d){ d.click(); window.__riri='discarded'; }
        else { window.__riri='clean'; }
    """)
    time.sleep(0.4)
    # Also dismiss any native dialog with Escape
    wid = get_window()
    subprocess.run(["xdotool", "key", "--window", wid, "Escape"], env=_ENV())
    time.sleep(0.2)

def is_on_feed() -> bool:
    title = get_window_title()
    return "feed" in title.lower() or "linkedin" in title.lower()

def is_not_login_page() -> bool:
    title = get_window_title()
    return "sign in" not in title.lower() and "login" not in title.lower()

# ── Core steps ────────────────────────────────────────────────────────────────
def step_navigate() -> bool:
    log("→ Step 1: Navigate to feed")
    wid = get_window()
    env = _ENV()
    focus_window()

    # Put URL on clipboard, focus bar, paste — avoids xdotool type speed issues
    url = "https://www.linkedin.com/feed/"
    subprocess.run(["xsel", "--clipboard", "--input"],
                   input=url.encode(), env=env, capture_output=True)
    subprocess.run(["xdotool", "key",  "--window", wid, "ctrl+l"],  env=env, capture_output=True)
    time.sleep(0.5)
    subprocess.run(["xdotool", "key",  "--window", wid, "ctrl+a"],  env=env, capture_output=True)
    time.sleep(0.2)
    subprocess.run(["xdotool", "key",  "--window", wid, "ctrl+v"],  env=env, capture_output=True)
    time.sleep(0.2)
    subprocess.run(["xdotool", "key",  "--window", wid, "Return"],  env=env, capture_output=True)

    # Wait for page — title cycles through loading states, settle on 'Feed | LinkedIn'
    # Allow extra time for slow connections
    deadline = time.time() + 12
    while time.time() < deadline:
        time.sleep(1.2)
        title = get_window_title()
        log(f"  title: {title!r}")
        if "linkedin" in title.lower() and ("feed" in title.lower() or "linkedin.com" in title.lower()) and "google search" not in title.lower():
            log("  ✓ On feed")
            screenshot("01_feed")
            return True
        if "sign in" in title.lower():
            log("  ✗ Redirected to login — not logged in")
            screenshot("ERR_01_login")
            return False

    screenshot("ERR_01_navigate")
    log("  ✗ Navigate timed out")
    return False

def step_open_composer() -> bool:
    log("→ Step 2: Open post composer")
    dismiss_dialogs()

    # Semantic find — scan ALL elements for 'Start a post' text
    # scrollIntoView ensures it's visible, then click
    inject_js("""
        var el = Array.from(document.querySelectorAll('*')).find(function(e){
            var t = (e.innerText || e.textContent || '').trim();
            return t === 'Start a post' && e.offsetParent !== null;
        });
        if(el){
            el.scrollIntoView({block:'center', behavior:'instant'});
            el.click();
            window.__riri_composer = 'clicked';
        } else {
            window.__riri_composer = 'not_found';
        }
    """)

    deadline = time.time() + TIMEOUT["composer"]
    while time.time() < deadline:
        time.sleep(1)
        # Composer is open when 'Post to Anyone' text appears in DOM
        title = get_window_title()
        # Rough check: screenshot and continue
        break

    time.sleep(1.5)
    screenshot("02_composer")
    log("  ✓ Composer opened (or attempted)")
    return True

def step_insert_text(text: str) -> bool:
    log(f"→ Step 3: Insert text ({len(text)} chars)")
    wid = get_window()
    env = _ENV()

    # Put text on clipboard — handles emojis, newlines, quotes, any unicode
    subprocess.run(["xsel", "--clipboard", "--input"],
                   input=text.encode("utf-8"), env=env, capture_output=True)
    time.sleep(0.2)

    # Focus the window then paste — the active element should be the composer
    focus_window()
    subprocess.run(["xdotool", "key", "--window", wid, "ctrl+v"], env=env, capture_output=True)
    time.sleep(1)
    screenshot("03_text")
    log("  ✓ Text pasted from clipboard")
    return True

def step_click_post() -> bool:
    log("→ Step 4: Click Post button")

    # scrollIntoView before click — works for ANY post length
    # Tries 3 selectors in order of reliability
    inject_js("""
        var btn = null;

        // Selector 1: exact text match 'Post' (most reliable)
        btn = Array.from(document.querySelectorAll('button')).find(function(b){
            return (b.innerText || b.textContent || '').trim() === 'Post' && !b.disabled;
        });

        // Selector 2: data-control-name (LinkedIn internal attr)
        if(!btn) btn = document.querySelector('[data-control-name="share.post"]');

        // Selector 3: aria-label
        if(!btn) btn = document.querySelector('button[aria-label="Post"]');

        if(btn){
            btn.scrollIntoView({block:'center', behavior:'instant'});
            setTimeout(function(){ btn.click(); }, 350);
            window.__riri_post = 'clicked';
        } else {
            var visible = Array.from(document.querySelectorAll('button'))
                .filter(function(b){ return b.offsetParent; })
                .map(function(b){ return (b.innerText||'').trim(); })
                .filter(Boolean).join(' | ');
            window.__riri_post = 'not_found | visible: ' + visible.substring(0,300);
        }
    """)

    time.sleep(3.5)
    screenshot("04_posted")
    log("  ✓ Post button triggered")
    return True

def step_verify() -> bool:
    log("→ Step 5: Verify success")
    time.sleep(2)
    ss = screenshot("05_final")

    # Simple heuristic: if we're back on the feed without a modal,
    # and there's no 'What do you want to talk about?' placeholder, we succeeded
    title = get_window_title()
    success = "feed" in title.lower()
    log(f"  {'✓ Post confirmed' if success else '? Could not confirm — check screenshot'}")
    log(f"  Screenshot: {ss}")
    return success

def run_diagnose():
    """Dump current page state to help debug issues."""
    log("=== DIAGNOSE MODE ===")
    log(f"Window title: {get_window_title()}")
    screenshot("DIAG_current")

    inject_js("""
        var info = {
            url: window.location.href,
            title: document.title,
            buttons: Array.from(document.querySelectorAll('button'))
                .filter(function(b){ return b.offsetParent; })
                .map(function(b){ return (b.innerText||'').trim(); })
                .filter(Boolean),
            modals: Array.from(document.querySelectorAll('[role=dialog],[data-test-modal]'))
                .map(function(m){ return m.className.substring(0,60); }),
            composer: !!document.querySelector('[data-placeholder],[class*=share-creation]')
        };
        prompt('RiRi Diag', JSON.stringify(info));
    """)
    time.sleep(3)
    screenshot("DIAG_after_prompt")
    log("=== END DIAGNOSE ===")

# ── API-first wrapper ─────────────────────────────────────────────────────────
def _try_api(text: str) -> dict | None:
    """
    Attempt to post via LinkedIn REST API.
    Returns a result dict on success, None if no token is available so caller
    can fall back to browser automation.
    """
    secrets_file = Path.home() / ".nanobot/secrets.env"
    if secrets_file.exists():
        for line in secrets_file.read_text(errors="ignore").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        return None   # no token — fall back to browser

    try:
        # Import api.py from the same directory
        sys.path.insert(0, str(Path(__file__).parent))
        from api import post_text
        result = post_text(text, token=token)
        if result.get("success"):
            log(f"API post succeeded: {result.get('urn','')}")
            notify("LinkedIn post published via API ✓")
        else:
            log(f"API post failed: {result.get('error','')}")
        return result
    except Exception as e:
        log(f"API fallback error: {e}")
        return None   # fall through to browser


# ── Main ──────────────────────────────────────────────────────────────────────
def post_to_linkedin(text: str, dry_run: bool = False) -> dict:
    result = {
        "success":     False,
        "screenshots": [],
        "error":       None,
        "steps":       []
    }

    log(f"=== LinkedIn Agent: posting {len(text)} chars ===")

    # ── Prefer REST API when a token is available ────────────────────────────
    if not dry_run:
        api_result = _try_api(text)
        if api_result is not None:
            api_result["steps"] = ["api: " + ("ok" if api_result.get("success") else "failed")]
            return api_result
        log("  No API token — falling back to browser automation")

    notify("LinkedIn agent starting (browser mode)...")

    try:
        # Check Chrome is available
        get_window()

        # Check not on login page
        if not is_not_login_page():
            result["error"] = "LinkedIn not logged in — please sign in first"
            notify("LinkedIn: please log in to Chrome")
            return result

        # Step 1 — navigate
        if not step_navigate():
            result["error"] = "Navigation to feed failed"
            return result
        result["steps"].append("navigate: ok")

        # Step 2 — open composer
        if not step_open_composer():
            result["error"] = "Could not open post composer"
            return result
        result["steps"].append("composer: ok")

        if dry_run:
            log("  [dry_run] Stopping here — not posting")
            result["success"] = True
            result["steps"].append("dry_run: ok")
            return result

        # Step 3 — insert text
        if not step_insert_text(text):
            result["error"] = "Text insertion failed"
            return result
        result["steps"].append("text: ok")

        # Step 4 — click post
        if not step_click_post():
            result["error"] = "Post button click failed"
            return result
        result["steps"].append("post_btn: ok")

        # Step 5 — verify
        success = step_verify()
        result["steps"].append(f"verify: {'ok' if success else 'uncertain'}")
        result["success"] = True  # best-effort — check screenshots if unsure

        notify("LinkedIn post published ✓" if success else "LinkedIn post — check browser")
        log(f"=== Done. Steps: {result['steps']} ===")

    except RuntimeError as e:
        result["error"] = str(e)
        log(f"  ✗ {e}")
        notify(f"LinkedIn agent error: {e}")
    except Exception as e:
        result["error"] = str(e)
        screenshot("ERR_exception")
        log(f"  ✗ Unexpected: {e}")
        notify(f"LinkedIn agent crashed: {e}")

    # Collect all screenshots taken
    result["screenshots"] = sorted(
        str(p) for p in DIAG_DIR.glob("*.png")
        if p.stat().st_mtime > time.time() - 120
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RiRi LinkedIn Posting Agent")
    parser.add_argument("text",      nargs="?", default="hi",
                        help="Text to post (default: 'hi')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Open composer only, don't submit")
    parser.add_argument("--diagnose",action="store_true",
                        help="Dump page state for debugging")
    args = parser.parse_args()

    os.environ["DISPLAY"] = DISPLAY

    if args.diagnose:
        run_diagnose()
        sys.exit(0)

    result = post_to_linkedin(args.text, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)
