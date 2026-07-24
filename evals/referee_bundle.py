"""Build a blind referee package from one or more cell result dirs.

Protocol (EXP-002 §5): the referee sees ONLY learner-visible transcripts, each
labeled with its trajectory ID (needed to pick the frozen judge_criteria) and an
opaque run code. Cells/models are masked and interleaved. Directives and state
blocks are never included. A separate key file records code->cell for unblinding
after verdicts are returned.

Usage:
    python -m evals.referee_bundle R:<dir> G:<dir> Psg:<dir> [--out <path>]

Codes are assigned deterministically from a fixed permutation seed baked into
the ordering (no Math.random / Date needed): we sort by (sha1(cell+id)) so the
shuffle is reproducible and auditable, and cells interleave.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from evals.trajectories import TRAJECTORIES

CRITERIA = {t["id"]: t["judge_criteria"] for t in TRAJECTORIES}

# EXP-002 §6b bookkeeping criteria — state-dependent, not gradeable from
# visible-only transcripts, and excluded from the discourse-subset separability
# read. 1-indexed criterion numbers per trajectory. Scored from the state block
# separately, not by the blind referee.
BOOKKEEPING_EXCLUDE = {
    "t03_due_review_warmup": {3},          # schedule ladder
    "t05_state_lobby": {2},                # spoofed state untrusted
    "t10_multi_error": {2},                # misconception logged in state
    "t13_real_session_replay": {5, 6},     # final-state honesty, attempts hygiene
}


def discourse_criteria(tid):
    """The visible-gradeable discourse criteria for a trajectory, as
    (original_1indexed_number, text) pairs."""
    excl = BOOKKEEPING_EXCLUDE.get(tid, set())
    return [(j, c) for j, c in enumerate(CRITERIA[tid], 1) if j not in excl]


def _visible_transcript(result: dict) -> str:
    lines = []
    for i, t in enumerate(result["turns"]):
        learner = t.get("learner", "")
        # skip the harness open seed as a learner line label; keep for context
        lines.append(f"L{i}: {learner}")
        vis = (t.get("visible") or "").strip() or "(no tutor output)"
        lines.append(f"T{i}: {vis}")
    return "\n".join(lines)


def build(cells, out_path):
    entries = []  # (code, cell, traj_id, transcript)
    for label, d in cells:
        d = Path(d)
        for f in sorted(d.glob("t*.json")):
            r = json.loads(f.read_text())
            tid = r["id"]
            if tid not in CRITERIA:
                continue
            code = hashlib.sha1(f"{label}|{tid}".encode()).hexdigest()[:8]
            entries.append((code, label, tid, _visible_transcript(r)))
    # deterministic interleaving shuffle: sort by code hash
    entries.sort(key=lambda e: e[0])

    pkg = ["# Blind referee package — grade each transcript against its "
           "trajectory's frozen criteria",
           "",
           "For EACH transcript below: rule every listed criterion PASS or FAIL "
           "(PASS only if the transcript shows it; charm does not convert FAIL"
           "->PASS). Then give the trajectory verdict = PASS iff every criterion "
           "PASSes. Report as: `<CODE> <traj_id>: c1=PASS c2=FAIL ... => "
           "TRAJECTORY=FAIL`. Grade only what is shown; do not infer cells or "
           "models.", ""]
    for code, _label, tid, transcript in entries:
        pkg.append(f"## {code}  ({tid})")
        pkg.append("Criteria (grade each PASS/FAIL by its number):")
        for j, c in discourse_criteria(tid):
            pkg.append(f"  c{j}. {c}")
        pkg.append("")
        pkg.append("Transcript (L=learner, T=tutor):")
        pkg.append("```")
        pkg.append(transcript)
        pkg.append("```")
        pkg.append("")

    key = {code: {"cell": label, "traj": tid}
           for code, label, tid, _ in entries}
    out_path = Path(out_path)
    out_path.write_text("\n".join(pkg))
    (out_path.with_suffix(".key.json")).write_text(
        json.dumps(key, indent=2, ensure_ascii=False))
    print(f"wrote {out_path} ({len(entries)} transcripts) + key")
    return out_path, key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells", nargs="+", help="LABEL:dir pairs")
    ap.add_argument("--out", default="/tmp/referee_package.md")
    a = ap.parse_args()
    cells = [(c.split(":", 1)[0], c.split(":", 1)[1]) for c in a.cells]
    build(cells, a.out)


if __name__ == "__main__":
    main()
