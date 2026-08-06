"""Garble-credit rate — the pre-registered primary metric for the
learner_text_facts A/B (docs/archive/reviews/pre-grading-20260805.md).

g = (# grade rows whose evidence quote contains an invalid-Spanish
token) / (# grade rows). Success bar (frozen): g_facts <= g_control
- 0.15 absolute, or >=30% relative when g_control < 0.20.

    python -m evals.garble_credit <result-dir>...
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from tutor.conjugations import is_real_spanish, parses_of_surface

_TOKEN_RE = re.compile(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+")


def _has_invalid_token(evidence: str) -> bool:
    for raw in _TOKEN_RE.findall(evidence or ""):
        low = raw.lower()
        if len(low) <= 2:
            continue
        if raw[:1].isupper():
            continue  # name-like: the names leak is tracked separately
        if parses_of_surface(low):
            continue
        if not is_real_spanish(low):
            return True
    return False


def rate_for(result_dir: Path) -> tuple[float, int, int]:
    rows = 0
    garbled = 0
    p = result_dir / "sheet_grades.jsonl"
    if not p.exists():
        return 0.0, 0, 0
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "grade" or r.get("direction") != "up":
            continue
        rows += 1
        if _has_invalid_token(str(r.get("evidence") or "")):
            garbled += 1
    return (garbled / rows if rows else 0.0), garbled, rows


def main() -> None:
    dirs = [Path(d) for d in sys.argv[1:]]
    if not dirs:
        raise SystemExit("usage: python -m evals.garble_credit <dir>...")
    for d in dirs:
        g, n, total = rate_for(d)
        print(f"{d.name:52s} g={g:.3f} ({n}/{total} up-grade rows credit "
              f"invalid tokens)")


if __name__ == "__main__":
    main()
