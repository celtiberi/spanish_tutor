"""Pedagogy contract — must not be soft-prompt only."""

import unittest
from pathlib import Path

from tutor.pedagogy_contract import (
    CONTRACT_VERSION,
    VIOLATION_NO_TEACH_MOVE,
    VIOLATION_OPEN_NEEDS_MODEL_TRY,
    VIOLATION_RECAST_WITHOUT_TRY,
    check_tutor_parts,
    evaluate_turn,
    has_teach_move,
)
from tutor.tutor_response import parse_tutor_response


class TestPedagogyContract(unittest.TestCase):
    def test_version_pinned(self):
        self.assertTrue(CONTRACT_VERSION)

    def test_chat_buddy_open_fails(self):
        """Bare greeting = the failure mode we actually shipped."""
        parts = {
            "continue": "¡Hola! ¿Cómo estás hoy?",
            "structured": True,
        }
        r = check_tutor_parts(parts, is_open=True)
        self.assertFalse(r.ok)
        self.assertIn(VIOLATION_NO_TEACH_MOVE, r.violations)
        self.assertIn(VIOLATION_OPEN_NEEDS_MODEL_TRY, r.violations)

    def test_teach_open_passes(self):
        parts = {
            "model": "**Estoy bien.** / **Estoy más o menos.**",
            "try": "¿Cómo estás hoy?",
            "structured": True,
        }
        r = check_tutor_parts(parts, is_open=True)
        self.assertTrue(r.ok)
        self.assertTrue(has_teach_move(parts))

    def test_recast_without_try_fails(self):
        parts = {
            "recast": "Natural: **Estoy bien.**",
            "continue": "¿Y el café?",
            "structured": True,
        }
        r = check_tutor_parts(parts, is_open=False)
        self.assertFalse(r.ok)
        self.assertIn(VIOLATION_RECAST_WITHOUT_TRY, r.violations)

    def test_recast_with_try_passes(self):
        parts = {
            "recast": "Natural: **Estoy bien.**",
            "try": "Di: **Estoy bien.**",
            "structured": True,
        }
        r = check_tutor_parts(parts, is_open=False)
        self.assertTrue(r.ok)

    def test_parse_integration(self):
        raw = """
        <tutor>
          <model>**Estoy en el bote.**</model>
          <try>¿Dónde estás?</try>
        </tutor>
        """
        p = parse_tutor_response(raw)
        r = evaluate_turn(p, is_open=True, structured=True)
        self.assertTrue(r.ok)

    def test_prompt_still_mentions_teach_cycle(self):
        """Regression: prompt rewrites must not delete the teach cycle.

        Soft backup only — the real gate is check_tutor_parts. This stops
        accidental deletion of the human-readable contract in the prompt.
        """
        path = Path(__file__).resolve().parents[1] / "prompts" / "conversational_tutor.md"
        text = path.read_text(encoding="utf-8")
        for needle in (
            "You are a tutor",
            "<model>",
            "<try>",
            "Teach cycle",
            "not a chat buddy",
        ):
            self.assertIn(needle, text, f"prompt missing {needle!r}")


if __name__ == "__main__":
    unittest.main()
