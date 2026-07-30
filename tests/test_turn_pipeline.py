"""Phase 4 batch 1 — TurnContext + the pre-model stage family.

Direct unit tests for tutor/turn_pipeline.py: each stage runs ALONE against
a real isolated session (conftest ``tutor_session_factory``) and its state
effects are asserted against facts the Phase 0 goldens pin (blank open =
placement; due «pan» success = ladder 0→1 / due tomorrow with status and
confidence untouched; english-only streak semantics incl. the CHAR-BUG-002
site; repair turns freeze the phase clock).  Plus the pipeline-order
contract: the head sequence must match the documented stage list, and
``stage_phase_tick`` must NOT ride the head (its real site is after the
contributor region — docs/reviews-architecture-refactor.md, Phase 4
batch 1).

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

DOCUMENTED_HEAD = [
    "stage_classify_signals",
    "stage_memory_intake",
    "stage_observe",
    "stage_english_streak",
    "stage_due_outcomes",
    "stage_open_scenes",
    "stage_bind_activity",
    "stage_select_mode",
    "stage_guard6_covered",
]

# §1.1b settlement round (2026-07-29): stage_image_costs DELETED — display
# bookkeeping fires at settle_chrome for CONFIRMED images only.
DOCUMENTED_REALIZE = [
    "stage_signal_shadow",
    "stage_mode_image",
    "stage_fallback_image",
    "stage_introduce_render",
    "stage_mode_snapshot",
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
    "stage_mode_record",
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

    def test_phase_tick_is_not_in_the_head(self):
        # Verified placement (Phase 4 batch 1): the phase clock ticks AFTER
        # the contributor region — the executor calls stage_phase_tick at
        # that true site, never as part of the pre-model head.
        assert tp.stage_phase_tick not in tp.PRE_MODEL_STAGES

    def test_realize_sequence_matches_documented_list(self):
        # Batch 3 census (docs/reviews-architecture-refactor.md, batch-1
        # re-derived inventory: REALIZE = 8) at the EXACT historical
        # inline order — last_mode_decision snapshots AFTER the deferred
        # INTRODUCE render, prompt build precedes the model call.
        assert [f.__name__ for f in tp.REALIZE_STAGES] == DOCUMENTED_REALIZE
        assert all(callable(f) for f in tp.REALIZE_STAGES)

    def test_gate_repair_sequence_matches_documented_list(self):
        # Batch 3 census: GATE/REPAIR = 3; §1.1b settlement round added
        # stage_settle_pixels FIRST (outside the executor's try, like the
        # context build) so image_present is settled truth before gating.
        assert [f.__name__ for f in tp.GATE_REPAIR_STAGES] == [
            "stage_settle_pixels",
            "stage_gate_context",
            "stage_gate_check",
            "stage_gate_repair",
        ]
        # The realize/gate families never leak into the head sequence.
        for f in tp.REALIZE_STAGES + tp.GATE_REPAIR_STAGES:
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
            assert f not in tp.GATE_REPAIR_STAGES

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
            + [tp.stage_contributors, tp.stage_phase_tick]
            + list(tp.REALIZE_STAGES)
            + list(tp.GATE_REPAIR_STAGES)
            + list(tp.RECORDER_STAGES)
            + list(tp.CAPTURE_LOG_STAGES)
        )
        assert [f.__name__ for f in full] == (
            DOCUMENTED_HEAD
            + ["stage_contributors", "stage_phase_tick"]
            + DOCUMENTED_REALIZE
            + [
                "stage_settle_pixels", "stage_gate_context",
                "stage_gate_check", "stage_gate_repair",
            ]
            + DOCUMENTED_RECORDERS
            + DOCUMENTED_CAPTURE_LOG
        )
        # No stage rides two families.
        assert len(set(full)) == len(full)
        # Census arithmetic: 9 + 2 + 7 + 4 + 12 + 2 = 36 stage functions
        # (§1.1b settlement round: realize −stage_image_costs, gate
        # +stage_settle_pixels, recorders −intro_morph +settle_chrome)
        # (recorders 11 + the atomic commit; post-campaign additions:
        # stage_intro_morph — 2026-07-29 morph-card review;
        # stage_frame_record — 2026-07-29 encounter-variety round); the 5
        # contributors are InstructionContributor instances under the
        # stage_contributors loop (pinned by
        # test_contributor_census_and_order).
        assert len(full) == 36
        assert len(tp.CONTRIBUTORS) == 5

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
        assert sorted(tp.TurnContext.__dataclass_fields__) == sorted([
            "learner", "is_open", "ev", "input_mode", "log_learner",
            "llm_signals", "sig_pre", "obs", "blank", "sigs",
            "open_scenes", "activity", "decision", "intro_plan",
            "phase_consumed",
            "teach_images", "image_decision", "system", "task", "messages",
            "final", "raw", "tool_delta", "usage", "error_result",
            "render_drops",
            "gate_ctx", "gate_result", "need_recast",
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
    def test_ticks_and_derives_blank_and_sigs(self, tutor_session_factory):
        session = tutor_session_factory().session  # blank sheet
        assert session.mode_state.learner_turn_index == 0
        ctx = _ctx(session, learner="tell me about the weather")
        tp.stage_observe(session, ctx)
        assert session.mode_state.learner_turn_index == 1
        assert ctx.blank is True  # blank-sheet learner (goldens: placement)
        assert "english_only" in ctx.sigs
        assert ctx.sigs == set(ctx.obs.get("signals") or [])

    def test_error_hits_recorded_at_turn_index(self, tutor_session_factory):
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="está calor hoy")
        tp.stage_observe(session, ctx)
        hits = list(ctx.obs.get("error_hit_ids") or [])
        assert "weather_hace" in hits
        for pid in hits:
            assert (
                session.mode_state.last_error_hit_turn[pid]
                == session.mode_state.learner_turn_index
            )


# ---------------------------------------------------------------------------
# stage_english_streak — the streak's SINGLE owner (CHAR-BUG-002 RESOLVED,
# Phase 4 batch 3: modes guard 4 reads the state only)
# ---------------------------------------------------------------------------


class TestEnglishStreak:
    def test_increments_on_english_only(self, tutor_session_factory):
        session = tutor_session_factory().session
        ctx = _ctx(session, learner="please speak english")
        ctx.sigs = {"english_only"}
        tp.stage_english_streak(session, ctx)
        assert session.mode_state.english_only_streak == 1
        tp.stage_english_streak(session, ctx)
        assert session.mode_state.english_only_streak == 2

    def test_resets_on_spanish_turn(self, tutor_session_factory):
        session = tutor_session_factory().session
        session.mode_state.english_only_streak = 3
        ctx = _ctx(session, learner="hola")
        ctx.sigs = {"spanish_ok"}
        tp.stage_english_streak(session, ctx)
        assert session.mode_state.english_only_streak == 0

    def test_open_turn_leaves_streak(self, tutor_session_factory):
        session = tutor_session_factory().session
        session.mode_state.english_only_streak = 2
        ctx = _ctx(session, learner="", is_open=True)
        ctx.sigs = set()
        tp.stage_english_streak(session, ctx)
        assert session.mode_state.english_only_streak == 2

    def test_char_bug_002_first_english_turn_no_hard_break(
        self, tutor_session_factory
    ):
        # CHAR-BUG-002 RESOLVED (known_bugs.json): the FIRST English-only
        # turn carries a genuine streak of 1 — guard 4 must NOT hard-break
        # into association (the old double count fired here).
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(
            session,
            learner="That was a long day at the office and there is a "
                    "lot to do.",
        )
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        assert session.mode_state.english_only_streak == 1
        assert ctx.decision.mode.value != "association"
        assert ctx.decision.reason != "english_stuck_association"
        assert not ctx.decision.hard_break

    def test_char_bug_002_second_english_turn_hard_breaks(
        self, tutor_session_factory
    ):
        # …and the SECOND consecutive English-only turn reaches the >=2
        # threshold honestly: association hard break fires.
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx1 = _ctx(
            session,
            learner="That was a long day at the office and there is a "
                    "lot to do.",
        )
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx1)
        assert not ctx1.decision.hard_break
        ctx2 = _ctx(
            session,
            learner="My day was long and there is so much work to "
                    "finish tonight.",
        )
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx2)
        assert session.mode_state.english_only_streak == 2
        assert ctx2.decision.mode.value == "association"
        assert ctx2.decision.reason == "english_stuck_association"
        assert ctx2.decision.hard_break


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
# stage_open_scenes
# ---------------------------------------------------------------------------


class TestOpenScenes:
    def test_binds_scene_ids_to_mode_state(self, tutor_session_factory):
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="hola")
        tp.stage_open_scenes(session, ctx)
        assert isinstance(ctx.open_scenes, list)
        assert ctx.open_scenes  # known-sheet goldens route through scenes
        assert session.mode_state.open_scene_ids == [
            s.get("id") for s in ctx.open_scenes if s.get("id")
        ]


# ---------------------------------------------------------------------------
# stage_bind_activity
# ---------------------------------------------------------------------------


class TestBindActivity:
    def test_retrieval_stays_while_something_is_due(
        self, tutor_session_factory
    ):
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        assert session.phase_state.current_activity() == "retrieval"
        index_before = session.phase_state.index
        ctx = _ctx(session, learner="hola")
        tp.stage_bind_activity(session, ctx)
        assert ctx.activity == "retrieval"
        assert session.phase_state.index == index_before

    def test_empty_retrieval_force_advances(self, tutor_session_factory):
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        # Grok AMEND 2b: never flavor a retrieval turn with nothing due.
        tomorrow = (
            datetime.date.today() + datetime.timedelta(days=1)
        ).isoformat()
        for key in ("pan", "agua"):
            session.sheet["lexicon"][key]["next_due"] = tomorrow
        index_before = session.phase_state.index
        ctx = _ctx(session, learner="hola")
        tp.stage_bind_activity(session, ctx)
        assert session.phase_state.index == index_before + 1
        assert ctx.activity != "retrieval"
        assert ctx.activity == session.phase_state.current_activity()


# ---------------------------------------------------------------------------
# stage_select_mode + stage_guard6_covered
# ---------------------------------------------------------------------------


class TestSelectMode:
    def test_blank_open_is_placement_with_select_events(
        self, tutor_session_factory
    ):
        session = tutor_session_factory().session  # blank sheet
        ctx = _ctx(session, learner="", is_open=True)
        _run_head(session, ctx, upto="stage_select_mode")
        # golden_blank_open: blank open routes to placement (hard break).
        assert ctx.decision is not None
        assert ctx.decision.mode.value == "placement"
        assert ctx.decision.reason == "blank_open_placement"
        mode_ev = ctx.ev.latest(EV.MODE)
        reason_ev = ctx.ev.latest(EV.MODE_REASON)
        assert mode_ev.key == "placement" and mode_ev.stage == "select"
        assert reason_ev.key == "blank_open_placement"
        assert reason_ev.stage == "select"


class TestGuard6Covered:
    def test_guard6_reason_records_covered_concept(
        self, tutor_session_factory
    ):
        session = tutor_session_factory().session
        ctx = _ctx(session, learner="mi casa es grande")
        # The MODE_REASON emit derives guard6_concept ONCE at the event
        # boundary (Phase 3 batch 1) — the stage reads the typed payload.
        ctx.ev.emit(EV.MODE_REASON, key="new_noun:casa", stage="select")
        tp.stage_guard6_covered(session, ctx)
        assert "casa" in session.pedagogy_memory.covered_concepts

    def test_non_guard6_reason_writes_nothing(self, tutor_session_factory):
        session = tutor_session_factory().session
        ctx = _ctx(session, learner="hola")
        ctx.ev.emit(EV.MODE_REASON, key="default_conversation",
                    stage="select")
        tp.stage_guard6_covered(session, ctx)
        assert session.pedagogy_memory.covered_concepts == set()


# ---------------------------------------------------------------------------
# stage_phase_tick (called at its REAL post-contributor site)
# ---------------------------------------------------------------------------


def _decision(mode: str, reason: str) -> SimpleNamespace:
    return SimpleNamespace(mode=SimpleNamespace(value=mode), reason=reason)


class TestPhaseTick:
    def test_conversation_turn_consumes_budget(self, tutor_session_factory):
        session = tutor_session_factory().session
        ctx = _ctx(session, learner="hola")
        ctx.decision = _decision("conversation", "default_conversation")
        before = (
            session.phase_state.index,
            session.phase_state.turns_in_phase,
            session.phase_state.frozen_turns,
        )
        tp.stage_phase_tick(session, ctx)
        assert ctx.phase_consumed is True
        assert session.phase_state.frozen_turns == before[2]
        assert (
            session.phase_state.index,
            session.phase_state.turns_in_phase,
        ) != (before[0], before[1])

    def test_repair_turn_freezes_clock(self, tutor_session_factory):
        session = tutor_session_factory().session
        ctx = _ctx(session, learner="what does that mean?")
        ctx.decision = _decision(
            "comprehension_repair", "meta_comprehension_stay_on_topic"
        )
        before = (
            session.phase_state.index,
            session.phase_state.turns_in_phase,
            session.phase_state.frozen_turns,
        )
        tp.stage_phase_tick(session, ctx)
        # golden_comprehension_repair: index/turns_in_phase unchanged,
        # frozen_turns +1, phase_consumed False.
        assert ctx.phase_consumed is False
        assert session.phase_state.index == before[0]
        assert session.phase_state.turns_in_phase == before[1]
        assert session.phase_state.frozen_turns == before[2] + 1


# ---------------------------------------------------------------------------
# Phase 4 batch 2 — CONTRIBUTORS family
# ---------------------------------------------------------------------------


class TestContributorOrder:
    def test_contributor_census_and_order(self):
        # The contributor census at the EXACT historical inline call order
        # (docs/reviews-architecture-refactor.md, Phase 4 batch 1 census:
        # CONTRIBUTORS 5, between the head and the phase tick).
        assert [c.name for c in tp.CONTRIBUTORS] == [
            "due_elicit",
            "self_flag_uptake",
            "introduce",
            "task",
            "close_summary",
        ]
        for c in tp.CONTRIBUTORS:
            assert callable(c.eligible) and callable(c.build)

    def test_contributors_run_between_head_and_tick(self):
        # stage_contributors is its own family site: not in the pre-model
        # head, and the phase tick stays a separate post-contributor stage.
        assert tp.stage_contributors not in tp.PRE_MODEL_STAGES
        assert tp.stage_phase_tick not in tp.PRE_MODEL_STAGES

    def test_zero_register_overlay_is_not_a_contributor(self):
        # Verified against the family markers (Phase 4 batch 2): the
        # true-zero overlay lives inside modes.select_mode (select stage)
        # and joins with a single "\n", not the contributor idiom.
        assert "zero_register" not in [c.name for c in tp.CONTRIBUTORS]


# ---------------------------------------------------------------------------
# flavorable() — the ONE eligibility predicate; one test per characterized
# spelling (the differences are explicit parameters, never silent
# unification).
# ---------------------------------------------------------------------------


def _flav_ctx(mode: str, reason: str, activity: str = "") -> tp.TurnContext:
    ctx = tp.TurnContext(learner="hola", is_open=False, ev=None)
    ctx.decision = _decision(mode, reason)
    ctx.activity = activity
    return ctx


class TestFlavorable:
    def test_spelling_a_due_elicit(self):
        # due_elicit_block's internal gate: modes {conversation, transfer},
        # guard reasons EXCLUDED, new_input activity EXCLUDED (Grok AMEND
        # 4a sole-orchestrator: introduce owns new_input).
        from tutor.conv_session import DUE_ELICIT_MODES, DUE_GUARD_REASONS

        kw = dict(
            modes=DUE_ELICIT_MODES,
            exclude_reasons=DUE_GUARD_REASONS,
            exclude_activities=frozenset({"new_input"}),
        )
        assert tp.flavorable(
            _flav_ctx("conversation", "default_conversation", "retrieval"),
            **kw,
        )
        assert tp.flavorable(
            _flav_ctx("transfer", "transfer_turn", "task"), **kw
        )
        for guard in DUE_GUARD_REASONS:
            assert not tp.flavorable(
                _flav_ctx("conversation", guard, "retrieval"), **kw
            )
        # cf_recast is NOT a due-elicit mode (narrower than spelling B).
        assert not tp.flavorable(
            _flav_ctx("cf_recast", "default_conversation", "retrieval"),
            **kw,
        )
        assert not tp.flavorable(
            _flav_ctx("conversation", "default_conversation", "new_input"),
            **kw,
        )

    def test_spelling_b_self_flag_uptake(self):
        # self_flag_uptake_block's internal gate: modes {conversation,
        # transfer, cf_recast}, guard reasons EXCLUDED, NO activity term —
        # uptake may fire in ANY phase, including new_input (historical
        # behavior, deliberately different from spelling A).
        from tutor.conv_session import DUE_GUARD_REASONS, SELF_FLAG_MODES

        kw = dict(modes=SELF_FLAG_MODES, exclude_reasons=DUE_GUARD_REASONS)
        assert tp.flavorable(
            _flav_ctx("cf_recast", "recent_error_pattern"), **kw
        )
        assert tp.flavorable(
            _flav_ctx("conversation", "default_conversation", "new_input"),
            **kw,
        )
        for guard in DUE_GUARD_REASONS:
            assert not tp.flavorable(_flav_ctx("conversation", guard), **kw)
        assert not tp.flavorable(
            _flav_ctx("placement", "blank_open_placement"), **kw
        )

    def test_spelling_c_flavorable_turns(self):
        # THE predicate the map found spelled three times (introduce_block
        # internal / task inline / close inline) — identical on (mode,
        # reason) in all three: conversation + reason-INCLUDING set
        # {known_open_from_sheet, default_conversation}; only the activity
        # term differs per contributor.
        from tutor.conv_session import INTRODUCE_FLAVORABLE_REASONS

        kw = dict(
            modes=frozenset({"conversation"}),
            include_reasons=INTRODUCE_FLAVORABLE_REASONS,
        )
        assert tp.flavorable(
            _flav_ctx("conversation", "known_open_from_sheet", "new_input"),
            activities=frozenset({"new_input"}),
            **kw,
        )
        assert tp.flavorable(
            _flav_ctx("conversation", "default_conversation", "close"),
            activities=frozenset({"close"}),
            **kw,
        )
        # Include-polarity: an unlisted reason fails even though it is not
        # a guard reason (the decisive difference from spellings A/B).
        assert not tp.flavorable(
            _flav_ctx("conversation", "scene_goal:boat_likes", "task"), **kw
        )
        assert not tp.flavorable(
            _flav_ctx("transfer", "default_conversation", "close"), **kw
        )
        # Wrong phase for the contributor's activity term.
        assert not tp.flavorable(
            _flav_ctx("conversation", "default_conversation", "task"),
            activities=frozenset({"close"}),
            **kw,
        )


class TestAppendInstruction:
    def test_matches_the_historical_idiom(self):
        d = _decision("conversation", "default_conversation")
        d.instructions = None
        tp.append_instruction(d, "FIRST BLOCK")
        assert d.instructions == "FIRST BLOCK"
        tp.append_instruction(d, "SECOND BLOCK")
        assert d.instructions == "FIRST BLOCK\n\nSECOND BLOCK"

    def test_empty_text_is_a_no_op(self):
        d = _decision("conversation", "default_conversation")
        d.instructions = "KEEP"
        tp.append_instruction(d, "")
        tp.append_instruction(d, None)
        assert d.instructions == "KEEP"


# ---------------------------------------------------------------------------
# stage_contributors — golden-pinned facts at unit level
# ---------------------------------------------------------------------------


class TestStageContributors:
    def test_due_contributor_appends_block_and_emits(
        self, tutor_session_factory
    ):
        # golden_due_open facts: known open + due queue → DUE block with
        # both items (oldest-due order agua, pan) + DUE_ELICIT_OFFERED.
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        ctx = _ctx(session, learner="", is_open=True)
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        tp.stage_contributors(session, ctx)
        assert "DUE RE-ENCOUNTERS" in (ctx.decision.instructions or "")
        assert "«agua»" in ctx.decision.instructions
        assert "«pan»" in ctx.decision.instructions
        offered = ctx.ev.find(EV.DUE_ELICIT_OFFERED)
        assert len(offered) == 1
        assert offered[0].payload["keys"] == ["agua", "pan"]
        assert offered[0].stage == "instruct"

    def test_introduce_contributor_defers_render(self, tutor_session_factory):
        # golden_introduce_open facts: no dues → new_input open plans one
        # item — the plan parks on ctx.intro_plan and the INSTRUCTIONS DO
        # NOT carry it yet (R-B honesty: the realize region renders after
        # image resolution). Key changed hola→me llamo 2026-07-29
        # (encounter-variety round: _known_seed has IP-01 known, so it is
        # mid-stream — openers sort last; docs/design-encounter-variety.md).
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="", is_open=True)
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        tp.stage_contributors(session, ctx)
        assert ctx.activity == "new_input"
        assert ctx.intro_plan is not None
        assert ctx.intro_plan.key == "me llamo"
        planned = ctx.ev.latest(EV.INTRODUCE_PLANNED)
        assert planned is not None and planned.key == "me llamo"
        # The plan's rendered block (golden pin: "INTRODUCE (one item,
        # rule R-E)") is NOT in the instructions yet — realize renders it.
        assert "INTRODUCE (one item" not in (ctx.decision.instructions or "")

    def test_hard_break_and_repair_turns_get_no_soft_additions(
        self, tutor_session_factory
    ):
        # Guard/hard-break/repair turns keep their single focus under every
        # spelling: dues are waiting, yet no contributor may touch the turn.
        session = tutor_session_factory(seed_sheet=_due_seed()).session
        # CHAR-BUG-002 RESOLVED: a hard break needs a GENUINE >=2 streak —
        # one prior English-only turn, then this one (the stage increments).
        session.mode_state.english_only_streak = 1
        ctx = _ctx(
            session, learner="That was a long day at the office."
        )
        for stage in tp.PRE_MODEL_STAGES:
            stage(session, ctx)
        # The head routes this SECOND consecutive English-only turn to an
        # association hard break — not a contributor mode.
        assert ctx.decision.mode.value == "association"
        before = ctx.decision.instructions
        tp.stage_contributors(session, ctx)
        assert ctx.decision.instructions == before
        assert ctx.ev.find(EV.DUE_ELICIT_OFFERED) == []
        assert ctx.intro_plan is None
        # Same law for a repair-shaped decision (the real repair arc is
        # pinned end-to-end by golden_comprehension_repair).
        ctx.decision = _decision(
            "comprehension_repair", "meta_comprehension_stay_on_topic"
        )
        ctx.decision.instructions = "REPAIR FOCUS"
        tp.stage_contributors(session, ctx)
        assert ctx.decision.instructions == "REPAIR FOCUS"
        assert ctx.ev.find(EV.DUE_ELICIT_OFFERED) == []


# ---------------------------------------------------------------------------
# PHASE HOST rule 7 (Proposal A micro-batch, 2026-07-29) — the scene_goal /
# task-block seam Grok's countersign caught: a topic scene pick during TASK
# activity binds the scene AND carries the task block (never bind-without-
# teach); close stays exact-set only; introduce already suppresses the pick.
# ---------------------------------------------------------------------------


class TestSceneGoalTaskSeam:
    def test_task_block_fires_on_scene_goal_under_task_activity(
        self, tutor_session_factory
    ):
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="Me gusta mucho el pan.")
        tp.stage_open_scenes(session, ctx)
        ctx.activity = "task"
        ctx.decision = _decision("conversation", "scene_goal:boat_likes")
        text = tp._task_build(session, ctx)
        assert text is not None
        assert "TASK (single convergent exit" in text
        offered = ctx.ev.find(EV.TASK_GOAL_OFFERED)
        assert len(offered) == 1
        assert offered[0].key == "boat_likes"
        assert session.task_state is not None
        assert session.task_state.scene_id == "boat_likes"

    def test_scene_goal_clause_requires_task_activity(
        self, tutor_session_factory
    ):
        # The expansion is task-activity-only (binding text rule 7): the
        # same scene_goal decision under another activity gets NO task
        # block from _task_build (and _task_eligible would not run it).
        session = tutor_session_factory(seed_sheet=_known_seed()).session
        ctx = _ctx(session, learner="Me gusta mucho el pan.")
        tp.stage_open_scenes(session, ctx)
        ctx.activity = "free"
        ctx.decision = _decision("conversation", "scene_goal:boat_likes")
        assert not tp._task_eligible(ctx)
        assert tp._task_build(session, ctx) is None
        assert ctx.ev.find(EV.TASK_GOAL_OFFERED) == []

    def test_close_gate_stays_exact_set_only(self):
        # Rule 7 expands the TASK text gate only — close refuses scene_goal
        # even under close activity (and the rule-6 suppression makes a
        # close-activity scene pick unreachable anyway).
        assert not tp._close_summary_eligible(
            _flav_ctx("conversation", "scene_goal:boat_likes", "close")
        )
        assert tp._close_summary_eligible(
            _flav_ctx("conversation", "default_conversation", "close")
        )


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

        assert ctx.session.open_session().error is None
        turn = ctx.session.user_turn(
            "Thanks! I don't know any Spanish yet, where do we start?"
        )
        assert turn.error is None
        # Phase 5 batch 2 declared delta: «estoy bien» is an in-pack table
        # key now — the longest-match overlap filter keeps the MWU span
        # over bare «bien», so the first_seen bit rides on «estoy bien».
        assert "first_seen:estoy bien" in turn.notes
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
        assert entry["mode"] == ctx.decision.mode.value
        assert entry["reason"] == ctx.decision.reason
        assert entry["activity"] == ctx.activity
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
        # readers through its historical name (turn_pipeline itself reads
        # session.pedagogy_memory / session.mode_state / …) — ALL 19 KEPT,
        # ZERO killed.  This census is the no-new-delegates lint: adding
        # or removing a delegate must update the batch record AND this pin.
        from tutor.conv_session import ConversationalSession

        delegates = sorted(
            name for name, val in vars(ConversationalSession).items()
            if isinstance(val, property)
        )
        assert delegates == sorted([
            "history", "messages_for_ui", "_focus_panel", "_focus_key",
            "_focus_meta", "_focus_version", "_focus_lock",
            "_focus_inflight", "_image_warm_lock", "_image_warm_inflight",
            "last_plan", "pedagogy_memory", "mode_state", "phase_state",
            "task_state", "last_mode_decision", "debug_requests", "costs",
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
