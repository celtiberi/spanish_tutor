"""Two-phase plan/round context (USER architecture 2026-08-03).

The pedagogy is handed to the teacher; the teacher writes its OWN session
plan on a full-context PLAN turn; later ROUND turns run on a small context
(the plan + sheet + facts + a recent history window) until the model asks
for a re-plan with <replan/>.

Unit half: tutor.session_plan.extract_plan (tag harvest + learner-visible
strip).  Integration half: the real pipeline against FakeModelClient with
config.TEACHER_CONTEXT="plan" (conftest clamps the suite to "full"; these
tests opt in per-case).
"""

from __future__ import annotations

import pytest

from tutor import config
from tutor.session_plan import (
    PLAN_INSTRUCTIONS,
    ROUND_HISTORY_MESSAGES,
    ROUND_NOTE,
    extract_plan,
    load_pedagogy,
)

PLAN_TEXT = "Learner: A1.\nGoal: greetings.\nDue: hola.\nAvoid: quizzing."

BODY_WITH_PLAN = (
    f"<plan>\n{PLAN_TEXT}\n</plan>\n"
    "<tutor>\n"
    "  <acknowledge>¡Hola!</acknowledge>\n"
    "  <model>**Buenos días** (good morning).</model>\n"
    "  <try>Di: **Buenos días**.</try>\n"
    "</tutor>"
)

BODY_PLAIN = (
    "<tutor>\n"
    "  <acknowledge>¡Bien!</acknowledge>\n"
    "  <model>**Estoy bien** (I'm fine).</model>\n"
    "  <try>Di: **Estoy bien**.</try>\n"
    "</tutor>"
)

BODY_WITH_REPLAN = BODY_PLAIN + "\n<replan/>"


# ---------------------------------------------------------------------------
# extract_plan unit contract
# ---------------------------------------------------------------------------


class TestExtractPlan:
    def test_harvests_plan_and_strips_it(self):
        plan, replan, cleaned = extract_plan(BODY_WITH_PLAN)
        assert plan == PLAN_TEXT
        assert replan is False
        assert "<plan>" not in cleaned and PLAN_TEXT not in cleaned
        assert "<tutor>" in cleaned  # reply body untouched

    def test_replan_tag_harvested_and_stripped(self):
        plan, replan, cleaned = extract_plan(BODY_WITH_REPLAN)
        assert plan is None
        assert replan is True
        assert "<replan" not in cleaned
        assert "<tutor>" in cleaned

    def test_noop_without_tags(self):
        plan, replan, cleaned = extract_plan(BODY_PLAIN)
        assert (plan, replan) == (None, False)
        assert cleaned == BODY_PLAIN

    def test_empty_plan_block_is_none(self):
        plan, _, cleaned = extract_plan("<plan>   </plan>" + BODY_PLAIN)
        assert plan is None
        assert "<plan>" not in cleaned

    def test_none_and_empty_input_safe(self):
        assert extract_plan("") == (None, False, "")
        assert extract_plan(None) == (None, False, "")


def test_pedagogy_loads_teaching_content():
    text = load_pedagogy()
    assert text, "PEDAGOGY.md missing or unreadable"
    # The sent copy is the RULES file: every §2 rule present.
    for rule in ("2.1 Learner uptake", "2.2 Nothing new arrives naked",
                 "2.3 English is scaffold", "2.4 Memory is retrieval",
                 "2.5 Correction is timely", "2.6 The level's scope",
                 "2.7 Affect is a signal"):
        assert rule in text, f"rule missing from teacher copy: {rule}"


def test_pedagogy_internal_blocks_cut():
    # USER 2026-08-03: bookkeeping stays in the FILE (marked), never in
    # what the AI teacher receives.
    from tutor.session_plan import PEDAGOGY_PATH

    raw = PEDAGOGY_PATH.read_text(encoding="utf-8")
    assert "INTERNAL:BEGIN" in raw and "INTERNAL:END" in raw, (
        "PEDAGOGY.md lost its internal-block markers"
    )
    sent = load_pedagogy()
    assert "INTERNAL" not in sent and "<!--" not in sent
    assert "How this file got confused" not in sent
    # Theory & evidence (§0) is OUR notes file, never sent.
    assert "Roediger" not in sent and "§0" not in sent
    # Bookkeeping vocabulary stays out of the teacher copy.
    for word in ("HARD LAW", "BINDING", "Incident:", "Reviewer test",
                 "countersign", "ENGINEERING.md"):
        assert word not in sent, f"bookkeeping leaked: {word}"


# ---------------------------------------------------------------------------
# Pipeline integration (plan-mode opt-in per test)
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_mode(monkeypatch):
    monkeypatch.setattr(config, "TEACHER_CONTEXT", "plan")


def _blob(req) -> str:
    return "\n".join(
        str(b.get("text") or "") if isinstance(b, dict) else str(b)
        for b in (req["system"] or [])
    )


class TestPlanTurn:
    def test_open_is_plan_turn_with_pedagogy(
        self, plan_mode, tutor_session_factory
    ):
        ctx = tutor_session_factory(replies=[BODY_WITH_PLAN])
        ctx.session.open_session()
        blob = _blob(ctx.fake.requests[-1])
        assert "## Your session plan (required on this turn)" in blob
        assert "# The teaching guide (yours)" in blob
        # Guard teardown asserts plan-turn completeness.

    def test_plan_stored_and_never_learner_visible(
        self, plan_mode, tutor_session_factory
    ):
        ctx = tutor_session_factory(replies=[BODY_WITH_PLAN])
        res = ctx.session.open_session()
        assert ctx.session.session_plan == PLAN_TEXT
        assert "<plan>" not in (res.reply or "")
        assert PLAN_TEXT.splitlines()[0] not in (res.reply or "")


class TestRoundTurn:
    def test_round_runs_small_with_own_plan(
        self, plan_mode, tutor_session_factory
    ):
        ctx = tutor_session_factory(
            replies=[BODY_WITH_PLAN, BODY_PLAIN, BODY_PLAIN]
        )
        s = ctx.session
        s.open_session()
        s.user_turn("Hola")
        s.user_turn("Buenos días")
        req = ctx.fake.requests[-1]
        blob = _blob(req)
        assert "## Working from your plan" in blob
        assert PLAN_INSTRUCTIONS not in blob
        assert "# The teaching guide (yours)" not in blob
        payload = ctx.fake.task_payload(-1)
        assert payload["your_session_plan"] == PLAN_TEXT
        # Guard teardown asserts: tail-aligned ROUND_HISTORY_MESSAGES
        # window, full sheet still present.

    def test_round_revised_plan_updates_without_replan(
        self, plan_mode, tutor_session_factory
    ):
        revised = "New goal: food vocabulary."
        body = f"<plan>\n{revised}\n</plan>\n" + BODY_PLAIN
        ctx = tutor_session_factory(
            replies=[BODY_WITH_PLAN, body, BODY_PLAIN]
        )
        s = ctx.session
        s.open_session()
        turn = s.user_turn("Hola")
        assert s.session_plan == revised
        assert s.replan_requested is False
        assert revised not in (turn.reply or "")
        s.user_turn("sí")
        assert ctx.fake.task_payload(-1)["your_session_plan"] == revised


class TestReplan:
    def test_replan_tag_triggers_full_context_next_turn(
        self, plan_mode, tutor_session_factory
    ):
        ctx = tutor_session_factory(
            replies=[BODY_WITH_PLAN, BODY_WITH_REPLAN, BODY_WITH_PLAN]
        )
        s = ctx.session
        s.open_session()
        turn = s.user_turn("Hola")
        assert s.replan_requested is True
        assert "<replan" not in (turn.reply or "")
        s.user_turn("¿Qué es esto?")
        blob = _blob(ctx.fake.requests[-1])
        assert "## Your session plan (required on this turn)" in blob
        assert "# The teaching guide (yours)" in blob
        assert s.replan_requested is False  # consumed by the plan turn

    def test_new_chat_resets_plan_state(
        self, plan_mode, tutor_session_factory
    ):
        ctx = tutor_session_factory(replies=[BODY_WITH_PLAN, BODY_PLAIN])
        s = ctx.session
        s.open_session()
        s.user_turn("Hola")
        assert s.session_plan == PLAN_TEXT
        ctx.fake.queue_reply(BODY_WITH_PLAN)
        s.open_session()  # every open IS the unified new-chat reset
        # Fresh chat: plan cleared, so the open was a PLAN turn again.
        blob = _blob(ctx.fake.requests[-1])
        assert "## Your session plan (required on this turn)" in blob


class TestFullPathUntouched:
    def test_full_mode_has_no_plan_machinery(self, tutor_session_factory):
        # conftest clamps TEACHER_CONTEXT=full for the legacy goldens —
        # assert the plan branch really is dormant there.
        ctx = tutor_session_factory(replies=[BODY_PLAIN, BODY_PLAIN])
        s = ctx.session
        s.open_session()
        s.user_turn("Hola")
        for req in ctx.fake.requests:
            blob = _blob(req)
            assert "## Your session plan" not in blob
            assert ROUND_NOTE not in blob
        assert '"your_session_plan"' not in ctx.fake.task_text(-1)


class TestPlanEdgeCases:
    def test_empty_plan_block_never_leaks_tags(
        self, plan_mode, tutor_session_factory
    ):
        # Audit D finding 1: <plan></plan> with no content must still be
        # stripped from the learner-visible reply.
        body = "<plan>   </plan>\n" + BODY_PLAIN
        ctx = tutor_session_factory(replies=[body])
        res = ctx.session.open_session()
        assert "<plan>" not in (res.reply or "")
        assert ctx.session.session_plan is None

    def test_planless_plan_turn_emits_missing(
        self, plan_mode, tutor_session_factory
    ):
        # Audit D finding 2: a plan turn that returns no <plan> is VISIBLE
        # (session_plan:missing) instead of silently re-running full
        # context with no trace.
        ctx = tutor_session_factory(replies=[BODY_PLAIN])
        res = ctx.session.open_session()
        assert any("session_plan:missing" in str(n) for n in res.notes)
        # And the next turn is another plan turn (plan still None).
        assert ctx.session.session_plan is None

    def test_failed_call_preserves_replan_request(
        self, plan_mode, tutor_session_factory, monkeypatch
    ):
        # Audit D finding 3: a provider error on the plan turn must not
        # swallow the model's earlier <replan/> request.
        ctx = tutor_session_factory(
            replies=[BODY_WITH_PLAN, BODY_WITH_REPLAN]
        )
        s = ctx.session
        s.open_session()
        s.user_turn("Hola")
        assert s.replan_requested is True

        def _boom(*a, **k):
            raise RuntimeError("provider down")

        monkeypatch.setattr(ctx.fake.messages, "create", _boom)
        turn = s.user_turn("¿Qué?")
        assert turn.error
        assert s.replan_requested is True  # NOT swallowed by the failure
