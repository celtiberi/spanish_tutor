"""SessionPhaseController (Phase 2) — plan arithmetic, phase clock, wiring.

No live API. Laws under test (docs/build-plan-pedagogy-engine.md Phase 2):
- code decides activity_type; guards ignore the hint entirely;
- comprehension_repair / guard turns FREEZE the phase clock;
- interventions (cf_recast etc.) consume budget WITHIN a phase;
- no profile hooks — pack topics + sheet lexicon only.
"""

import unittest

from tutor.character_sheet import default_sheet
from tutor.conv_session import phase_turn_consumed
from tutor.modes import (
    Mode,
    ModeSessionState,
    PHASE_FREEZE_REASONS,
    select_mode,
)
from tutor.session_phases import (
    ACTIVITY_TYPES,
    PhasePlan,
    PhaseSpec,
    PhaseState,
    build_phase_plan,
)

PACK_TOPICS = ["Greetings", "Life on the river", "Food and drink"]


def _known_sheet() -> dict:
    s = default_sheet()
    s["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
    return s


def _budgets(plan: PhasePlan) -> dict[str, int]:
    return {p.activity: p.turn_budget for p in plan.phases}


def _order(plan: PhasePlan) -> list[str]:
    return [p.activity for p in plan.phases]


class TestBuildPhasePlan(unittest.TestCase):
    def test_default_14_turn_arithmetic(self):
        plan = build_phase_plan(_known_sheet(), due_count=1, blank=False)
        self.assertEqual(_order(plan), list(ACTIVITY_TYPES))
        # round(14×{.20,.30,.35,.15}) = 3/4/5/2; close (PEDAGOGY §1.2,
        # USER-ratified 2026-07-28) borrows 1 from free (2 ≥ 2 → 1) so the
        # session stays at the 14-turn estimate.
        self.assertEqual(_budgets(plan), {
            "retrieval": 3, "new_input": 4, "task": 5, "free": 1, "close": 1,
        })
        total = sum(p.turn_budget for p in plan.phases)
        self.assertLessEqual(total, 14 + 1)
        self.assertTrue(all(p.turn_budget >= 1 for p in plan.phases))

    def test_due_zero_parks_retrieval_budget_into_free(self):
        plan = build_phase_plan(_known_sheet(), due_count=0, blank=False)
        self.assertEqual(_order(plan), ["new_input", "task", "free", "close"])
        # AMEND 2a (Grok countersign 2026-07-28): the parked retrieval
        # budget (3) redistributes to free — then close borrows 1 back.
        self.assertEqual(_budgets(plan), {
            "new_input": 4, "task": 5, "free": 4, "close": 1,
        })
        self.assertEqual(sum(p.turn_budget for p in plan.phases), 14)

    def test_due_three_expands_retrieval_shrinks_free(self):
        plan = build_phase_plan(_known_sheet(), due_count=3, blank=False)
        b = _budgets(plan)
        self.assertEqual(b["retrieval"], 4)  # 3 + 1
        # free 2-1=1 < 2 → close is ADDITIVE here (free never zeroed)
        self.assertEqual(b["free"], 1)
        self.assertEqual(b["close"], 1)
        self.assertLessEqual(sum(b.values()), 14 + 1)

    def test_free_never_below_one(self):
        # Small estimate: free would round to 1 already; close must be
        # additive (never bought by zeroing free).
        plan = build_phase_plan(
            _known_sheet(), due_count=3, blank=False,
            session_turns_estimate=6,
        )
        self.assertEqual(_budgets(plan)["free"], 1)

    def test_limited_time_compresses_to_retrieval_and_task(self):
        s = _known_sheet()
        s["affect"] = {"energy": "limited_time"}
        plan = build_phase_plan(s, due_count=2, blank=False)
        self.assertEqual(_order(plan), ["retrieval", "task", "close"])

    def test_limited_time_without_due_uses_new_input(self):
        s = _known_sheet()
        s["affect"] = {"energy": "limited_time"}
        plan = build_phase_plan(s, due_count=0, blank=False)
        self.assertEqual(_order(plan), ["new_input", "task", "close"])

    def test_blank_sheet_is_new_input_heavy_placement_pathway(self):
        plan = build_phase_plan(default_sheet(), due_count=0, blank=True)
        self.assertEqual(_order(plan), ["new_input", "free", "close"])
        b = _budgets(plan)
        self.assertGreater(b["new_input"], b["free"])
        # round(14×0.7)=10, free = 14-10 = 4 → close borrows 1 (free 3)
        self.assertEqual(b, {"new_input": 10, "free": 3, "close": 1})


    def test_close_is_last_in_every_variant(self):
        # PEDAGOGY §1.2 (USER-ratified 2026-07-28): EVERYONE gets a close —
        # blank, limited_time, boredom, due-zero, due-heavy included.
        lt = _known_sheet()
        lt["affect"] = {"energy": "limited_time"}
        bored = _known_sheet()
        bored["affect"] = {"boredom_risk": "high"}
        variants = [
            build_phase_plan(_known_sheet(), due_count=1, blank=False),
            build_phase_plan(_known_sheet(), due_count=0, blank=False),
            build_phase_plan(_known_sheet(), due_count=3, blank=False),
            build_phase_plan(default_sheet(), due_count=0, blank=True),
            build_phase_plan(lt, due_count=2, blank=False),
            build_phase_plan(lt, due_count=0, blank=False),
            build_phase_plan(bored, due_count=1, blank=False),
            build_phase_plan(
                _known_sheet(), due_count=1, blank=False,
                session_turns_estimate=6,
            ),
        ]
        for plan in variants:
            self.assertEqual(plan.phases[-1].activity, "close")
            self.assertEqual(plan.phases[-1].turn_budget, 1)
            # exactly one close per plan
            self.assertEqual(
                sum(1 for p in plan.phases if p.activity == "close"), 1,
            )

    def test_no_pack_topic_refs_without_boredom(self):
        plan = build_phase_plan(
            _known_sheet(), due_count=1, blank=False,
            pack_topics=PACK_TOPICS,
        )
        for p in plan.phases:
            self.assertEqual(p.item_refs, [])

    def test_as_dict_shape(self):
        plan = build_phase_plan(_known_sheet(), due_count=1, blank=False)
        d = plan.as_dict()
        self.assertIn("phases", d)
        self.assertEqual(
            d["phases"][0],
            {"activity": "retrieval", "turn_budget": 3, "item_refs": []},
        )


class TestPhaseState(unittest.TestCase):
    def _state(self) -> PhaseState:
        return PhaseState(PhasePlan([
            PhaseSpec("retrieval", 2),
            PhaseSpec("task", 1),
        ]))

    def test_freeze_does_not_consume_budget(self):
        st = self._state()
        st.tick(consumed=False)
        self.assertEqual(st.turns_in_phase, 0)
        self.assertEqual(st.frozen_turns, 1)
        self.assertEqual(st.current_activity(), "retrieval")

    def test_exhaustion_advances(self):
        st = self._state()
        st.tick(consumed=True)
        self.assertEqual(st.current_activity(), "retrieval")
        st.tick(consumed=True)  # budget 2 consumed → advance
        self.assertEqual(st.index, 1)
        self.assertEqual(st.turns_in_phase, 0)
        self.assertEqual(st.current_activity(), "task")

    def test_plan_exhausted_falls_back_to_free(self):
        st = self._state()
        for _ in range(3):
            st.tick(consumed=True)
        self.assertEqual(st.current_activity(), "free")
        # further ticks stay in free without error
        st.tick(consumed=True)
        self.assertEqual(st.current_activity(), "free")

    def test_force_advance(self):
        st = self._state()
        self.assertTrue(st.force_advance())
        self.assertEqual(st.current_activity(), "task")
        self.assertTrue(st.force_advance())
        self.assertEqual(st.current_activity(), "free")
        self.assertFalse(st.force_advance())  # past plan end: no-op

    def test_snapshot_round_trips(self):
        st = self._state()
        st.tick(consumed=True)
        st.tick(consumed=False)
        snap = st.snapshot()
        self.assertEqual(snap["activity"], "retrieval")
        st2 = PhaseState.from_snapshot(snap)
        self.assertEqual(st2.snapshot(), snap)
        self.assertEqual(st2.index, st.index)
        self.assertEqual(st2.turns_in_phase, 1)
        self.assertEqual(st2.frozen_turns, 1)
        self.assertEqual(
            [p.as_dict() for p in st2.plan.phases],
            [p.as_dict() for p in st.plan.phases],
        )


class TestSelectModeActivityHint(unittest.TestCase):
    def test_retrieval_hint_flavors_default_conversation(self):
        d = select_mode(
            _known_sheet(),
            learner="Hola",
            observations={"blank_sheet": False, "signals": ["greet", "spanish_ok"]},
            mode_state=ModeSessionState(),
            activity_hint="retrieval",
        )
        self.assertEqual(d.mode, Mode.CONVERSATION)
        self.assertEqual(d.reason, "default_conversation")
        self.assertIn("SESSION PHASE: RETRIEVAL", d.instructions)

    def test_retrieval_hint_flavors_known_open(self):
        d = select_mode(
            _known_sheet(),
            is_open=True,
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
            activity_hint="retrieval",
        )
        self.assertEqual(d.reason, "known_open_from_sheet")
        self.assertIn("SESSION PHASE: RETRIEVAL", d.instructions)

    def test_new_input_hint_carries_intro_budget_number(self):
        d = select_mode(
            _known_sheet(),
            learner="Hola",
            observations={"blank_sheet": False, "signals": ["greet", "spanish_ok"]},
            mode_state=ModeSessionState(),
            session_memory={"intro_budget_remaining": 2},
            activity_hint="new_input",
        )
        self.assertIn("SESSION PHASE: NEW INPUT", d.instructions)
        self.assertIn("2 left this session", d.instructions)

    def test_new_input_hint_budget_exhausted(self):
        d = select_mode(
            _known_sheet(),
            learner="Hola",
            observations={"blank_sheet": False, "signals": ["greet", "spanish_ok"]},
            mode_state=ModeSessionState(),
            session_memory={"intro_budget_remaining": 0},
            activity_hint="new_input",
        )
        self.assertIn("EXHAUSTED", d.instructions)

    def test_task_hint_flavors_default_conversation(self):
        d = select_mode(
            _known_sheet(),
            learner="Hola",
            observations={"blank_sheet": False, "signals": ["greet", "spanish_ok"]},
            mode_state=ModeSessionState(),
            activity_hint="task",
        )
        self.assertIn("SESSION PHASE: TASK", d.instructions)

    def test_free_hint_keeps_current_behavior(self):
        d = select_mode(
            _known_sheet(),
            learner="Hola",
            observations={"blank_sheet": False, "signals": ["greet", "spanish_ok"]},
            mode_state=ModeSessionState(),
            activity_hint="free",
        )
        self.assertNotIn("SESSION PHASE:", d.instructions)

    def test_topic_request_guard_ignores_hint(self):
        d = select_mode(
            _known_sheet(),
            learner="Can we talk about food instead?",
            observations={"blank_sheet": False, "signals": ["topic_request"]},
            mode_state=ModeSessionState(),
            activity_hint="retrieval",
        )
        self.assertEqual(d.reason, "learner_topic_request")
        self.assertNotIn("SESSION PHASE:", d.instructions)

    def test_help_request_guard_ignores_hint(self):
        d = select_mode(
            _known_sheet(),
            learner="How do I say boat in Spanish?",
            observations={"blank_sheet": False, "signals": ["help_request"]},
            mode_state=ModeSessionState(),
            activity_hint="task",
        )
        self.assertEqual(d.reason, "learner_help_request")
        self.assertNotIn("SESSION PHASE:", d.instructions)

    def test_comprehension_repair_unaffected_by_hint(self):
        d = select_mode(
            _known_sheet(),
            learner="No entiendo.",
            observations={"blank_sheet": False, "signals": ["meta_comprehension"]},
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿Cómo estás hoy?",
                "last_tutor_model": "Estoy bien.",
                "last_concepts": [],
                "await_comprehension": True,
            },
            activity_hint="retrieval",
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertNotIn("SESSION PHASE:", d.instructions)


class TestPhaseTurnConsumed(unittest.TestCase):
    """conv_session wiring: freeze on repair + guard reasons only."""

    def test_repair_freezes(self):
        self.assertFalse(
            phase_turn_consumed(
                "comprehension_repair", "meta_comprehension_stay_on_topic",
            )
        )

    def test_guard_reasons_freeze(self):
        for reason in (
            "time_pressure_inline_recast",
            "time_pressure_chat",
            "learner_topic_request",
            "learner_help_request",
            "boredom_new_topic",
            "grammar_question_inline",
            "blank_open_placement",
        ):
            self.assertIn(reason, PHASE_FREEZE_REASONS)
            self.assertFalse(
                phase_turn_consumed("conversation", reason), reason,
            )

    def test_interventions_consume_within_phase(self):
        # r6 rule 5: cf_recast / form_focus / association / transfer are
        # interventions WITHIN a phase — they consume budget, never freeze.
        for mode, reason in (
            ("cf_recast", "single_error:weather_hace"),
            ("form_focus", "error_streak:estar_yo_estoy_vs_esta"),
            ("association", "english_stuck_association"),
            ("association", "new_noun:bote"),
            ("transfer", "success_transfer"),
            ("conversation", "default_conversation"),
            ("conversation", "known_open_from_sheet"),
            ("conversation", "scene_goal:sc-01"),
        ):
            self.assertTrue(phase_turn_consumed(mode, reason), (mode, reason))


class TestSessionWiring(unittest.TestCase):
    """Smallest conv_session wiring surface without a live client."""

    def test_build_session_phase_state_known_sheet(self):
        from tutor import config
        from tutor.conv_session import build_session_phase_state
        from tutor.retrieval_scheduler import enqueue

        s = _known_sheet()
        # firmly past-due item → retrieval phase present
        import datetime

        s = enqueue(
            s, "hasta luego", "lexicon",
            today=datetime.date.today() - datetime.timedelta(days=5),
        )
        st = build_session_phase_state(s, config.DEFAULT_PACK_DIR)
        self.assertEqual(st.current_activity(), "retrieval")
        self.assertEqual(st.index, 0)

    def test_build_session_phase_state_blank_sheet(self):
        from tutor import config
        from tutor.conv_session import build_session_phase_state

        st = build_session_phase_state(default_sheet(), config.DEFAULT_PACK_DIR)
        self.assertEqual(
            [p.activity for p in st.plan.phases],
            ["new_input", "free", "close"],
        )


class TestClosePhase(unittest.TestCase):
    """PEDAGOGY §1.2 Close phase (USER-ratified 2026-07-28) — prefix +
    session-summary data block."""

    def test_close_prefix_flavors_default_conversation(self):
        d = select_mode(
            _known_sheet(),
            learner="Hola",
            observations={
                "blank_sheet": False, "signals": ["greet", "spanish_ok"],
            },
            mode_state=ModeSessionState(),
            activity_hint="close",
        )
        self.assertEqual(d.mode, Mode.CONVERSATION)
        self.assertIn("SESSION PHASE: CLOSE", d.instructions)
        self.assertIn("ONE short English line", d.instructions)
        self.assertIn("farewell exchange", d.instructions)
        self.assertIn("no new items", d.instructions)

    def test_close_prefix_flavors_known_open(self):
        d = select_mode(
            _known_sheet(),
            is_open=True,
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
            activity_hint="close",
        )
        self.assertIn("SESSION PHASE: CLOSE", d.instructions)

    def test_guard_ignores_close_hint(self):
        d = select_mode(
            _known_sheet(),
            learner="Can we talk about food instead?",
            observations={"blank_sheet": False, "signals": ["topic_request"]},
            mode_state=ModeSessionState(),
            activity_hint="close",
        )
        self.assertEqual(d.reason, "learner_topic_request")
        self.assertNotIn("SESSION PHASE:", d.instructions)

    def test_close_summary_block_from_session_state(self):
        from tutor.conv_session import close_summary_block
        from tutor.session_memory import SessionMemory

        mem = SessionMemory()
        mem.note_introduced("hasta luego")
        mem.shown.add("estoy")
        block = close_summary_block(
            mem.snapshot(),
            resolved_forms=["me_llamo_es"],
        )
        self.assertIn("SESSION SUMMARY", block)
        self.assertIn("hasta luego", block)
        self.assertIn("me_llamo_es", block)
        self.assertIn("estoy", block)
        # Compact: ≤ 2 lines
        self.assertLessEqual(len(block.splitlines()), 2)

    def test_close_summary_block_empty_session(self):
        from tutor.conv_session import close_summary_block
        from tutor.session_memory import SessionMemory

        block = close_summary_block(SessionMemory().snapshot())
        self.assertIn("SESSION SUMMARY", block)
        self.assertIn("first short Spanish exchange", block)


if __name__ == "__main__":
    unittest.main()
