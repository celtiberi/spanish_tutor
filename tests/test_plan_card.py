"""PlanCard, gate, and rules planner (no live API)."""

import unittest

from tutor.character_sheet import default_sheet
from tutor.plan_card import (
    PlanCard,
    PlanTargets,
    fallback_diagnostic_card,
    gate_plan_card,
)
from tutor.rules_planner import plan_turn
from tutor.teach_assets import assets_for_plan, resolve_concept


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
        self.assertEqual(g.card.phase, "diagnostic")

    def test_roundtrip_dict(self):
        card = fallback_diagnostic_card()
        d = card.as_dict()
        c2 = PlanCard.from_dict(d)
        self.assertEqual(c2.models, card.models)
        self.assertEqual(c2.move, card.move)


class TestRulesPlanner(unittest.TestCase):
    def test_blank_open_diagnostic(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="", is_open=True)
        self.assertEqual(card.phase, "diagnostic")
        self.assertTrue(card.models)
        self.assertTrue(card.try_prompt)
        self.assertTrue(card.english_frame)
        g = gate_plan_card(card)
        self.assertTrue(g.ok)

    def test_yo_esta_triggers_recast(self):
        sheet = default_sheet()
        # Give some evidence so not pure blank follow-up only
        sheet["skills"]["IP-01"]["status"] = "emerging"
        sheet["skills"]["IP-01"]["confidence"] = 0.3
        sheet["skills"]["IP-01"]["evidence"] = ["hola"]
        card = plan_turn(sheet, learner="Yo está bien", is_open=False)
        self.assertEqual(card.move, "recast_retry")
        self.assertEqual(card.targets.error_pattern, "estar_yo_estoy_vs_esta")
        self.assertTrue(any("Estoy" in m or "estoy" in m.lower() for m in card.models))
        g = gate_plan_card(card)
        self.assertTrue(g.ok, g.errors)

    def test_blank_after_hola(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="Hola", is_open=False)
        self.assertEqual(card.phase, "diagnostic")
        self.assertTrue(any("Estoy" in m for m in card.models))
        self.assertIn("I am fine", card.english_frame)
        self.assertEqual(card.image_concept, "estoy_bien")

    def test_after_estoy_associates_me_llamo(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="Estoy bien", is_open=False)
        self.assertEqual(card.move, "associate")
        self.assertEqual(card.image_concept, "me_llamo")
        self.assertIn("My name is", card.english_frame)
        self.assertTrue(any("Me llamo" in m for m in card.models))
        # Do not dump a second unmodeled question form first
        self.assertFalse(any("Cómo te llamas" in m for m in card.models))
        assets = assets_for_plan(card)
        self.assertTrue(assets)
        self.assertEqual(assets[0]["concept"], "me_llamo")

    def test_diagnostic_has_hola_image(self):
        sheet = default_sheet()
        card = plan_turn(sheet, learner="", is_open=True)
        self.assertEqual(card.image_concept, "hola")
        assets = assets_for_plan(card)
        self.assertTrue(assets, "hola teach asset should resolve")
        self.assertEqual(assets[0]["concept"], "hola")
        self.assertIn("/static/teach_assets/", assets[0]["url"])
        self.assertIsNotNone(resolve_concept("hola"))
        self.assertIsNotNone(resolve_concept("estoy_bien"))


if __name__ == "__main__":
    unittest.main()
