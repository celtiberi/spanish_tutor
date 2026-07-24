"""Tiny ANSI color helpers for CLI tutors.

Respects NO_COLOR and non-TTY stdout. Force with FORCE_COLOR=1.
"""

from __future__ import annotations

import os
import sys


def color_enabled(stream=None) -> bool:
    stream = stream or sys.stdout
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR", "").strip() in ("1", "true", "yes"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class Palette:
    """Named styles. Empty strings when color is off."""

    def __init__(self, enabled: bool | None = None):
        self.enabled = color_enabled() if enabled is None else enabled
        if not self.enabled:
            for name in (
                "reset", "bold", "dim", "italic",
                "tutor", "tutor_label", "you", "you_label",
                "sheet", "meta", "ok", "warn", "err", "cmd", "header",
            ):
                setattr(self, name, "")
            return
        self.reset = "\033[0m"
        self.bold = "\033[1m"
        self.dim = "\033[2m"
        self.italic = "\033[3m"
        # Roles
        self.tutor = "\033[96m"          # bright cyan — tutor speech
        self.tutor_label = "\033[1;36m"  # bold cyan — tutor>
        self.you = "\033[0m"             # default for typed text
        self.you_label = "\033[1;32m"    # bold green — you>
        self.sheet = "\033[33m"          # yellow — sheet notes
        self.meta = "\033[2;37m"         # dim gray — banners, paths
        self.ok = "\033[32m"             # green
        self.warn = "\033[33m"           # yellow
        self.err = "\033[1;31m"          # bold red
        self.cmd = "\033[35m"            # magenta — slash commands / help
        self.header = "\033[1;34m"       # bold blue — section headers


_PALETTE: Palette | None = None


def palette() -> Palette:
    global _PALETTE
    if _PALETTE is None:
        _PALETTE = Palette()
    return _PALETTE


def paint(text: str, style: str, *, p: Palette | None = None) -> str:
    """Wrap text in a named style from the palette."""
    p = p or palette()
    code = getattr(p, style, "") or ""
    if not code:
        return text
    return f"{code}{text}{p.reset}"


def label_line(label: str, body: str = "", *, label_style: str = "meta",
               body_style: str = "") -> str:
    p = palette()
    left = paint(label, label_style, p=p)
    if not body:
        return left
    if body_style:
        return f"{left}{paint(body, body_style, p=p)}"
    return f"{left}{body}"
