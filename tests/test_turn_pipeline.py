"""Phase 4 batch 1 — TurnContext + the pre-model stage family.

Direct unit tests for tutor/turn_pipeline.py: each stage runs ALONE against
a real isolated session (conftest ``tutor_session_factory``) and its state
effects are asserted against facts the goldens pin (due «pan» success =
ladder 0→1 / due tomorrow with status and confidence untouched).  Plus the
pipeline-order contract: the head sequence must match the documented stage
list.  (Scenes, the session-phase clock and the task runtime were DELETED
2026-08-03 — full-code-audit S9; the MODE ROUTER and its stages/
contributors were DELETED 2026-08-03 — full-code-audit S4; all asserted
GONE below.)

The full-turn integration net stays with the Phase 0 characterization
goldens (byte-unchanged this batch).
"""

from __future__ import annotations

import datetime
from types import SimpleNamespace

from tutor import turn_pipeline as tp
from tutor.character_sheet import default_sheet
from tutor.turn_events import TurnEventKind as EV, begin_turn_log

# ---------------------------------------------------------------------------
# Helpers (seeds mirror tests/test_characterization_ai_path.py)
# ---------------------------------------------------------------------------


def _known_seed() -> dict:
    s = default_sheet()
    s["skills"]["IP-01"].update(
        {"confidence": 0.6, "status": "known", "evidence": ["said hola"]}
    )
    return s


def _due_seed() -> dict:
    s = _known_seed()
    intro = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
    yday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    for key in ("pan", "agua"):
        s["lexicon"][key] = {
            "status": "fragile",
            "confidence": 0.3,
            "introduced_at": intro,
            "scaffold": "gloss",
            "next_due": yday,
            "interval_days": 1,
            "successive_successes": 0,
        }
    return s


def _ctx(session, *, learner: str = "", is_open: bool = False,
         **kw) -> tp.TurnContext:
    return tp.TurnContext(
        learner=learner, is_open=is_open, ev=begin_turn_log(session), **kw
    )


def _run_head(session, ctx, *, upto: str | None = None) -> None:
    """Run the head sequence in order, optionally stopping AFTER ``upto``."""
    for stage in tp.PRE_MODEL_STAGES:
        stage(session, ctx)
        if upto is not None and stage.__name__ == upto:
            return


# ---------------------------------------------------------------------------
# Pipeline-order contract
# ---------------------------------------------------------------------------

# Router teardown 2026-08-03 (full-code-audit S4): stage_english_streak /
# stage_select_mode / stage_guard6_covered died with the mode router;
# stage_uptake_flag (the §2.1a observation) + stage_introduce_plan (the
# shadow introduce planner, ex-contributor) joined the head.
DOCUMENTED_HEAD = [
    "stage_classify_signals",
    "stage_memory_intake",
    "stage_uptake_flag",
    "stage_observe",
    "stage_due_outcomes",
    "stage_introduce_plan",
]

# §1.1b settlement round (2026-07-29): stage_image_costs DELETED — display
# bookkeeping fires at settle_chrome for CONFIRMED images only.
# stage_mode_image + stage_mode_snapshot DELETED with the router
# (2026-08-03); stage_intro_image is the surviving code-side attach wire.
DOCUMENTED_REALIZE = [
    "stage_signal_shadow",
    "stage_intro_image",
    "stage_fallback_image",
    "stage_introduce_render",
    "stage_prompt_build",
    "stage_model_call",
]

# Batch 4 census (docs/reviews-architecture-refactor.md, batch-1 re-derived
# inventory: RECORDERS = 9) at the EXACT historical inline order, plus the
# atomic commit point as the family's FINAL member (CHAR-BUG-001 RESOLVED —
# the batch's declared delta per Grok amendment (a)).  Post-campaign:
# stage_frame_record (encounter-variety round); §1.1b settlement round
# 2026-07-29 — stage_intro_morph DELETED, stage_settle_chrome ADDED (the
# card view is a projection settled AFTER the recorder events it consumes
# and after declared images join the confirmed set).
DOCUMENTED_RECORDERS = [
    "stage_finish",
    "stage_introduce_ledger",
    "stage_first_seen",
    "stage_memory_notes",
    "stage_frame_record",
    "stage_declared_image",
    "stage_resolve_enqueue",
    "stage_soft_plan",
    "stage_tail_events",
    "stage_settle_chrome",
    "stage_parts_notes",
    "stage_sheet_commit",
]

# Batch 5 census (the final family — the stage inventory closes here):
# debug ring capture, then the single session-log write.
DOCUMENTED_CAPTURE_LOG = [
    "stage_debug_capture",
    "stage_log_turn",
]


class TestPipelineOrder:
    def test_head_sequence_matches_documented_list(self):
        assert [f.__name__ for f in tp.PRE_MODEL_STAGES] == DOCUMENTED_HEAD
        assert all(callable(f) for f in tp.PRE_MODEL_STAGES)

    def test_phase_and_scene_stages_are_gone(self):
        # Full-code-audit S9 deletion (2026-08-03): the session-phase clock,
        # scenes and the task runtime are DELETED — their stages must stay
        # gone from the module surface.
        for name in ("stage_phase_tick", "stage_bind_activity",
                     "stage_open_scenes", "_task_build", "_task_eligible",
                     "_close_summary_build", "_close_summary_eligible",
                     "_due_elicit_build", "_due_elicit_eligible"):
            assert not hasattr(tp, name), name

    def test_mode_router_stages_are_gone(self):
        # Full-code-audit S4 (2026-08-03): the mode router died — its
        # stages, the contributor family and the instruction plumbing must
        # stay gone from the module surface.
        for name in ("stage_select_mode", "stage_guard6_covered",
                     "stage_english_streak", "stage_mode_image",
                     "stage_mode_snapshot", "stage_mode_record",
                     "stage_contributors", "CONTRIBUTORS",
                     "InstructionContributor", "flavorable",
                     "append_instruction"):
            assert not hasattr(tp, name), name

    def test_realize_sequence_matches_documented_list(self):
        # Post-teardown census: prompt build precedes the model call; the
        # introduce settle (R-B→R-D) follows the image stages.
        assert [f.__name__ for f in tp.REALIZE_STAGES] == DOCUMENTED_REALIZE
        assert all(callable(f) for f in tp.REALIZE_STAGES)

    def test_gate_audit_sequence_matches_documented_list(self):
        # Batch 3 census: GATE AUDIT = 4 (renamed from GATE_REPAIR_STAGES
        # 2026-08-03 — no repair exists); §1.1b settlement round added
        # stage_settle_pixels FIRST (outside the executor's try, like the
        # context build) so image_present is settled truth before gating.
        assert [f.__name__ for f in tp.GATE_AUDIT_STAGES] == [
            "stage_settle_pixels",
            "stage_gate_context",
            "stage_gate_check",
            "stage_gate_verdict",
        ]
        # The repair-era names stay deleted (full-code-audit S2).
        assert not hasattr(tp, "GATE_REPAIR_STAGES")
        assert not hasattr(tp, "stage_gate_repair")
        # The realize/gate families never leak into the head sequence.
        for f in tp.REALIZE_STAGES + tp.GATE_AUDIT_STAGES:
            assert f not in tp.PRE_MODEL_STAGES

    def test_recorder_sequence_matches_documented_list(self):
        # Batch 4 census: RECORDERS = 9 post-gate recorder stages at the
        # exact historical inline order, then stage_sheet_commit — THE
        # atomic-turn commit point — as the family's LAST member (the sheet
        # persists only after every recorder wrote its fields).
        assert [f.__name__ for f in tp.RECORDER_STAGES] == DOCUMENTED_RECORDERS
        assert all(callable(f) for f in tp.RECORDER_STAGES)
        assert tp.RECORDER_STAGES[-1] is tp.stage_sheet_commit
        # Recorders never leak into the earlier families.
        for f in tp.RECORDER_STAGES:
            assert f not in tp.PRE_MODEL_STAGES
            assert f not in tp.REALIZE_STAGES
            assert f not in tp.GATE_AUDIT_STAGES

    def test_capture_log_sequence_matches_documented_list(self):
        # Batch 5 census: CAPTURE/LOG = 2 (the batch-1 re-derived
        # inventory's final family) — debug ring capture, then the single
        # session-log write, at the exact historical inline order.
        assert [f.__name__ for f in tp.CAPTURE_LOG_STAGES] == (
            DOCUMENTED_CAPTURE_LOG
        )
        assert all(callable(f) for f in tp.CAPTURE_LOG_STAGES)

    def test_final_stage_inventory_complete_order(self):
        # Phase 4 CLOSED (batch 5): the COMPLETE stage inventory at the
        # executor's exact call order — head 9, the contributor loop, the
        # phase tick at its verified real site (AFTER the contributors),
        # realize 8, gate/repair 3, recorders 9 + the atomic commit,
        # capture/log 2.  _execute_ai_tutor is nothing but this sequence
        # plus the ctx build, the error-result early return and the
        # historical gate try/except.
        full = (
            list(tp.PRE_MODEL_STAGES)
            + list(tp.REALIZE_STAGES)
            + list(tp.GATE_AUDIT_STAGES)
            + list(tp.RECORDER_STAGES)
            + list(tp.CAPTURE_LOG_STAGES)
        )
        assert [f.__name__ for f in full] == (
            DOCUMENTED_HEAD
            + DOCUMENTED_REALIZE
            + [
                "stage_settle_pixels", "stage_gate_context",
                "stage_gate_check", "stage_gate_verdict",
            ]
            + DOCUMENTED_RECORDERS
            + DOCUMENTED_CAPTURE_LOG
        )
        # No stage rides two families.
        assert len(set(full)) == len(full)
        # Census arithmetic: 6 + 6 + 4 + 12 + 2 = 30 stage functions
        # (router teardown 2026-08-03: select_mode/guard6/english_streak/
        # mode_image/mode_snapshot gone; mode_record → resolve_enqueue;
        # the contributor loop replaced by stage_uptake_flag +
        # stage_introduce_plan in the head).
        assert len(full) == 30

    def test_turn_context_lean_field_census(self):
        # Keep-it-lean law: fields exist only for what the extracted stages
        # produce/consume; later batches add theirs with their migrations.
        # Batch 2 added intro_plan; batch 3 added the realize products
        # (teach_images … error_result) and the gate/repair products
        # (gate_ctx, gate_result, need_recast); batch 4 added the recorder
        # products (result, phase_label, phase_note_key, soft_plan);
        # batch 5 added NOTHING — the capture/log stages read fields
        # batches 3/4 already carry (the keep-it-lean law held to the end).
        # §1.1b settlement round (2026-07-29) added render_drops (the
        # settle_pixels → settle_chrome drop trail for TurnRender).
        # (decision + need_recast died with the router, 2026-08-03;
        # realization_artifact died with the B0 brief path —
        # full-code-audit S2, 2026-08-03.)
        assert sorted(tp.TurnContext.__dataclass_fields__) == sorted([
            "learner", "is_open", "ev", "input_mode", "log_learner",
            "llm_signals", "sig_pre", "obs", "blank", "sigs",
            "intro_plan",
            "teach_images", "image_decision", "system", "task", "messages",
            "final", "raw", "model_raw", "plan_turn", "tool_delta",
            "usage", "error_result",
            "render_drops",
            "gate_ctx", "gate_result", "gate_hold", "gate_fail",
            "result", "phase_label", "phase_note_key", "soft_plan",
        ])


# ---------------------------------------------------------------------------
# stage_classify_signals
# ---------------------------------------------------------------------------


class TestClassifySignals:
    def test_off_by_default(self, tutor_session_factory):
        session = tutor_session_factory().session  # blocking=False fixture
        ctx = _ctx(session, learner="hola")
        tp.stage_classify_signals(session, ctx)
        assert ctx.llm_signals is None

    def test_blocking_strips_observational_and_bills(
        self, tutor_session_factory, monkeypatch
    ):
        import tutor.signal_classifier as sc
        from tutor import config

        session = tutor_session_factory().session
        monkeypatch.setattr(config, "SIGNAL_CLASSIFIER_BLOCKING", True)
        monkeypatch.setattr(
            sc, "classify_signals",
            lambda text: (
                {"spanish_ok", "content_offer"},
                {"model": "clf-x",
                 "usage": {"input_tokens": 5, "output_tokens": 2}},
            ),
        )
        billed = []
        monkeypatch.setattr(
            session.state.costs, "add_llm",
            lambda *a, **k: billed.append((a, k)),
        )
        ctx = _ctx(session, learner="hola amigo")
        tp.stage_classify_signals(session, ctx)
        # §2.1a: observational signals never reach routing.
        assert ctx.llm_signals == {"spanish_ok"}
        assert len(billed) == 1
        assert billed[0][0] == ("classifier", "clf-x")

    def test_open_turn_never_classifies(
        self, tutor_session_factory, monkeypatch
    ):
        import tutor.signal_classifier as sc
        from tutor import config

        session = tutor_session_factory().session
        monkeypatch.setattr(config, "SIGNAL_CLASSIFIER_BLOCKING", True)
        called = []
        monkeypatch.setattr(
            sc, "classify_signals", lambda text: called.append(text)
        )
        ctx = _ctx(session, learner="", is_open=True)
        tp.stage_classify_signals(session, ctx)
        assert called == []
        assert ctx.llm_signals is None


# ---------------------------------------------------------------------------
# stage_memory_intake
# ---------------------------------------------------------------------------


class TestMemoryIntake:
    def test_spanish_turn_eagerly_clears_hold(self, tutor_session_factory):
        session = tutor_session_factory().session
        mem = session.pedagogy_memory
        # Armed hold with ttl=1: note_learner ALONE would keep it (ttl→0,
        # still held); the stage's eager clear (Grok round-1 C) drops it.
        mem.await_comprehension = True
        mem.await_comprehension_ttl = 1
        ctx = _ctx(session, learner="hola amigo")
        tp.stage_memory_intake(session, ctx)
        assert "spanish_ok" in ctx.sig_pre
        assert mem.await_comprehension is False
        assert mem.await_comprehension_ttl == 0

    def test_open_turn_skips_intake(self, tutor_session_factory):
        session = tutor_session_factory().session
        turns_before = session.pedagogy_memory.turns
        ctx = _ctx(session, learner="", is_open=True)
        tp.stage_memory_intake(session, ctx)
        assert ctx.sig_pre == set()
        assert session.pedagogy_memory.turns == turns_before


# ---------------------------------------------------------------------------
# stage_observe
# ---------------------------------------------------------------------------


class TestObserve:
    def test_derives_blank_and_sigs(self, tutor_session_factory):
        session = tutor_session_factory().session  # blank sheet
        ctx = _ctx(session, learner="tell me about the weather")
        tp.stage_observe(session, ctx)
        assert ctx.blank is True  # blank-sheet learner
        assert "english_only" in ctx.sigs
        assert ctx.sigs == set(ctx.obs.get("signals") or [])

    def test_error_hits_surface_in_observations(self, tutor_session_factory):
        # (The mode_state recency memory died with the router — the hits
        # themselves stay observation facts.)
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="está calor hoy")
        tp.stage_observe(session, ctx)
        hits = list(ctx.obs.get("error_hit_ids") or [])
        assert "weather_hace" in hits


# ---------------------------------------------------------------------------
# stage_due_outcomes (golden_due_turn facts)
# ---------------------------------------------------------------------------


class TestDueOutcomes:
    def test_success_advances_ladder_honesty_lawful(
        self, tutor_session_factory
    ):
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        ctx = _ctx(session, learner="quiero pan por favor")
        ctx.sigs = set()
        tp.stage_due_outcomes(session, ctx)
        pan = session.sheet["lexicon"]["pan"]
        tomorrow = (
            datetime.date.today() + datetime.timedelta(days=1)
        ).isoformat()
        # golden_due_turn: ladder 0→1, due tomorrow; status/confidence
        # untouched by the scheduler (honesty law).
        assert pan["successive_successes"] == 1
        assert pan["next_due"] == tomorrow
        assert pan["status"] == "fragile"
        assert pan["confidence"] == 0.3
        # agua not used this turn — byte-identical to seed.
        assert session.sheet["lexicon"]["agua"]["successive_successes"] == 0
        events = ctx.ev.find(EV.DUE_OUTCOME_SUCCESS)
        assert [e.key for e in events] == ["pan"]
        assert events[0].stage == "schedule"

    def test_meta_comprehension_records_failure(self, tutor_session_factory):
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        ctx = _ctx(session, learner="what does pan mean?")
        ctx.sigs = {"meta_comprehension"}
        tp.stage_due_outcomes(session, ctx)
        pan = session.sheet["lexicon"]["pan"]
        assert pan["successive_successes"] == 0  # ladder reset, not advanced
        assert [e.key for e in ctx.ev.find(EV.DUE_OUTCOME_FAIL)] == ["pan"]

    def test_open_turn_records_nothing(self, tutor_session_factory):
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        before = {k: dict(v) for k, v in session.sheet["lexicon"].items()}
        ctx = _ctx(session, learner="", is_open=True)
        tp.stage_due_outcomes(session, ctx)
        assert session.sheet["lexicon"] == before
        assert ctx.ev.events == []


# ---------------------------------------------------------------------------
# stage_introduce_plan + prompt-data due offers (ex-contributor family)
# ---------------------------------------------------------------------------


class TestHeadPlanningStages:
    def test_due_offer_fires_from_the_prompt_data_path(
        self, tutor_session_factory
    ):
        # S9 rewire (2026-08-03): DUE_ELICIT_OFFERED fires from
        # stage_prompt_build when due items ride teaching_data as FACTS.
        # stage_frame_record keeps reading this event for the frames_seen
        # writes (tests/test_encounter_variety.py proves that leg).
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        ctx = _ctx(session, learner="", is_open=True)
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        assert ctx.ev.find(EV.DUE_ELICIT_OFFERED) == []
        tp.stage_prompt_build(session, ctx)
        offered = ctx.ev.find(EV.DUE_ELICIT_OFFERED)
        assert len(offered) == 1
        assert offered[0].payload["keys"] == ["agua", "pan"]
        assert offered[0].stage == "instruct"
        # The facts themselves ride the task payload.
        assert '"due_for_review"' in ctx.task
        assert '"agua"' in ctx.task and '"pan"' in ctx.task

    def test_introduce_plan_parks_on_ctx(self, tutor_session_factory):
        # golden facts: no dues → the shadow planner plans one item — the
        # plan parks on ctx.intro_plan; NO instruction text exists anywhere
        # (§1.1: the render died with the router).  Key me llamo since
        # 2026-07-29 (encounter-variety round).
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="", is_open=True)
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        assert ctx.intro_plan is not None
        assert ctx.intro_plan.key == "me llamo"
        planned = ctx.ev.latest(EV.INTRODUCE_PLANNED)
        assert planned is not None and planned.key == "me llamo"

    def test_uptake_flag_is_pure_observation(self, tutor_session_factory):
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="No uvia (rain) hoy")
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        flagged = ctx.ev.find(EV.UPTAKE_FLAGGED)
        assert [e.key for e in flagged] == ["uvia"]


# ---------------------------------------------------------------------------
# stage_sheet_commit — the atomic-turn save (CHAR-BUG-001 RESOLVED, batch 4)
# ---------------------------------------------------------------------------


class TestAtomicSheetCommit:
    """Grok round-1 (a) amendment (BINDING): at most one durable sheet
    persist per successful turn at a single recorder-stage commit point
    (atomic turn).  Partial mid-turn saves are removed deliberately; crash
    recovery semantics are "the turn commits or it doesn't".  The harness
    asserts commit-point FIELD SETS, not byte-identical intermediate
    files — each write family's fields must be present in the ONE
    committed snapshot."""

    @staticmethod
    def _record_commits(monkeypatch, record):
        """Capture (caller, deep-copied sheet) at every conv_session save."""
        import copy
        import sys

        import tutor.conv_session as conv_session_mod
        from tutor.character_sheet import save_sheet as real_save_sheet

        def _spy(path, sheet):
            record.append(
                (sys._getframe(1).f_code.co_name, copy.deepcopy(sheet))
            )
            return real_save_sheet(path, sheet)

        monkeypatch.setattr(conv_session_mod, "save_sheet", _spy)

    def test_exactly_one_commit_with_introduce_field_set(
        self, tutor_session_factory, monkeypatch
    ):
        # The old multi-site turn (_finish save + introduce-marked mid-turn
        # save) collapses to ONE post-gate commit whose snapshot carries
        # BOTH write families: process_turn maintenance (updated_at) AND the
        # introduce ledger's schedule fields — proof the commit point sits
        # AFTER the introduce recorder.
        import json as _json

        from test_characterization_ai_path import (
            OPEN_KNOWN_REPLY,
            TURN_INTRO_REPLY,
        )

        ctx = tutor_session_factory(
            seed_sheet=_known_seed(),
            replies=[OPEN_KNOWN_REPLY, TURN_INTRO_REPLY],
        )
        commits: list = []
        self._record_commits(monkeypatch, commits)

        assert ctx.session.open_session().error is None
        assert [c[0] for c in commits] == ["_commit_sheet"]

        turn = ctx.session.user_turn("Muy bien, gracias.")
        assert turn.error is None
        # (introduce key hola→me llamo 2026-07-29, encounter-variety round)
        assert "introduced:me llamo" in turn.notes
        assert [c[0] for c in commits] == ["_commit_sheet", "_commit_sheet"]

        # Commit-point field set (the binding declaration's assertion
        # surface): the single snapshot has the introduce fields...
        snap = commits[-1][1]
        me_llamo = (snap.get("lexicon") or {})["me llamo"]
        assert me_llamo["introduced_at"] == datetime.date.today().isoformat()
        assert me_llamo["scaffold"] == "gloss"
        assert me_llamo["next_due"]
        # ...and the sheet-maintenance field set from _finish's process_turn
        # (no earlier partial save carried one without the other).
        assert snap.get("updated_at")
        # The committed snapshot IS the durable state: disk == snapshot.
        on_disk = _json.loads(ctx.sheet_path.read_text(encoding="utf-8"))
        assert on_disk == snap

    def test_first_seen_rides_the_same_single_commit(
        self, tutor_session_factory, monkeypatch
    ):
        # Round-2 AMEND 1c writes (gate scaffold_saved → first_seen bits)
        # had their own conditional save site; they now ride the one
        # commit.  Field-set: first_seen present, introduce fields absent
        # (honesty law — a scaffold save is not an introduction).
        from test_characterization_ai_path import (
            OPEN_BLANK_REPLY,
            TURN_BLANK_REPLY,
        )

        ctx = tutor_session_factory(
            seed_sheet=None,
            replies=[OPEN_BLANK_REPLY, TURN_BLANK_REPLY],
        )
        commits: list = []
        self._record_commits(monkeypatch, commits)

        open_res = ctx.session.open_session()
        assert open_res.error is None
        turn = ctx.session.user_turn(
            "Thanks! I don't know any Spanish yet, where do we start?"
        )
        assert turn.error is None
        # Phase 5 batch 2 declared delta: «estoy bien» is an in-pack table
        # key — the longest-match overlap filter keeps the MWU span over
        # bare «bien», so the first_seen bit rides on «estoy bien».  Since
        # the gate retune (2026-08-03) the scan runs on the OPEN turn too
        # (the placement exemption died with the router), so the write
        # lands on whichever turn first showed the key.
        assert any(
            "first_seen:estoy bien" in n
            for n in list(open_res.notes) + list(turn.notes)
        )
        assert [c[0] for c in commits] == ["_commit_sheet", "_commit_sheet"]
        eb = (commits[-1][1].get("lexicon") or {})["estoy bien"]
        assert eb.get("first_seen")
        assert not eb.get("introduced_at")
        assert not eb.get("next_due")

    def test_failed_model_call_commits_nothing(
        self, tutor_session_factory, monkeypatch
    ):
        # Crash semantics: the turn commits or it doesn't.  A provider
        # error returns before the recorder family — the sheet on disk
        # stays the PREVIOUS turn's committed state (no partial writes,
        # although pre-call stages may have mutated the in-memory sheet).
        ctx = tutor_session_factory(seed_sheet=_known_seed())
        commits: list = []
        self._record_commits(monkeypatch, commits)

        assert ctx.session.open_session().error is None
        assert [c[0] for c in commits] == ["_commit_sheet"]

        def _boom(**kwargs):
            raise RuntimeError("provider down")

        monkeypatch.setattr(ctx.fake.messages, "create", _boom)
        turn = ctx.session.user_turn("Hola, estoy bien.")
        assert turn.error  # the error TurnResult, as before
        assert [c[0] for c in commits] == ["_commit_sheet"]  # no new commit


# ---------------------------------------------------------------------------
# Phase 4 batch 5 — CAPTURE/LOG family + cleanup regressions
# ---------------------------------------------------------------------------


class TestCaptureLogStages:
    def test_stage_debug_capture_appends_one_ring_entry(
        self, tutor_session_factory
    ):
        # The stage carries the exact historical _capture_debug_request
        # call: outbound request (system blocks / history / task) +
        # response metadata, in-memory ring only.
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="hola")
        _run_head(session, ctx)
        # Hand-built realize/recorder products (the capture's input set —
        # all TurnContext fields batches 3/4 already carry).
        ctx.system = [{"type": "text", "text": "SYS"}]
        ctx.task = "TASK"
        ctx.messages = [{"role": "user", "content": "TASK"}]
        ctx.usage = {"input_tokens": 3, "output_tokens": 5}
        ctx.final = SimpleNamespace(stop_reason="end_turn")
        ctx.result = SimpleNamespace(notes=["n1"])
        before = len(session.debug_requests)
        tp.stage_debug_capture(session, ctx)
        assert len(session.debug_requests) == before + 1
        entry = session.debug_requests[-1]
        assert entry["task_message"] == "TASK"
        # Router-shadow fields died with the router (2026-08-03).
        assert "mode" not in entry and "reason" not in entry
        assert entry["response"]["notes"] == ["n1"]
        assert entry["response"]["stop_reason"] == "end_turn"
        assert entry["response"]["usage"]["output_tokens"] == 5

    def test_stage_log_turn_without_logger_is_noop(
        self, tutor_session_factory
    ):
        # log=False sessions (every test session) have logger=None — the
        # stage is a guarded no-op inside _log_turn_result, never a crash.
        from tutor.conv_session import TurnResult

        session = tutor_session_factory().session
        assert session.logger is None
        ctx = _ctx(session, is_open=True)
        ctx.result = TurnResult(reply="¡Hola!")
        tp.stage_log_turn(session, ctx)  # must not raise

    def test_stage_log_turn_log_learner_defaulting(
        self, tutor_session_factory
    ):
        # The historical log_learner defaulting, byte-preserved by the
        # extraction: an explicit label wins; an open turn logs
        # "(session open)"; a learner turn logs its own text.
        from tutor.conv_session import TurnResult

        session = tutor_session_factory().session
        calls: list[dict] = []
        session.logger = SimpleNamespace(
            log_simple_turn=lambda **kw: calls.append(kw),
        )
        try:
            ctx = _ctx(session, is_open=True)
            ctx.result = TurnResult(reply="¡Hola!")
            tp.stage_log_turn(session, ctx)
            ctx2 = _ctx(session, learner="hola", is_open=False)
            ctx2.result = TurnResult(reply="¡Muy bien!")
            tp.stage_log_turn(session, ctx2)
            ctx3 = _ctx(session, learner="hola",
                        log_learner="[voice] hola")
            ctx3.result = TurnResult(reply="¡Muy bien!")
            tp.stage_log_turn(session, ctx3)
        finally:
            session.logger = None
        assert [c["learner"] for c in calls] == [
            "(session open)", "hola", "[voice] hola",
        ]


class TestPhase4CleanupRegressions:
    def test_delegate_census_is_the_adjudicated_kept_list(self):
        # Phase 4 batch 5 delegate decision point (docs/reviews-
        # architecture-refactor.md): every _state_delegate has production
        # readers through its historical name.  14 kept (phase_state,
        # task_state and _focus_key died with their stores — S9 deletion;
        # mode_state and last_mode_decision died with the mode router —
        # S4, both 2026-08-03).  This census is the no-new-delegates lint:
        # adding or removing a delegate must update the batch record AND
        # this pin.
        from tutor.conv_session import ConversationalSession

        delegates = sorted(
            name for name, val in vars(ConversationalSession).items()
            if isinstance(val, property)
        )
        assert delegates == sorted([
            "history", "messages_for_ui", "_focus_panel",
            "_focus_meta", "_focus_version", "_focus_lock",
            "_focus_inflight", "_image_warm_lock", "_image_warm_inflight",
            "last_plan", "pedagogy_memory", "debug_requests", "costs",
            "progress_session_id",
        ])

    def test_locals_unpack_shim_is_retired(self):
        # Batch 5 cleanup: the executor is the stage sequence — the
        # batch-1 ctx-to-locals bridge must not creep back into
        # _execute_ai_tutor (stages read ctx directly).
        import inspect

        from tutor.conv_session import ConversationalSession

        src = inspect.getsource(ConversationalSession._execute_ai_tutor)
        for bridge in (
            "activity = ctx.", "decision = ctx.", "system = ctx.",
            "task = ctx.", "messages = ctx.", "final = ctx.",
            "usage = ctx.", "gate_result = ctx.", "result = ctx.",
        ):
            assert bridge not in src, f"locals bridge crept back: {bridge!r}"


# ---------------------------------------------------------------------------
# Image attach survives the router teardown (Grok AMEND: no silent loss)
# ---------------------------------------------------------------------------


class TestImageAttachSurvivors:
    """Router teardown 2026-08-03: the mode-decision attach died; these are
    the surviving attach wires — model-declared, introduce R-B, blank-open
    fallback — pinned so image attach is never silently lost."""

    @staticmethod
    def _seed_cache(concept: str) -> None:
        """Plant a real cache asset in the ISOLATED teach-assets dir."""
        import tutor.teach_assets as ta

        path = ta.CACHE_DIR / f"{concept}.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
        idx = ta._load_index()
        idx.setdefault("entries", {})[concept] = {
            "file": path.name, "form": concept, "caption": "",
        }
        ta._save_index()

    def test_declared_image_attaches_from_cache(self, tutor_session_factory):
        # The model's own <image concept="hola"/> declaration attaches a
        # cache hit post-reply (stage_declared_image).
        from tutor.conv_session import TurnResult

        session = tutor_session_factory(seed_sheet=_known_seed()).session
        self._seed_cache("hola")
        ctx = _ctx(session, learner="hola")
        ctx.result = TurnResult(
            reply="¡Hola! Di: hola.",
            parts={"image_concept": "hola", "structured": True},
        )
        ctx.teach_images = []
        tp.stage_declared_image(session, ctx)
        assert ctx.teach_images, "declared cache-hit must attach"
        assert ctx.teach_images[0]["concept"] == "hola"
        assert ctx.teach_images[0]["decision_reason"] == "tutor_declared"

    def test_intro_image_stage_attaches_rb_plan(self, tutor_session_factory):
        # An R-B introduce plan requests its key's image via the surviving
        # _attach_concept_image wire (cache-only).
        from types import SimpleNamespace

        session = tutor_session_factory(seed_sheet=_known_seed()).session
        self._seed_cache("hola")
        ctx = _ctx(session, learner="hola")
        ctx.intro_plan = SimpleNamespace(
            key="hola", scaffold_type="image", rule_id="R-B",
            scaffold_payload={}, forbid_cluster_with=[],
        )
        tp.stage_intro_image(session, ctx)
        assert ctx.teach_images
        assert ctx.teach_images[0]["concept"] == "hola"
        assert ctx.teach_images[0]["decision_reason"] == "introduce:R-B"

    def test_blank_open_fallback_still_wants_the_open_image(
        self, tutor_session_factory
    ):
        # Blank open: the fallback still decides the greeting scene image
        # (harness has generation disabled → visible miss note, decision
        # recorded). A KNOWN open ships no code-picked image — exactly the
        # pre-teardown coverage.
        session = tutor_session_factory().session  # blank
        ctx = _ctx(session, is_open=True)
        tp.stage_observe(session, ctx)
        tp.stage_fallback_image(session, ctx)
        assert ctx.image_decision is not None
        assert ctx.image_decision.want
        assert ctx.image_decision.concept == "hola"

        known = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx2 = _ctx(known, is_open=True)
        tp.stage_observe(known, ctx2)
        tp.stage_fallback_image(known, ctx2)
        assert ctx2.teach_images == []
        assert ctx2.image_decision is None
