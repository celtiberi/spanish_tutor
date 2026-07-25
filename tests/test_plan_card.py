"""PlanCard, gate, rules planner, session memory (no live API)."""

import unittest

from tutor.character_sheet import default_sheet
from tutor.plan_card import PlanCard, fallback_diagnostic_card, gate_plan_card
from tutor.rules_planner import plan_turn, probe_signals
from tutor.session_memory import SessionMemory
from tutor.teach_assets import assets_for_plan, cache_lookup


class TestPlanCard(unittest.TestCase):
    def test_gate_accepts_open(self):
        card = fallback_diagnostic_card()
        g = gate_plan_card(card)
        self.assertTrue(g.ok, g.errors)

    def test_free_chat_empty_models_ok_via_planner(self):
        sheet = default_sheet()
        mem = SessionMemory()
        mem.shown = {"greet", "estoy", "name", "origin"}
        mem.asked = {"ask_how", "ask_name", "ask_origin"}
        card = plan_turn(
            sheet,
            learner="Me gusta el café",
            is_open=False,
            memory=mem,
        )
        self.assertIn(card.phase, ("chat_stretch", "diagnostic", "teach_form"))
        g = gate_plan_card(card)
        self.assertTrue(g.ok, g.errors)


class TestRulesPlanner(unittest.TestCase):
    def test_open_comm(self):
        card = plan_turn(default_sheet(), is_open=True)
        self.assertTrue(card.try_prompt)
        self.assertNotIn("if you can", card.try_prompt.lower())

    def test_hola_estoy_asks_name_once(self):
        mem = SessionMemory()
        card = plan_turn(
            default_sheet(),
            learner="Hola, estoy bien.",
            memory=mem,
        )
        mem.note_learner("Hola, estoy bien.")
        mem.note_plan_try(card.reason, card.try_prompt)
        self.assertIn("name", card.reason.lower() + card.try_prompt.lower())
        # Second time with name already shown — not name again
        mem.shown.add("name")
        mem.asked.add("ask_name")
        card2 = plan_turn(
            default_sheet(),
            learner="Me llamo Pat.",
            memory=mem,
        )
        self.assertNotIn("ask_name", card2.reason)
        self.assertTrue(
            "origin" in card2.reason or "dónde" in card2.try_prompt.lower()
            or "donde" in card2.try_prompt.lower().replace("ó", "o")
            or "from" in card2.try_prompt.lower()
        )

    def test_origin_then_not_how_are_you(self):
        mem = SessionMemory()
        mem.shown = {"greet", "estoy", "name", "origin"}
        mem.asked = {"ask_how", "ask_name", "ask_origin"}
        card = plan_turn(
            default_sheet(),
            learner="Yo soy de Estados Unidos.",
            memory=mem,
        )
        low = (card.try_prompt + card.reason).lower()
        self.assertNotIn("cómo estás", low.replace("á", "a"))
        self.assertNotIn("como estas", low)

    def test_loop_complaint_recovers(self):
        mem = SessionMemory()
        mem.asked = {"ask_how", "ask_name"}
        card = plan_turn(
            default_sheet(),
            learner="I think you already asked me this",
            memory=mem,
        )
        self.assertEqual(card.reason, "loop_recovery")

    def test_yo_esta_recast(self):
        card = plan_turn(default_sheet(), learner="Yo está bien")
        self.assertEqual(card.move, "recast_retry")

    def test_open_has_hola_asset(self):
        card = plan_turn(default_sheet(), is_open=True)
        self.assertEqual(card.image_concept, "hola")
        self.assertTrue(assets_for_plan(card))
        self.assertEqual(cache_lookup("hola")["cache"], "hit")


class TestSessionMemory(unittest.TestCase):
    def test_accumulates(self):
        m = SessionMemory()
        m.note_learner("Hola, estoy bien")
        self.assertIn("greet", m.shown)
        self.assertIn("estoy", m.shown)
        m.note_plan_try("chat_ask_name", "¿Cómo te llamas?")
        self.assertIn("ask_name", m.asked)


if __name__ == "__main__":
    unittest.main()
