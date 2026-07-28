"""Tutor persona layer (prompts/tutor_persona.md, TUTOR_PERSONA toggle)."""

import unittest

from tutor import config
from tutor.executor import build_ai_tutor_system, load_persona


def _block_texts(blocks) -> str:
    return "\n".join(b.get("text", "") for b in blocks)


class TestPersona(unittest.TestCase):
    def test_persona_file_loads(self):
        p = load_persona()
        self.assertIn("Marisol", p)
        # Countersigned hard rule: pedagogy outranks persona
        self.assertIn("Personality never cancels a required recast", p)

    def test_persona_block_in_system(self):
        blocks = build_ai_tutor_system(
            sheet_summary="{}", personal_context="# Learner personal context"
        )
        joined = _block_texts(blocks)
        self.assertIn("Marisol", joined)
        # Persona sits before the ability sheet block
        idx_persona = next(
            i for i, b in enumerate(blocks) if "Marisol" in b.get("text", "")
        )
        idx_sheet = next(
            i for i, b in enumerate(blocks)
            if "Spanish ABILITIES" in b.get("text", "")
        )
        self.assertLess(idx_persona, idx_sheet)

    def test_persona_disabled_by_env(self):
        old = config.PERSONA_ENABLED
        try:
            config.PERSONA_ENABLED = False
            self.assertEqual(load_persona(), "")
            blocks = build_ai_tutor_system(sheet_summary="{}")
            self.assertNotIn("Marisol", _block_texts(blocks))
        finally:
            config.PERSONA_ENABLED = old

    def test_persona_declares_pedagogy_precedence_and_variety(self):
        p = load_persona()
        # Load-bearing countersigned lines: LatAm production only; fictional
        # self-ID; no real channel/creator branding in the system file
        self.assertIn("Latin American default", p)
        self.assertIn("fictional AI tutor persona", p)
        self.assertNotIn("Spanish After Hours", p)
        self.assertNotIn("YouTube channel", p)
        # Recast isolation + peninsular caps survived edits
        self.assertIn("Recasts stay clean", p)
        self.assertIn("per session", p)


if __name__ == "__main__":
    unittest.main()
