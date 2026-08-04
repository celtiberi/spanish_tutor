"""AI-student behavioral smoke (R4, docs/reviews-system-review-20260730.md).

Runs the Grok-driven AI student (tutor/ai_student.py) against the REAL tutor
model on the planned pipeline, then applies evals/student_checks.py
mechanical post-checks: repetition/fixation, output_gate_still_fail count,
probe-on-known, english-wall drift. Cadence per R4: every behavior-touching
change + nightly; regressions block promotion (extends the §4.3 bar).

Usage:
    python -m evals.run_student_smoke
    python -m evals.run_student_smoke --n 2 --turns 8 --persona maya_shy
    python -m evals.run_student_smoke --model gemini-3.6-flash --level novice_mid

Personas run in PARALLEL (each process is fully isolated: per-run sheet,
progress/cost/grade ledgers, and session dir — nothing shared but API
rate limits). The three standing archetypes:
    for P in sam_stuck casey_steady sofia_fluent; do
        python -m evals.run_student_smoke --turns 10 --persona $P --quiet &
    done; wait

Results: evals/results/<stamp>-student/ with per-session report JSON
(transcript + findings) + summary.json. Exit nonzero on any FAIL/ERROR.

Isolation (operator-pollution incident 2026-07-28 — tutor/progress_ledger.py
docstring, tests/test_progress_ledger.py): per-run sheets under the results
stamp, so logs/character_sheet.json is NEVER touched; PROGRESS_LEDGER_PATH,
COST_LEDGER_PATH and GRADE_LOG_PATH point at per-run files; session logging
off; focus rail off; image generation off. The tutor package is imported
INSIDE main(), after the ledger env is pinned — tutor/costs.py binds
COST_LEDGER_PATH at import time, so import order here is load-bearing.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import traceback
from pathlib import Path

# --- env clamps BEFORE any tutor import (run_conv_smoke pattern) ---
os.environ.setdefault("TEACHER_MODE", "planned")
os.environ.setdefault("TEACH_IMAGE_GENERATE", "0")
# Tools ON (full-code-audit S7.11): update_character_sheet is the ONLY
# grading path since the rules-based sheet update was deleted 2026-07-31 —
# with tools off this smoke structurally cannot exercise grading.
os.environ.setdefault("SHEET_TOOLS", "true")
# Voice is browser-triggered on the web path and never fires in this
# headless harness (verified: zero `tts` rows in run ledgers) — clamped
# anyway so no future change can silently bill audio for a text sim.
os.environ.setdefault("TTS_ENABLED", "false")
# Full teacher context while testing (project gate:
# docs/teacher-context-no-truncate.md)
os.environ.setdefault("TEACHER_CONTEXT_TRUNCATE", "false")

from evals.student_checks import run_student_checks  # noqa: E402 (tutor.textnorm only)

RESULTS_ROOT = Path(__file__).resolve().parent / "results"


def _pin_ledgers(outdir: Path) -> None:
    """Per-run ledger files. Hard assignment, not setdefault: an ambient
    ledger path pointing at the real files is exactly the pollution the
    2026-07-28 incident wrote up. GRADE_LOG_PATH rides the same pin
    (full-code-audit S7.11): with SHEET_TOOLS on, tool grades would
    otherwise land in the learner's live logs/sheet_grades.jsonl —
    grade_log.default_grade_log_path honors the env var, so no plumbing
    through ConvSession is needed."""
    os.environ["PROGRESS_LEDGER_PATH"] = str(outdir / "progress.jsonl")
    os.environ["COST_LEDGER_PATH"] = str(outdir / "costs.jsonl")
    os.environ["GRADE_LOG_PATH"] = str(outdir / "sheet_grades.jsonl")


def _patch_runtime_for_smoke(config) -> None:
    """Module-level flags may already be bound; force smoke-safe values."""
    config.load_env()
    config.TEACHER_MODE = "planned"
    try:
        import tutor.teach_assets as teach_assets

        teach_assets.GENERATE_ON_MISS = False
    except Exception:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AI-student smoke: Grok student vs real tutor + mechanical checks"
    )
    ap.add_argument("--n", type=int, default=1, help="number of sessions (default 1)")
    ap.add_argument("--turns", type=int, default=8, help="exchanges per session (default 8)")
    ap.add_argument("--persona", default="alex_boat", help="student persona preset")
    ap.add_argument("--level", default=None, help="ability band override")
    ap.add_argument(
        "--student-model",
        default=None,
        help="Grok model for the student (default AI_STUDENT_MODEL / grok-4.5)",
    )
    ap.add_argument(
        "--model", default=None, help="tutor model (default TUTOR_MODEL / config.MODEL)"
    )
    ap.add_argument("--pack", type=Path, default=None, help="course pack dir")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = RESULTS_ROOT / f"{stamp}-student"
    (outdir / "sheets").mkdir(parents=True, exist_ok=True)
    _pin_ledgers(outdir)

    # tutor imports AFTER the ledger pins (tutor/costs.py binds COST_LEDGER_PATH
    # at import time — see module docstring).
    from tutor import config
    from tutor.ai_student import run_simulation

    _patch_runtime_for_smoke(config)
    model = args.model or config.MODEL
    pack_dir = Path(args.pack or config.DEFAULT_PACK_DIR)

    cell = {
        "arch": "ai_student_planned",
        "model": model,
        "teacher_mode": "planned",
        "persona": args.persona,
        "level": args.level,
        "turns": args.turns,
        "pack": str(pack_dir),
    }
    print(
        f"[student-smoke] tutor={model} persona={args.persona} "
        f"turns={args.turns} n={args.n} out={outdir}"
    )
    print(
        f"[student-smoke] isolation sheets={outdir / 'sheets'} "
        f"(not {config.CHARACTER_SHEET_PATH}); "
        f"ledgers={outdir}/progress.jsonl,costs.jsonl,sheet_grades.jsonl"
    )

    summary: list[dict] = []
    for ix in range(1, max(1, args.n) + 1):
        sid = f"s{ix:02d}-{args.persona}"
        sheet_path = outdir / "sheets" / f"{sid}.json"
        print(f"\n=== session {sid} ===")
        try:
            report = run_simulation(
                turns=max(1, args.turns),
                persona_id=args.persona,
                ability_level=args.level,
                student_model=args.student_model,
                tutor_model=model,
                pack_dir=pack_dir,
                sheet_path=sheet_path,
                reset_sheet=True,
                live_print=not args.quiet,
                use_tools=True,      # tool grading is the ONLY grades path
                session_log=False,   # no logs/sessions writes from eval traffic
                sim_log_dir=outdir / "sessions",
            )
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            print(f"[{sid}] ERROR {err}")
            traceback.print_exc()
            summary.append({"id": sid, "status": "ERROR", "error": err[:500]})
            (outdir / f"{sid}.json").write_text(
                json.dumps(
                    {"id": sid, **cell, "status": "ERROR", "error": err},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            continue

        findings, passed = run_student_checks(report.get("transcript") or [])
        status = "PASS" if passed else "FAIL"
        # Plan-lifecycle visibility (USER 2026-08-04: when does the
        # teacher call for a new plan?): count session_plan events.
        plan_counts: dict[str, int] = {}
        for t_row in report.get("transcript") or []:
            for n in t_row.get("notes") or []:
                n = str(n)
                if n.startswith("session_plan:"):
                    k = n.split(":", 1)[1]
                    plan_counts[k] = plan_counts.get(k, 0) + 1
        row = {
            "id": sid,
            "status": status,
            "plan_events": plan_counts,
            "warns": sum(
                1 for v in findings.values() for f in v if str(f).startswith("WARN")
            ),
            "findings": findings,
            "harness_checks_failed": [
                c.get("id") for c in report.get("checks") or [] if not c.get("ok")
            ],
        }
        summary.append(row)
        (outdir / f"{sid}.json").write_text(
            json.dumps(
                {"id": sid, **cell, "status": status, "findings": findings,
                 "report": report},
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    summary_doc = {
        "cell": cell,
        "stamp": stamp,
        "n": len(summary),
        "results": summary,
        "isolation": {
            "sheets_dir": str(outdir / "sheets"),
            "default_character_sheet_untouched": str(config.CHARACTER_SHEET_PATH),
            "progress_ledger": os.environ.get("PROGRESS_LEDGER_PATH"),
            "cost_ledger": os.environ.get("COST_LEDGER_PATH"),
            "grade_log": os.environ.get("GRADE_LOG_PATH"),
            "session_log": False,
            "teach_image_generate": False,
        },
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(f"AI-student mechanical scoreboard ({outdir}):")
    failed = 0
    for row in summary:
        if row["status"] != "PASS":
            failed += 1
        warns = f" ({row['warns']} warns)" if row.get("warns") else ""
        extra = f" err={row.get('error')}" if row["status"] == "ERROR" else ""
        pc = row.get("plan_events") or {}
        plan_s = (
            " plan[" + " ".join(f"{k}={v}" for k, v in sorted(pc.items())) + "]"
            if pc else ""
        )
        print(f"  {row['status']:5} {row['id']}{warns}{plan_s}{extra}")
        for name, items in (row.get("findings") or {}).items():
            for f in items:
                print(f"        [{name}] {f}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
