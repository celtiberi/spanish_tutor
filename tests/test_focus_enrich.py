"""Focus enricher: static merge + cache key (no live API required)."""

import unittest

from tutor.can_dos import build_focus_panel
from tutor.character_sheet import default_sheet
from tutor.focus_enrich import (
    _merge_enrichment,
    _parse_json_object,
    focus_cache_key,
    focus_model_enabled,
)


class TestFocusEnrich(unittest.TestCase):
    def test_focus_model_enabled(self):
        self.assertTrue(focus_model_enabled("grok-3-mini"))
        self.assertFalse(focus_model_enabled("off"))
        self.assertFalse(focus_model_enabled("static"))
        self.assertFalse(focus_model_enabled(""))

    def test_parse_json(self):
        raw = '```json\n{"focus_blurb": "Practice leave-taking", "watch": ""}\n```'
        d = _parse_json_object(raw)
        self.assertEqual(d["focus_blurb"], "Practice leave-taking")

    def test_merge_enrichment(self):
        s = default_sheet()
        s["next_best"] = {
            "can_do": "IP-05",
            "activity": "close_exchange_naturally",
            "reason": "end politely",
            "statement": "I can end a short exchange politely.",
        }
        base = build_focus_panel(s)
        merged = _merge_enrichment(
            base,
            {
                "focus_blurb": "Patrick can close with Hasta luego.",
                "watch": "adios is fine; try hasta luego too",
                "highlight_forms": ["Hasta luego"],
                "extra_rows": [
                    {"form": "Nos vemos", "person": "—", "gloss": "See you"},
                ],
            },
        )
        self.assertIn("Patrick", merged["focus"]["blurb"])
        self.assertIn("hasta luego", merged["focus"]["watch"].lower())
        forms = [r["form"] for r in merged["morphology"][0]["paradigm"]]
        self.assertIn("Nos vemos", forms)
        hi = [r for r in merged["morphology"][0]["paradigm"] if r.get("highlight")]
        self.assertTrue(hi)

    def test_cache_key_changes_with_can_do(self):
        s = default_sheet()
        s["next_best"] = {"can_do": "IP-05", "activity": "a"}
        k1 = focus_cache_key(s)
        s["next_best"] = {"can_do": "IP-06", "activity": "a"}
        k2 = focus_cache_key(s)
        self.assertNotEqual(k1, k2)


if __name__ == "__main__":
    unittest.main()
