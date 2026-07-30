"""Turn-engaged morphology card (incident 2026-07-28: card never updated).

The Morphology rail must update when the learner's turn engages a verb form
(meta question about dice/digo, "I am making?" aiming at hacer, a produced
form error) and must stay on its existing fallback otherwise. Code picks the
form; content stays A1 pack-aware (present tense, no untaught-tense dumps).

§1.1b settlement round (2026-07-29): the _turn_morph shared-dict stash is
DEAD — the card view is derived once per turn by
exchange_render.card_engagement and frozen into TurnRender; panel
integration reads sheet["_last_turn_render"]. Precedence tests live on the
projection now.
"""

import unittest

from tutor.can_dos import build_focus_panel
from tutor.character_sheet import default_sheet
from tutor.exchange_render import card_engagement
from tutor.turn_morph import (
    A1_VERB_MORPH,
    detect_intro_morph,
    detect_turn_morph,
)

# Verbatim learner turns from session 20260728-103617 (the incident).
DICE_TURN = (
    "digo and dices.. can I get a breakdown on what these mean and how to "
    'use them? I know its around "say" and dice I think is "you say".. '
    "I just need some help"
)
MAKING_TURN = (
    "yo no tengo cafe.  Yo hacer (I am making?) deysayunas.  "
    "Papas y savoyes (onions)"
)


class TestDetectTurnMorph(unittest.TestCase):
    def test_dice_meta_question_yields_decir(self):
        block = detect_turn_morph(DICE_TURN)
        self.assertIsNotNone(block)
        self.assertEqual(block["lemma"], "decir")
        self.assertEqual(block["engaged_by"], "meta_question")
        forms = [r["form"] for r in block["paradigm"]]
        self.assertIn("digo", forms)
        self.assertIn("dices", forms)
        # The asked-about persons are highlighted (digo=yo, dices=tú, dice=3sg)
        hi = {r["person"] for r in block["paradigm"] if r.get("highlight")}
        self.assertIn("yo", hi)
        self.assertIn("tú", hi)

    def test_i_am_making_yields_hacer_with_attempt(self):
        block = detect_turn_morph(MAKING_TURN)
        self.assertIsNotNone(block)
        self.assertEqual(block["lemma"], "hacer")
        self.assertEqual(block["engaged_by"], "form_error")
        self.assertIn("hacer", block["learner_attempt"].lower())
        # attempted form vs target surfaces in watch
        self.assertIn("hacer", block["watch"])
        self.assertIn("hago", block["watch"])
        hi = {r["person"] for r in block["paradigm"] if r.get("highlight")}
        self.assertEqual(hi, {"yo"})

    def test_english_how_say_maps_to_verb(self):
        block = detect_turn_morph("how do I say I am making breakfast?")
        self.assertIsNotNone(block)
        self.assertEqual(block["lemma"], "hacer")
        self.assertEqual(block["engaged_by"], "translation_request")
        block2 = detect_turn_morph("how do you say to go")
        self.assertIsNotNone(block2)
        self.assertEqual(block2["lemma"], "ir")

    def test_form_error_recast_turn_yields_estar(self):
        block = detect_turn_morph("yo está bien y el rio es bonito")
        self.assertIsNotNone(block)
        self.assertEqual(block["form_id"], "present_estar_person")
        self.assertEqual(block["engaged_by"], "error_pattern")
        self.assertTrue(block.get("learner_attempt"))

    def test_no_engagement_returns_none(self):
        # Correct production, plain chat, greetings: no morphology flash.
        self.assertIsNone(detect_turn_morph("Estoy bien, gracias. ¿Y tú?"))
        self.assertIsNone(detect_turn_morph("hola, me gusta el café"))
        self.assertIsNone(detect_turn_morph("That sounds good, thanks!"))
        self.assertIsNone(detect_turn_morph(""))

    def test_como_se_dice_frame_does_not_self_trigger_decir(self):
        # «cómo se dice boat» asks for "boat", not for decir morphology.
        self.assertIsNone(detect_turn_morph("¿Cómo se dice boat?"))

    def test_pack_aware_present_only_a1(self):
        allowed_persons = {"yo", "tú", "usted/él/ella", "nosotros", "—"}
        untaught = {
            "hice", "haré", "hacía", "dije", "diré", "decía", "fui",
            "iré", "iba", "comí", "comeré", "quise", "querré", "bebí",
            "hablé", "viví", "estuve", "estaré", "tuve", "tendré",
        }
        for lemma, block in A1_VERB_MORPH.items():
            rows = block["paradigm"]
            self.assertLessEqual(len(rows), 5, lemma)
            for r in rows:
                self.assertIn(r["person"], allowed_persons, lemma)
                self.assertNotIn(r["form"], untaught, lemma)


class TestPanelIntegration(unittest.TestCase):
    """§1.1b: the panel's LIVE card comes only from the settled TurnRender
    (sheet["_last_turn_render"]); agenda fallbacks render labeled up_next."""

    def _sheet_with_render(self, sheet, card):
        return {
            **sheet,
            "_last_turn_render": {"images": [], "card": card, "drops": []},
        }

    def test_settled_card_leads_panel_morphology(self):
        s = default_sheet()
        card = card_engagement(DICE_TURN, "")
        self.assertIsNotNone(card)
        panel = build_focus_panel(self._sheet_with_render(s, card))
        morph = panel["morphology"]
        self.assertTrue(morph)
        self.assertEqual(morph[0]["lemma"], "decir")
        self.assertTrue(morph[0].get("live"))
        self.assertTrue(str(morph[0]["id"]).startswith("turn:"))
        self.assertLessEqual(len(morph), 2)

    def test_settled_card_gets_learner_grammar_status(self):
        s = default_sheet()
        s["grammar"]["present_estar_person"]["status"] = "fragile"
        s["grammar"]["present_estar_person"]["confidence"] = 0.3
        card = card_engagement("yo está bien", "")
        panel = build_focus_panel(self._sheet_with_render(s, card))
        first = panel["morphology"][0]
        self.assertEqual(first.get("form_id"), "present_estar_person")
        self.assertEqual((first.get("learner") or {}).get("status"), "fragile")

    def test_no_engagement_panel_shows_only_labeled_up_next(self):
        # The me-llamo pin incident: with NO settled card, agenda fallbacks
        # may render only as up_next chrome — never live.
        s = default_sheet()
        panel = build_focus_panel(self._sheet_with_render(s, None))
        for b in panel["morphology"]:
            self.assertFalse(b.get("live"), b.get("id"))
            self.assertEqual(b.get("engaged_by"), "up_next")


class TestIntroMorph(unittest.TestCase):
    """Tutor-side introductions engage the card (review 2026-07-29:
    estar introduced via recast+model never reached the Morphology card —
    every detect path above reads only the learner's turn)."""

    def test_introduced_lemma_key_engages_card(self):
        block = detect_intro_morph(["estar"])
        self.assertIsNotNone(block)
        self.assertEqual(block["form_id"], "present_estar_person")
        self.assertEqual(block["engaged_by"], "introduction")
        hi = {r["person"] for r in block["paradigm"] if r.get("highlight")}
        self.assertEqual(hi, {"yo"})

    def test_phrase_key_engages_card_space_or_underscore(self):
        # first_seen keys arrive space-separated ("estoy bien"); asset keys
        # use underscores ("estoy_bien") — both must reach the same lemma.
        for key in ("estoy bien", "estoy_bien"):
            block = detect_intro_morph([key])
            self.assertIsNotNone(block, key)
            self.assertEqual(block["form_id"], "present_estar_person", key)
            self.assertIn("new this turn: estoy bien", block["watch"])
            hi = {r["person"] for r in block["paradigm"] if r.get("highlight")}
            self.assertEqual(hi, {"yo"}, key)

    def test_non_verb_and_ambiguous_keys_stay_silent(self):
        # buenos días has no verb; "esta"/"como" are the deliberately
        # excluded ambiguous tokens (better to miss than wrong card).
        self.assertIsNone(detect_intro_morph(["buenos días"]))
        self.assertIsNone(detect_intro_morph(["esta", "como"]))
        self.assertIsNone(detect_intro_morph([]))
        self.assertIsNone(detect_intro_morph([""]))

    def test_first_key_with_verb_wins(self):
        block = detect_intro_morph(["buenos días", "quiero café"])
        self.assertIsNotNone(block)
        self.assertEqual(block["lemma"], "querer")

    def test_projection_learner_engagement_beats_introduction(self):
        # card_engagement priority (§1.1b projection): learner engagement
        # wins even when introduction events are present.
        card = card_engagement(
            DICE_TURN, "", (("introduced", "estar"),)
        )
        self.assertEqual(card["lemma"], "decir")

    def test_projection_introduction_when_learner_silent(self):
        card = card_engagement(
            "gracias, hasta luego", "", (("first_seen", "estoy bien"),)
        )
        self.assertIsNotNone(card)
        self.assertEqual(card["form_id"], "present_estar_person")
        self.assertEqual(card["engaged_by"], "introduction")

    def test_projection_ignores_non_allowlisted_events(self):
        # Defense in depth: agenda kinds leaked into the events tuple are
        # ignored — the allowlist is enforced inside the projection.
        card = card_engagement(
            "gracias", "", (("mode", "estar"), ("due_elicit_offered", "ir"))
        )
        self.assertIsNone(card)

    def test_projection_no_engagement_is_none(self):
        self.assertIsNone(card_engagement("Estoy bien, gracias. ¿Y tú?", ""))


if __name__ == "__main__":
    unittest.main()
