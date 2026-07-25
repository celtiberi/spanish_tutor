"""PlanCard gate, optional rules planner, session memory, teach images."""

import unittest

from tutor.character_sheet import default_sheet
from tutor.executor import build_ai_tutor_user_message
from tutor.observe import build_observations, probe_signals
from tutor.plan_card import PlanCard, PlanTargets, fallback_diagnostic_card, gate_plan_card
from tutor.rules_planner import plan_turn
from tutor.session_memory import SessionMemory
from tutor.teach_assets import (
    assets_for_ai_turn,
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


class TestObserve(unittest.TestCase):
    def test_probe_signals_name(self):
        s = probe_signals("Me llamo Patrick")
        self.assertIn("name", s)

    def test_observations_bundle(self):
        sheet = default_sheet()
        obs = build_observations(sheet, learner="Yo está bien", is_open=False)
        self.assertTrue(obs.get("error_hit_ids") or obs.get("signals"))


class TestAiTutorContext(unittest.TestCase):
    def test_context_is_facts_not_ladder(self):
        msg = build_ai_tutor_user_message(
            learner="Estoy bien",
            is_open=False,
            session_memory={"shown": ["estoy"], "asked": ["ask_how"], "turns": 1},
            observations={
                "signals": ["estoy", "spanish_ok"],
                "error_hits": [],
                "active_errors": [],
                "next_best": {"can_do": "IP-03"},
            },
            blank_sheet=False,
        )
        self.assertIn("session_facts", msg)
        self.assertIn("hard_observations", msg)
        self.assertIn("Decide the pedagogical move yourself", msg)
        # Must not ship a scripted next-card ladder
        self.assertNotIn("chat_ask_name", msg)
        self.assertNotIn("origin_to_gusta", msg)


class TestRulesPlannerOptional(unittest.TestCase):
    """Rules mode kept for experiments — not the product default."""

    def test_open_comm(self):
        card = plan_turn(default_sheet(), is_open=True)
        self.assertTrue(card.try_prompt)

    def test_yo_esta_recast(self):
        card = plan_turn(default_sheet(), learner="Yo está bien")
        self.assertEqual(card.move, "recast_retry")

    def test_free_chat_gate_ok(self):
        mem = SessionMemory()
        mem.shown = {"greet", "estoy", "name", "origin"}
        mem.asked = {"ask_how", "ask_name", "ask_origin"}
        card = plan_turn(
            default_sheet(),
            learner="Me gusta el café",
            memory=mem,
        )
        g = gate_plan_card(card)
        self.assertTrue(g.ok, g.errors)


class TestSessionMemory(unittest.TestCase):
    def test_accumulates(self):
        m = SessionMemory()
        m.note_learner("Hola, estoy bien")
        self.assertIn("greet", m.shown)
        self.assertIn("estoy", m.shown)
        m.note_plan_try("ai_tutor", "¿Cómo te llamas?")
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
        card = PlanCard(
            phase="diagnostic",
            move="model_try",
            models=["¡Hola!"],
            try_prompt="¿Cómo estás?",
            image_concept="hola",
            targets=PlanTargets(concepts=["hola"]),
            reason="comm_open",
        )
        d = decide_teach_image(card, images_shown=set(), session_turns=0)
        self.assertTrue(d.want)
        self.assertEqual(d.concept, "hola")
        imgs = assets_for_plan(card, images_shown=set(), session_turns=0)
        self.assertTrue(imgs)
        self.assertEqual(cache_lookup("hola")["cache"], "hit")

    def test_ai_turn_open_image(self):
        imgs, d = assets_for_ai_turn(
            is_open=True,
            blank_sheet=True,
            images_shown=set(),
            session_turns=0,
        )
        self.assertTrue(d.want)
        self.assertTrue(imgs)
        self.assertEqual(imgs[0]["concept"], "hola")

    def test_ai_turn_no_wallpaper_on_empty_chat(self):
        imgs, d = assets_for_ai_turn(
            is_open=False,
            tutor_models=["¡Claro!", "¿Y tú?"],
            tutor_try="¿Qué te gusta?",
            images_shown=set(),
            session_turns=5,
            turns_since_image=5,
        )
        # no concrete concept → no image
        self.assertFalse(d.want or imgs)

    def test_ai_turn_cafe_from_tutor_model(self):
        imgs, d = assets_for_ai_turn(
            is_open=False,
            tutor_models=["A mí me gusta el café."],
            tutor_try="¿Qué te gusta?",
            images_shown=set(),
            session_turns=3,
            turns_since_image=3,
        )
        self.assertIn("cafe", d.candidates or ([d.concept] if d.concept else []))
        # may want cafe if decision triggers
        if d.want:
            self.assertEqual(d.concept, "cafe")

    def test_no_image_when_already_shown(self):
        card = PlanCard(
            phase="diagnostic",
            move="model_try",
            models=["¡Hola!"],
            try_prompt="hi",
            image_concept="hola",
            reason="comm_open",
        )
        d = decide_teach_image(card, images_shown={"hola"}, session_turns=3)
        self.assertFalse(d.want)
        self.assertEqual(d.reason, "concepts_already_shown")

    def test_loop_recovery_no_image(self):
        imgs, d = assets_for_ai_turn(
            is_open=False,
            signals=["loop_complaint"],
            tutor_models=["Perdón"],
            tutor_try="¿Te gusta el café?",
            images_shown=set(),
            session_turns=4,
        )
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
            images_shown=set(),
            session_turns=2,
            turns_since_image=0,
        )
        self.assertFalse(d.want)
        self.assertEqual(d.reason, "skip_rate_limit")

    def test_recast_abstract_no_image(self):
        card = plan_turn(default_sheet(), learner="Yo está bien")
        self.assertEqual(card.move, "recast_retry")
        d = decide_teach_image(card, images_shown=set(), session_turns=2, turns_since_image=5)
        self.assertFalse(d.want)


if __name__ == "__main__":
    unittest.main()
