"""The persona gate: the three standing students, IN PARALLEL, one verdict.

USER 2026-08-04: "this kind of testing should be able to happen each with
their own character sheets and at the same time." Each persona runs as its
own fully-isolated run_student_smoke process (per-run sheet + progress/
cost/grade ledgers + session dir — nothing shared but API rate limits).

Cadence (R4 convention): every behavior-touching change + nightly.

    python -m evals.run_persona_gate            # sam, casey, sofia; 10 turns
    python -m evals.run_persona_gate --turns 8 --personas sam_stuck,sofia_fluent
"""

from __future__ import annotations

import argparse
import subprocess
import sys

DEFAULT_PERSONAS = ("sam_stuck", "casey_steady", "sofia_fluent")


def main() -> None:
    ap = argparse.ArgumentParser(description="Parallel persona gate")
    ap.add_argument("--turns", type=int, default=10)
    ap.add_argument(
        "--personas", default=",".join(DEFAULT_PERSONAS),
        help="comma-separated persona ids",
    )
    args = ap.parse_args()
    personas = [p.strip() for p in args.personas.split(",") if p.strip()]

    procs = {}
    for p in personas:
        procs[p] = subprocess.Popen(
            [sys.executable, "-m", "evals.run_student_smoke",
             "--turns", str(args.turns), "--n", "1", "--persona", p,
             "--quiet"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
    failed = []
    for p, proc in procs.items():
        out, _ = proc.communicate()
        tail = "\n".join((out or "").splitlines()[-14:])
        print(f"\n======== {p} (exit {proc.returncode}) ========")
        print(tail)
        if proc.returncode != 0:
            failed.append(p)
    print(f"\nPERSONA GATE: {'FAIL ' + ','.join(failed) if failed else 'PASS'}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
