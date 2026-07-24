"""Recurring error_patterns on the character sheet."""

import unittest

from tutor.character_sheet import (
    active_error_patterns,
    apply_error_pattern_updates,
    default_sheet,
    process_turn,
    recompute_next_best,
)


class TestErrorPatterns(unittest.TestCase):
    def test_detect_yo_esta(self):
        s = default_sheet()
        s = apply_error_pattern_updates(s, "Yo está en mi bote.")
        ep = s["error_patterns"]["estar_yo_estoy_vs_esta"]
        self.assertEqual(ep["count"], 1)
        self.assertTrue(ep["last_examples"])

    def test_recurring_becomes_active_and_steers_next_best(self):
        s = default_sheet()
        for _ in range(3):
            s = apply_error_pattern_updates(s, "Yo está en Río Dulce.")
        active = active_error_patterns(s)
        self.assertTrue(active)
        self.assertEqual(active[0]["id"], "estar_yo_estoy_vs_esta")
        self.assertGreaterEqual(active[0]["count"], 3)
        s = recompute_next_best(s)
        self.assertEqual(s["next_best"].get("error_pattern"), "estar_yo_estoy_vs_esta")
        self.assertEqual(s["next_best"].get("form_focus"), "present_estar_person")
        self.assertIn("recurring error", (s["next_best"].get("reason") or "").lower())
        self.assertIn("estoy", (s["next_best"].get("teach_hint") or "").lower())

    def test_resolve_eases_count(self):
        s = default_sheet()
        s = apply_error_pattern_updates(s, "Yo está en mi bote.")
        s = apply_error_pattern_updates(s, "Yo está en mi bote.")
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["count"], 2)
        s = apply_error_pattern_updates(s, "Estoy en mi bote.")
        s = apply_error_pattern_updates(s, "Yo estoy en Río Dulce.")
        # two resolves → count drops by 1
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["count"], 1)

    def test_process_turn_notes_error(self):
        s = default_sheet()
        s, _, notes = process_turn(
            s, "Yo está en mi bote.", "Estoy en mi bote.",
        )
        s, _, notes = process_turn(
            s, "Yo está en Río Dulce.", "Estoy…",
        )
        self.assertTrue(any(n.startswith("err×") for n in notes))
        self.assertIn("estar_yo_estoy_vs_esta", s["error_patterns"])


if __name__ == "__main__":
    unittest.main()
