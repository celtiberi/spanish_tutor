"""Conversational smoke driver: real ConvSession planned pipeline + mechanical checks.

Usage:
    python -m evals.run_conv_smoke
    python -m evals.run_conv_smoke c02 c03
    python -m evals.run_conv_smoke --model gemini-3.6-flash --cell conv-smoke

Results: evals/results/<stamp>/ with per-traj JSON + summary.json
Isolation: per-traj character sheets under that stamp; never writes
logs/character_sheet.json. Session logging off; focus model off; image
generation off.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import traceback
from copy import deepcopy
from pathlib import Path

# --- env clamps BEFORE config-dependent imports (re-patched after import too) ---
os.environ.setdefault("TEACHER_MODE", "planned")
os.environ.setdefault("TEACH_IMAGE_GENERATE", "0")
os.environ.setdefault("FOCUS_MODEL", "off")
os.environ.setdefault("FOCUS_ASYNC", "false")
os.environ.setdefault("FOCUS_BLOCKING", "false")
os.environ.setdefault("SHEET_TOOLS", "false")
# Full teacher context while testing (project gate)
os.environ.setdefault("TEACHER_CONTEXT_TRUNCATE", "false")

from evals.conv_checks import run_conv_checks
from evals.conv_trajectories import CONV_TRAJECTORIES, get_seed_sheet
from tutor import config
from tutor.character_sheet import save_sheet
from tutor.conv_session import ConversationalSession

RESULTS_ROOT = Path(__file__).resolve().parent / "results"

SNAPSHOT_SKILLS = ("IP-01", "IP-03", "IP-04", "IP-07")


def _patch_runtime_for_smoke() -> None:
    """Module-level flags may already be bound; force smoke-safe values."""
    config.load_env()
    config.TEACHER_MODE = "planned"
    config.FOCUS_ASYNC = False
    config.FOCUS_BLOCKING = False
    config.FOCUS_MODEL = "off"
    try:
        import tutor.teach_assets as teach_assets

        teach_assets.GENERATE_ON_MISS = False
    except Exception:
        pass


def _apply_mode_state(session: ConversationalSession, seed: dict | None) -> None:
    if not seed:
        return
    ms = session.mode_state
    for k, v in seed.items():
        if k == "form_focus_cooldown" and isinstance(v, dict):
            ms.form_focus_cooldown = dict(v)
        elif hasattr(ms, k):
            setattr(ms, k, v)


def _apply_phase_state(session: ConversationalSession, seed: dict | None) -> None:
    """Advance the session PhaseState to a later plan phase (e.g. task).

    Mechanical seeding only — the plan itself stays code-built from the seed
    sheet; we just move the clock so a trajectory can exercise a later phase
    without burning live turns."""
    if not seed:
        return
    ps = session.phase_state
    try:
        ps.index = int(seed.get("index", ps.index))
    except (TypeError, ValueError):
        pass
    try:
        ps.turns_in_phase = int(seed.get("turns_in_phase", ps.turns_in_phase))
    except (TypeError, ValueError):
        pass


def _skill_conf(sheet: dict, cid: str) -> float:
    try:
        return float(((sheet.get("skills") or {}).get(cid) or {}).get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _snapshot_skills(sheet: dict) -> dict[str, float]:
    return {cid: _skill_conf(sheet, cid) for cid in SNAPSHOT_SKILLS}


def run_conv_trajectory(
    traj: dict,
    *,
    model: str,
    pack_dir: Path,
    sheet_path: Path,
    cell: dict,
) -> dict:
    seed = get_seed_sheet(traj)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    if sheet_path.exists():
        sheet_path.unlink()
    save_sheet(sheet_path, seed)
    # Progress-ledger isolation: per-trajectory file beside the isolated
    # sheet, never logs/progress.jsonl — AND a fresh dedupe universe, so
    # milestone expectations (progress_milestones_fired) can't be suppressed
    # by a previous run's crossings.
    progress_path = sheet_path.with_name(f"{traj['id']}-progress.jsonl")
    if progress_path.exists():
        progress_path.unlink()
    os.environ["PROGRESS_LEDGER_PATH"] = str(progress_path)

    session = ConversationalSession(
        model=model,
        pack_dir=pack_dir,
        sheet_path=sheet_path,
        use_tools=False,
        label=f"conv-smoke-{traj['id']}",
        log=False,  # do not write logs/sessions/*
        focus_model="off",
    )
    # Re-assert planned path regardless of ambient env
    session.teacher_mode = "planned"
    _apply_mode_state(session, traj.get("seed_mode_state"))
    _apply_phase_state(session, traj.get("seed_phase_state"))

    turns_out: list[dict] = []
    conf_series: dict[str, list[float]] = {cid: [] for cid in SNAPSHOT_SKILLS}

    def _push(learner: str, tr, *, is_open: bool) -> None:
        parts = dict(tr.parts or {})
        snap = _snapshot_skills(session.sheet)
        if not tr.error:
            for cid, val in snap.items():
                conf_series[cid].append(val)
        turns_out.append({
            "learner": learner,
            "is_open": is_open,
            "visible": tr.reply or "",
            "reply": tr.reply or "",
            "error": tr.error,
            "notes": list(tr.notes or []),
            # Typed turn events (Phase 3 batch 2): the serialized timeline —
            # conv_checks consumes these first; the notes list above is their
            # chronological string projection (kept for replay/display).
            "events": [
                e.as_dict() if hasattr(e, "as_dict") else e
                for e in (tr.events or [])
            ],
            "usage": dict(tr.usage or {}),
            "stop_reason": tr.stop_reason,
            "parts": parts,
            "mode": parts.get("mode"),
            "mode_decision": parts.get("mode_decision"),
            "output_gate": parts.get("output_gate"),
            "next_best": dict(tr.next_best or {}),
            "sheet_identity": deepcopy(session.sheet.get("identity") or {}),
            "sheet_error_patterns": deepcopy(
                session.sheet.get("error_patterns") or {}
            ),
            "skill_confidence": snap,
            "mode_state": session.mode_state.snapshot(),
        })

    print(f"\n--- {traj['id']} open ---")
    open_res = session.open_session()
    _push("(session open)", open_res, is_open=True)
    if open_res.error:
        session.close(persist_sheet=True)  # isolated sheet_path only
        return {
            "id": traj["id"],
            **cell,
            "status": "ERROR",
            "error": open_res.error,
            "turns": turns_out,
            "final_sheet": deepcopy(session.sheet),
            "final_profile": deepcopy(getattr(session, "profile", {}) or {}),
            "skill_confidence_series": conf_series,
            "seed_sheet": seed,
        }

    for i, learner_turn in enumerate(traj.get("turns") or []):
        print(f"\n--- {traj['id']} turn {i + 1} ---")
        tr = session.user_turn(learner_turn)
        _push(learner_turn, tr, is_open=False)
        if tr.error:
            break

    final_sheet = deepcopy(session.sheet)
    final_profile = deepcopy(getattr(session, "profile", {}) or {})
    session.close(persist_sheet=True)  # isolated sheet_path only

    return {
        "id": traj["id"],
        **cell,
        "turns": turns_out,
        "final_sheet": final_sheet,
        "final_profile": final_profile,
        "skill_confidence_series": conf_series,
        "seed_sheet": seed,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="ConvSession behavioral smoke gate")
    ap.add_argument("prefixes", nargs="*", help="trajectory id prefixes")
    ap.add_argument(
        "--model",
        default=None,
        help=f"tutor model (default: config.MODEL={config.MODEL})",
    )
    ap.add_argument("--pack", type=Path, default=config.DEFAULT_PACK_DIR)
    ap.add_argument("--cell", default=None, help="cell label in results")
    args = ap.parse_args()

    _patch_runtime_for_smoke()
    model = args.model or config.MODEL

    selected = [
        t
        for t in CONV_TRAJECTORIES
        if not args.prefixes
        or any(t["id"].startswith(p) for p in args.prefixes)
    ]
    if not selected:
        raise SystemExit(f"no trajectories matched {args.prefixes!r}")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = RESULTS_ROOT / stamp
    sheets_dir = outdir / "sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)

    cell = {
        "arch": "conversational_planned",
        "model": model,
        "teacher_mode": "planned",
        "cell": args.cell or f"conv-{model}",
        "pack": str(args.pack),
    }
    print(
        f"[conv-smoke] model={model} teacher_mode=planned "
        f"n={len(selected)} out={outdir}"
    )
    print(
        f"[conv-smoke] isolation sheets_dir={sheets_dir} "
        f"(not {config.CHARACTER_SHEET_PATH})"
    )

    summary = []
    for traj in selected:
        sheet_path = sheets_dir / f"{traj['id']}.json"
        try:
            result = run_conv_trajectory(
                traj,
                model=model,
                pack_dir=Path(args.pack),
                sheet_path=sheet_path,
                cell=cell,
            )
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            print(f"\n[{traj['id']}] ERROR {err}")
            traceback.print_exc()
            summary.append({
                "id": traj["id"],
                "status": "ERROR",
                "error": err[:500],
            })
            (outdir / f"{traj['id']}.json").write_text(
                json.dumps(
                    {"id": traj["id"], **cell, "status": "ERROR", "error": err},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            continue

        if result.get("error") and not any(
            not t.get("error") for t in result.get("turns") or []
        ):
            summary.append({
                "id": traj["id"],
                "status": "ERROR",
                "error": result.get("error"),
            })
        else:
            findings, passed = run_conv_checks(traj, result)
            result["findings"] = findings
            result["mechanical_pass"] = passed
            summary.append({
                "id": traj["id"],
                "status": "PASS" if passed else "FAIL",
                "warns": sum(
                    1
                    for v in findings.values()
                    for f in v
                    if str(f).startswith("WARN")
                ),
                "findings": findings,
                "modes": [t.get("mode") for t in result.get("turns") or []],
            })

        (outdir / f"{traj['id']}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    summary_doc = {
        "cell": cell,
        "stamp": stamp,
        "n": len(selected),
        "results": summary,
        "isolation": {
            "sheets_dir": str(sheets_dir),
            "default_character_sheet_untouched": str(config.CHARACTER_SHEET_PATH),
            "session_log": False,
            "teach_image_generate": False,
        },
    }
    (outdir / "summary.json").write_text(
        json.dumps(summary_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 50}")
    print(f"Conv mechanical scoreboard [{cell['cell']}] ({outdir}):")
    for row in summary:
        warns = f" ({row['warns']} warns)" if row.get("warns") else ""
        modes = row.get("modes")
        mode_s = f" modes={modes}" if modes else ""
        extra = f" err={row.get('error')}" if row.get("status") == "ERROR" else ""
        print(f"  {row['status']:5} {row['id']}{warns}{mode_s}{extra}")


if __name__ == "__main__":
    main()
