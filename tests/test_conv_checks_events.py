"""Phase 3 batch 2 — evals/conv_checks.py typed-event migration pins.

Contract (docs/reviews-architecture-refactor.md, batch-2 scope):
  - every migrated checker PREFERS the typed ``turn["events"]`` timeline and
    falls back to note strings when the key is absent — old recorded eval
    results (historical artifacts) must replay unchanged;
  - live parity: on real golden-scenario turns the event path and the
    stripped-events replay path produce IDENTICAL findings;
  - the DECLARED TIGHTENING: the two joined-notes substring scans in
    ``recast_or_gate_attempt`` are precise event-kind checks on the event
    path — an accidental substring inside an unrelated payload no longer
    counts as gate evidence (false positive fixed, module docstring).
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
    _mode,
    due_elicit_fired,
    introduce_scaffolded,
    phase_adherence,
    progress_milestones_fired,
    recast_or_gate_attempt,
    task_goal_offered,
    uptake_flag_honored,
)

MIGRATED_CHECKERS = (
    recast_or_gate_attempt,
    uptake_flag_honored,
    due_elicit_fired,
    progress_milestones_fired,
    introduce_scaffolded,
    task_goal_offered,
    phase_adherence,
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
        "mode": parts.get("mode"),
        "mode_decision": parts.get("mode_decision"),
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
    for t_new, t_old in zip(result["turns"], stripped["turns"]):
        assert _mode(t_new) == _mode(t_old)


def test_live_parity_events_vs_replay(tutor_session_factory):
    """Event path == note-string replay path on real golden-scenario runs
    (due elicit + introduce arcs; the trajectories exercise due_elicit,
    introduce_planned, progress_milestones, phase and mode parsing)."""
    ctx = tutor_session_factory(
        seed_sheet=_due_seed(),
        replies=[OPEN_DUE_REPLY, TURN_DUE_REPLY],
    )
    s = ctx.session
    turns = [_turn_record(s.open_session(), "(session open)")]
    turns.append(_turn_record(s.user_turn("Me gusta el pan")))
    result = {"turns": turns}
    _parity({"expect": {"due_elicit": True}}, result)
    _parity(
        {"expect": {"phase_sequence": [["retrieval"], ["retrieval"]]}},
        result,
    )

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
        {"expect": {"progress_milestones": ["planted:hola"]}}, result2
    )
    # The introduce turn really carried the expectations (not vacuous).
    assert introduce_scaffolded(
        {"expect": {"introduce_planned": True}}, result2
    ) == []
    assert progress_milestones_fired(
        {"expect": {"progress_milestones": ["planted:hola"]}}, result2
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
    assert task_goal_offered(
        {"expect": {"task_instructions_offered": True}}, result
    ) == []
    assert progress_milestones_fired(
        {"expect": {"progress_milestones": ["planted:hola"]}}, result
    ) == []
    assert phase_adherence(
        {"expect": {"phase_sequence": [["new_input"]]}}, result
    ) == []
    assert _mode(result["turns"][0]) == "conversation"


def test_tightening_substring_in_payload_no_longer_counts():
    """DECLARED TIGHTENING: a cf_recast turn with no recast part and NO gate
    events, whose notes merely CONTAIN the substrings inside an unrelated
    payload, HARD-fails on the event path (correct) where the legacy
    substring scan would have soft-WARNed it (false positive)."""
    base_turn = {
        "parts": {"mode": "cf_recast"},
        "notes": [
            "mode=cf_recast",
            # unrelated payloads that CONTAIN the scanned substrings:
            "why=tutor mentioned the output_gate design",
            "image_decision:missing_recast_lookalike",
        ],
    }
    # Old artifact (no events): substring scan → WARN (gate notes only).
    old = {"turns": [dict(base_turn)]}
    out_old = recast_or_gate_attempt({}, old)
    assert len(out_old) == 1 and out_old[0].startswith("WARN")
    # New artifact (typed events, none of them gate kinds): HARD finding.
    new_turn = dict(base_turn)
    new_turn["events"] = [
        {"kind": "mode", "key": "cf_recast", "payload": {}, "seq": 0,
         "stage": "select"},
        {"kind": "why", "key": "tutor mentioned the output_gate design",
         "payload": {}, "seq": 1, "stage": "sheet"},
        {"kind": "image_decision", "key": "missing_recast_lookalike",
         "payload": {}, "seq": 2, "stage": "record"},
    ]
    new = {"turns": [new_turn]}
    out_new = recast_or_gate_attempt({}, new)
    assert len(out_new) == 1 and not out_new[0].startswith("WARN")
    assert "no gate signal" in out_new[0]


def test_event_path_gate_fault_payloads_scanned_precisely():
    """missing_recast INSIDE a gate-fail event payload still counts as a
    gate signal on the event path (fault ids are gate evidence)."""
    turn = {
        "parts": {"mode": "cf_recast"},
        "notes": ["output_gate_fail:gate:missing_recast"],
        "events": [{
            "kind": "output_gate_fail", "key": "",
            "payload": {"faults": ["gate:missing_recast"]},
            "seq": 0, "stage": "gate",
        }],
    }
    out = recast_or_gate_attempt({}, {"turns": [turn]})
    assert len(out) == 1 and out[0].startswith("WARN")
