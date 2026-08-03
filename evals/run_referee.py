"""RETIRED multi-arm referee driver (pending a new pre-registration).

The r9 falsifier arms are DEAD (full-code-audit S1f, 2026-08-03):
TEACHER_CONTEXT=brief was DELETED (B0 lost the blind grade, then its
course pack was deleted) and the TEACHER_PROMPT_ORDER selector +
p1_reorder / p2_structured branches were DELETED from
config.py/executor.py — those env vars are now no-ops, so the historical
arm list would have silently run FOUR COPIES of the same configuration
(fabricated-comparison hazard, Grok countersign).

Until a NEW pre-registered comparison exists, ARMS holds the single live
configuration (the plan-mode teacher). The driver mechanics — isolated
cost ledgers, transcript-backed stats, fail-fast on provider refusal —
are kept intact for that next registration.

Usage: nohup .venv/bin/python -m evals.run_referee --n 20 &
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

# The single live arm (see module docstring — multi-arm runs require a new
# pre-registration with real, code-backed arm selectors).
ARMS: list[tuple[str, dict]] = [
    ("plan", {}),
]

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def _arm_stats(run_dir: Path) -> dict:
    """Aggregate ONE arm from its real session artifacts.

    Run-1 incident (2026-07-30): the first version globbed
    ``*findings*.json`` (no such files — every arm read as 0 sessions)
    and, in the ad-hoc fix, counted the REQUESTED ``turns`` field as
    executed turns — which reported an arm whose every session ERRORed
    as a flawless zero-fault winner. Only transcript-backed turns count;
    ERROR sessions are counted separately and never silently absorbed
    (§3.4 unknown-is-not-neutral).
    """
    stats = {
        "sessions_ran": 0, "sessions_error": 0, "turns": 0,
        "still_fail_turns": 0, "fixation": 0, "probe_on_known": 0,
        "english_wall": 0, "cost_usd": 0.0, "errors": [],
    }
    for f in sorted(run_dir.glob("s*-*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        transcript = (d.get("report") or {}).get("transcript") or []
        if not transcript:
            stats["sessions_error"] += 1
            err = str(d.get("error") or d.get("status") or "unknown")
            if err not in stats["errors"]:
                stats["errors"].append(err[:200])
            continue
        stats["sessions_ran"] += 1
        stats["turns"] += len(transcript)
        findings = d.get("findings") or {}
        for k_src, k_dst in (
            ("still_fail", "still_fail_turns"), ("fixation", "fixation"),
            ("probe_on_known", "probe_on_known"),
            ("english_wall", "english_wall"),
        ):
            v = findings.get(k_src)
            stats[k_dst] += len(v) if isinstance(v, list) else int(v or 0)
    ledger = run_dir / "costs.jsonl"
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                stats["cost_usd"] += float(json.loads(line).get("usd") or 0)
            except Exception:
                continue
    if stats["turns"]:
        stats["still_fail_per_turn"] = round(
            stats["still_fail_turns"] / stats["turns"], 4
        )
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
        "arms": {},
        # No live pre-registration: the r9 arms died with their selectors
        # (full-code-audit S1f). A future multi-arm run must register anew.
        "preregistration": None,
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
        stats = _arm_stats(run_dir) if run_dir else {}
        manifest["arms"][arm] = {
            "env": env_extra, "exit_code": rc,
            "run_dir": str(run_dir) if run_dir else None,
            "stats": stats,
        }
        # Persist incrementally — a crash keeps completed arms.
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False)
        )
        ran = stats.get("sessions_ran", 0)
        errs = stats.get("sessions_error", 0)
        print(
            f"[referee] arm {arm} done rc={rc} ran={ran} err={errs} "
            f"-> {run_dir}", flush=True,
        )
        # Fail fast (run-1 incident): an arm that produced NO usable
        # sessions means the provider is refusing — burning the remaining
        # arms just manufactures more empty directories and hides which
        # arms are actually untested.
        if ran == 0 and errs:
            manifest["aborted_after"] = arm
            manifest["abort_reason"] = (
                f"arm {arm} produced 0 usable sessions ({errs} errors: "
                f"{stats.get('errors')}) — provider refusing; remaining "
                "arms NOT run (they would be empty, not passing)"
            )
            (out / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False)
            )
            print(
                f"[referee] ABORT after {arm}: 0 usable sessions. "
                f"Untested arms remain untested — no arm may be read as "
                f"clean. -> {out}/manifest.json", flush=True,
            )
            return 2

    print(f"[referee] COMPLETE -> {out}/manifest.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
