"""Phase 3 contract tests — typed turn events + note-prefix catalog.

docs/reviews-architecture-refactor.md (adjudicated Phase 3; batch 2 landed):

  - every catalogued kind round-trips (emit → render == the legacy string;
    classify(render(e)) == e's fields);
  - the three re-parse replacements produce results identical to the old
    string-splitting on live golden-scenario turns;
  - **CHAR-BUG-003 RESOLVED (batch 2)**: on the AI executor (the rules
    executor was deleted — E4, 2026-07-28) ``result.notes`` IS the
    seq-ordered projection of the event log — the per-turn contract below
    asserts EXACT list equality, not just multiset;
  - the catalog is COMPLETE: every note emitted on the golden scenarios
    classifies to a catalogued kind.  Adding a new note without a
    NOTE_CATALOG entry fails here;
  - batch-2 push-down: the leaf emitters (character_sheet ×10 families)
    mint typed events natively — ``absorb`` is only the safety net and
    sees ZERO events on golden runs (spy-tested).  (The pedagogy_contract
    leaf emitter and the gate-context DUE_OUTCOME_FAIL sourcing died
    2026-08-03 with the S11 judgment deletion — absence pins below.);
  - the two ui-pinned note families' rendered strings are frozen
    (web_static/app.js parses them by membership).
"""

from __future__ import annotations

import pytest

from test_characterization_ai_path import (
    OPEN_DUE_REPLY,
    OPEN_KNOWN_REPLY,
    TURN_DUE_REPLY,
    TURN_INTRO_REPLY,
    _due_seed,
    _known_seed,
)

from tutor.turn_events import (
    NOTE_CATALOG,
    TurnEvent,
    TurnEventKind,
    TurnEventLog,
    _RENDER,
    classify_note,
    render,
    render_note,
)

EV = TurnEventKind


# ---------------------------------------------------------------------------
# Catalog structure: enum ⇄ catalog ⇄ render table, prefix uniqueness
# ---------------------------------------------------------------------------


def test_catalog_covers_every_kind_and_only_kinds():
    kinds = set(TurnEventKind) - {EV.LEGACY_UNCATALOGUED}
    assert set(NOTE_CATALOG) == kinds
    # the sentinel is deliberately NOT catalogued
    assert EV.LEGACY_UNCATALOGUED not in NOTE_CATALOG


def test_render_table_covers_every_kind():
    assert set(_RENDER) == set(TurnEventKind)


def test_catalog_count_published_number():
    # The measured bus inventory (review said "~40"; the real number was 62
    # at the campaign close; +1 = MORPH_CARD, 2026-07-29 morph-card review;
    # +1 = FRAME_RECORDED, 2026-07-29 encounter-variety round;
    # +1 = RENDER_DROPPED, 2026-07-29 §1.1b settlement round;
    # +2 = OUTPUT_GATE_STRIPPED/HELD, 2026-07-30 still_fail floor;
    # −8 = ACTIVITY/PHASE_CONSUMED/OPEN_SCENES/TASK_SLOT_FILLED/
    #      TASK_COMPLETE/TASK_GOAL_OFFERED/CLOSE_PHASE_OFFERED/FOCUS_ASYNC,
    #      2026-08-03 full-code-audit S9 deletions (scenes, session-phase
    #      clock, task runtime, focus enricher);
    # −3 = MODE/MODE_REASON/HARD_BREAK, 2026-08-03 mode-router teardown
    #      (full-code-audit S4);
    # −1 = OUTPUT_GATE_REPAIRED, 2026-08-03 full-code-audit S2 (the repair
    #      path died 2026-08-01; the kind had no emission site left);
    # −1 = OUTPUT_GATE_SOFT_FAIL, 2026-08-03 S11 (the plumbing-only gate
    #      has no soft class — its emission site died with the
    #      teaching-opinion checks)).
    assert len(NOTE_CATALOG) == 58


def test_output_gate_repaired_kind_stays_deleted():
    # Absence pin (full-code-audit S2): the repair event KIND does not
    # exist — no member, no catalog row, no render row.
    assert not hasattr(TurnEventKind, "OUTPUT_GATE_REPAIRED")
    assert "output_gate_repaired" not in {
        k.value for k in TurnEventKind
    }
    assert classify_note("output_gate_repaired") is None


def test_output_gate_soft_fail_kind_stays_deleted():
    # Absence pin (S11, 2026-08-03): the plumbing-only gate has no soft
    # fault class — no member, no catalog row, no render row.
    assert not hasattr(TurnEventKind, "OUTPUT_GATE_SOFT_FAIL")
    assert "output_gate_soft_fail" not in {
        k.value for k in TurnEventKind
    }
    assert classify_note("output_gate_soft_fail:gate:regloss") is None


def test_stability_classes_are_the_measured_vocabulary():
    classes = {s.stability for s in NOTE_CATALOG.values()}
    assert classes == {"eval-pinned", "ui-pinned", "log-only"}
    eval_pinned = {s.kind for s in NOTE_CATALOG.values()
                   if s.stability == "eval-pinned"}
    assert eval_pinned == {
        EV.UPTAKE_FLAGGED, EV.DUE_ELICIT_OFFERED,
        EV.PROGRESS_MILESTONE, EV.INTRODUCE_PLANNED,
        EV.OUTPUT_GATE_OK, EV.OUTPUT_GATE_FAIL,
        EV.OUTPUT_GATE_STILL_FAIL, EV.OUTPUT_GATE_ERROR,
    }
    ui_pinned = {s.kind for s in NOTE_CATALOG.values()
                 if s.stability == "ui-pinned"}
    assert ui_pinned == {EV.SHEET_TOOL_UPDATE, EV.SHEET_RULES_BACKUP}


def test_no_catalog_match_shadows_another():
    # No prefix is a prefix of a different family's match string in a way
    # classify could mis-route: classification of every spec's own sample
    # must return the spec's kind (longest-prefix-first + exact-first law).
    for spec in NOTE_CATALOG.values():
        sample = spec.match if spec.exact else spec.match + "x"
        got = classify_note(sample)
        assert got is not None, spec.match
        assert got[0] is spec.kind, (
            f"{sample!r} classified as {got[0]} not {spec.kind}"
        )


# ---------------------------------------------------------------------------
# Round-trip: one representative REAL legacy string per kind
# ---------------------------------------------------------------------------

ROUND_TRIP = [
    (EV.DUE_OUTCOME_SUCCESS, "due_outcome_success:pan"),
    (EV.DUE_OUTCOME_FAIL, "due_outcome_fail:agua"),
    (EV.PROGRESS_MILESTONE, "progress_milestone:planted:hola"),
    (EV.PROGRESS_REGRESSION, "progress_regression:regression:pan"),
    (EV.IMAGE_GEN_CAPPED, "image_gen_capped:bote"),
    (EV.IMAGE_GEN_DISABLED, "image_gen_disabled:cafe"),
    (EV.IMAGE_GEN_ASYNC, "image_gen_async:casa"),
    (EV.DUE_ELICIT_OFFERED, "due_elicit_offered:agua,pan"),
    (EV.UPTAKE_FLAGGED, "uptake_flagged:leche"),
    (EV.INTRODUCE_TABLE_MISSING, "introduce_table_missing"),
    (EV.INTRODUCE_PLANNED, "introduce_planned:buenos días:R-D"),
    (EV.INTRODUCE_DOWNGRADED, "introduce_downgraded:hola:R-B_to_R-D"),
    (EV.OUTPUT_GATE_OK, "output_gate_ok"),
    # Historical fault ids inside payloads still classify/replay; the live
    # vocabulary is gate:truncated | gate:sheet_leak (S11).
    (EV.OUTPUT_GATE_FAIL,
     "output_gate_fail:gate:truncated,gate:sheet_leak"),
    (EV.OUTPUT_GATE_STILL_FAIL, "output_gate_still_fail:gate:sheet_leak"),
    (EV.OUTPUT_GATE_ERROR, "output_gate_error:ValueError"),
    (EV.INTERNAL_ERROR, "internal_error:progress_note:KeyError: 'x'"),
    (EV.SESSION_PLAN, "session_plan:updated"),
    (EV.INTRODUCED, "introduced:hola"),
    (EV.INTRODUCE_LAPSED, "introduce_lapsed:buenos días:no_scaffold"),
    (EV.FIRST_SEEN, "first_seen:mucho gusto"),
    (EV.MORPH_CARD, "morph_card:estar"),
    (EV.FRAME_RECORDED, "frame_recorded:estar:wellbeing"),
    (EV.RENDER_DROPPED, "render_dropped:image:cafe"),
    (EV.OUTPUT_GATE_STRIPPED, "output_gate_stripped"),
    (EV.OUTPUT_GATE_RECOVERED, "output_gate_recovered"),
    (EV.OUTPUT_GATE_DEGRADED, "output_gate_degraded:gate:probe_loop"),
    (EV.OUTPUT_GATE_HELD, "output_gate_held:gate:probe_loop"),
    (EV.ASKED_TOPIC, "asked_topic:location:tu"),
    (EV.DUE_ENQUEUED, "due_enqueued:weather_hace"),
    (EV.IMAGE_DECLARED_IRRELEVANT, "image_declared_irrelevant:bote"),
    (EV.IMAGE_DECLARED_SKIP_REPEAT, "image_declared_skip_repeat:casa"),
    (EV.IMAGE_DECLARED_COOLDOWN, "image_declared_cooldown:pan"),
    (EV.IMAGE_DECISION, "image_decision:no_image_worthy_concept"),
    (EV.TEACH_IMAGE, "teach_image:bote"),
    (EV.RECAST, "recast"),
    (EV.STRUCTURED_REPLY, "structured_reply"),
    (EV.SHEET_TOOL_UPDATE, "tool_update"),
    (EV.SHEET_WHY, "why=learner produced estar correctly"),
    (EV.SHEET_HARD_OBSERVER, "hard_observer"),
    (EV.SHEET_AI_UPDATE, "ai_update"),
    (EV.SHEET_RULES_BACKUP, "rules_backup"),
    (EV.SHEET_INLINE_DELTA, "inline_delta"),
    (EV.SHEET_ERROR_PATTERN, "err×3:ser_estar_confusion"),
    (EV.SHEET_CAN_DOS, "can-dos IP-01:0.30→0.55/emerging"),
    (EV.SHEET_NEXT_BEST, "next=IP-03 / greet practice"),
    (EV.SHEET_SCAFFOLD, "scaffold=ES-forward+EN-rescue"),
    (EV.SHEET_SCAFFOLD, "scaffold=mostly_ES"),
    (EV.PEDAGOGY, "pedagogy:ok"),
    (EV.PEDAGOGY, "pedagogy:diagnostic_open"),
    (EV.OPEN_PHASE, "open_phase=diagnostic"),
    (EV.PHASE, "phase=ai_tutor"),
    (EV.PHASE, "phase=chat_stretch"),
    (EV.PLAN_SOURCE, "plan_source=model"),
    (EV.TEACHER_MODE, "teacher_mode=planned"),
    (EV.MEM_SHOWN, "mem_shown=english_only,greet"),
    (EV.MEM_SHOWN, "mem_shown=—"),
    (EV.MEM_ASKED, "mem_asked=ask_how,free_chat:ip-03"),
    (EV.PLAN_GATE_OK, "plan_gate_ok"),
    (EV.PLAN_GATE_FAIL, "plan_gate_fail:missing try_prompt"),
    (EV.PLAN_CARD, "plan:diagnostic/model_try"),
    (EV.PLAN_REASON, "plan_reason=comm_open"),
]


def test_round_trip_every_kind_classify_then_render():
    seen_kinds = set()
    for kind, legacy in ROUND_TRIP:
        hit = classify_note(legacy)
        assert hit is not None, legacy
        got_kind, key, payload = hit
        assert got_kind is kind, (legacy, got_kind)
        rebuilt = render(TurnEvent(kind=got_kind, key=key, payload=payload))
        assert rebuilt == legacy
        seen_kinds.add(kind)
    # every catalogued kind has at least one representative above
    assert seen_kinds == set(NOTE_CATALOG)


def test_emit_renders_the_legacy_string():
    log = TurnEventLog()
    assert log.emit(EV.INTRODUCED, key="hola") == "introduced:hola"
    assert log.emit(
        EV.OUTPUT_GATE_FAIL, payload={"faults": ["gate:english_wall"]}
    ) == "output_gate_fail:gate:english_wall"
    assert log.emit(EV.MEM_SHOWN, payload={"items": []}) == "mem_shown=—"
    assert log.emit(
        EV.PLAN_CARD, payload={"phase": "diagnostic", "move": "model_try"}
    ) == "plan:diagnostic/model_try"
    assert render_note(EV.RECAST) == "recast"


def test_absorb_preserves_bytes_and_classifies():
    log = TurnEventLog()
    for _, legacy in ROUND_TRIP:
        assert log.absorb(legacy) == legacy
    assert not [e for e in log.events
                if e.kind is EV.LEGACY_UNCATALOGUED]
    # An uncatalogued string still passes through byte-safe but is marked.
    weird = "totally_new_note:xyz"
    assert log.absorb(weird) == weird
    assert log.events[-1].kind is EV.LEGACY_UNCATALOGUED


def test_mode_event_kinds_stay_deleted():
    # Absence pin (router teardown 2026-08-03): the mode-selection kinds
    # must not resurface.
    for name in ("MODE", "MODE_REASON", "HARD_BREAK"):
        assert not hasattr(EV, name), name


def test_seq_monotonic_and_stage_tagged():
    log = TurnEventLog()
    log.emit(EV.UPTAKE_FLAGGED, key="uvia", stage="instruct")
    log.absorb("pedagogy:ok", stage="contract")
    log.emit(EV.OUTPUT_GATE_OK, stage="gate")
    seqs = [e.seq for e in log.events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert [e.stage for e in log.events] == ["instruct", "contract", "gate"]


# ---------------------------------------------------------------------------
# Live-session contracts (golden scenarios through the real integrator)
# ---------------------------------------------------------------------------


def _assert_turn_contract(result):
    """The three per-turn laws: monotone seq, complete catalog coverage,
    notes == the rendered projection of the events IN SEQ ORDER (exact list
    equality — CHAR-BUG-003 resolved in Phase 3 batch 2: note order is turn
    chronology)."""
    events = list(result.events or [])
    seqs = [e.seq for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert not [e for e in events if e.kind is EV.LEGACY_UNCATALOGUED], (
        "uncatalogued note reached the bus — add a NOTE_CATALOG entry"
    )
    for n in result.notes or []:
        assert classify_note(n) is not None, (
            f"note {n!r} is not catalogued (E6 completeness law)"
        )
    assert [render(e) for e in events] == [
        str(n) for n in (result.notes or [])
    ], (
        "chronology drift: notes list is not the seq-ordered projection of "
        "the event log (CHAR-BUG-003 contract)"
    )


def _reparse_equivalence(result):
    """The re-parse replacements vs the OLD string-splitting, per turn."""
    events = list(result.events or [])
    notes = [str(n) for n in (result.notes or [])]
    # (1) gate-ctx retrieval_failed_keys (was startswith/split on notes)
    old_failed = {
        n.split(":", 1)[1] for n in notes
        if n.startswith("due_outcome_fail:")
    }
    new_failed = {e.key for e in events if e.kind is EV.DUE_OUTCOME_FAIL}
    assert new_failed == old_failed
    # (2) introduce branch (was startswith("introduced:"))
    old_marked = [n.split(":", 1)[1] for n in notes
                  if n.startswith("introduced:")]
    new_marked = [e.key for e in events if e.kind is EV.INTRODUCED]
    assert new_marked == old_marked
    old_lapsed = [n for n in notes if n.startswith("introduce_lapsed:")]
    new_lapsed = [render(e) for e in events
                  if e.kind is EV.INTRODUCE_LAPSED]
    assert new_lapsed == old_lapsed
    # ((3) guard-6 covered concept died with the mode router, 2026-08-03 —
    # MODE_REASON no longer exists.)


def test_blank_session_dual_emit(tutor_session):
    s = tutor_session.session
    open_res = s.open_session()
    assert open_res.error is None
    _assert_turn_contract(open_res)
    _reparse_equivalence(open_res)
    turn = s.user_turn("Hola")
    assert turn.error is None
    _assert_turn_contract(turn)
    _reparse_equivalence(turn)
    # fresh log per turn: seq restarts, the open's events are not the turn's
    assert turn.events[0].seq == 0
    assert open_res.events is not turn.events


def test_due_session_success_and_fail_paths(tutor_session_factory):
    ctx = tutor_session_factory(
        seed_sheet=_due_seed(),
        replies=[OPEN_DUE_REPLY, TURN_DUE_REPLY, TURN_DUE_REPLY],
    )
    s = ctx.session
    open_res = s.open_session()
    _assert_turn_contract(open_res)
    # success: learner uses due «pan»
    turn1 = s.user_turn("Me gusta el pan")
    _assert_turn_contract(turn1)
    _reparse_equivalence(turn1)
    assert "due_outcome_success:pan" in turn1.notes
    assert [e.key for e in turn1.events
            if e.kind is EV.DUE_OUTCOME_SUCCESS] == ["pan"]
    # fail: due key named inside a meta-comprehension turn (deterministic:
    # meta_comprehension + word_present(agua) → conservative fail record)
    turn2 = s.user_turn("What does agua mean?")
    _assert_turn_contract(turn2)
    _reparse_equivalence(turn2)
    assert "due_outcome_fail:agua" in turn2.notes
    assert {e.key for e in turn2.events
            if e.kind is EV.DUE_OUTCOME_FAIL} == {"agua"}
    # and the gate context read the typed events, not the strings — same set
    assert {e.key for e in turn2.events if e.kind is EV.DUE_OUTCOME_FAIL} \
        == {n.split(":", 1)[1] for n in turn2.notes
            if str(n).startswith("due_outcome_fail:")}


def test_introduce_session_typed_status_matches_strings(
    tutor_session_factory,
):
    ctx = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, TURN_INTRO_REPLY],
    )
    s = ctx.session
    s.open_session()
    turn = s.user_turn("muy bien")
    _assert_turn_contract(turn)
    _reparse_equivalence(turn)
    # the golden introduce arc: planned + marked introduced, typed and
    # legacy (key hola→me llamo 2026-07-29, encounter-variety round —
    # _known_seed is mid-stream, openers sort last)
    assert any(e.kind is EV.INTRODUCE_PLANNED for e in turn.events)
    assert "introduced:me llamo" in turn.notes
    assert [e.key for e in turn.events if e.kind is EV.INTRODUCED] == [
        "me llamo"
    ]


# ---------------------------------------------------------------------------
# Batch 2: leaf push-down, absorb safety net, gate-context event sourcing,
# ui-pinned string freeze
# ---------------------------------------------------------------------------


def test_absorb_sees_zero_events_on_golden_runs(
    tutor_session_factory, monkeypatch,
):
    """Push-down proof: the golden scenarios (blank, due success+fail,
    introduce, uptake) mint every note as a NATIVE typed event —
    TurnEventLog.absorb is never invoked.  absorb stays only as the safety
    net for un-typed strays (see the safety-net test below).  The rules-path
    leg died with the runtime (E4 deletion, 2026-07-28)."""
    from tutor.turn_events import TurnEventLog as _Log

    absorbed: list[str] = []
    real_absorb = _Log.absorb

    def spy(self, note, *, stage=""):
        absorbed.append(str(note))
        return real_absorb(self, note, stage=stage)

    monkeypatch.setattr(_Log, "absorb", spy)

    # blank open + zero-register turn
    ctx = tutor_session_factory()
    s = ctx.session
    assert s.open_session().error is None
    assert s.user_turn("Hola").error is None
    # due elicit: success turn + deterministic meta fail turn
    ctx2 = tutor_session_factory(
        seed_sheet=_due_seed(),
        replies=[OPEN_DUE_REPLY, TURN_DUE_REPLY, TURN_DUE_REPLY],
    )
    s2 = ctx2.session
    assert s2.open_session().error is None
    assert s2.user_turn("Me gusta el pan").error is None
    assert s2.user_turn("What does agua mean?").error is None
    # introduce mark path
    ctx3 = tutor_session_factory(
        seed_sheet=_known_seed(),
        replies=[OPEN_KNOWN_REPLY, TURN_INTRO_REPLY],
    )
    s3 = ctx3.session
    assert s3.open_session().error is None
    t3 = s3.user_turn("Muy bien, gracias.")
    assert "introduced:me llamo" in t3.notes
    # §2.1a uptake flag (the family that WAS absorbed pre-batch-2)
    ctx4 = tutor_session_factory(seed_sheet=_known_seed())
    s4 = ctx4.session
    assert s4.open_session().error is None
    t4 = s4.user_turn("No uvia (rain) hoy, ¿sí?")
    assert any(str(n).startswith("uptake_flagged:") for n in t4.notes)

    assert absorbed == [], (
        f"absorb was hit on golden runs after the push-down: {absorbed!r}"
    )


def test_absorb_safety_net_for_untyped_emitter(
    tutor_session_factory, monkeypatch,
):
    """The safety net stands: an un-typed emitter (fake process_turn
    returning a stray string with no triples) still flows byte-safe through
    absorb and is marked LEGACY_UNCATALOGUED."""
    import tutor.conv_session as cs

    def fake_process_turn(sheet, learner, reply, *, tool_delta=None,
                          event_sink=None, **_kw):
        return sheet, reply, ["totally_new_note:xyz"]

    monkeypatch.setattr(cs, "process_turn", fake_process_turn)
    ctx = tutor_session_factory()
    open_res = ctx.session.open_session()
    assert open_res.error is None
    assert "totally_new_note:xyz" in [str(n) for n in open_res.notes]
    assert any(e.kind is EV.LEGACY_UNCATALOGUED for e in open_res.events)


def test_gate_context_has_no_teaching_fields(tutor_session_factory):
    """S11 pin: the GateContext carries ONLY the plumbing + exposure-scan
    surface — the teaching-check fields (retrieval_failed_keys /
    already_asked / asked_topics / topic_nouns / introduce_key /
    blank_zero / is_open) died with their checks.  The DUE_OUTCOME_FAIL
    events themselves keep flowing (retrieval bookkeeping)."""
    from tutor.output_gate import GateContext

    for gone in ("retrieval_failed_keys", "already_asked", "asked_topics",
                 "topic_nouns", "introduce_key", "blank_zero", "is_open"):
        assert gone not in GateContext.__dataclass_fields__, gone
    ctx = tutor_session_factory(
        seed_sheet=_due_seed(),
        replies=[OPEN_DUE_REPLY, TURN_DUE_REPLY],
    )
    s = ctx.session
    assert s.open_session().error is None
    turn = s.user_turn("What does agua mean?")
    assert turn.error is None
    failed = {e.key for e in turn.events if e.kind is EV.DUE_OUTCOME_FAIL}
    assert failed == {"agua"}


def test_no_note_string_derivation_in_conv_session():
    """Source pin (batch 2, grep-verified): the historical note re-parse
    idioms may not return to conv_session — typed events are the only
    context source.  Comments are stripped so documentation may still
    NAME the old idioms."""
    import io
    import tokenize
    from pathlib import Path

    import tutor.conv_session as cs

    src = Path(cs.__file__).read_text(encoding="utf-8")
    code = "".join(
        t.string
        for t in tokenize.generate_tokens(io.StringIO(src).readline)
        if t.type != tokenize.COMMENT
    )
    for forbidden in (
        'startswith("due_outcome_fail',
        "startswith('due_outcome_fail",
        'startswith("introduced:',
        "startswith('introduced:",
        'startswith("new_noun:',
        "startswith('new_noun:",
        'startswith("uptake_flagged',
        "startswith('uptake_flagged",
    ):
        assert forbidden not in code, (
            f"note-string re-parse idiom {forbidden!r} returned to "
            "conv_session (Phase 3 gate-context law)"
        )


def test_process_turn_event_sink_matches_notes():
    """Leaf push-down contract: process_turn's event_sink triples render
    1:1 (and in order) to the returned note strings."""
    from tutor.character_sheet import default_sheet, process_turn

    sink: list = []
    _s, _vis, notes = process_turn(
        default_sheet(),
        "hola",
        "<tutor><model>**Hola** (hello).</model>"
        "<try>Di **hola**.</try></tutor>",
        event_sink=sink,
    )
    assert len(sink) == len(notes) > 0
    assert [
        render_note(kind, key=key, payload=payload)
        for kind, key, payload in sink
    ] == notes
    assert notes[0] == "rules_backup"  # backup path, render-sourced


def test_pedagogy_contract_judgment_stays_deleted():
    """S11 absence pin: the pedagogy-contract judgment (evaluate_turn /
    PedagogyCheck note_keys leaf emitter) is gone from the runtime — the
    PEDAGOGY kind survives solely as the turn-tail phase note (its
    historical judgment payloads still classify for replay)."""
    import tutor.pedagogy_contract as pc

    for name in ("evaluate_turn", "PedagogyCheck", "check_tutor_parts",
                 "check_visible_fallback"):
        assert not hasattr(pc, name), name
    # Replay classification of historical judgment notes stays intact.
    hit = classify_note("pedagogy:no_teach_move")
    assert hit is not None and hit[0] is EV.PEDAGOGY
    # And the live tail vocabulary renders unchanged.
    assert render_note(EV.PEDAGOGY, key=pc.KEY_DIAGNOSTIC_OPEN) == (
        "pedagogy:diagnostic_open"
    )


def test_ui_pinned_note_strings_frozen():
    # ui-pinned guard (batch 2): web_static/app.js setNotes styles the notes
    # line WARN on rules_backup-without-tool_update MEMBERSHIP —
    #   const warn = notes.includes("rules_backup")
    #                && !notes.includes("tool_update");
    # These two rendered strings may NEVER drift without a matching client
    # change, and ANY web_static/app.js (or styles.css) edit REQUIRES
    # bumping its ?v= in web_static/index.html (asset cache-bust law).
    assert render_note(EV.SHEET_RULES_BACKUP) == "rules_backup"
    assert render_note(EV.SHEET_TOOL_UPDATE) == "tool_update"
    for kind in (EV.SHEET_RULES_BACKUP, EV.SHEET_TOOL_UPDATE):
        assert NOTE_CATALOG[kind].stability == "ui-pinned"


def test_turn_result_json_surface_carries_events():
    # Batch 2: to_dict() exposes the serialized timeline (the declared
    # surface change) — web /api responses and run_conv_smoke turn records
    # carry it; each entry is TurnEvent.as_dict() (kind/key/payload/seq/
    # stage plain dicts, JSON-serializable).
    import json as _json

    from tutor.conv_session import TurnResult

    r = TurnResult(reply="x")
    assert r.to_dict()["events"] == []
    r.events = [TurnEvent(kind=EV.UPTAKE_FLAGGED, key="uvia", seq=0,
                          stage="instruct")]
    d = r.to_dict()
    assert d["events"] == [{
        "kind": "uptake_flagged", "key": "uvia", "payload": {}, "seq": 0,
        "stage": "instruct",
    }]
    _json.dumps(d["events"])  # serializable end-to-end


def test_wrapper_keeps_string_contract():
    # mark_introduced_if_visible still renders the historical strings from
    # the structured introduce_outcome (existing callers/tests untouched).
    from tutor.conv_session import mark_introduced_if_visible

    sheet, note = mark_introduced_if_visible({}, None, "hola")
    assert note is None


@pytest.mark.parametrize("kind", sorted(NOTE_CATALOG, key=lambda k: k.value))
def test_catalog_rows_have_all_e6_columns(kind):
    spec = NOTE_CATALOG[kind]
    assert spec.match, kind
    assert spec.emitters, kind
    assert spec.consumers, kind  # at minimum the shared bus consumers
    assert spec.stability in ("eval-pinned", "ui-pinned", "log-only")
    assert isinstance(spec.golden, bool)
