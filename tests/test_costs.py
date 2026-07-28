"""Cost tracking: pricing math, tracker aggregation, ledger events."""

import json
import os
import tempfile
import unittest
from pathlib import Path


class TestCosts(unittest.TestCase):
    def setUp(self):
        # Isolate the ledger so tests never pollute logs/costs.jsonl
        self._tmp = tempfile.TemporaryDirectory()
        import tutor.costs as costs

        self._costs = costs
        self._old_ledger = costs.LEDGER_PATH
        costs.LEDGER_PATH = Path(self._tmp.name) / "costs.jsonl"

    def tearDown(self):
        self._costs.LEDGER_PATH = self._old_ledger
        self._tmp.cleanup()

    def test_tutor_pricing_math(self):
        from tutor.costs import SessionCostTracker

        t = SessionCostTracker(source="test")
        # 23k in, 100 out, 900 thinking @ $1.50/M in, $7.50/M out
        usd = t.add_llm(
            "tutor", "gemini-3.6-flash",
            input_tokens=23_000, output_tokens=100, thinking_tokens=900,
        )
        expect = 23_000 * 1.50 / 1e6 + (100 + 900) * 7.50 / 1e6
        self.assertAlmostEqual(usd, expect, places=8)

    def test_cached_input_discount(self):
        from tutor.costs import SessionCostTracker

        t = SessionCostTracker(source="test")
        usd = t.add_llm(
            "tutor", "gemini-3.6-flash",
            input_tokens=20_000, cached_input_tokens=10_000, output_tokens=0,
        )
        expect = 10_000 * 1.50 / 1e6 + 10_000 * 0.15 / 1e6
        self.assertAlmostEqual(usd, expect, places=8)

    def test_unknown_model_tracked_unpriced(self):
        from tutor.costs import SessionCostTracker

        t = SessionCostTracker(source="test")
        usd = t.add_llm("tutor", "mystery-model-9", input_tokens=1000,
                        output_tokens=1000)
        self.assertEqual(usd, 0.0)
        s = t.summary()
        self.assertIn("mystery-model-9", s["unpriced_models"])
        self.assertEqual(s["by_category"]["tutor"]["input_tokens"], 1000)

    def test_image_flat_pricing(self):
        from tutor.costs import SessionCostTracker

        t = SessionCostTracker(source="test")
        usd = t.add_image("gemini-2.5-flash-image", 2)
        self.assertAlmostEqual(usd, 0.078, places=6)

    def test_prefix_match_inherits_family_price(self):
        from tutor.costs import price_for

        self.assertIsNotNone(price_for("gemini-3.6-flash-001"))
        self.assertIsNone(price_for("totally-unknown"))

    def test_env_price_override(self):
        from tutor.costs import price_for

        os.environ["COST_PRICING_JSON"] = json.dumps(
            {"gemini-3.6-flash": {"input": 9.0}})
        try:
            self.assertEqual(price_for("gemini-3.6-flash")["input"], 9.0)
        finally:
            del os.environ["COST_PRICING_JSON"]

    def test_ledger_events_and_report(self):
        from tutor.costs import SessionCostTracker, ledger_report

        t = SessionCostTracker(source="eval-run")
        t.add_llm("tutor", "gemini-3.6-flash", input_tokens=1_000_000)
        t.add_image("gemini-2.5-flash-image", 1)
        rep = ledger_report()
        self.assertAlmostEqual(rep["total_usd"], 1.50 + 0.039, places=4)
        day = list(rep["days"].values())[0]
        self.assertIn("tutor", day["by_category"])
        self.assertIn("image", day["by_category"])
        self.assertIn("eval-run", day["by_source"])

    def test_summary_total_sums_categories(self):
        from tutor.costs import SessionCostTracker

        t = SessionCostTracker(source="test")
        t.add_llm("tutor", "gemini-3.6-flash", input_tokens=1_000_000)
        t.add_llm("tts", "gemini-2.5-flash-preview-tts",
                  input_tokens=100_000, output_tokens=100_000)
        s = t.summary()
        self.assertAlmostEqual(
            s["total_usd"], 1.50 + (0.05 + 1.00), places=6)


if __name__ == "__main__":
    unittest.main()
