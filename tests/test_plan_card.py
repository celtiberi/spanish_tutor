"""AI tutor context, session memory, teach images (PlanCard as image DTO).

The rules planner/gate runtime and its tests were DELETED (E4,
docs/reviews-architecture-refactor.md, 2026-07-28); PlanCard/PlanTargets
survive only as the live image-decision DTO on the AI path.
"""

import unittest

from tutor.character_sheet import default_sheet
from tutor.executor import build_ai_tutor_user_message
from tutor.observe import build_observations, probe_signals
from tutor.plan_card import PlanCard, PlanTargets
from tutor.session_memory import SessionMemory
from tutor.teach_assets import (
    assets_for_ai_turn,
    cache_lookup,
    concept_in_text,
    decide_teach_image,
    extract_concept_candidates,
)


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
        self.assertIn("mode", msg)
        # Must not ship a scripted next-card ladder
        self.assertNotIn("chat_ask_name", msg)
        self.assertNotIn("origin_to_gusta", msg)
        # Standing orders moved to the STATIC system prompt (cache-stable);
        # the per-turn task carries only facts.
        from tutor.executor import AI_TUTOR_SYSTEM

        self.assertIn("Realize MODE targets and legality", AI_TUTOR_SYSTEM)
        self.assertIn("LEARNER UPTAKE", AI_TUTOR_SYSTEM)
        self.assertIn("Mode playbooks", AI_TUTOR_SYSTEM)

    def test_correction_rules_in_system_prompt(self):
        # Amended §2.5 (blind-grade defect #3, 2026-07-28): prompt-level
        # correction rules — never confirm an incorrect form; one
        # grammatical person per repair.
        from tutor.executor import AI_TUTOR_SYSTEM

        self.assertIn(
            "NEVER confirm or praise an incorrect form", AI_TUTOR_SYSTEM
        )
        self.assertIn("¡Sí!/¡Exacto!/¡Perfecto!", AI_TUTOR_SYSTEM)
        self.assertIn("ONE grammatical person per repair", AI_TUTOR_SYSTEM)
        self.assertIn(
            "1st and 2nd person variants in the same repair",
            AI_TUTOR_SYSTEM,
        )

    def test_true_zero_english_exception_in_system_prompt(self):
        # Incident 2026-07-28: reset beginner got zero English. The lifeline
        # stance must carry an explicit true-zero exception (PEDAGOGY P1,
        # §2.3) while keeping the English-wall ban intact.
        from tutor.executor import AI_TUTOR_SYSTEM

        self.assertIn("English is a lifeline only", AI_TUTOR_SYSTEM)
        self.assertIn(
            "EXCEPTION — true-zero learner (blank sheet)", AI_TUTOR_SYSTEM
        )
        self.assertIn(
            "gloss on every Spanish item until the", AI_TUTOR_SYSTEM
        )
        # Wall ban stays
        self.assertIn("walls stay banned", AI_TUTOR_SYSTEM.lower())


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
        # Asset resolution retargeted to the live AI path (assets_for_plan
        # deleted with the rules runtime — E4, option (b)).
        imgs, d2 = assets_for_ai_turn(
            is_open=True,
            blank_sheet=True,
            images_shown=set(),
            session_turns=0,
        )
        self.assertTrue(d2.want)
        self.assertTrue(imgs)
        self.assertEqual(imgs[0]["concept"], "hola")
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
        # Hand-built recast card (plan_turn died with the rules planner —
        # E4): a grammar repair with no concrete visual concept gets no image.
        card = PlanCard(
            phase="teach_form",
            move="recast_retry",
            models=["Yo **estoy** bien."],
            try_prompt="¿Cómo estás?",
            targets=PlanTargets(
                form_id="present_estar_person", concepts=[]
            ),
            reason="recast:yo_esta",
        )
        d = decide_teach_image(card, images_shown=set(), session_turns=2, turns_since_image=5)
        self.assertFalse(d.want)


class TestFallbackRelevanceGate(unittest.TestCase):
    """Incident 2026-07-28: the comprehension_repair fallback must never
    serve a concept absent from the current exchange (dice/digo grammar
    question got a «hola» image). No relevant concept → NO image."""

    def test_gate_blocks_concept_not_in_exchange(self):
        exchange = (
            "digo and dices.. what do these mean and how do I use them?"
        )
        imgs, d = assets_for_ai_turn(
            is_open=False,
            tutor_models=["**Hola** significa hello."],
            learner=exchange,
            require_relevant_to=exchange,
            images_shown=set(),
            session_turns=3,
            turns_since_image=3,
        )
        self.assertFalse(d.want)
        self.assertFalse(imgs)
        self.assertEqual(d.reason, "skip_irrelevant_concept")

    def test_gate_allows_concept_present_in_exchange(self):
        exchange = "what does hola mean?"
        imgs, d = assets_for_ai_turn(
            is_open=False,
            tutor_models=["**Hola** significa hello."],
            learner=exchange,
            require_relevant_to=exchange,
            images_shown=set(),
            session_turns=3,
            turns_since_image=3,
        )
        self.assertTrue(d.want)
        self.assertTrue(imgs)
        self.assertEqual(imgs[0]["concept"], "hola")

    def test_no_gate_when_not_required(self):
        # Non-repair callers pass require_relevant_to=None → behavior unchanged
        imgs, d = assets_for_ai_turn(
            is_open=False,
            tutor_models=["**Hola** significa hello."],
            learner="ok",
            images_shown=set(),
            session_turns=3,
            turns_since_image=3,
        )
        self.assertTrue(d.want)
        self.assertEqual(d.concept, "hola")

    def test_concept_in_text_surface_matching(self):
        self.assertTrue(concept_in_text("hola", 'what does "hola" mean?'))
        self.assertTrue(concept_in_text("hola", "is it hello or goodbye?"))
        self.assertTrue(concept_in_text("bote", "I saw a barco on the water"))
        self.assertFalse(concept_in_text("hola", "digo and dices.. help me"))
        # 'hi' inside 'think' must not match (boundary-safe)
        self.assertFalse(concept_in_text("hola", "I think so"))
        self.assertFalse(concept_in_text("hola", ""))
        self.assertFalse(concept_in_text(None, "hola"))


if __name__ == "__main__":
    unittest.main()
