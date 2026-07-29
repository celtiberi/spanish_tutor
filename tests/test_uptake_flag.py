"""§2.1a content-uptake mechanism (BINDING, 2026-07-28) — shadow labels,
self-flag surface detection, instruction path, and the anti-starvation
budget. No live API.

Per docs/reviews-content-uptake-law.md condition (c): detection starts
shadow/instruction+eval — content_offer / self_flagged_form are
OBSERVATIONAL classifier labels that must NOT change select_mode routing,
and the regex path handles only the surface-visible self-flag shapes
(quoted single token, "(english)?" gloss-guess).
"""

import unittest

from tutor.character_sheet import default_sheet
from tutor.conv_session import self_flag_uptake_block
from tutor.modes import Mode, ModeSessionState, select_mode
from tutor.observe import detect_self_flagged_token


def _known_sheet() -> dict:
    s = default_sheet()
    s["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
    return s


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

    def test_observational_labels_do_not_change_routing(self):
        # §2.1a architecture clause: shadow only — the new labels riding the
        # signal set must leave select_mode's decision untouched.
        base = select_mode(
            _known_sheet(),
            learner="Estoy en mi casa hoy",
            observations={
                "blank_sheet": False, "signals": ["spanish_ok"],
            },
            mode_state=ModeSessionState(),
        )
        with_labels = select_mode(
            _known_sheet(),
            learner="Estoy en mi casa hoy",
            observations={
                "blank_sheet": False,
                "signals": [
                    "spanish_ok", "content_offer", "self_flagged_form",
                ],
            },
            mode_state=ModeSessionState(),
        )
        self.assertEqual(base.mode, with_labels.mode)
        self.assertEqual(base.reason, with_labels.reason)


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


class TestSelfFlagUptakeBlock(unittest.TestCase):
    def test_fires_on_conversation_turn_with_note(self):
        state = ModeSessionState()
        state.learner_turn_index = 5
        txt, token = self_flag_uptake_block(
            "No uvia (rain) hoy",
            mode="conversation",
            reason="default_conversation",
            mode_state=state,
        )
        self.assertIn("UPTAKE (§2.1a)", txt)
        self.assertIn("«uvia»", txt)
        self.assertIn("pack-legal", txt)
        # Phase 3 batch 2 push-down: the RAW token returns; the caller emits
        # the typed UPTAKE_FLAGGED event whose render is the legacy note.
        self.assertEqual(token, "uvia")
        from tutor.turn_events import TurnEventKind, render_note

        self.assertEqual(
            render_note(TurnEventKind.UPTAKE_FLAGGED, key=token),
            "uptake_flagged:uvia",
        )
        self.assertEqual(state.content_uptake_last_turn, 5)

    def test_budget_blocks_second_consecutive_offer(self):
        # §2.1a anti-starvation: ≤1 per 3 teaching turns, never consecutive.
        state = ModeSessionState()
        state.learner_turn_index = 5
        txt1, _ = self_flag_uptake_block(
            "No uvia (rain) hoy",
            mode="conversation",
            reason="default_conversation",
            mode_state=state,
        )
        self.assertTrue(txt1)
        state.learner_turn_index = 6  # next teaching turn
        txt2, note2 = self_flag_uptake_block(
            "Yo hacer (I am making?) deysayunas",
            mode="conversation",
            reason="default_conversation",
            mode_state=state,
        )
        self.assertEqual((txt2, note2), ("", ""))
        # Budget recovers after the 3-turn rate window.
        state.learner_turn_index = 8
        txt3, token3 = self_flag_uptake_block(
            "Yo hacer (I am making?) deysayunas",
            mode="conversation",
            reason="default_conversation",
            mode_state=state,
        )
        self.assertIn("«hacer»", txt3)
        self.assertEqual(token3, "hacer")

    def test_guard_turns_do_not_fire(self):
        # Help/topic/grammar guards already perform uptake; repair keeps its
        # single focus.
        state = ModeSessionState()
        for mode, reason in (
            ("conversation", "learner_help_request"),
            ("conversation", "learner_topic_request"),
            ("conversation", "grammar_question_inline"),
            ("comprehension_repair", "meta_comprehension_stay_on_topic"),
            ("form_focus", "error_streak:me_llamo_es"),
        ):
            txt, note = self_flag_uptake_block(
                'is "uvia" right?',
                mode=mode,
                reason=reason,
                mode_state=state,
            )
            self.assertEqual((txt, note), ("", ""), (mode, reason))

    def test_no_flag_no_note(self):
        state = ModeSessionState()
        txt, note = self_flag_uptake_block(
            "estoy bien. Me llamo Patrick",
            mode="conversation",
            reason="default_conversation",
            mode_state=state,
        )
        self.assertEqual((txt, note), ("", ""))
        self.assertEqual(state.content_uptake_last_turn, -999)

    def test_snapshot_carries_budget_field(self):
        state = ModeSessionState()
        state.learner_turn_index = 4
        state.note_content_uptake()
        snap = state.snapshot()
        self.assertEqual(snap["content_uptake_last_turn"], 4)


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
