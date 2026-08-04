"""Focus rail panel — sheet projection + the MODEL-AUTHORED morphology card.

2026-08-03: the agenda-morphology assembly (next_best form_focus / can-do
paradigm blocks) was DELETED with the code-detection card; the Morphology
panel renders session.last_morph — the card the teacher emitted via
<morph> — merged in by sheet_public. build_focus_panel itself no longer
produces morphology blocks.
"""

import unittest

from tutor.can_dos import build_focus_panel
from tutor.character_sheet import default_sheet
from tutor.conv_session import ConversationalSession


class TestFocusPanel(unittest.TestCase):
    def test_build_focus_panel_sheet_arc(self):
        s = default_sheet()
        panel = build_focus_panel(s)
        self.assertIn("focus", panel)
        self.assertIsNone(panel["focus"]["learner_name"])

    def test_panel_produces_no_agenda_morphology(self):
        """The panel never assembles paradigms (model-authored card only)."""
        import inspect

        from tutor import can_dos

        s = default_sheet()
        s["next_best"] = {
            "can_do": "IP-03",
            "activity": "introduce_in_conversation",
            "statement": "I can say my name and ask another person's name.",
            "form_focus": "present_estar_person",
            "error_pattern": "estar_yo_estoy_vs_esta",
            "reason": "form focus | weakest IP-03",
        }
        panel = build_focus_panel(s)
        self.assertEqual(panel["morphology"], [])
        # Absence pins: agenda-card machinery stays deleted.
        self.assertFalse(hasattr(can_dos, "morphology_blocks_for_form"))
        self.assertFalse(hasattr(can_dos, "morphology_blocks_for_can_do"))
        self.assertFalse(hasattr(can_dos, "_live_focus_from_mode"))
        self.assertFalse(hasattr(can_dos, "_MODE_TITLES"))
        sig = inspect.signature(build_focus_panel)
        self.assertNotIn("mode_decision", sig.parameters)

    def test_sheet_public_merges_model_card(self):
        """sheet_public shows the teacher's <morph> card; none → empty."""
        sess = ConversationalSession(log=False)
        pub = sess.sheet_public()
        self.assertIn("focus", pub)
        self.assertEqual(pub.get("morphology"), [])

        sess.last_morph = {
            "label": "trabajar — to work",
            "paradigm": [
                {"form": "trabajo", "person": "yo", "gloss": "I work",
                 "highlight": False},
            ],
            "note": "",
            "live": True,
            "source": "model",
        }
        pub2 = sess.sheet_public()
        self.assertEqual(len(pub2["morphology"]), 1)
        self.assertEqual(pub2["morphology"][0]["label"], "trabajar — to work")
        self.assertTrue(pub2["morphology"][0]["live"])


if __name__ == "__main__":
    unittest.main()
