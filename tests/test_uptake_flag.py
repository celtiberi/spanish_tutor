"""§2.1a content-uptake mechanism (BINDING, 2026-07-28) — shadow labels +
self-flag surface detection. No live API.

Router teardown 2026-08-03 (full-code-audit S4): the instruction path
(self_flag_uptake_block), its mode/reason gates and the ModeSessionState
budget are DELETED — the §2.1a self-flag survives as a pure OBSERVATION:
turn_pipeline.stage_uptake_flag emits the typed UPTAKE_FLAGGED event from
observe.detect_self_flagged_token; the uptake_flag_honored eval keeps
measuring whether the model honored it.
"""

import unittest

from tutor.observe import detect_self_flagged_token


class TestClassifierLabels(unittest.TestCase):
    def test_prompt_contains_new_labels(self):
        from tutor.signal_classifier import (
            INTENT_SIGNALS,
            OBSERVATIONAL_SIGNALS,
            _SYSTEM,
        )

        self.assertIn("content_offer", _SYSTEM)
        self.assertIn("self_flagged_form", _SYSTEM)
        # Definitions + incident few-shots (session 20260728-103617 turns
        # 6/9: the weather offer and the «uvia (rain)» self-flag).
        self.assertIn("uvia (rain)", _SYSTEM)
        self.assertIn("deysayunas", _SYSTEM)
        self.assertIn("content_offer", INTENT_SIGNALS)
        self.assertIn("self_flagged_form", INTENT_SIGNALS)
        self.assertEqual(
            OBSERVATIONAL_SIGNALS,
            frozenset({"content_offer", "self_flagged_form"}),
        )

    def test_observational_labels_stay_out_of_memory_signals(self):
        # §2.1a architecture clause: shadow only — the blocking classifier
        # path strips the observational labels before they reach memory /
        # observations (turn_pipeline.stage_classify_signals).
        import inspect

        import tutor.turn_pipeline as tp

        src = inspect.getsource(tp.stage_classify_signals)
        self.assertIn("OBSERVATIONAL_SIGNALS", src)


class TestSelfFlagDetection(unittest.TestCase):
    def test_gloss_guess_fires(self):
        # Incident turn 6: «No uvia (rain) hoy»
        self.assertEqual(
            detect_self_flagged_token(
                "estoy en mi casa.  Afruera (outside?) esta muy bien.  "
                "No uvia (rain) hoy"
            ),
            "afruera",  # first flagged token wins
        )
        self.assertEqual(
            detect_self_flagged_token("No uvia (rain) hoy"), "uvia"
        )

    def test_gloss_guess_with_question_mark(self):
        # Incident turn 9: «Yo hacer (I am making?) deysayunas»
        self.assertEqual(
            detect_self_flagged_token(
                "yo no tengo cafe.  Yo hacer (I am making?) deysayunas."
            ),
            "hacer",
        )

    def test_quoted_single_token_fires(self):
        self.assertEqual(detect_self_flagged_token("no sé si «uvia» está bien"), "uvia")
        self.assertEqual(detect_self_flagged_token('is "uvia" right?'), "uvia")
        self.assertEqual(detect_self_flagged_token("is 'uvia' right?"), "uvia")

    def test_plain_spanish_production_never_fires(self):
        self.assertIsNone(
            detect_self_flagged_token("buenas tardes. Yo busco huevos.")
        )
        self.assertIsNone(detect_self_flagged_token("estoy bien. Me llamo Patrick"))
        self.assertIsNone(detect_self_flagged_token(""))

    def test_multiword_quote_does_not_fire(self):
        # Multiword quotes are tutor-Spanish echoes → meta guard territory.
        self.assertIsNone(
            detect_self_flagged_token("what does «hasta luego amigo» mean?")
        )

    def test_english_contractions_do_not_fire(self):
        self.assertIsNone(
            detect_self_flagged_token("I don't know what's right here")
        )


class TestUptakeFlagObservation(unittest.TestCase):
    """stage_uptake_flag: pure observation — typed UPTAKE_FLAGGED event,
    no instruction, no budget (router teardown 2026-08-03)."""

    def _run(self, learner, *, is_open=False):
        from tutor.turn_events import TurnEventKind, TurnEventLog
        from tutor.turn_pipeline import TurnContext, stage_uptake_flag

        ev = TurnEventLog()
        ctx = TurnContext(learner=learner, is_open=is_open, ev=ev)
        stage_uptake_flag(None, ctx)
        return [e for e in ev.events if e.kind is TurnEventKind.UPTAKE_FLAGGED]

    def test_self_flag_emits_typed_event(self):
        evs = self._run("No uvia (rain) hoy")
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].key, "uvia")
        from tutor.turn_events import render

        self.assertEqual(render(evs[0]), "uptake_flagged:uvia")

    def test_plain_production_emits_nothing(self):
        self.assertEqual(self._run("estoy bien. Me llamo Patrick"), [])

    def test_open_turn_emits_nothing(self):
        self.assertEqual(self._run("No uvia (rain) hoy", is_open=True), [])

    def test_instruction_path_is_dead(self):
        # Absence pin: the instruction builder + its budget died with the
        # router; the observation path is the only survivor.
        import tutor.conv_session as conv_session

        self.assertFalse(hasattr(conv_session, "self_flag_uptake_block"))
        self.assertFalse(hasattr(conv_session, "SELF_FLAG_MODES"))
        self.assertFalse(hasattr(conv_session, "DUE_GUARD_REASONS"))


class TestUptakeFlagHonoredCheck(unittest.TestCase):
    """WARN-level eval (measurement first, per the closed review)."""

    def _result(self, notes, visible, parts=None):
        return {
            "turns": [{
                "visible": visible,
                "notes": notes,
                "parts": parts or {},
            }],
        }

    def test_warns_when_flag_ignored(self):
        from evals.conv_checks import uptake_flag_honored

        out = uptake_flag_honored(
            {}, self._result(
                ["uptake_flagged:uvia"], "¡Qué bien! ¿Y tu amigo Paul?",
            ),
        )
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("WARN"))
        self.assertIn("uvia", out[0])

    def test_clean_when_model_given(self):
        from evals.conv_checks import uptake_flag_honored

        out = uptake_flag_honored(
            {}, self._result(
                ["uptake_flagged:uvia"],
                "No llueve hoy.",
                parts={"model": "No llueve hoy."},
            ),
        )
        self.assertEqual(out, [])

    def test_recast_praise_warn_is_warn_only(self):
        from evals.conv_checks import recast_no_confirm_praise

        out = recast_no_confirm_praise(
            {}, self._result(
                [],
                "¡Sí, exacto! Te llamas Marisol.",
                parts={
                    "acknowledge": "¡Sí, exacto!",
                    "recast": "Te llamas Marisol.",
                },
            ),
        )
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("WARN"))
        # No recast part → silent (praise alone is not the defect)
        out2 = recast_no_confirm_praise(
            {}, self._result(
                [], "¡Perfecto!", parts={"acknowledge": "¡Perfecto!"},
            ),
        )
        self.assertEqual(out2, [])


if __name__ == "__main__":
    unittest.main()
