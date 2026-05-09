#!/usr/bin/env python3
"""
RiRi — Dynamic Island personal assistant for Linux
Apple Dynamic Island clone with Hermes brain + persistent memory.

Modes:
  idle       → hidden (opacity 0), hover near top-center to reveal
  notify     → expands to (360×68), shows message, plays chime, auto-collapses 4s
  assistant  → expands to (390×360), chat input + Hermes AI brain

IPC:  Unix socket /tmp/riri.sock
      Send:  "notify:message text"
             "expand"
             "hide"
             "ask:prompt text"
CLI:  riri "message"   →  ~/projects/riri/notify.py "message"
"""

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_foreign("cairo")
import cairo  # pycairo — must import after gi.require_foreign
from gi.repository import Gtk, Gdk, GLib, Pango

import json, math, os, re, socket, struct, subprocess, threading, wave
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from memory import init_db, remember, recall_text, set_fact, compact_session, log_cmd, build_context_block

def _pipeline_context(query: str) -> str:
    """
    Pull relevant Claude session data for a query.
    Injected into brain context when question relates to past Claude work.
    """
    keywords = ("claude", "session", "what did", "last time", "yesterday",
                "when did", "which file", "what changed", "worked on",
                "what was", "error", "fixed", "built", "wrote", "edited")
    if not any(k in query.lower() for k in keywords):
        return ""
    try:
        sys.path.insert(0, str(Path.home() / ".claude/hooks"))
        from riri_pipeline import query_sessions, query_tool_events
        sessions = query_sessions(limit=5)
        if not sessions:
            return ""
        lines = ["[Recent Claude sessions]"]
        for s in sessions[:4]:
            from datetime import datetime
            import json as _json
            ts   = datetime.fromtimestamp(s.get("ended_at") or s.get("started_at", 0)).strftime("%m/%d %H:%M")
            proj = s.get("project", "?")
            summ = (s.get("summary") or "(in progress)")[:100]
            n_f  = len(_json.loads(s.get("files_changed") or "[]"))
            lines.append(f"[{ts}] {proj} ({n_f} files): {summ}")
        return "\n".join(lines)
    except Exception:
        return ""


def _tool_hints(task: str) -> str:
    """Pull relevant tools from ChromaDB knowledge base (silent on failure)."""
    try:
        sys.path.insert(0, str(Path(__file__).parent / "tools"))
        from index import query
        results = query(task, n=3, category="tools")
        lines = ["[Tools that may help]"]
        for r in results:
            if r["score"] < 0.52:
                continue
            snippet = "\n".join(r["content"].split("\n")[:4])
            lines.append(snippet)
        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""

# ── Constants ───────────────────────────────────────────────────────────────────
SOCK_PATH    = "/tmp/riri.sock"
SOUND_FILE   = Path(__file__).parent / "sounds" / "chime.wav"
LOG_FILE     = Path.home() / ".local/share/riri/errors.log"
SCROT        = "/usr/bin/scrot"
OLLAMA_URL   = "http://localhost:11434"
BRAIN_MODEL  = "gemma3:4b"   # fast local model (swap to llama3.1:8b for smarter)
HERMES_ID    = "2f897616-7ca2-4f5b-8db0-b76a661473d7"
COMPANY_ID   = "050104eb-63a6-4684-93ef-90f53d7e66eb"

# Pill geometry
COMPACT_W,  COMPACT_H  = 120, 36
NOTIFY_W,   NOTIFY_H   = 360, 68
EXPANDED_W, EXPANDED_H = 390, 360
PILL_R   = 18
HOVER_RADIUS = 180   # px from top-center to trigger reveal

# Colors (Apple palette)
C_BG       = (0.0,  0.0,  0.0,  0.97)
C_TEXT     = (1.0,  1.0,  1.0,  1.0)
C_PURPLE   = (0.49, 0.23, 0.93, 1.0)
C_GREEN    = (0.20, 0.83, 0.50, 1.0)
C_AMBER    = (0.98, 0.75, 0.18, 1.0)
C_RED      = (0.98, 0.32, 0.32, 1.0)

# Animation
FPS        = 60
FRAME_MS   = 1000 // FPS
ANIM_MS    = 280
NOTIFY_TTL = 4500
FADE_STEPS = 12     # opacity fade steps

# ── Sound generation ─────────────────────────────────────────────────────────────
def _gen_chime():
    SOUND_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SOUND_FILE.exists():
        return
    rate = 44100; dur = 0.45; n = int(rate * dur)
    with wave.open(str(SOUND_FILE), "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(rate)
        for i in range(n):
            t    = i / rate
            fade = math.exp(-5 * t / dur)
            s    = fade * (0.55 * math.sin(2*math.pi*587*t) +
                           0.35 * math.sin(2*math.pi*740*t))
            wf.writeframes(struct.pack("<h", int(s * 28000)))

def play_chime():
    try:
        subprocess.Popen(["aplay", "-q", str(SOUND_FILE)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _style_widget(widget, css: str):
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode())
    widget.get_style_context().add_provider(
        provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


# ── Easing ───────────────────────────────────────────────────────────────────────
def spring(t: float) -> float:
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    omega = 2 * math.pi * 1.8; zeta = 0.62
    wd = omega * math.sqrt(1 - zeta**2)
    return 1 - math.exp(-zeta * omega * t) * (
        math.cos(wd * t) + (zeta / math.sqrt(1 - zeta**2)) * math.sin(wd * t))


class State:
    IDLE     = "idle"
    NOTIFY   = "notify"
    EXPANDED = "expanded"


# ── Brain system prompt ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are **RiRi**, Ahmed's personal Linux assistant running on his machine.

Identity:
- Direct, concise, action-oriented — no filler phrases
- You remember past sessions and improve over time
- You execute bash commands on Ahmed's behalf

When a task needs a command, reply ONLY with JSON:
  {"cmd": "bash command here", "explain": "one line what it does"}

Multi-step: chain with &&. Background: append &.
Otherwise: plain text, max 2 sentences.

Available tools:
- Terminal: any bash command
- Email: gws gmail users messages list/send --params '{"userId":"me",...}'
- Browser: google-chrome --new-tab "url"  OR  google-chrome --headless --screenshot=/tmp/ss.png "url"
- Outreach: python3 /home/ahmed/projects/outreach-engine/cli.py <status|leads|stats>
- Services: systemctl --user status|restart pipeline-bot
- Paperclip: curl http://localhost:3100/api/companies/050104eb-63a6-4684-93ef-90f53d7e66eb/issues

GWS auth note: if gws returns auth error → tell Ahmed to run: gws auth login
"""

# ── Brain fallback chain (cheapest → most expensive) ─────────────────────────────
# Priority: 1. Ollama local (free)  2. Gemini CLI (free)
#           3. Groq API (free tier)  4. OpenAI (paid, last resort)

GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "REDACTED_GROQ_API_KEY")
GROQ_MODEL    = "llama-3.3-70b-versatile"
OPENAI_KEY    = os.getenv("OPENAI_API_KEY", "")   # paid — only used if all else fails


def _build_messages(prompt: str, history_text: str, context: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        msgs.append({"role": "system", "content": f"[Memory context]\n{context}"})
    if history_text:
        msgs.append({"role": "system", "content": f"[Recent chat]\n{history_text}"})
    msgs.append({"role": "user", "content": prompt})
    return msgs


def _try_ollama(prompt: str, history_text: str, context: str) -> str:
    """Tier 1 — Local Ollama. Free, private, no rate limits."""
    import urllib.request
    msgs = _build_messages(prompt, history_text, context)
    body = json.dumps({
        "model": BRAIN_MODEL, "messages": msgs,
        "stream": False, "options": {"temperature": 0.4, "num_predict": 400}
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=body, method="POST",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())["message"]["content"].strip()


def _try_gemini_cli(prompt: str, history_text: str, context: str) -> str:
    """Tier 2 — Gemini CLI (Google free tier). Good for complex/stuck tasks."""
    parts = []
    if context:
        parts.append(f"[Memory]\n{context}")
    if history_text:
        parts.append(f"[History]\n{history_text}")
    parts.append(SYSTEM_PROMPT)
    parts.append(f"Human: {prompt}\nRiRi:")
    full_prompt = "\n\n".join(parts)
    result = subprocess.run(
        ["/usr/bin/gemini", full_prompt],
        capture_output=True, text=True, timeout=45
    )
    out = result.stdout.strip()
    if not out:
        raise RuntimeError(result.stderr.strip() or "empty response")
    return out


def _try_groq(prompt: str, history_text: str, context: str) -> str:
    """Tier 3 — Groq API (free tier, very fast llama-3.3-70b)."""
    import urllib.request
    msgs = _build_messages(prompt, history_text, context)
    body = json.dumps({
        "model": GROQ_MODEL, "messages": msgs,
        "temperature": 0.4, "max_tokens": 400
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def _try_openai(prompt: str, history_text: str, context: str) -> str:
    """Tier 4 — OpenAI (paid, last resort). Only used if key is set."""
    if not OPENAI_KEY:
        raise RuntimeError("no OpenAI key configured")
    import urllib.request
    msgs = _build_messages(prompt, history_text, context)
    body = json.dumps({
        "model": "gpt-4o-mini", "messages": msgs,
        "temperature": 0.4, "max_tokens": 400
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_KEY}"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


# Ordered fallback chain — index 0 is tried first
_BRAIN_TIERS = [
    ("local",  _try_ollama),
    ("gemini", _try_gemini_cli),
    ("groq",   _try_groq),
    ("openai", _try_openai),
]

_last_tier_used: str = "local"   # tracked for UI display


def ask_brain(prompt: str, history_text: str = "", context: str = "") -> tuple[str, str]:
    """
    Try each brain tier in order. Returns (response_text, tier_name_used).
    Only moves to next tier on exception/timeout — never spends money if free works.
    """
    global _last_tier_used
    errors = []
    for tier_name, fn in _BRAIN_TIERS:
        try:
            result = fn(prompt, history_text, context)
            _last_tier_used = tier_name
            return result, tier_name
        except Exception as e:
            errors.append(f"{tier_name}: {e}")
            continue
    return f"All brains failed:\n" + "\n".join(errors), "none"


# ── RiRi window ──────────────────────────────────────────────────────────────────
class RiRi(Gtk.Window):

    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _gen_chime()
        init_db()

        # Window flags
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        self.set_accept_focus(False)

        # RGBA visual
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # State
        self.state         = State.IDLE
        self.notify_msg    = ""
        self.notify_color  = C_PURPLE
        self._chat_history: list[dict] = []
        self._input_sensitive = True
        self._opacity      = 0.0    # start hidden
        self._target_opacity = 0.0
        self._notify_timer_id = None
        self._session_turn_count = 0

        # Animation
        self._anim_start  = 0.0
        self._anim_from_w = COMPACT_W
        self._anim_from_h = COMPACT_H
        self._anim_to_w   = COMPACT_W
        self._anim_to_h   = COMPACT_H
        self._cur_w       = COMPACT_W
        self._cur_h       = COMPACT_H
        self._pulse_t     = 0.0

        # Screen geometry
        display  = Gdk.Display.get_default()
        monitor  = display.get_primary_monitor()
        geom     = monitor.get_geometry()
        self._screen_cx  = geom.x + geom.width // 2
        self._screen_y   = geom.y + 6
        self._screen_w   = geom.width

        self._build_ui()
        self._reposition()

        self.connect("delete-event",       Gtk.main_quit)
        self.connect("draw",               self._draw)
        self.connect("button-press-event", self._on_click)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        GLib.timeout_add(FRAME_MS, self._tick)
        GLib.timeout_add(50,        self._pulse_tick)
        GLib.timeout_add(120,       self._hover_tick)   # hover detection
        GLib.timeout_add(200,       self._fade_tick)    # opacity fade

    # ── Position ─────────────────────────────────────────────────────────────
    def _reposition(self):
        w, h = int(self._cur_w), int(self._cur_h)
        self.resize(w, h)
        self.move(self._screen_cx - w // 2, self._screen_y)

    # ── Hover detection ───────────────────────────────────────────────────────
    def _hover_tick(self):
        if self.state != State.IDLE:
            return True
        try:
            seat    = Gdk.Display.get_default().get_default_seat()
            ptr     = seat.get_pointer()
            _, px, py, _ = ptr.get_position()
            # Reveal when mouse is in top strip (within HOVER_RADIUS of pill)
            near_x = abs(px - self._screen_cx) < HOVER_RADIUS
            near_y = py < 80
            if near_x and near_y:
                self._target_opacity = 1.0
            else:
                self._target_opacity = 0.0
        except Exception:
            pass
        return True

    def _fade_tick(self):
        step = 1.0 / FADE_STEPS
        if self._opacity < self._target_opacity:
            self._opacity = min(1.0, self._opacity + step)
        elif self._opacity > self._target_opacity:
            self._opacity = max(0.0, self._opacity - step)
        if self.state == State.IDLE:
            gdk_win = self.get_window()
            if gdk_win:
                gdk_win.set_opacity(self._opacity)
        return True

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def _build_ui(self):
        self._stack = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._stack.set_margin_start(16)
        self._stack.set_margin_end(16)
        self.add(self._stack)

        # Notification row
        self._notif_row = Gtk.Box(spacing=10)
        self._notif_row.set_valign(Gtk.Align.CENTER)
        self._notif_row.set_vexpand(True)
        self._notif_icon = Gtk.Label()
        self._notif_icon.set_markup('<span font_size="18000">●</span>')
        self._notif_text = Gtk.Label()
        self._notif_text.set_markup('<span font_family="Inter,sans-serif" font_size="13000" foreground="white"></span>')
        self._notif_text.set_ellipsize(Pango.EllipsizeMode.END)
        self._notif_text.set_xalign(0)
        self._notif_row.pack_start(self._notif_icon, False, False, 0)
        self._notif_row.pack_start(self._notif_text, True,  True,  0)
        self._notif_row.set_no_show_all(True)
        self._stack.pack_start(self._notif_row, False, False, 0)

        # Chat box (expanded state)
        self._chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._chat_box.set_no_show_all(True)

        # Header
        hdr = Gtk.Box(spacing=8)
        hdr.set_margin_top(14); hdr.set_margin_bottom(8)
        dot  = Gtk.Label()
        dot.set_markup('<span foreground="#7c3aed" font_size="14000">●</span>')
        name = Gtk.Label()
        name.set_markup('<span font_family="Inter,sans-serif" font_size="13000" font_weight="bold" foreground="white">RiRi</span>')
        self._tier_label = Gtk.Label()
        self._tier_label.set_markup('<span font_family="monospace" font_size="9000" foreground="#334155">local</span>')
        mem_btn = Gtk.Button(label="🧠")
        mem_btn.set_relief(Gtk.ReliefStyle.NONE)
        mem_btn.set_tooltip_text("Show recent memories")
        mem_btn.connect("clicked", self._on_show_memory)
        screen_btn = Gtk.Button(label="📸")
        screen_btn.set_relief(Gtk.ReliefStyle.NONE)
        screen_btn.set_tooltip_text("Describe screen")
        screen_btn.connect("clicked", self._on_screenshot)
        close_btn = Gtk.Button(label="✕")
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda *_: self.go_idle())
        hdr.pack_start(dot,             False, False, 0)
        hdr.pack_start(name,            False, False, 0)
        hdr.pack_start(self._tier_label,False, False, 4)
        hdr.pack_end(close_btn,         False, False, 0)
        hdr.pack_end(screen_btn,        False, False, 0)
        hdr.pack_end(mem_btn,           False, False, 0)
        self._chat_box.pack_start(hdr, False, False, 0)

        # Chat scroll
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_min_content_height(180)

        self._chat_buf  = Gtk.TextBuffer()
        self._chat_view = Gtk.TextView(buffer=self._chat_buf)
        self._chat_view.set_editable(False)
        self._chat_view.set_cursor_visible(False)
        self._chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._chat_view.set_left_margin(4)
        self._chat_view.set_right_margin(4)
        _style_widget(self._chat_view, "textview { background: transparent; color: #f1f5f9; }")

        buf = self._chat_buf
        self._t_you  = buf.create_tag("you",  foreground="#a78bfa", weight=Pango.Weight.BOLD, size_points=12)
        self._t_riri = buf.create_tag("riri", foreground="#f1f5f9", size_points=12)
        self._t_cmd  = buf.create_tag("cmd",  foreground="#34d399", family="monospace", size_points=11)
        self._t_out  = buf.create_tag("out",  foreground="#64748b", family="monospace", size_points=10)
        self._t_err  = buf.create_tag("err",  foreground="#f87171", size_points=11)
        self._t_sys  = buf.create_tag("sys",  foreground="#334155", style=Pango.Style.ITALIC, size_points=10)
        self._t_mem  = buf.create_tag("mem",  foreground="#7c3aed", style=Pango.Style.ITALIC, size_points=10)

        scroll.add(self._chat_view)
        self._chat_box.pack_start(scroll, True, True, 0)

        # Input row
        in_row = Gtk.Box(spacing=6)
        in_row.set_margin_top(8); in_row.set_margin_bottom(10)
        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Ask RiRi anything…")
        _style_widget(self._entry,
            "entry { background: rgba(26,26,36,0.92); color: white; "
            "border: 1px solid rgba(124,58,237,0.5); border-radius: 8px; padding: 6px 10px; }")
        self._entry.set_hexpand(True)
        self._entry.connect("activate", self._on_send)

        send = Gtk.Button(label="→")
        _style_widget(send,
            "button { background: rgba(124,58,237,0.9); color: white; "
            "border: none; border-radius: 8px; padding: 6px 12px; font-weight: bold; }")
        send.connect("clicked", self._on_send)

        in_row.pack_start(self._entry, True,  True,  0)
        in_row.pack_start(send,        False, False, 0)
        self._chat_box.pack_start(in_row, False, False, 0)

        self._stack.pack_start(self._chat_box, True, True, 0)
        self._append_sys("RiRi online. What do you need?")

    # ── Draw (cairo pill) ─────────────────────────────────────────────────────
    def _draw(self, widget, ctx):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = min(PILL_R, h / 2)

        ctx.set_operator(1)
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.paint()

        if self.state != State.IDLE:
            gc = self.notify_color
            ctx.set_source_rgba(gc[0], gc[1], gc[2], 0.20)
            self._pill(ctx, -4, -4, w+8, h+8, r+4)
            ctx.fill()

        ctx.set_source_rgba(*C_BG)
        self._pill(ctx, 0, 0, w, h, r)
        ctx.fill()

        if self.state == State.IDLE:
            alpha = 0.5 + 0.5 * math.sin(self._pulse_t)
            ctx.set_source_rgba(C_PURPLE[0], C_PURPLE[1], C_PURPLE[2], alpha)
            cx = w / 2 - 22
            cy = h / 2
            ctx.arc(cx, cy, 5, 0, 2*math.pi)
            ctx.fill()
            ctx.set_source_rgba(1, 1, 1, 0.90)
            ctx.select_font_face("Inter", 0, 1)
            ctx.set_font_size(13)
            ctx.move_to(w/2 - 12, h/2 + 5)
            ctx.show_text("RiRi")

        return False

    def _pill(self, ctx, x, y, w, h, r):
        ctx.new_path()
        ctx.arc(x + r,     y + r,     r, math.pi,     1.5*math.pi)
        ctx.arc(x + w - r, y + r,     r, 1.5*math.pi, 2*math.pi)
        ctx.arc(x + w - r, y + h - r, r, 0,            0.5*math.pi)
        ctx.arc(x + r,     y + h - r, r, 0.5*math.pi,  math.pi)
        ctx.close_path()

    # ── Animation ─────────────────────────────────────────────────────────────
    def _tick(self):
        now  = GLib.get_monotonic_time() / 1000.0
        t    = min((now - self._anim_start) / ANIM_MS, 1.0)
        ease = spring(t)
        self._cur_w = self._anim_from_w + (self._anim_to_w - self._anim_from_w) * ease
        self._cur_h = self._anim_from_h + (self._anim_to_h - self._anim_from_h) * ease
        self._reposition()
        self.queue_draw()
        return True

    def _pulse_tick(self):
        self._pulse_t += 0.06
        if self.state == State.IDLE:
            self.queue_draw()
        return True

    def _animate_to(self, tw, th):
        self._anim_from_w = self._cur_w; self._anim_from_h = self._cur_h
        self._anim_to_w   = tw;          self._anim_to_h   = th
        self._anim_start  = GLib.get_monotonic_time() / 1000.0

    # ── State transitions ─────────────────────────────────────────────────────
    def go_idle(self):
        # Compact session if we had a conversation
        if self._chat_history and self._session_turn_count >= 4:
            threading.Thread(
                target=self._compact_and_save,
                args=(list(self._chat_history),),
                daemon=True
            ).start()
            self._session_turn_count = 0

        self.state = State.IDLE
        self._notif_row.hide()
        self._chat_box.hide()
        self.set_accept_focus(False)
        self._target_opacity = 0.0
        self._animate_to(COMPACT_W, COMPACT_H)
        if self._notify_timer_id:
            GLib.source_remove(self._notify_timer_id)
            self._notify_timer_id = None

    def go_notify(self, msg: str, color=None):
        self.notify_msg   = msg
        self.notify_color = color or C_PURPLE
        self.state        = State.NOTIFY

        r, g, b = self.notify_color[:3]
        hex_col = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
        self._notif_icon.set_markup(f'<span foreground="{hex_col}" font_size="18000">●</span>')
        short = msg[:55] + ("…" if len(msg) > 55 else "")
        self._notif_text.set_markup(
            f'<span font_family="Inter,sans-serif" font_size="13000" foreground="white">{short}</span>'
        )
        self._chat_box.hide()
        self._notif_row.show()
        self.set_accept_focus(False)
        gdk_win = self.get_window()
        if gdk_win:
            gdk_win.set_opacity(1.0)
        self._opacity = 1.0
        self._animate_to(NOTIFY_W, NOTIFY_H)
        play_chime()
        # Store notification as memory
        threading.Thread(target=remember, args=(f"Notification: {msg}",),
                         kwargs={"tags": "notification"}, daemon=True).start()

        if self._notify_timer_id:
            GLib.source_remove(self._notify_timer_id)
        self._notify_timer_id = GLib.timeout_add(NOTIFY_TTL, self._auto_collapse)

    def _auto_collapse(self):
        if self.state == State.NOTIFY:
            self.go_idle()
        self._notify_timer_id = None
        return False

    def go_expanded(self):
        self.state = State.EXPANDED
        self._notif_row.hide()
        self._chat_box.show_all()
        self.set_accept_focus(True)
        gdk_win = self.get_window()
        if gdk_win:
            gdk_win.set_opacity(1.0)
        self._opacity = 1.0
        self._target_opacity = 1.0
        self._animate_to(EXPANDED_W, EXPANDED_H)
        if self._notify_timer_id:
            GLib.source_remove(self._notify_timer_id)
            self._notify_timer_id = None
        GLib.timeout_add(350, lambda: (self._entry.grab_focus(), False)[1])

    def _on_click(self, w, e):
        if e.button == 1:
            if self.state in (State.IDLE, State.NOTIFY):
                self.go_expanded()
            elif self.state == State.EXPANDED:
                if int(e.y) < 10:
                    self.go_idle()

    # ── Chat helpers ──────────────────────────────────────────────────────────
    def _append(self, text, tag=None):
        end = self._chat_buf.get_end_iter()
        if tag:
            self._chat_buf.insert_with_tags(end, text, tag)
        else:
            self._chat_buf.insert(end, text)
        GLib.idle_add(self._scroll_bottom)

    def _scroll_bottom(self):
        adj = self._chat_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def _append_sys(self, t):  self._append(f"{t}\n", self._t_sys)
    def _append_you(self, t):  self._append(f"\nYou: {t}\n", self._t_you)
    def _append_riri(self, t): self._append(f"RiRi: {t}\n", self._t_riri)
    def _append_cmd(self, t):  self._append(f"$ {t}\n", self._t_cmd)
    def _append_out(self, t):
        if t.strip(): self._append(f"{t.strip()}\n", self._t_out)
    def _append_err(self, t):
        self._append(f"⚠ {t}\n", self._t_err)
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {t}\n")
    def _append_mem(self, t):  self._append(f"🧠 {t}\n", self._t_mem)

    # ── Pipeline query ────────────────────────────────────────────────────────
    def _show_pipeline(self, query: str = ""):
        try:
            sys.path.insert(0, str(Path.home() / ".claude/hooks"))
            from riri_pipeline import query_sessions, query_tool_events
            import json as _json
            sessions = query_sessions(query, limit=8)
            if not sessions:
                GLib.idle_add(self._append_sys, "No Claude sessions recorded yet.")
                GLib.idle_add(self._set_input, True)
                return
            GLib.idle_add(self._append_sys, f"Claude sessions ({len(sessions)} found):")
            for s in sessions:
                from datetime import datetime as _dt
                ts    = _dt.fromtimestamp(s.get("ended_at") or s.get("started_at", 0)).strftime("%m/%d %H:%M")
                proj  = s.get("project", "?")
                summ  = (s.get("summary") or "(in progress)")[:90]
                files = _json.loads(s.get("files_changed") or "[]")
                n_f   = len(files)
                line  = f"[{ts}] {proj}  {n_f}f  {summ}"
                GLib.idle_add(self._append_out, line)
                if files:
                    GLib.idle_add(self._append_out, "  files: " + ", ".join(Path(f).name for f in files[:4]))
        except Exception as e:
            GLib.idle_add(self._append_err, f"pipeline query: {e}")
        finally:
            GLib.idle_add(self._set_input, True)

    # ── Memory button ─────────────────────────────────────────────────────────
    def _on_show_memory(self, *_):
        from memory import recall
        mems = recall("recent activities preferences", k=5)
        if mems:
            self._append_mem("Recent memories:")
            for m in mems[:4]:
                self._append_mem(f"  [{m['score']:.2f}] {m['content'][:80]}")
        else:
            self._append_sys("No memories yet.")

    # ── Session compaction ────────────────────────────────────────────────────
    def _compact_and_save(self, history: list):
        summary = compact_session(history)
        if summary:
            GLib.idle_add(self._append_sys, f"Session saved: {summary[:60]}…")

    # ── Screenshot ────────────────────────────────────────────────────────────
    def _on_screenshot(self, *_):
        self._append_sys("Taking screenshot…")
        threading.Thread(target=self._capture_and_describe, daemon=True).start()

    def _capture_and_describe(self):
        tmp = "/tmp/riri-screen.png"
        try:
            subprocess.run(["scrot", "-z", tmp], timeout=5, check=True)
        except Exception as e:
            GLib.idle_add(self._append_err, f"scrot failed: {e}")
            return
        # Use Gemini CLI for image analysis (has vision)
        try:
            result = subprocess.run(
                ["/usr/bin/gemini", tmp,
                 "Describe what's on the screen briefly. Note anything that needs attention."],
                capture_output=True, text=True, timeout=30
            )
            raw = result.stdout.strip() or "Could not describe screen."
        except Exception as e:
            raw = f"Vision failed: {e}"
        GLib.idle_add(self._append_riri, raw)

    # ── Send / RiRi brain ─────────────────────────────────────────────────────
    def _on_send(self, *_):
        if not self._input_sensitive:
            return
        text = self._entry.get_text().strip()
        if not text:
            return
        self._entry.set_text("")
        self._input_sensitive = False
        self._append_you(text)
        self._chat_history.append({"role": "user", "text": text})
        self._session_turn_count += 1

        # Handle "pipeline:" direct session query
        if text.lower().startswith("pipeline:") or text.lower().startswith("sessions"):
            q = text.split(":", 1)[-1].strip() if ":" in text else ""
            threading.Thread(target=self._show_pipeline, args=(q,), daemon=True).start()
            return

        # Handle explicit "remember:" command
        if text.lower().startswith("remember:"):
            fact = text[9:].strip()
            threading.Thread(target=remember, args=(fact,),
                             kwargs={"tags": "explicit", "source": "user"}, daemon=True).start()
            GLib.idle_add(self._append_riri, f"Got it. I'll remember: {fact[:60]}")
            self._input_sensitive = True
            return

        threading.Thread(target=self._query_brain, args=(text,), daemon=True).start()

    def _update_tier_label(self, tier: str):
        colors = {"local": "#22c55e", "gemini": "#3b82f6", "groq": "#f59e0b", "openai": "#ef4444", "none": "#6b7280"}
        color  = colors.get(tier, "#ffffff")
        self._tier_label.set_markup(
            f'<span font_family="monospace" font_size="9000" foreground="{color}">{tier}</span>'
        )

    def _query_brain(self, prompt: str):
        # Build history
        history_text = "\n".join(
            f"{'Ahmed' if h['role']=='user' else 'RiRi'}: {h['text']}"
            for h in self._chat_history[-8:]
        )
        # Recall relevant memories + tool hints + pipeline context
        context      = build_context_block(prompt)
        tool_hints   = _tool_hints(prompt)
        pipeline_ctx = _pipeline_context(prompt)
        full_ctx     = "\n\n".join(x for x in [context, pipeline_ctx, tool_hints] if x)
        if full_ctx:
            GLib.idle_add(self._append_mem, "Recalling context…")

        GLib.idle_add(self._append_sys, "Thinking…")
        raw, tier = ask_brain(prompt, history_text=history_text, context=full_ctx)
        GLib.idle_add(self._update_tier_label, tier)

        if tier == "none":
            GLib.idle_add(self._append_err, raw)
            GLib.idle_add(self._set_input, True)
            return
        elif tier != "local":
            # Let user know it fell back
            GLib.idle_add(self._append_sys, f"↳ used {tier}")

        # Try JSON command
        try:
            m = re.search(r'\{[^{}]*"cmd"[^{}]*\}', raw, re.DOTALL)
            if m:
                parsed  = json.loads(m.group())
                cmd     = parsed.get("cmd", "")
                explain = parsed.get("explain", "")
                if explain:
                    GLib.idle_add(self._append_riri, explain)
                self._chat_history.append({"role": "riri", "text": explain or cmd})
                GLib.idle_add(self._exec_cmd, cmd)
                return
        except Exception:
            pass

        GLib.idle_add(self._append_riri, raw)
        self._chat_history.append({"role": "riri", "text": raw})
        GLib.idle_add(self._set_input, True)

    def _set_input(self, v):
        self._input_sensitive = v

    def _exec_cmd(self, cmd: str):
        self._append_cmd(cmd)
        threading.Thread(target=self._run_cmd, args=(cmd,), daemon=True).start()

    def _run_cmd(self, cmd: str):
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=60, cwd=Path.home())
            GLib.idle_add(self._append_out, r.stdout)
            if r.returncode != 0:
                GLib.idle_add(self._append_err, r.stderr or f"Exit {r.returncode}")
                self._chat_history.append({"role": "riri", "text": f"[ERROR] {r.stderr[:200]}"})
                log_cmd(cmd, r.returncode)
            else:
                if r.stderr:
                    GLib.idle_add(self._append_out, r.stderr)
                self._chat_history.append({"role": "riri", "text": f"[DONE] {r.stdout[:200]}"})
                log_cmd(cmd, 0)
        except subprocess.TimeoutExpired:
            GLib.idle_add(self._append_err, "Command timed out")
        except Exception as e:
            GLib.idle_add(self._append_err, str(e))
        finally:
            GLib.idle_add(self._set_input, True)


# ── IPC server ────────────────────────────────────────────────────────────────
def _ipc_server(riri: RiRi):
    try:
        os.unlink(SOCK_PATH)
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK_PATH); srv.listen(5)
    while True:
        conn, _ = srv.accept()
        try:
            data = conn.recv(1024).decode("utf-8", errors="ignore").strip()
            if data.startswith("notify:"):
                msg   = data[7:]
                color = C_AMBER if "warn" in msg.lower() else \
                        C_RED   if any(w in msg.lower() for w in ("error","fail","blocked")) else \
                        C_GREEN if any(w in msg.lower() for w in ("done","success","complete","finished")) else \
                        C_PURPLE
                GLib.idle_add(riri.go_notify, msg, color)
            elif data == "expand":
                GLib.idle_add(riri.go_expanded)
            elif data in ("hide", "collapse"):
                GLib.idle_add(riri.go_idle)
            elif data.startswith("ask:"):
                GLib.idle_add(riri.go_expanded)
                prompt = data[4:]
                GLib.timeout_add(400, lambda p=prompt: (
                    riri._entry.set_text(p), riri._on_send(), False)[2])
        except Exception:
            pass
        conn.close()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    win = RiRi()
    win.show_all()
    win._chat_box.hide()
    win._notif_row.hide()
    # Start hidden — will fade in on hover
    GLib.timeout_add(100, lambda: win.get_window() and win.get_window().set_opacity(0.0) or False)

    t = threading.Thread(target=_ipc_server, args=(win,), daemon=True)
    t.start()

    Gtk.main()


if __name__ == "__main__":
    main()
