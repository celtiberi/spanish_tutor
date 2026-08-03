"""Recurring error_patterns on the character sheet."""

import unittest

from tutor.character_sheet import (
    active_error_patterns,
    apply_delta,
    apply_error_pattern_updates,
    default_sheet,
    normalize_error_pattern_id,
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
        # each clean use drops count (progressive)
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["count"], 1)
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["resolved_streak"], 1)
        s = apply_error_pattern_updates(s, "Yo estoy en Río Dulce.")
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["count"], 0)
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["resolved_streak"], 2)
        self.assertEqual(s["error_patterns"]["estar_yo_estoy_vs_esta"]["correct_uses"], 2)

    def test_same_turn_error_beats_resolve(self):
        s = default_sheet()
        s = apply_error_pattern_updates(s, "Yo está en mi bote.")
        # mixed line: still counts as error, not resolve
        s = apply_error_pattern_updates(s, "Yo está… um estoy?")
        ep = s["error_patterns"]["estar_yo_estoy_vs_esta"]
        self.assertEqual(ep["resolved_streak"], 0)
        self.assertGreaterEqual(ep["count"], 2)

    def test_form_focus_until_healthy_streak(self):
        s = default_sheet()
        for _ in range(3):
            s = apply_error_pattern_updates(s, "Yo está en Río Dulce.")
        # three clean uses → count 0 but streak < 3 until third... 
        s = apply_error_pattern_updates(s, "Estoy en mi bote.")
        s = apply_error_pattern_updates(s, "Yo estoy bien.")
        # count may be 1 or 0; still needs form focus until streak 3
        active = active_error_patterns(s)
        self.assertTrue(active)
        self.assertEqual(active[0]["id"], "estar_yo_estoy_vs_esta")
        s = recompute_next_best(s)
        self.assertEqual(s["next_best"].get("error_pattern"), "estar_yo_estoy_vs_esta")
        self.assertEqual(s["next_best"].get("form_focus"), "present_estar_person")
        # one more clean → streak 3, count 0 → drop form focus
        s = apply_error_pattern_updates(s, "Estoy en el río.")
        ep = s["error_patterns"]["estar_yo_estoy_vs_esta"]
        self.assertGreaterEqual(ep["resolved_streak"], 3)
        self.assertEqual(ep["count"], 0)
        active = active_error_patterns(s)
        self.assertFalse(active)
        s = recompute_next_best(s)
        self.assertIsNone(s["next_best"].get("error_pattern"))

    def test_process_turn_notes_error_via_tool(self):
        """Error patterns are tool-noted, not regex-graded (2026-07-31)."""
        s = default_sheet()
        s, _, notes = process_turn(
            s,
            "Yo está en mi bote.",
            "Estoy en mi bote.",
            tool_delta={
                "reason": "Learner used yo está instead of estoy",
                "evidence": "Yo está en mi bote",
                "error_patterns": {
                    "estar_yo_estoy_vs_esta": {
                        "last_examples": ["Yo está en mi bote."],
                    }
                },
            },
        )
        self.assertTrue(
            any(n.startswith("err×") for n in notes)
            or "estar_yo_estoy_vs_esta" in s.get("error_patterns", {})
        )
        self.assertIn("estar_yo_estoy_vs_esta", s["error_patterns"])

    def test_normalize_alias(self):
        self.assertEqual(
            normalize_error_pattern_id("estar_yo_esta"),
            "estar_yo_estoy_vs_esta",
        )

    def test_tool_examples_do_not_multi_count(self):
        """Tool listing many examples bumps count once, stores all examples."""
        s = default_sheet()
        s = apply_delta(s, {
            "error_patterns": {
                "estar_yo_esta": {  # alias
                    "last_examples": [
                        "Yo está bien",
                        "Yo está en el bote",
                        "Yo está en Río Dulce",
                    ],
                }
            }
        })
        ep = s["error_patterns"].get("estar_yo_estoy_vs_esta") or {}
        self.assertIn("Yo está bien", ep.get("last_examples") or [])
        self.assertEqual(int(ep.get("count") or 0), 1)
        self.assertNotIn("estar_yo_esta", s["error_patterns"])
        # Regex apply_error_pattern_updates is no longer the ability path;
        # tool already counted once for this grade event.


if __name__ == "__main__":
    unittest.main()
