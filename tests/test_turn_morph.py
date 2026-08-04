"""Morphology: model-authored <morph> extraction + the frames wire.

2026-08-03 (USER: the card "changes or gets updated along with the
response like grading"): the code-detection card (detect_turn_morph /
detect_intro_morph / A1_VERB_MORPH / card_engagement) is DELETED; the
teacher emits the card. lemma_engaged_by_text survives as the
frames_seen conjugated-surface matcher.
"""

import unittest

from tutor.turn_morph import extract_morph, lemma_engaged_by_text

BODY = (
    'reply text <morph title="trabajar — to work" note="yo has no -s">\n'
    "trabajo | yo | I work\n"
    "*trabajas | tú | you work\n"
    "trabaja | usted/él/ella | works\n"
    "</morph> more"
)


class TestExtractMorph(unittest.TestCase):
    def test_harvest_and_strip(self):
        card, cleaned = extract_morph(BODY)
        self.assertEqual(card["label"], "trabajar — to work")
        self.assertEqual(card["note"], "yo has no -s")
        self.assertEqual(len(card["paradigm"]), 3)
        self.assertTrue(card["live"])
        self.assertEqual(card["source"], "model")
        self.assertNotIn("<morph", cleaned)
        self.assertIn("reply text", cleaned)
        self.assertIn("more", cleaned)

    def test_highlight_star(self):
        card, _ = extract_morph(BODY)
        flags = [r["highlight"] for r in card["paradigm"]]
        self.assertEqual(flags, [False, True, False])
        self.assertEqual(card["paradigm"][1]["form"], "trabajas")

    def test_no_tag_is_noop(self):
        card, cleaned = extract_morph("plain reply")
        self.assertIsNone(card)
        self.assertEqual(cleaned, "plain reply")

    def test_empty_block_strips_but_no_card(self):
        card, cleaned = extract_morph("a <morph title=\"x\">\n\n</morph> b")
        self.assertIsNone(card)
        self.assertNotIn("<morph", cleaned)

    def test_partial_rows_tolerated(self):
        card, _ = extract_morph("<morph>\nvivo | yo\nvive\n</morph>x")
        self.assertEqual(card["paradigm"][0]["gloss"], "")
        # a line without | is skipped, not crashed on
        self.assertEqual(len(card["paradigm"]), 1)

    def test_detection_era_stays_deleted(self):
        import tutor.turn_morph as tm

        for gone in ("detect_turn_morph", "detect_intro_morph",
                     "A1_VERB_MORPH", "LEMMA_TO_FORM_ID"):
            self.assertFalse(hasattr(tm, gone), gone)


class TestLemmaEngaged(unittest.TestCase):
    """The frames_seen wire (encounter-variety round, 2026-07-29)."""

    def test_verbatim_phrase(self):
        self.assertTrue(lemma_engaged_by_text("di hola por favor", "hola"))

    def test_conjugated_surface_hits_lemma(self):
        self.assertTrue(lemma_engaged_by_text("¿Cómo estás hoy?", "estar"))

    def test_ambiguous_token_never_overcredits(self):
        # "es" collides with English/Spanish function words — deliberately
        # absent from the token index (better to miss than over-credit).
        self.assertFalse(lemma_engaged_by_text("this es a test", "estar"))


if __name__ == "__main__":
    unittest.main()
