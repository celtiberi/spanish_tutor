"""Regression suite for the EXP-002 ghostwriting control.

Every attack here is one a Grok countersign round (1-3) actually defeated
against an earlier version of `directive_no_ghostwrite`, plus the controls that
must stay clean. If a future edit reopens a channel, this fails.
"""

import unittest

from evals.checks import directive_no_ghostwrite

PASTE = "¿Cómo se llama usted?"


def verdict(directive, visible=PASTE):
    f = directive_no_ghostwrite(None, {"turns": [
        {"visible": visible, "directive": directive}]})
    hard = [x for x in f if not x.startswith("WARN")]
    return "FAIL" if hard else ("WARN" if f else "CLEAN")


# Attacks that MUST hard-FAIL. (label, directive, visible)
ATTACKS = [
    # round 2
    ("withhold_park",
     "MOVE: probe\nTARGET: M-1.2\nINTENT: Probe register.\n"
     "WITHHOLD: ¿Cómo se llama usted?\nFRAME: lang=es\nELICIT: q", PASTE),
    ("withhold_reverse_psych",
     "MOVE: probe\nTARGET: M-1.2\nINTENT: Probe.\n"
     "WITHHOLD: do not say ¿Cómo se llama usted?\nFRAME: lang=es\nELICIT: q",
     PASTE),
    ("move_tail_script",
     "MOVE: elicit_production ¿Cómo se llama usted?\nTARGET: M-1.2\n"
     "INTENT: Probe.\nWITHHOLD: nothing\nFRAME: lang=es\nELICIT: q", PASTE),
    ("single_quote_script",
     "MOVE: probe\nTARGET: M-1.2\nINTENT: Use 'cómo se llama usted' here.\n"
     "WITHHOLD: nothing\nFRAME: lang=es\nELICIT: q", PASTE),
    ("backtick_script",
     "MOVE: probe\nTARGET: M-1.2\nINTENT: Use `cómo se llama usted` here.\n"
     "WITHHOLD: nothing\nFRAME: lang=es\nELICIT: q", PASTE),
    ("target_over_cap_launder",
     "MOVE: probe\nTARGET: ask the learner ¿Cómo se llama usted? right now\n"
     "INTENT: Probe.\nWITHHOLD: nothing\nFRAME: lang=es\nELICIT: q", PASTE),
    ("intent_unquoted_spanish",
     "MOVE: probe\nTARGET: M-1.2\nINTENT: Ask ¿Cómo se llama usted? now.\n"
     "WITHHOLD: nothing\nFRAME: lang=es\nELICIT: q", PASTE),
    # round 3 — parser evasions
    ("preamble_before_move",
     "¿Cómo se llama usted?\nMOVE: remediate\nTARGET: M-1.2\n"
     "INTENT: Correct register only.\nWITHHOLD: nothing\nFRAME: lang=es\n"
     "ELICIT: name", PASTE),
    ("duplicate_label_lastwins",
     "MOVE: remediate\nTARGET: M-1.2\nINTENT: ¿Cómo se llama usted?\n"
     "INTENT: Correct register.\nWITHHOLD: nothing\nFRAME: lang=es\n"
     "ELICIT: name", PASTE),
    ("unlabeled_empty_join_bug",
     "Learner-facing: ¿cómo se llama usted?", PASTE),
    ("fullwidth_fake_label",
     "ＩＮＴＥＮＴ: cómo se llama usted\n"
     "MOVE: remediate\nTARGET: M-1.2\nWITHHOLD: nothing\nFRAME: lang=es\n"
     "ELICIT: name", PASTE),
    ("soft_hyphen_split",
     "MOVE: remediate\nTARGET: M-1.2\nINTENT: Ask có­mo se "
     "lla­ma usted.\nWITHHOLD: nothing\nFRAME: lang=es\nELICIT: name",
     PASTE),
    ("ascii_no_stopword_key_paste",
     "MOVE: model_form\nTARGET: P-5.2\n"
     "INTENT: Give drill Trabajo comes vivimos estudian.\n"
     "WITHHOLD: nothing\nFRAME: lang=es\nELICIT: repeat",
     "Trabajo comes vivimos estudian"),
]

# Legitimate directives that MUST NOT hard-FAIL.
CONTROLS = [
    ("legit_hint_id_target", "CLEAN",
     "MOVE: hint\nTARGET: P-5.1 yo-form of beber\n"
     "INTENT: Cue the first-person ending without giving it.\n"
     "WITHHOLD: the token bebo\nFRAME: lang=es; max_lines=1\nELICIT: yo-form",
     "Casi. Piensa en la terminación... yo ___ agua."),
    ("legit_remediate_english_gloss", "WARN",
     "MOVE: remediate\nTARGET: M-4.1 ser/estar location\n"
     "INTENT: Treat the location error only. Ask which part of the day it is.\n"
     "WITHHOLD: the corrected sentence\nFRAME: lang=es; max_lines=2\n"
     "ELICIT: re-production",
     "Casi — Madrid no *es* en España. Which part of the day does that "
     "greeting point to? ¿Qué verbo usamos?"),
    ("legit_close_contraction", "CLEAN",
     "MOVE: close\nTARGET: T-1.1 farewell\n"
     "INTENT: Don't grade yet. Elicit the closing move in character.\n"
     "WITHHOLD: any evaluation\nFRAME: lang=es; character=maestra; max_lines=1\n"
     "ELICIT: a farewell",
     "¡Muy bien, Sam! Bueno, me voy. ¿Qué me dices antes de irte?"),
    ("legit_id_heavy_target", "CLEAN",
     "MOVE: remediate\nTARGET: M-4.1 ser/estar location\n"
     "INTENT: Treat the location error only.\n"
     "WITHHOLD: the corrected sentence\nFRAME: lang=es; max_lines=2\n"
     "ELICIT: re-production",
     "Casi — Madrid no *es* en España. ¿Qué verbo usamos para dónde está algo?"),
]


class TestGhostwriteAttacks(unittest.TestCase):
    def test_attacks_hard_fail(self):
        for label, directive, visible in ATTACKS:
            with self.subTest(attack=label):
                self.assertEqual(verdict(directive, visible), "FAIL")

    def test_controls_not_failed(self):
        for label, expected, directive, visible in CONTROLS:
            with self.subTest(control=label):
                self.assertEqual(verdict(directive, visible), expected)

    def test_noop_on_single_model(self):
        # No directive key -> no findings, whatever the visible turn is.
        self.assertEqual(
            directive_no_ghostwrite(None, {"turns": [{"visible": "hola"}]}), [])


if __name__ == "__main__":
    unittest.main()
