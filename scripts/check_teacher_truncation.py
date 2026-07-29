#!/usr/bin/env python3
"""Fail if teacher-context code reintroduces silent truncation.

Why: latency "optimisations" repeatedly sliced character sheet, pack, stance,
and chat history before the AI tutor saw them. That broke pedagogy. Testing
default is full context (`TEACHER_CONTEXT_TRUNCATE` off).

Run:
  python scripts/check_teacher_truncation.py           # whole teacher tree
  python scripts/check_teacher_truncation.py --staged  # pre-commit (staged only)
  SKIP_TRUNCATION_CHECK=1 git commit ...               # emergency bypass

Allow a line intentionally:
  some_slice = text[:80]  # truncation-ok: error log only
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Modules that build or feed the AI *teacher* turn (not STT/TTS/UI rail).
TEACHER_PATHS = frozenset(
    {
        "tutor/conv_session.py",
        "tutor/turn_pipeline.py",
        "tutor/executor.py",
        "tutor/character_sheet.py",
        "tutor/config.py",
        "tutor/modes.py",
        "tutor/observe.py",
        "tutor/output_gate.py",
        "tutor/scenes.py",
        "tutor/session_memory.py",
        "tutor/corpus.py",
        "tutor/plan_card.py",
        "tutor/pedagogy_contract.py",
        "tutor/tutor_response.py",
    }
)

# High severity: always block on these in teacher paths (unless truncation-ok).
HIGH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "hard history drop (history[-N:])",
        re.compile(
            r"(?:self\.)?history\s*=\s*(?:self\.)?history\s*\[\s*-\s*\d+\s*:\s*\]"
        ),
    ),
    (
        "hard history window mutation",
        re.compile(r"(?:self\.)?history\s*=\s*.*\[\s*-\s*\d+\s*:\s*\]"),
    ),
    (
        "history length gate that drops turns",
        re.compile(r"len\s*\(\s*(?:self\.)?history\s*\)\s*>\s*\d+"),
    ),
    (
        "sliced pack/sheet/stance/previous_raw for model",
        re.compile(
            r"\b(sheet_summary|pack_palette|stance|previous_raw|pack_txt|sheet_txt|"
            r"format_sheet_for_prompt\s*\([^)]*\))\s*\[\s*:\s*\d+\s*\]"
        ),
    ),
    (
        "load_pack(...)[:N] for teacher",
        re.compile(r"load_pack\s*\([^)]*\)\s*\[\s*:\s*\d+\s*\]"),
    ),
    (
        "clip_prompt with hard positive literal cap",
        re.compile(r"clip_prompt\s*\([^)]*?,\s*[1-9]\d*\s*\)"),
    ),
    (
        "TEACHER_CONTEXT_TRUNCATE defaulting on",
        re.compile(
            r"""TEACHER_CONTEXT_TRUNCATE.*?get\(\s*["']TEACHER_CONTEXT_TRUNCATE["']\s*,\s*["'](?:true|1|yes|on)["']""",
            re.I,
        ),
    ),
    (
        "HISTORY_TURNS / PROMPT_CHARS reintroduced as always-on int default",
        re.compile(
            r"""(?:HISTORY_TURNS|SHEET_PROMPT_CHARS|PACK_PROMPT_CHARS|STANCE_PROMPT_CHARS)\s*=\s*int\(\s*os\.environ\.get\([^)]+,\s*["'][1-9]"""
        ),
    ),
]

# Medium: large string/list clips in teacher files (often context loss).
MED_SLICE = re.compile(r"\[\s*:\s*(\d+)\s*\]")
MED_MIN = 100  # ignore tiny storage snippets under this

# Clearly not model-context (logs, exceptions, binary sniff).
SAFE_LINE = re.compile(
    r"(r\.text|str\s*\(\s*e|__name__|print\s*\(|logging\.|log\.|"
    r"raise |warn|debug|exception|error_in|magic|PNG|RIFF|WAVE|"
    r"hashlib|hexdigest|truncate?d marker|STATE_MARKER)",
    re.I,
)

OK_MARK = re.compile(r"truncation-ok\s*:", re.I)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _staged_paths() -> list[Path]:
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    out: list[Path] = []
    for line in (r.stdout or "").splitlines():
        p = ROOT / line.strip()
        if p.suffix == ".py" and p.is_file():
            out.append(p)
    return out


def _teacher_tree() -> list[Path]:
    return [ROOT / rel for rel in sorted(TEACHER_PATHS) if (ROOT / rel).is_file()]


def _scan_file(path: Path) -> list[tuple[str, str, int, str]]:
    """Return list of (severity, rule, lineno, line)."""
    rel = _rel(path)
    if rel not in TEACHER_PATHS:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [("high", f"unreadable: {e}", 0, "")]

    findings: list[tuple[str, str, int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if OK_MARK.search(line):
            continue
        code = line.split("#", 1)[0]
        for name, pat in HIGH_PATTERNS:
            if pat.search(code):
                findings.append(("high", name, i, stripped[:160]))
        if SAFE_LINE.search(code):
            continue
        m = MED_SLICE.search(code)
        if m and int(m.group(1)) >= MED_MIN:
            # Skip pure tests / comments already handled
            findings.append(
                (
                    "medium",
                    f"slice [:{m.group(1)}] in teacher path (add '# truncation-ok: reason' if intentional)",
                    i,
                    stripped[:160],
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    if os.environ.get("SKIP_TRUNCATION_CHECK", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        print("check_teacher_truncation: SKIP_TRUNCATION_CHECK set — bypass")
        return 0

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--staged",
        action="store_true",
        help="Only scan staged teacher-path files (pre-commit)",
    )
    ap.add_argument(
        "--warn-medium",
        action="store_true",
        help="Medium findings are warnings only (default: fail on medium too)",
    )
    args = ap.parse_args(argv)

    if args.staged:
        paths = [p for p in _staged_paths() if _rel(p) in TEACHER_PATHS]
        if not paths:
            print("check_teacher_truncation: no staged teacher-path files")
            return 0
    else:
        paths = _teacher_tree()

    highs: list[str] = []
    meds: list[str] = []
    for path in paths:
        for sev, rule, lineno, line in _scan_file(path):
            loc = f"{_rel(path)}:{lineno}"
            msg = f"  [{sev}] {loc}  {rule}\n    {line}"
            if sev == "high":
                highs.append(msg)
            else:
                meds.append(msg)

    if highs or meds:
        print("check_teacher_truncation: teacher-context truncation risk\n")
        print(
            "Policy: do not silently truncate sheet / pack / stance / history\n"
            "sent to the AI teacher while testing. Use TEACHER_CONTEXT_TRUNCATE=1\n"
            "only as an explicit prod optimisation. Full policy:\n"
            "  docs/teacher-context-no-truncate.md\n"
        )
        if highs:
            print("HIGH (block commit):")
            print("\n".join(highs))
        if meds:
            print("MEDIUM:")
            print("\n".join(meds))
        print(
            "\nFix the slice, or mark intentional with:  # truncation-ok: <reason>\n"
            "Bypass once: SKIP_TRUNCATION_CHECK=1 git commit ...\n"
        )
        if highs:
            return 1
        if meds and not args.warn_medium:
            return 1
    print(f"check_teacher_truncation: ok ({len(paths)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
