"""PlanCard, gate, rules planner, session memory, teach images (no live API)."""

import unittest

from tutor.character_sheet import default_sheet
from tutor.plan_card import PlanCard, PlanTargets, fallback_diagnostic_card, gate_plan_card
from tutor.rules_planner import plan_turn, probe_signals
from tutor.session_memory import SessionMemory
from tutor.teach_assets import (
    assets_for_plan,
    cache_lookup,
    decide_teach_image,
    extract_concept_candidates,
)


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
        imgs = assets_for_plan(card, images_shown=set(), session_turns=0)
        self.assertTrue(imgs)
        self.assertEqual(imgs[0]["concept"], "hola")
        self.assertEqual(cache_lookup("hola")["cache"], "hit")


class TestSessionMemory(unittest.TestCase):
    def test_accumulates(self):
        m = SessionMemory()
        m.note_learner("Hola, estoy bien")
        self.assertIn("greet", m.shown)
        self.assertIn("estoy", m.shown)
        m.note_plan_try("chat_ask_name", "¿Cómo te llamas?")
        self.assertIn("ask_name", m.asked)

    def test_image_memory(self):
        m = SessionMemory()
        m.note_image("hola")
        self.assertIn("hola", m.images_shown)
        self.assertEqual(m.turns_since_image, 0)
        m.note_learner("Estoy bien")
        self.assertGreaterEqual(m.turns_since_image, 1)


class TestImageDecision(unittest.TestCase):
    def test_open_wants_hola(self):
        card = plan_turn(default_sheet(), is_open=True)
        d = decide_teach_image(card, images_shown=set(), session_turns=0)
        self.assertTrue(d.want)
        self.assertEqual(d.concept, "hola")

    def test_no_image_when_already_shown(self):
        card = plan_turn(default_sheet(), is_open=True)
        d = decide_teach_image(card, images_shown={"hola"}, session_turns=3)
        self.assertFalse(d.want)
        self.assertEqual(d.reason, "concepts_already_shown")

    def test_loop_recovery_no_image(self):
        mem = SessionMemory()
        mem.asked = {"ask_how", "ask_name"}
        card = plan_turn(
            default_sheet(),
            learner="I think you already asked me this",
            memory=mem,
        )
        d = decide_teach_image(card, images_shown=set(), session_turns=4)
        self.assertFalse(d.want)
        self.assertIn("loop", d.reason)

    def test_free_chat_without_concrete_no_wallpaper(self):
        card = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["¡Claro!", "¿Y tú?"],
            try_prompt="Continue a real Spanish conversation.",
            targets=PlanTargets(can_do="IP-06", concepts=[]),
            reason="free_chat:IP-06",
        )
        d = decide_teach_image(card, images_shown=set(), session_turns=5)
        self.assertFalse(d.want)

    def test_cafe_candidate_from_models(self):
        card = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["A mí me gusta el café."],
            try_prompt="Ask what they like — coffee, music, boat.",
            targets=PlanTargets(can_do="IP-06", concepts=["me_gusta", "cafe"]),
            image_concept="cafe",
            reason="origin_to_gusta",
        )
        cands = extract_concept_candidates(card)
        self.assertIn("cafe", cands)
        d = decide_teach_image(card, images_shown=set(), session_turns=3, turns_since_image=3)
        self.assertTrue(d.want)
        self.assertEqual(d.concept, "cafe")

    def test_rate_limit_skips_back_to_back(self):
        card = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["Estoy bien."],
            try_prompt="Ask how they are.",
            targets=PlanTargets(concepts=["estoy_bien"]),
            image_concept="estoy_bien",
            reason="chat_ask_how",
        )
        d = decide_teach_image(
            card,
            images_shown=set(),  # new concept
            session_turns=2,
            turns_since_image=0,  # just showed something last turn
        )
        # estoy_bien visual 0.85 < 0.9 highly visual → rate limited
        self.assertFalse(d.want)
        self.assertEqual(d.reason, "skip_rate_limit")

    def test_recast_abstract_no_image(self):
        card = plan_turn(default_sheet(), learner="Yo está bien")
        self.assertEqual(card.move, "recast_retry")
        d = decide_teach_image(card, images_shown=set(), session_turns=2, turns_since_image=5)
        # recast of person agreement is not highly visual enough alone
        self.assertFalse(d.want)


if __name__ == "__main__":
    unittest.main()
