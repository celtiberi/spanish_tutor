"""CLI for conversational Spanish + character sheet.

Core logic lives in `tutor.conv_session` (shared with the web app).

  python -m tutor.conversational
  python -m tutor.conversational --model gemini-3.6-flash
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import anthropic

from . import config
from .character_sheet import format_sheet_human
from .conv_session import (
    DEFAULT_SHEET_PATH,
    ConversationalSession,
    build_conversational_system,
    tutor_turn,
)
from .term import paint, palette

# Re-exports for tests / older imports
__all__ = [
    "build_conversational_system",
    "tutor_turn",
    "main",
    "ConversationalSession",
]

HELP = """Commands:
  /sheet   show character sheet (what the tutor believes you can do)
  /next    show next_best stretch only
  /reset   clear character sheet (fresh learner)
  /help    this message
  /quit    end session
Anything else is conversation with the tutor."""


def _print_banner(pack_name: str, model: str, sheet_path: Path,
                  mode: str, log_path) -> None:
    p = palette()
    title = paint(
        f"Conversational Spanish ({pack_name}, {model})", "header", p=p)
    print(title)
    print(paint(f"  sheet={sheet_path}  ({mode})", "meta", p=p))
    print(paint(f"  log={log_path}", "meta", p=p))
    print(paint(HELP, "cmd", p=p))
    print()


def _print_tutor_label() -> None:
    print(paint("tutor> ", "tutor_label"), end="", flush=True)


def _print_tutor_body(text: str) -> None:
    p = palette()
    if not text:
        print()
        return
    if not p.enabled:
        print(text, flush=True)
        return
    for line in (text.splitlines() or [text]):
        print(f"{p.tutor}{line}{p.reset}", flush=True)


def _print_sheet_notes(notes: list[str]) -> None:
    if not notes:
        return
    p = palette()
    joined = "; ".join(notes)
    style = "ok" if any(n == "tool_update" for n in notes) else "sheet"
    if any(n == "rules_backup" for n in notes) and "tool_update" not in notes:
        style = "warn"
    print(paint(f"  [sheet: {joined}]", style, p=p), flush=True)


def _print_error(msg: str) -> None:
    print(paint(msg, "err"), flush=True)


def _print_ok(msg: str) -> None:
    print(paint(msg, "ok"), flush=True)


def _print_meta(msg: str) -> None:
    print(paint(msg, "meta"), flush=True)


def _color_sheet_human(text: str) -> str:
    p = palette()
    if not p.enabled:
        return text
    out = []
    for line in text.splitlines():
        if line.startswith("# "):
            out.append(paint(line, "header", p=p))
        elif line.startswith("## "):
            out.append(paint(line, "tutor_label", p=p))
        elif line.startswith("**") or line.startswith("- **"):
            out.append(paint(line, "sheet", p=p))
        elif line.startswith("- "):
            out.append(paint(line, "meta", p=p))
        else:
            out.append(line)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Conversational Spanish + tool-updated character sheet")
    ap.add_argument("--pack", type=Path, default=config.DEFAULT_PACK_DIR)
    ap.add_argument(
        "--model",
        default=config.MODEL,
        help=f"tutor model (default: {config.MODEL})",
    )
    ap.add_argument(
        "--sheet",
        type=Path,
        default=DEFAULT_SHEET_PATH,
        help="character sheet JSON path",
    )
    ap.add_argument(
        "--no-tools",
        action="store_true",
        help="disable update_character_sheet tool (rules backup only)",
    )
    ap.add_argument(
        "--no-ai-sheet",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = ap.parse_args(argv)
    use_tools = not (args.no_tools or args.no_ai_sheet)

    session = ConversationalSession(
        model=args.model,
        pack_dir=args.pack,
        sheet_path=args.sheet,
        use_tools=use_tools,
        label="chat",
    )
    mode = "tool: update_character_sheet" if use_tools else "rules backup only"
    log_path = session.logger.jsonl_path if session.logger else "(no log)"
    _print_banner(args.pack.name, args.model, args.sheet, mode, log_path)

    _print_tutor_label()
    result = session.open_session()
    if result.error:
        _print_error(f"[error opening: {result.error}]")
        session.close()
        return
    print()
    _print_tutor_body(result.reply)
    _print_sheet_notes(result.notes)
    print(flush=True)

    while True:
        try:
            user_input = input(paint("you> ", "you_label")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input in ("/quit", "/exit"):
            break
        if user_input == "/help":
            print(paint(HELP, "cmd"))
            continue
        if user_input == "/sheet":
            print(_color_sheet_human(format_sheet_human(session.sheet)))
            continue
        if user_input == "/next":
            print(paint(
                json.dumps(session.sheet.get("next_best"), indent=2, ensure_ascii=False),
                "sheet",
            ))
            continue
        if user_input == "/reset":
            session.reset_sheet()
            _print_ok("[character sheet cleared]")
            continue

        _print_tutor_label()
        try:
            result = session.user_turn(user_input)
        except anthropic.RateLimitError:
            _print_error("[Rate limited — wait and resend.]")
            continue
        if result.error:
            _print_error(f"[error: {result.error}]")
            continue
        print()
        _print_tutor_body(result.reply)
        _print_sheet_notes(result.notes)
        print(flush=True)

    path = session.close()
    if path:
        _print_meta(f"Session log: {path}")
    _print_meta(f"Character sheet: {args.sheet}")


if __name__ == "__main__":
    main()
