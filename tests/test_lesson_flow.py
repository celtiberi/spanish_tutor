"""Lesson flow + pack lookup (no API)."""

import unittest
from pathlib import Path

from tutor.lesson_flow import (
    advance_phase,
    allowed_moves_for_state,
    build_session_open_decision,
    due_items,
    flow_gate_errors,
)
from tutor.pack_lookup import lookup_entry, seed_dialogue_excerpt
from tutor.pedagogy_controller import check_controller_decision, render_executor_brief
from tutor.student import default_state

PACK = Path(__file__).resolve().parents[1] / "course_packs" / "spanish_a1"


class TestSessionOpen(unittest.TestCase):
    def test_open_without_due_is_input_first(self):
        d = build_session_open_decision(default_state())
        self.assertEqual(d["move"], "present_input")
        self.assertEqual(d["sequence_slot"], "input")
        self.assertIn("input first", d.get("_open_note", "").lower())
        ok, errs, norm = check_controller_decision(
            {k: v for k, v in d.items() if not k.startswith("_")},
            learner_text="Please open the session per policy.",
        )
        self.assertTrue(ok, errs)
        self.assertEqual(norm["move"], "present_input")

    def test_open_with_due_is_review(self):
        st = default_state()
        st["review_schedule"] = [{
            "item": "¿Cómo está usted? (P-1.1)",
            "misconception": "M-1.2",
            "due": "2020-01-01",
            "successes": 0,
        }]
        d = build_session_open_decision(st)
        self.assertEqual(d["sequence_slot"], "review")
        self.assertEqual(d["move"], "elicit_production")
        self.assertEqual(d["focus"]["ref"], "P-1.1")


class TestPhaseGate(unittest.TestCase):
    def test_production_forbidden_during_input(self):
        st = default_state()
        st["lesson_phase"] = "input"
        errs = flow_gate_errors({"move": "elicit_production"}, st)
        self.assertTrue(errs)
        self.assertIn("present_input", allowed_moves_for_state(st))

    def test_advance_on_present_input(self):
        st = default_state()
        st["lesson_phase"] = "input"
        st = advance_phase(st, "present_input")
        self.assertEqual(st["lesson_phase"], "comprehension")

    def test_success_in_production_goes_to_task(self):
        st = default_state()
        st["lesson_phase"] = "production"
        st = advance_phase(st, "elicit_production", success_signal=True)
        self.assertEqual(st["lesson_phase"], "task")

    def test_surface_issue_advances(self):
        st = default_state()
        st["lesson_phase"] = "production"
        st = advance_phase(
            st, "remediate", success_signal=True, issue_class="surface",
            focus_ref="M-1.2")
        self.assertEqual(st["lesson_phase"], "task")
        self.assertEqual(st["same_target_retries"], 0)

    def test_double_remediate_same_target_blocked(self):
        st = default_state()
        st["lesson_phase"] = "production"
        st["same_target_retries"] = 2
        st["last_focus_ref"] = "M-1.2"
        errs = flow_gate_errors(
            {"move": "remediate", "focus": {"ref": "M-1.2"}}, st)
        self.assertTrue(any("retried" in e for e in errs))


class TestIssueClass(unittest.TestCase):
    def test_uested_is_surface(self):
        from tutor.lesson_flow import classify_learner_issue
        c = classify_learner_issue(
            "Buenos dias senora. Como esta uested?",
            ["Buenos días, señora. ¿Cómo está usted?"],
        )
        self.assertEqual(c, "surface")

    def test_estas_to_teacher_is_conceptual(self):
        from tutor.lesson_flow import classify_learner_issue
        c = classify_learner_issue(
            "Buenos dias senora. Como estas?",
            ["Buenos días, señora. ¿Cómo está usted?"],
        )
        self.assertEqual(c, "conceptual")

    def test_esta_bien_conceptual(self):
        from tutor.lesson_flow import classify_learner_issue
        self.assertEqual(
            classify_learner_issue("Esta bien y tu?"), "conceptual")


class TestPackLookup(unittest.TestCase):
    def test_m12_remediation(self):
        text = lookup_entry(PACK, "M-1.2")
        self.assertIsNotNone(text)
        self.assertIn("estás", text.lower())
        self.assertIn("Remediation", text)

    def test_seed_excerpt(self):
        seed = seed_dialogue_excerpt(PACK, 1)
        self.assertIsNotNone(seed)
        self.assertIn("Buenas noches", seed)

    def test_brief_includes_pack_entry(self):
        d = {
            "situation": "multi_error_production",
            "move": "remediate",
            "focus": {"kind": "pack_id", "ref": "M-1.2"},
            "reveal_policy": "prefer_scaffold",
            "error_policy": {"mode": "one_error_only", "priority": "goal_relevant"},
            "sequence_slot": "production",
            "frame": {
                "lang": "en", "register": "tu",
                "character": "none", "max_lines": 3,
            },
            "elicit": {"type": "re_produce_corrected_form", "of": "focus"},
            "constraints": ["one_correction_max", "always_re_elicit"],
            "session_state": "{}",
        }
        ok, errs, norm = check_controller_decision(d)
        self.assertTrue(ok, errs)
        brief = render_executor_brief(norm, pack_dir=PACK)
        self.assertIn("pack_entry", brief)
        self.assertIn("M-1.2", brief)
        self.assertIn("Remediation", brief)


if __name__ == "__main__":
    unittest.main()
