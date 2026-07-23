"""Smoke-test driver: runs pre-registered trajectories through the real tutor
turn path (tutor.cli.run_turn) and applies mechanical checks.

Usage:
    python -m evals.run_smoke              # all trajectories
    python -m evals.run_smoke t04 t05      # by id prefix

Reads ANTHROPIC_API_KEY from the environment or from .env at the repo root.
Results land in evals/results/<stamp>/ (gitignored raw transcripts + a
summary.json scoreboard).
"""

import datetime
import json
import sys
from pathlib import Path

from evals.checks import run_checks
from evals.trajectories import TRAJECTORIES
from tutor import config
from tutor.cli import run_turn
from tutor.policy import build_system
from tutor.student import default_state

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def load_env():
    import os
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env = config.REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def run_trajectory(client, system, traj):
    state = traj.get("seed_state") or default_state()
    history, turns, parse_ok = [], [], True
    scripted = ["Please open the session per policy."] + traj["turns"]
    for i, learner_turn in enumerate(scripted):
        print(f"\n--- {traj['id']} turn {i} ---")
        history, state, final, visible, parse_ok = run_turn(
            client, system, history, state, learner_turn,
            parse_failed=not parse_ok, session_open=(i == 0),
        )
        turns.append({
            "learner": learner_turn,
            "visible": visible,
            "state": state,
            "parse_ok": parse_ok,
            "stop_reason": final.stop_reason,
            "usage": {
                "input_tokens": final.usage.input_tokens,
                "output_tokens": final.usage.output_tokens,
                "cache_read_input_tokens": getattr(
                    final.usage, "cache_read_input_tokens", 0) or 0,
            },
        })
    return {"id": traj["id"], "turns": turns}


def main():
    load_env()
    import anthropic
    prefixes = sys.argv[1:]
    selected = [t for t in TRAJECTORIES
                if not prefixes or any(t["id"].startswith(p) for p in prefixes)]
    client = anthropic.Anthropic()
    system = build_system(config.POLICY_PATH, config.DEFAULT_PACK_DIR)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = RESULTS_ROOT / stamp
    outdir.mkdir(parents=True, exist_ok=True)

    summary = []
    for traj in selected:
        try:
            result = run_trajectory(client, system, traj)
        except anthropic.APIStatusError as e:
            summary.append({"id": traj["id"], "status": "ERROR",
                            "error": f"{e.status_code}: {e.message}"})
            print(f"\n[{traj['id']}] API error {e.status_code}; continuing")
            continue
        findings, passed = run_checks(traj, result)
        result["findings"] = findings
        result["mechanical_pass"] = passed
        (outdir / f"{traj['id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2))
        summary.append({
            "id": traj["id"],
            "status": "PASS" if passed else "FAIL",
            "warns": sum(1 for v in findings.values()
                         for f in v if f.startswith("WARN")),
            "findings": findings,
        })

    (outdir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n{'='*50}\nMechanical scoreboard ({outdir}):")
    for row in summary:
        warns = f" ({row['warns']} warns)" if row.get("warns") else ""
        print(f"  {row['status']:5} {row['id']}{warns}")
    print("Judge-criteria scoring happens separately (blind referee "
          "on the transcript JSONs).")


if __name__ == "__main__":
    main()
