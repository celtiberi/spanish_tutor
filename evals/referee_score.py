"""Turn blind-referee verdicts + the unblinding key into per-cell
discourse-subset pass vectors (r, g, p).

A trajectory PASSES for a cell iff every discourse criterion the referee graded
for it is PASS (bookkeeping criteria were excluded from the package upstream).
Vector = count of passing trajectories per cell.

Usage:
    python -m evals.referee_score <verdicts.txt> <package.key.json>

Verdict lines are expected to contain the 8-char code and `cN=PASS|FAIL`
tokens; parsing is tolerant of surrounding prose.
"""

import json
import re
import sys
from collections import defaultdict

CODE_RE = re.compile(r"\b([0-9a-f]{8})\b")
CRIT_RE = re.compile(r"c(\d+)\s*[=:]\s*(PASS|FAIL|PARTIAL)", re.I)


def parse(verdicts: str, key: dict):
    """Returns {code: {crit_num: bool_pass}} for codes present in the key."""
    out = {}
    for line in verdicts.splitlines():
        m = CODE_RE.search(line)
        if not m or m.group(1) not in key:
            continue
        code = m.group(1)
        crits = {int(n): (v.upper() == "PASS")
                 for n, v in CRIT_RE.findall(line)}
        if crits:
            out.setdefault(code, {}).update(crits)
    return out


def score(verdicts_path, key_path):
    key = json.loads(open(key_path).read())
    verdicts = open(verdicts_path).read()
    graded = parse(verdicts, key)

    # per cell: trajectory -> pass(all graded discourse criteria PASS)
    cell_traj = defaultdict(dict)
    missing = []
    for code, meta in key.items():
        cell, tid = meta["cell"], meta["traj"]
        crits = graded.get(code)
        if not crits:
            missing.append((code, cell, tid))
            continue
        cell_traj[cell][tid] = all(crits.values())

    print("=== discourse-subset pass vectors ===")
    for cell in sorted(cell_traj):
        passes = sum(1 for v in cell_traj[cell].values() if v)
        n = len(cell_traj[cell])
        failed = [t for t, v in sorted(cell_traj[cell].items()) if not v]
        print(f"  {cell}: {passes}/{n} discourse-pass   failed: {failed}")
    if missing:
        print(f"\n  WARNING: {len(missing)} transcripts not graded (parse gaps):")
        for c, cell, tid in missing:
            print(f"    {c} {cell} {tid}")
    return cell_traj


if __name__ == "__main__":
    score(sys.argv[1], sys.argv[2])
