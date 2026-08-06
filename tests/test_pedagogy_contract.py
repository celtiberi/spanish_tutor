"""pedagogy_contract — record-keeping half only (S11, 2026-08-03).

The per-turn contract JUDGMENT (evaluate_turn / check_tutor_parts /
PedagogyCheck and the pedagogy:* fault vocabulary) was deleted from the
runtime and lives as evals/student_checks.py::check_teach_shape — see
tests/test_student_checks.py.  What remains here: blank-sheet detection,
the open-phase label, the mechanical has_teach_move helper, and absence
pins for the deleted judgment surface.
"""

import unittest
from pathlib import Path

from tutor.character_sheet import default_sheet
from tutor.pedagogy_contract import (
    KEY_DIAGNOSTIC_OPEN,
    KEY_KNOWN_LEARNER_OPEN,
    has_teach_move,
    is_blank_learner,
    open_phase,
)


class TestBlankDetection(unittest.TestCase):
    def test_blank_sheet_is_diagnostic(self):
        s = default_sheet()
        self.assertTrue(is_blank_learner(s))
        self.assertEqual(open_phase(s), "diagnostic")

    def test_known_sheet_not_blank(self):
        s = default_sheet()
        s["identity"]["preferred_name"] = "Alex"
        s["skills"]["IP-01"] = {
            **s["skills"]["IP-01"],
            "status": "known",
            "confidence": 0.8,
            "evidence": ["hola"],
        }
        self.assertFalse(is_blank_learner(s))
        self.assertEqual(open_phase(s), "known")

    def test_phase_note_keys_are_the_tail_vocabulary(self):
        # The turn tail's PEDAGOGY event renders "pedagogy:" + these keys
        # (bookkeeping — which open script ran).
        self.assertEqual(KEY_DIAGNOSTIC_OPEN, "diagnostic_open")
        self.assertEqual(KEY_KNOWN_LEARNER_OPEN, "known_learner_open")


class TestHasTeachMove(unittest.TestCase):
    def test_teach_parts_detected(self):
        self.assertTrue(has_teach_move({"model": "Estoy bien.", "try": "¿Y tú?"}))
        self.assertTrue(has_teach_move({"recast": "Natural: **Estoy bien.**"}))

    def test_chat_only_parts_are_not_a_teach_move(self):
        self.assertFalse(
            has_teach_move({"continue": "¡Hola! ¿Cómo estás hoy?"})
        )
        self.assertFalse(has_teach_move({}))
        self.assertFalse(has_teach_move(None))


class TestJudgmentHalfStaysDeleted(unittest.TestCase):
    def test_deleted_judgment_surface(self):
        # S11 absence pins: the runtime contract checker must not resurface.
        import tutor.pedagogy_contract as pc

        for name in (
            "evaluate_turn", "check_tutor_parts", "check_visible_fallback",
            "PedagogyCheck", "CONTRACT_VERSION", "TEACH_MODALITIES",
            "KEY_NO_TEACH_MOVE", "KEY_OPEN_NEEDS_MODEL_TRY",
            "KEY_RECAST_WITHOUT_TRY", "KEY_OK", "KEY_UNSTRUCTURED",
            "VIOLATION_NO_TEACH_MOVE", "VIOLATION_OPEN_NEEDS_MODEL_TRY",
            "VIOLATION_RECAST_WITHOUT_TRY", "OK_TEACH_MOVE",
            "PEDAGOGY_NOTE_PREFIX", "NOTE_DIAGNOSTIC_OPEN",
            "NOTE_KNOWN_LEARNER_OPEN",
        ):
            self.assertFalse(hasattr(pc, name), name)

    def test_conv_session_no_longer_judges(self):
        # The _finish contract block is gone: no evaluate_turn import, no
        # "contract"-stage emission, no parts["pedagogy"] payload.
        # Comments are stripped so documentation may still NAME the old
        # idiom (same discipline as the conv_session source pin in
        # tests/test_turn_events.py).
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
        self.assertNotIn("evaluate_turn", code)
        self.assertNotIn('"pedagogy": ped', code)


class TestPromptStillTeaches(unittest.TestCase):
    def test_prompt_still_mentions_teach_cycle(self):
        """Regression: prompt rewrites must not delete the teach cycle.

        S11 moved ENFORCEMENT to evals — the teaching rules themselves must
        keep shipping to the model. This stops accidental deletion of the
        human-readable contract in the prompt.
        """
        path = Path(__file__).resolve().parents[1] / "prompts" / "conversational_tutor.md"
        text = path.read_text(encoding="utf-8")
        for needle in (
            "You are a tutor",
            "<model>",
            "<try>",
            "Teach cycle",
            "not a chat buddy",
            # Diagnostic feel-out superseded by orientation + placement
            # (2026-08-06 round, docs/archive/reviews/onboarding-
            # placement-20260806.md) — pin the new contract's spine.
            "Orientation + placement",
            "Hard stop rules",
            "Never mark `known` from",
            "Blank sheet",
        ):
            self.assertIn(needle, text, f"prompt missing {needle!r}")


if __name__ == "__main__":
    unittest.main()
