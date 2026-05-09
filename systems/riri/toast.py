#!/usr/bin/env python3
"""
RiRi toast notification — bottom-right bubble, auto-dismisses.
Replaces the broken GTK3 dynamic-island overlay with a simple, reliable popup.

Usage:
  python3 toast.py "your message"
  python3 toast.py "your message" --timeout 8
  python3 toast.py "your message" --title "Custom Title"
"""

import gi, sys, argparse
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

MARGIN  = 20    # px from screen edge
TASKBAR = 48    # px for taskbar at bottom


# ── Drawing hook (punches out transparent background) ─────────────────────────
def _on_draw(widget, cr):
    cr.set_source_rgba(0, 0, 0, 0)
    cr.set_operator(1)   # CAIRO_OPERATOR_SOURCE
    cr.paint()
    cr.set_operator(0)   # CAIRO_OPERATOR_OVER


# ── Main toast ────────────────────────────────────────────────────────────────
def show_toast(message: str, title: str = "🤖 RiRi", timeout: int = 5):
    win = Gtk.Window()
    win.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
    win.set_skip_taskbar_hint(True)
    win.set_skip_pager_hint(True)
    win.set_keep_above(True)
    win.set_decorated(False)
    win.set_resizable(False)
    win.set_accept_focus(False)

    # Transparency
    screen = win.get_screen()
    visual  = screen.get_rgba_visual()
    if visual:
        win.set_visual(visual)
        win.set_app_paintable(True)
        win.connect("draw", _on_draw)

    # ── CSS ──────────────────────────────────────────────────────────────────
    css = b"""
    window {
        background-color: rgba(24, 24, 28, 0.93);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    box.toast-box {
        padding: 14px 20px;
    }
    label.toast-title {
        color: #7db4f0;
        font-weight: bold;
        font-size: 11px;
        letter-spacing: 0.5px;
    }
    label.toast-msg {
        color: #e2e2e2;
        font-size: 13px;
    }
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # ── Layout ───────────────────────────────────────────────────────────────
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    box.get_style_context().add_class("toast-box")

    title_lbl = Gtk.Label(label=title)
    title_lbl.get_style_context().add_class("toast-title")
    title_lbl.set_halign(Gtk.Align.START)

    msg_lbl = Gtk.Label(label=message)
    msg_lbl.get_style_context().add_class("toast-msg")
    msg_lbl.set_halign(Gtk.Align.START)
    msg_lbl.set_line_wrap(True)
    msg_lbl.set_max_width_chars(42)

    box.pack_start(title_lbl, False, False, 0)
    box.pack_start(msg_lbl,   False, False, 0)
    win.add(box)

    # ── Position: bottom-right after window is realized ───────────────────
    def _position(*_):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geom    = monitor.get_geometry()
        win.show_all()
        w, h = win.get_size()
        x = geom.x + geom.width  - w - MARGIN
        y = geom.y + geom.height - h - MARGIN - TASKBAR
        win.move(x, y)
    win.connect("realize", lambda *a: GLib.idle_add(_position))

    # ── Dismiss: click or timeout ─────────────────────────────────────────
    win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    win.connect("button-press-event", lambda *_: Gtk.main_quit())
    GLib.timeout_add_seconds(timeout, lambda: (Gtk.main_quit(), False)[1])

    win.show_all()
    Gtk.main()


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RiRi toast notification")
    parser.add_argument("message",  nargs="+",        help="Message to display")
    parser.add_argument("--title",  default="🤖 RiRi", help="Toast title")
    parser.add_argument("--timeout",type=int, default=5, help="Auto-dismiss seconds (default 5)")
    args = parser.parse_args()
    show_toast(" ".join(args.message), title=args.title, timeout=args.timeout)
