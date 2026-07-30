"""Pre-registered r9 referee driver (docs/design-planner-rounds.md).

Runs the frozen arms sequentially — A (legacy), P1 (reorder), P2
(structured tail), B0 (brief context; B1 exists only if B0 leaves
residual) — at N sessions × 6 turns each via evals.run_student_smoke,
then aggregates per-arm still_fail / fixation / probe-on-known /
english-wall counts and per-arm cost from each run's ISOLATED cost
ledger into evals/results/referee-<stamp>/manifest.json.

Frozen bounds (Grok round-1/round-2, B0 countersign): N≥20 sessions/arm
or CI width ≤0.10 on still_fail; session-clustered intervals computed at
analysis time, NOT here (this driver only collects); promotion/kill per
the design doc. Nothing in this driver may drop an arm after seeing
data (P1 stays as control by pre-registration).

Usage: nohup .venv/bin/python -m evals.run_referee --n 20 &
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ARMS: list[tuple[str, dict]] = [
    ("A_legacy", {}),
    ("P1_reorder", {"TEACHER_PROMPT_ORDER": "p1_reorder"}),
    ("P2_structured", {"TEACHER_PROMPT_ORDER": "p2_structured"}),
    ("B0_brief", {"TEACHER_CONTEXT": "brief"}),
]

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def _arm_stats(run_dir: Path) -> dict:
    stats = {
        "sessions": 0, "turns": 0, "still_fail_turns": 0,
        "fixation": 0, "probe_on_known": 0, "english_wall": 0,
        "cost_usd": 0.0,
    }
    for f in sorted(run_dir.glob("*findings*.json")) + sorted(
        run_dir.glob("s*_findings.json")
    ):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        stats["sessions"] += 1
        for k_src, k_dst in (
            ("still_fail", "still_fail_turns"), ("fixation", "fixation"),
            ("probe_on_known", "probe_on_known"),
            ("english_wall", "english_wall"),
        ):
            v = d.get(k_src)
            stats[k_dst] += len(v) if isinstance(v, list) else int(v or 0)
    summ = run_dir / "summary.json"
    if summ.exists():
        try:
            s = json.loads(summ.read_text(encoding="utf-8"))
            stats["summary"] = s
            stats["sessions"] = s.get("sessions", stats["sessions"]) or stats["sessions"]
        except Exception:
            pass
    ledger = run_dir / "costs.jsonl"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                stats["cost_usd"] += float(json.loads(line).get("usd") or 0)
            except Exception:
                continue
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--turns", type=int, default=6)
    args = ap.parse_args()

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_ROOT / f"referee-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "stamp": stamp, "n_per_arm": args.n, "turns": args.turns,
        "arms": {}, "preregistration": "docs/design-planner-rounds.md",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    for arm, env_extra in ARMS:
        before = {p.name for p in RESULTS_ROOT.glob("*-student")}
        import os

        env = {**os.environ, **env_extra}
        rc = subprocess.call(
            [sys.executable, "-m", "evals.run_student_smoke",
             "--n", str(args.n), "--turns", str(args.turns), "-q"],
            env=env, cwd=str(Path(__file__).resolve().parent.parent),
        )
        after = {p.name for p in RESULTS_ROOT.glob("*-student")}
        new_dirs = sorted(after - before)
        run_dir = RESULTS_ROOT / new_dirs[-1] if new_dirs else None
        manifest["arms"][arm] = {
            "env": env_extra, "exit_code": rc,
            "run_dir": str(run_dir) if run_dir else None,
            "stats": _arm_stats(run_dir) if run_dir else {},
        }
        # Persist incrementally — a crash keeps completed arms.
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False)
        )
        print(f"[referee] arm {arm} done rc={rc} -> {run_dir}", flush=True)

    print(f"[referee] COMPLETE -> {out}/manifest.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
