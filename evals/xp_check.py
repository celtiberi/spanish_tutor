"""XP tracking check over persona-gate result dirs (design doc
pre-registered check 3: sam_stuck earns near-zero XP honestly; casey
earns moderately; sofia earns fast).

    python -m evals.xp_check evals/results/<stamp>-sam_stuck-student ...

Prints per-persona XP totals + event breakdowns from the run's own
grade + progress ledgers (the same pure computation the app serves).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tutor.xp import compute_xp, read_ledger


def main() -> None:
    dirs = [Path(d) for d in sys.argv[1:]]
    if not dirs:
        raise SystemExit("usage: python -m evals.xp_check <result-dir>...")
    rows = []
    for d in dirs:
        grades = read_ledger(d / "sheet_grades.jsonl")
        progress = read_ledger(d / "progress.jsonl")
        sheet = {}
        for cand in sorted(d.glob("**/*sheet*.json")):
            try:
                sheet = json.loads(cand.read_text())
                break
            except (OSError, ValueError):
                continue
        xp = compute_xp(grades, progress, sheet=sheet)
        by_src: dict[str, int] = {}
        for ev in xp["events"]:
            k = ev.get("kind") or ev.get("section") or ev["source"]
            by_src[k] = by_src.get(k, 0) + ev["xp"]
        rows.append((d.name, xp, by_src, len(grades), len(progress)))
    print(f"{'run':46s} {'XP':>5s} {'lvl':>4s}  breakdown")
    for name, xp, by_src, ng, np_ in rows:
        bd = " ".join(f"{k}:{v}" for k, v in sorted(by_src.items())) or "—"
        print(f"{name:46s} {xp['total']:>5d} {xp['level']:>4d}  {bd}"
              f"  (ledger rows: {ng} grade / {np_} progress)")


if __name__ == "__main__":
    main()
