"""PlanCard, gate, and rules planner (no live API)."""

import unittest

from tutor.character_sheet import default_sheet
from tutor.plan_card import (
    PlanCard,
    fallback_diagnostic_card,
    gate_plan_card,
)
from tutor.rules_planner import plan_turn, probe_signals
from tutor.teach_assets import (
    assets_for_plan,
    cache_lookup,
    cache_put,
    ensure_asset,
    resolve_concept,
)


class TestPlanCard(unittest.TestCase):
    def test_gate_rejects_empty_models(self):
        card = PlanCard(
            phase="teach_form",
            move="model_try",
            models=[],
            try_prompt="Di hola",
        )
        g = gate_plan_card(card)
        self.assertFalse(g.ok)
        self.assertIn("models_required", g.errors)

    def test_gate_accepts_diagnostic(self):
        card = fallback_diagnostic_card()
        g = gate_plan_card(card)
        self.assertTrue(g.ok)
        self.assertIn("Cómo estás", card.try_prompt)

    def test_roundtrip_dict(self):
        card = fallback_diagnostic_card()
        d = card.as_dict()
        c2 = PlanCard.from_dict(d)
        self.assertEqual(c2.models, card.models)
        self.assertEqual(c2.move, card.move)


class TestRulesPlanner(unittest.TestCase):
    def test_open_is_real_question(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="", is_open=True)
        self.assertIn("Cómo estás", card.try_prompt)
        self.assertNotIn("if you can", card.try_prompt.lower())
        self.assertTrue(any("Hola" in m or "hola" in m.lower() for m in card.models))
        g = gate_plan_card(card)
        self.assertTrue(g.ok, g.errors)

    def test_hola_estoy_probes_name_not_flashcard_only(self):
        sheet = default_sheet()
        sig = probe_signals("Hola, estoy bien.")
        self.assertIn("multi_skill", sig)
        card = plan_turn(sheet, learner="Hola, estoy bien.", is_open=False)
        # Conversational name probe
        self.assertIn("Cómo te llamas", card.try_prompt)
        self.assertEqual(card.phase, "chat_stretch")
        self.assertTrue(card.allow_new_topic)
        self.assertEqual(card.image_concept, "me_llamo")
        self.assertIn("My name is", card.english_frame)

    def test_name_then_origin_chat(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="Me llamo Patrick.", is_open=False)
        self.assertIn("donde eres", card.try_prompt.lower().replace("ó", "o"))
        self.assertNotEqual(card.try_prompt, "Di: **Me llamo** + your name.")
        self.assertEqual(card.phase, "chat_stretch")

    def test_ask_name_not_redrill_me_llamo(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="¿Cómo te llamas?", is_open=False)
        # Must not send them back to "say Me llamo + name"
        self.assertNotIn("Me llamo** + your name", card.try_prompt)
        self.assertTrue(
            "gusta" in card.try_prompt.lower() or "café" in " ".join(card.models).lower()
        )

    def test_yo_esta_triggers_recast(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"]["status"] = "emerging"
        sheet["skills"]["IP-01"]["confidence"] = 0.3
        sheet["skills"]["IP-01"]["evidence"] = ["hola"]
        card = plan_turn(sheet, learner="Yo está bien", is_open=False)
        self.assertEqual(card.move, "recast_retry")
        self.assertEqual(card.targets.error_pattern, "estar_yo_estoy_vs_esta")
        g = gate_plan_card(card)
        self.assertTrue(g.ok, g.errors)

    def test_diagnostic_has_hola_image(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="", is_open=True)
        self.assertEqual(card.image_concept, "hola")
        assets = assets_for_plan(card)
        self.assertTrue(assets, "hola teach asset should resolve")
        self.assertEqual(assets[0]["concept"], "hola")
        self.assertEqual(assets[0].get("cache"), "hit")

    def test_cache_lookup_no_generate(self):
        hit = cache_lookup("hola")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["cache"], "hit")
        miss = cache_lookup("totally_unknown_xyz")
        self.assertIsNone(miss)
        still = ensure_asset("totally_unknown_xyz", generate=False)
        self.assertIsNone(still)

    def test_cache_put_then_hit(self):
        key = "test_cache_blob"
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 64
        put = cache_put(key, data, form="Test", caption="cache unit", ext=".jpg")
        self.assertIsNotNone(put)
        hit = cache_lookup(key)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["concept"], key)


if __name__ == "__main__":
    unittest.main()
