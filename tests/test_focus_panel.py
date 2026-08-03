"""Focus + morphology rail data for the web UI."""

import unittest

from tutor.can_dos import build_focus_panel, morphology_blocks_for_can_do
from tutor.character_sheet import default_sheet
from tutor.conv_session import ConversationalSession


class TestFocusPanel(unittest.TestCase):
    def test_morphology_for_ip04(self):
        blocks = morphology_blocks_for_can_do("IP-04")
        ids = [b["id"] for b in blocks]
        self.assertTrue(any("present_estar_person" in i for i in ids))
        self.assertTrue(blocks[0]["paradigm"])

    def test_morphology_for_ip06(self):
        blocks = morphology_blocks_for_can_do("IP-06")
        labels = " ".join(b.get("label", "") for b in blocks).lower()
        self.assertIn("gust", labels)

    def test_build_focus_panel_sheet_arc(self):
        """Without mode_decision: live title is generic; sheet arc keeps can-do."""
        s = default_sheet()
        s["next_best"] = {
            "can_do": "IP-05",
            "activity": "close_exchange_naturally",
            "reason": "practice leave-taking",
            "avoid": "more greetings",
            "statement": "I can end a short exchange politely.",
        }
        s["skills"]["IP-05"]["status"] = "emerging"
        s["skills"]["IP-05"]["confidence"] = 0.4
        s["identity"]["preferred_name"] = "Patrick"
        panel = build_focus_panel(s)
        self.assertEqual(panel["focus"]["can_do"], "IP-05")
        self.assertIn("end a short exchange", (panel["focus"].get("sheet_title") or "").lower())
        # Personal-data capture disabled 2026-07-28: even a sheet carrying a
        # residual name must never emit it to the UI focus panel.
        self.assertIsNone(panel["focus"]["learner_name"])
        self.assertTrue(panel["morphology"])
        forms = " ".join(
            p["form"] for b in panel["morphology"] for p in b.get("paradigm") or []
        )
        self.assertIn("Adiós", forms)

    def test_panel_is_pure_sheet_projection(self):
        """Router teardown 2026-08-03 (full-code-audit S4): the live-mode
        overlay is gone — the rail is a sheet projection; form_focus still
        drives the morphology card."""
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
        f = panel["focus"]
        for gone in ("live", "mode", "mode_reason", "hard_break",
                     "image_concept"):
            self.assertNotIn(gone, f)
        self.assertIn("name", f["title"].lower())
        morph_labels = " ".join(b.get("label", "") for b in panel["morphology"]).lower()
        self.assertIn("estar", morph_labels)
        # Absence pins: the live-mode machinery stays deleted.
        self.assertFalse(hasattr(can_dos, "_live_focus_from_mode"))
        self.assertFalse(hasattr(can_dos, "_MODE_TITLES"))
        sig = inspect.signature(build_focus_panel)
        self.assertNotIn("mode_decision", sig.parameters)

    def test_sheet_public_has_focus_and_morphology(self):
        """Regression: sheet_public must not crash (broke web rail)."""
        sess = ConversationalSession(log=False)
        pub = sess.sheet_public()
        self.assertIn("focus", pub)
        self.assertTrue(pub["focus"].get("title") or pub["focus"].get("can_do")
                        or pub.get("next_best"))
        self.assertIsInstance(pub.get("morphology"), list)
        self.assertGreater(len(pub["morphology"]), 0)


if __name__ == "__main__":
    unittest.main()
