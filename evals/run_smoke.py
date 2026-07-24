"""Smoke-test driver: runs pre-registered trajectories through the real tutor
turn path and applies mechanical checks.

Usage:
    python -m evals.run_smoke                      # all trajectories, single model
    python -m evals.run_smoke t04 t05              # by id prefix
    python -m evals.run_smoke --arch planner       # EXP-002 planner/executor
    python -m evals.run_smoke --arch planner --planner claude-opus-4-8 \
        --executor gemini-3.6-flash --cell P

Single-model runs use tutor.cli.run_turn unchanged (TUTOR_MODEL selects the
model), so EXP-001 cells stay reproducible. `--arch planner` routes through
tutor.planner.run_planned_turn instead.

Reads API keys from the environment or from .env at the repo root. Results land
in evals/results/<stamp>/ (gitignored raw transcripts + a summary.json).
"""

import argparse
import datetime
import json
from pathlib import Path

from evals.checks import run_checks
from evals.trajectories import TRAJECTORIES
from tutor import config
from tutor.cli import run_turn
from tutor.planner import (
    CONTROLLER_PATH,
    EXECUTOR_CONTROLLER_PATH,
    PLANNER_PATH,
    STRUCTURED_PATH,
    THIN_PATH,
    build_controller_planner_system,
    build_executor_system,
    build_planner_system,
    run_controller_turn,
    run_planned_turn,
    run_structured_turn,
)
from tutor.policy import build_system
from tutor.session_log import SessionLogger
from tutor.student import default_state

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def load_env():
    config.load_env()


def _usage(final):
    return {
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "cache_read_input_tokens": getattr(
            final.usage, "cache_read_input_tokens", 0) or 0,
    }


def run_trajectory(traj, cell, step):
    """`step(history, state, learner_turn, parse_ok, session_open)` returns
    (history, state, final, visible, parse_ok, extra) for either architecture."""
    state = traj.get("seed_state") or default_state()
    history, turns, parse_ok = [], [], True
    scripted = ["Please open the session per policy."] + traj["turns"]
    for i, learner_turn in enumerate(scripted):
        print(f"\n--- {traj['id']} turn {i} ---")
        history, state, final, visible, parse_ok, extra = step(
            history, state, learner_turn, parse_ok, i == 0)
        turns.append({
            "learner": learner_turn,
            "visible": visible,
            "state": state,
            "parse_ok": parse_ok,
            "stop_reason": final.stop_reason,
            "usage": _usage(final),
            **extra,
        })
    return {"id": traj["id"], **cell, "turns": turns}


def single_stepper(client, system):
    def step(history, state, learner_turn, parse_ok, session_open):
        h, s, final, visible, ok = run_turn(
            client, system, history, state, learner_turn,
            parse_failed=not parse_ok, session_open=session_open)
        return h, s, final, visible, ok, {}
    return step


def planner_stepper(planner, executor, planner_system, executor_system,
                    turn_fn=run_planned_turn, session_logger=None):
    def step(history, state, learner_turn, parse_ok, session_open):
        kwargs = dict(
            planner=planner, executor=executor,
            planner_system=planner_system, executor_system=executor_system,
            history=history, state=state, user_input=learner_turn,
            parse_failed=not parse_ok, session_open=session_open,
        )
        # Only controller path accepts session_logger today.
        if turn_fn is run_controller_turn and session_logger is not None:
            kwargs["session_logger"] = session_logger
        return turn_fn(**kwargs)
    return step


def _side(model):
    from types import SimpleNamespace
    return SimpleNamespace(caps=config.caps_for(model),
                           client=config.make_client_for(model))


def main():
    ap = argparse.ArgumentParser(description="Behavioral gate driver")
    ap.add_argument("prefixes", nargs="*", help="trajectory id prefixes")
    ap.add_argument(
        "--arch",
        choices=["single", "planner", "structured", "controller"],
        default="single",
        help="single | planner (EXP-002 free-text) | structured (EXP-003) | "
             "controller (limited pedagogical DSL + act cards)",
    )
    ap.add_argument(
        "--planner", default=config.CONTROLLER_PLANNER,
        help=f"planner model (default: {config.CONTROLLER_PLANNER})")
    ap.add_argument(
        "--executor", default=config.CONTROLLER_EXECUTOR,
        help=f"executor model (default: {config.CONTROLLER_EXECUTOR})")
    ap.add_argument("--pack", type=Path, default=config.DEFAULT_PACK_DIR)
    ap.add_argument("--cell", default=None, help="cell label recorded in results")
    args = ap.parse_args()

    load_env()
    selected = [t for t in TRAJECTORIES
                if not args.prefixes
                or any(t["id"].startswith(p) for p in args.prefixes)]

    session_logger = None
    if args.arch in ("planner", "structured", "controller"):
        planner, executor = _side(args.planner), _side(args.executor)
        if args.arch == "controller":
            wrapper = CONTROLLER_PATH
            thin = EXECUTOR_CONTROLLER_PATH
            turn_fn = run_controller_turn
            default_cell = "Pc"
        elif args.arch == "structured":
            wrapper = STRUCTURED_PATH
            thin = THIN_PATH
            turn_fn = run_structured_turn
            default_cell = "Ps"
        else:
            wrapper = PLANNER_PATH
            thin = THIN_PATH
            turn_fn = run_planned_turn
            default_cell = "P"
        if args.arch == "controller":
            planner_system = build_controller_planner_system(args.pack)
        else:
            planner_system = build_planner_system(
                config.POLICY_PATH, wrapper, args.pack)
        executor_system = build_executor_system(thin, args.pack)
        if args.arch == "controller":
            session_logger = SessionLogger(
                arch="controller",
                label=args.cell or "smoke",
                meta={
                    "mode": "run_smoke",
                    "planner_model": args.planner,
                    "executor_model": args.executor,
                    "pack": str(args.pack),
                    "prefixes": list(args.prefixes),
                },
            )
            print(f"[session log] {session_logger.jsonl_path}")
            print(f"[session md ] {session_logger.md_path}")
        step = planner_stepper(planner, executor, planner_system,
                               executor_system, turn_fn=turn_fn,
                               session_logger=session_logger)
        cell = {"arch": args.arch, "planner_model": args.planner,
                "executor_model": args.executor, "model": args.executor,
                "cell": args.cell or default_cell}
        print(f"[{args.arch}] planner {args.planner} -> executor {args.executor} "
              f"(wrapper {wrapper.name}, executor {thin.name})")
    else:
        client = config.make_client()
        system = build_system(config.POLICY_PATH, args.pack)
        step = single_stepper(client, system)
        cell = {"arch": "single", "model": config.MODEL,
                "cell": args.cell or config.MODEL}
        print(f"model under test: {config.MODEL} (provider {config.PROVIDER})")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = RESULTS_ROOT / stamp
    outdir.mkdir(parents=True, exist_ok=True)

    summary = []
    for traj in selected:
        try:
            result = run_trajectory(traj, cell, step)
        except Exception as e:  # provider-agnostic: log and continue the suite
            summary.append({"id": traj["id"], "status": "ERROR",
                            "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"\n[{traj['id']}] {type(e).__name__}; continuing")
            if session_logger is not None:
                session_logger.event(
                    "trajectory_error", traj_id=traj["id"],
                    error=f"{type(e).__name__}: {str(e)[:300]}")
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
        if session_logger is not None:
            session_logger.event(
                "trajectory_done", traj_id=traj["id"],
                mechanical_pass=passed, findings=findings)

    (outdir / "summary.json").write_text(
        json.dumps({"cell": cell, "results": summary},
                   ensure_ascii=False, indent=2))
    if session_logger is not None:
        session_logger.close(
            mode="run_smoke", results_dir=str(outdir), summary=summary)
        print(f"[session log closed] {session_logger.jsonl_path}")
    print(f"\n{'='*50}\nMechanical scoreboard [{cell['cell']}] ({outdir}):")
    for row in summary:
        warns = f" ({row['warns']} warns)" if row.get("warns") else ""
        print(f"  {row['status']:5} {row['id']}{warns}")
    print("Judge-criteria scoring happens separately (blind referee "
          "on the transcript JSONs).")


if __name__ == "__main__":
    main()
