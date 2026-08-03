"""Phase 3 batch 2 — evals/conv_checks.py typed-event migration pins.

Contract (docs/reviews-architecture-refactor.md, batch-2 scope):
  - every migrated checker PREFERS the typed ``turn["events"]`` timeline and
    falls back to note strings when the key is absent — old recorded eval
    results (historical artifacts) must replay unchanged;
  - live parity: on real golden-scenario turns the event path and the
    stripped-events replay path produce IDENTICAL findings.

(The mode-keyed checkers — _mode / mode_sequence / recast_or_gate_attempt /
association_signal / comprehension_repair_targets / transfer_seen_or_warn —
were DELETED 2026-08-03 with the mode router, full-code-audit S4; their
parity pins died with them and an absence pin stands guard below.)
"""

from __future__ import annotations

import copy

from test_characterization_ai_path import (
    OPEN_DUE_REPLY,
    OPEN_KNOWN_REPLY,
    TURN_DUE_REPLY,
    TURN_INTRO_REPLY,
    _due_seed,
    _known_seed,
)

from evals.conv_checks import (
    due_elicit_fired,
    introduce_scaffolded,
    progress_milestones_fired,
    uptake_flag_honored,
)

# (phase_adherence + task_goal_offered DELETED 2026-08-03 with the
# session-phase machinery + task runtime — full-code-audit S9;
# recast_or_gate_attempt + the mode checkers DELETED with the router, S4.)
MIGRATED_CHECKERS = (
    uptake_flag_honored,
    due_elicit_fired,
    progress_milestones_fired,
    introduce_scaffolded,
)


def _turn_record(tr, learner="x") -> dict:
    """A turn record shaped like run_conv_smoke._push output."""
    parts = dict(tr.parts or {})
    return {
        "learner": learner,
        "visible": tr.reply or "",
        "reply": tr.reply or "",
        "error": tr.error,
        "notes": list(tr.notes or []),
        "events": [e.as_dict() for e in (tr.events or [])],
        "parts": parts,
        "output_gate": parts.get("output_gate"),
    }


def _strip_events(result: dict) -> dict:
    """The same result as an OLD artifact (recorded before events existed)."""
    out = copy.deepcopy(result)
    for t in out.get("turns") or []:
        t.pop("events", None)
    return out


def _parity(traj: dict, result: dict) -> None:
    stripped = _strip_events(result)
    for fn in MIGRATED_CHECKERS:
        assert fn(traj, result) == fn(traj, stripped), fn.__name__


def test_live_parity_events_vs_replay(tutor_session_factory):
    """Event path == note-string replay path on real golden-scenario runs
    (due elicit + introduce arcs)."""
    ctx = tutor_session_factory(
        seed_sheet=_due_seed(),
        replies=[OPEN_DUE_REPLY, TURN_DUE_REPLY],
    )
    s = ctx.session
    turns = [_turn_record(s.open_session(), "(session open)")]
    turns.append(_turn_record(s.user_turn("Me gusta el pan")))
    result = {"turns": turns}
    _parity({"expect": {"due_elicit": True}}, result)

    ctx2 = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, TURN_INTRO_REPLY],
    )
    s2 = ctx2.session
    turns2 = [_turn_record(s2.open_session(), "(session open)")]
    turns2.append(_turn_record(s2.user_turn("Muy bien, gracias.")))
    result2 = {"turns": turns2}
    _parity({"expect": {"introduce_planned": True}}, result2)
    _parity(
        {"expect": {"progress_milestones": ["planted:me llamo"]}}, result2
    )
    # The introduce turn really carried the expectations (not vacuous).
    # (planted key hola→me llamo 2026-07-29, encounter-variety round.)
    assert introduce_scaffolded(
        {"expect": {"introduce_planned": True}}, result2
    ) == []
    assert progress_milestones_fired(
        {"expect": {"progress_milestones": ["planted:me llamo"]}}, result2
    ) == []


def test_old_artifacts_without_events_still_replay():
    """A pre-batch-2 result (no events key anywhere) drives the note path."""
    result = {
        "turns": [{
            "notes": [
                "mode=conversation",
                "due_elicit_offered:agua,pan",
                "introduce_planned:hola:R-E",
                "task_goal_offered:boat_likes",
                "progress_milestone:planted:hola",
                "activity=new_input",
            ],
            "parts": {},
        }],
    }
    assert due_elicit_fired({"expect": {"due_elicit": True}}, result) == []
    assert introduce_scaffolded(
        {"expect": {"introduce_planned": True}}, result
    ) == []
    assert progress_milestones_fired(
        {"expect": {"progress_milestones": ["planted:hola"]}}, result
    ) == []


def test_mode_checkers_stay_deleted():
    """Absence pin (router teardown 2026-08-03): the mode-keyed checkers
    must not resurface in conv_checks."""
    import evals.conv_checks as cc

    for name in (
        "_mode", "mode_sequence", "recast_or_gate_attempt",
        "association_signal", "comprehension_repair_targets",
        "transfer_seen_or_warn",
    ):
        assert not hasattr(cc, name), name
    assert "mode_sequence" not in cc.CHECKS
