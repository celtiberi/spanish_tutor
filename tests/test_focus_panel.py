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

    def test_panel_morphology_is_record_projection_never_agenda(self):
        """Panel paradigms come from the learner's GRAMMAR RECORD (forms
        with emerging/fragile evidence), never from next_best/agenda."""
        import inspect

        from tutor import can_dos

        s = default_sheet()
        # Agenda alone (next_best form_focus) must produce NOTHING:
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
        # Learner RECORD produces the reference paradigm, weakest first:
        s["grammar"]["present_estar_person"].update(
            {"status": "emerging", "confidence": 0.3}
        )
        s["grammar"]["present_ser"].update(
            {"status": "fragile", "confidence": 0.2}
        )
        panel2 = build_focus_panel(s)
        ids = [b["form_id"] for b in panel2["morphology"]]
        self.assertEqual(ids, ["present_ser", "present_estar_person"])
        for b in panel2["morphology"]:
            self.assertFalse(b["live"])
            self.assertEqual(b["kind"], "from_sheet")
            self.assertTrue(b["paradigm"])
            self.assertIn("status", b["learner"])
        # Absence pins: agenda-card machinery stays deleted.
        self.assertFalse(hasattr(can_dos, "morphology_blocks_for_form"))
        self.assertFalse(hasattr(can_dos, "morphology_blocks_for_can_do"))
        self.assertFalse(hasattr(can_dos, "_live_focus_from_mode"))
        self.assertFalse(hasattr(can_dos, "_MODE_TITLES"))
        sig = inspect.signature(build_focus_panel)
        self.assertNotIn("mode_decision", sig.parameters)

    def test_sheet_public_merges_model_card(self):
        """sheet_public shows the teacher's <morph> card; none → empty.

        Isolated sheet path — building on the default path reads the
        OPERATOR'S live sheet (the 2026-07-28 pollution class; caught
        2026-08-04 when the record projection made it visible)."""
        import tempfile
        from pathlib import Path

        tmp = tempfile.mkdtemp()
        sess = ConversationalSession(
            log=False, sheet_path=Path(tmp) / "sheet.json"
        )
        pub = sess.sheet_public()
        # "This turn" focus card deleted from the payload (USER
        # 2026-08-04); focus_version survives — it drives rail refresh.
        self.assertNotIn("focus", pub)
        self.assertIn("focus_version", pub)
        self.assertEqual(pub.get("morphology"), [])  # blank sheet, no card

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
        self.assertGreaterEqual(len(pub2["morphology"]), 1)
        # The model's card leads; record-projection reference follows.
        self.assertEqual(pub2["morphology"][0]["label"], "trabajar — to work")
        self.assertTrue(pub2["morphology"][0]["live"])


if __name__ == "__main__":
    unittest.main()
