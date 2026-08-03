"""Pedagogy phase/record-keeping helpers (the judgment half is DELETED).

S11 (USER-ruled 2026-08-03, docs/reviews-full-code-audit-20260803.md):
runtime teaching-judgment is a relic of the code-is-teacher era.  The
per-turn contract checker that lived here — ``evaluate_turn`` /
``check_tutor_parts`` / ``check_visible_fallback`` / ``PedagogyCheck`` and
the pedagogy:no_teach_move / pedagogy:open_needs_model_try /
pedagogy:recast_without_try fault vocabulary — was deleted from the runtime
(§4.6: git is the archive) and lives ONLY as eval test cases over
AI-student transcripts (evals/student_checks.py::check_teach_shape).  The
teaching rules themselves are unchanged in PEDAGOGY §2 — the model still
receives them.

What remains is record-keeping, not judgment:

- ``is_blank_learner`` / ``open_phase``: blank-sheet detection feeding the
  turn pipeline (diagnostic vs known open) and the observer.
- ``has_teach_move``: a mechanical shape helper (are model/try/recast
  non-empty) used by the AI-student harness transcript stats.
- ``KEY_DIAGNOSTIC_OPEN`` / ``KEY_KNOWN_LEARNER_OPEN``: the phase-note keys
  the turn tail's PEDAGOGY event renders from
  (turn_pipeline.stage_soft_plan / stage_tail_events).
"""

from __future__ import annotations

from typing import Any

# Phase-note keys for the turn tail's PEDAGOGY event (bookkeeping — which
# open script ran; "pedagogy:" + key is the rendered note).
KEY_DIAGNOSTIC_OPEN = "diagnostic_open"
KEY_KNOWN_LEARNER_OPEN = "known_learner_open"

# (TEACH_MODALITIES DELETED 2026-08-03, full-code-audit S2. CONTRACT_VERSION,
# PedagogyCheck, check_tutor_parts, check_visible_fallback, evaluate_turn and
# the violation/note-key constants DELETED 2026-08-03, S11 — the contract is
# now an eval check, not a runtime judgment; git history is the archive.)


def is_blank_learner(sheet: dict | None) -> bool:
    """True when we have essentially no ability evidence — feel-out required.

    A wiped / default sheet is not an intermediate speaker. Opening pure
    Spanish monologue at them is a failure of judgment.
    """
    if not isinstance(sheet, dict):
        return True
    ident = sheet.get("identity") or {}
    name = (ident.get("preferred_name") or ident.get("name") or "").strip()
    skills = sheet.get("skills") or {}
    any_evidence = False
    for _k, v in skills.items() if isinstance(skills, dict) else []:
        if not isinstance(v, dict):
            continue
        conf = float(v.get("confidence") or 0)
        status = (v.get("status") or "unknown").lower()
        ev = v.get("evidence") or []
        if conf > 0.05 or status not in ("unknown", "", "none") or ev:
            any_evidence = True
            break
    eps = sheet.get("error_patterns") or {}
    if isinstance(eps, dict):
        for k, v in eps.items():
            if k in ("active", "history", "resolved"):
                continue
            if isinstance(v, dict) and int(v.get("count") or 0) > 0:
                any_evidence = True
                break
    # Named but no skills still ≈ blank for placement
    if any_evidence:
        return False
    return True


def open_phase(sheet: dict | None) -> str:
    """Which open script to use: diagnostic | known."""
    return "diagnostic" if is_blank_learner(sheet) else "known"


def _truthy_part(parts: dict | Any, key: str) -> bool:
    if parts is None:
        return False
    if isinstance(parts, dict):
        val = parts.get(key) or ""
    else:
        # TutorParts
        if key == "try":
            val = getattr(parts, "try_", None) or getattr(parts, "try", None) or ""
        elif key == "continue":
            val = getattr(parts, "continue_", None) or getattr(parts, "continue", None) or ""
        else:
            val = getattr(parts, key, None) or ""
    return bool(str(val).strip())


def has_teach_move(parts: dict | Any) -> bool:
    """True if model, try, or recast is non-empty (mechanical shape helper)."""
    return (
        _truthy_part(parts, "model")
        or _truthy_part(parts, "try")
        or _truthy_part(parts, "recast")
    )
