"""Unit tests for the limited pedagogical controller (no API calls)."""

import unittest

from tutor.pedagogy_controller import (
    EXAMPLES,
    LEGAL_MOVES,
    check_controller_decision,
    classify_learner_signals,
    demo,
    legality_errors,
    render_executor_brief,
)


def _base(**overrides):
    d = {
        "situation": "other_teaching",
        "move": "hint",
        "focus": {"kind": "pack_id", "ref": "P-4.2"},
        "reveal_policy": "prefer_scaffold",
        "error_policy": {"mode": "none", "priority": "none"},
        "sequence_slot": "production",
        "frame": {
            "lang": "es", "register": "tu",
            "character": "none", "max_lines": 2,
        },
        "elicit": {"type": "attempt_current_item", "of": "focus"},
        "constraints": ["no_second_move"],
        "session_state": "{}",
    }
    d.update(overrides)
    return d


class TestMalformedPlannerShapes(unittest.TestCase):
    """Grok-style JSON without schema enforcement sometimes nests enums."""

    def test_reveal_policy_as_object_does_not_crash(self):
        d = _base(reveal_policy={"mode": "never"})
        ok, errs, norm = check_controller_decision(d)
        # Coerced to prefer_scaffold via legacy never → should pass if rest ok
        self.assertTrue(ok, errs)
        self.assertEqual(norm["reveal_policy"], "prefer_scaffold")

    def test_reveal_policy_unusable_object_coerced_not_crash(self):
        d = _base(reveal_policy={"foo": {"bar": 1}})
        ok, errs, norm = check_controller_decision(d)
        # Soft-coerce to prefer_scaffold rather than crash or hard-fail.
        self.assertTrue(ok, errs)
        self.assertEqual(norm["reveal_policy"], "prefer_scaffold")

    def test_session_open_seed_upgrades_passthrough(self):
        d = _base(
            situation="bare_ack_or_chitchat",
            move="passthrough",
            sequence_slot="session_open",
            frame="tutor",
            error_policy={"mode": "one_error_only", "priority": "current_goal"},
            elicit={"type": "preference_or_consent", "of": "none"},
            constraints=["No due review items on schedule", "One emoji max"],
        )
        ok, errs, norm = check_controller_decision(
            d, learner_text="Please open the session per policy.")
        self.assertTrue(ok, errs)
        self.assertEqual(norm["situation"], "session_open")
        # Input-first fallback (not production drill)
        self.assertEqual(norm["move"], "present_input")
        self.assertEqual(norm["sequence_slot"], "input")

    def test_situation_as_object_coerced(self):
        d = _base(
            situation={"name": "learner_wants_answer"},
            move="teach_answer",
            reveal_policy="give_with_followup",
            elicit={"type": "new_item_same_pattern", "of": "focus"},
        )
        ok, errs, norm = check_controller_decision(
            d, learner_text="what's the answer?")
        self.assertTrue(ok, errs)
        self.assertEqual(norm["situation"], "learner_wants_answer")


class TestTeacherNotSchoolmarm(unittest.TestCase):
    def test_asking_for_answer_may_teach_answer(self):
        d = EXAMPLES["wants_answer_teach"]["controller_decision"]
        ok, errs, norm = check_controller_decision(
            d, learner_text=EXAMPLES["wants_answer_teach"]["learner"])
        self.assertTrue(ok, errs)
        self.assertEqual(norm["move"], "teach_answer")
        self.assertIn("always_re_elicit", norm["constraints"])
        brief = render_executor_brief(norm)
        self.assertIn("Give the form clearly", brief)
        self.assertIn("Shame them for asking", brief)  # must_not

    def test_legacy_pressure_name_aliases_to_wants_answer(self):
        d = _base(
            situation="social_pressure_for_answer",
            move="teach_answer",
            reveal_policy="give_with_followup",
            elicit={"type": "new_item_same_pattern", "of": "focus"},
        )
        ok, errs, norm = check_controller_decision(
            d, learner_text="what's the answer to P-4.2?")
        self.assertTrue(ok, errs)
        self.assertEqual(norm["situation"], "learner_wants_answer")

    def test_no_forced_no_answer_key(self):
        d = EXAMPLES["wants_answer_teach"]["controller_decision"]
        ok, errs, norm = check_controller_decision(
            d, learner_text="just give me the answer")
        self.assertTrue(ok, errs)
        self.assertNotIn("no_answer_key", norm["constraints"])


class TestLegality(unittest.TestCase):
    def test_multi_error_remediate_requires_one_error_only(self):
        d = _base(
            situation="multi_error_production",
            move="remediate",
            error_policy={"mode": "none", "priority": "person_before_adjunct"},
        )
        ok, errs, _ = check_controller_decision(d, learner_text="Yo es profesora")
        self.assertFalse(ok)
        self.assertTrue(any("one_error_only" in e for e in errs))

    def test_multi_error_example_passes(self):
        d = EXAMPLES["multi_error"]["controller_decision"]
        ok, errs, _ = check_controller_decision(
            d, learner_text=EXAMPLES["multi_error"]["learner"])
        self.assertTrue(ok, errs)

    def test_chitchat_passthrough(self):
        d = EXAMPLES["chitchat"]["controller_decision"]
        ok, errs, norm = check_controller_decision(
            d, learner_text=EXAMPLES["chitchat"]["learner"])
        self.assertTrue(ok, errs)
        self.assertEqual(norm["elicit"]["type"], "short_ack_only")

    def test_spanish_in_focus_rejected(self):
        d = _base(focus={"kind": "grammatical_name", "ref": "buenas noches"})
        ok, errs, _ = check_controller_decision(d)
        self.assertFalse(ok)
        self.assertTrue(any("Spanish" in e or "surface" in e for e in errs))

    def test_pack_id_format(self):
        d = _base(focus={"kind": "pack_id", "ref": "not-an-id"})
        ok, errs, _ = check_controller_decision(d)
        self.assertFalse(ok)

    def test_answer_key_item_only_in_keys_situation(self):
        d = _base(
            situation="other_teaching",
            move="answer_key_item",
            reveal_policy="answer_list_ok",
        )
        ok, errs, _ = check_controller_decision(d)
        self.assertFalse(ok)


class TestSignals(unittest.TestCase):
    def test_wants_answer_vs_keys(self):
        self.assertTrue(
            classify_learner_signals("what's the answer to P-4.2?")[
                "wants_answer"])
        self.assertTrue(
            classify_learner_signals("answer-key mode please")[
                "keys_request"])
        self.assertFalse(
            classify_learner_signals("answer-key mode please")[
                "wants_answer"])


class TestRender(unittest.TestCase):
    def test_brief_is_teacher_shaped(self):
        d = EXAMPLES["wants_answer_teach"]["controller_decision"]
        _, _, norm = check_controller_decision(
            d, learner_text=EXAMPLES["wants_answer_teach"]["learner"])
        brief = render_executor_brief(norm)
        self.assertIn("teach_answer", brief)
        self.assertIn("Do not moralize", brief)
        self.assertNotIn("INTENT:", brief)

    def test_demo_runs(self):
        text = demo()
        self.assertIn("teach_answer", text)
        self.assertIn("schoolmarm", text.lower())


class TestLegalTableCoverage(unittest.TestCase):
    def test_all_situations_have_moves(self):
        for sit, moves in LEGAL_MOVES.items():
            self.assertTrue(moves, f"{sit} has empty legal set")

    def test_wants_answer_includes_teach_answer(self):
        self.assertIn("teach_answer", LEGAL_MOVES["learner_wants_answer"])


if __name__ == "__main__":
    unittest.main()
