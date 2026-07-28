"""Turn-engaged morphology card (incident 2026-07-28: card never updated).

The Morphology rail must update when the learner's turn engages a verb form
(meta question about dice/digo, "I am making?" aiming at hacer, a produced
form error) and must stay on its existing fallback otherwise. Code picks the
form; content stays A1 pack-aware (present tense, no untaught-tense dumps).
"""

import unittest

from tutor.can_dos import build_focus_panel
from tutor.character_sheet import default_sheet
from tutor.focus_enrich import enrich_focus_panel
from tutor.turn_morph import (
    A1_VERB_MORPH,
    detect_turn_morph,
    stash_turn_morph,
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
    def test_turn_block_leads_panel_morphology(self):
        s = default_sheet()
        md = {"mode": "conversation", "reason": "grammar_question_inline",
              "targets": {"answer_language_question": True}}
        stash_turn_morph(md, DICE_TURN)
        self.assertIn("_turn_morph", md)
        panel = build_focus_panel(s, mode_decision=md)
        morph = panel["morphology"]
        self.assertTrue(morph)
        self.assertEqual(morph[0]["lemma"], "decir")
        self.assertTrue(str(morph[0]["id"]).startswith("turn:"))
        self.assertLessEqual(len(morph), 2)

    def test_turn_block_gets_learner_grammar_status(self):
        s = default_sheet()
        s["grammar"]["present_estar_person"]["status"] = "fragile"
        s["grammar"]["present_estar_person"]["confidence"] = 0.3
        md = {"mode": "cf_recast", "reason": "err", "targets": {}}
        stash_turn_morph(md, "yo está bien")
        panel = build_focus_panel(s, mode_decision=md)
        first = panel["morphology"][0]
        self.assertEqual(first.get("form_id"), "present_estar_person")
        self.assertEqual((first.get("learner") or {}).get("status"), "fragile")

    def test_no_engagement_leaves_panel_unchanged(self):
        s = default_sheet()
        md = {"mode": "conversation", "reason": "default", "targets": {}}
        baseline = build_focus_panel(s, mode_decision=dict(md))["morphology"]
        stash_turn_morph(md, "Estoy bien, gracias. ¿Y tú?")
        self.assertNotIn("_turn_morph", md)
        after = build_focus_panel(s, mode_decision=md)["morphology"]
        self.assertEqual(
            [b.get("id") for b in after], [b.get("id") for b in baseline]
        )

    def test_stale_block_cleared_on_next_non_engaging_turn(self):
        md = {"mode": "conversation", "reason": "default", "targets": {}}
        stash_turn_morph(md, DICE_TURN)
        self.assertIn("_turn_morph", md)
        stash_turn_morph(md, "gracias, hasta luego")
        self.assertNotIn("_turn_morph", md)

    def test_enrich_static_path_stashes_and_shows_turn_block(self):
        s = default_sheet()
        md = {"mode": "conversation", "reason": "grammar_question_inline",
              "targets": {}}
        sheet = {**s, "_last_mode_decision": md}
        panel, meta = enrich_focus_panel(
            sheet, learner=MAKING_TURN, tutor_reply="", force_static=True,
        )
        self.assertEqual(meta["source"], "static")
        self.assertIn("_turn_morph", md)  # persists for sheet_public repaints
        self.assertEqual(panel["morphology"][0]["lemma"], "hacer")


if __name__ == "__main__":
    unittest.main()
