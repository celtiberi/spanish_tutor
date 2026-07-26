"""select_mode + scenes (no live API)."""

import unittest

from tutor.character_sheet import default_sheet, note_error_pattern
from tutor.modes import Mode, ModeSessionState, select_mode
from tutor.scenes import (
    evaluate_exit_predicate,
    load_scenes,
    open_scenes_for_sheet,
)


class TestSelectMode(unittest.TestCase):
    def test_placement_on_blank_open(self):
        d = select_mode(default_sheet(), is_open=True, observations={"blank_sheet": True, "signals": []})
        self.assertEqual(d.mode, Mode.PLACEMENT)
        self.assertTrue(d.hard_break)

    def test_bote_triggers_association_image(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        d = select_mode(
            sheet,
            learner="estoy en mi bote",
            observations={"blank_sheet": False, "signals": ["estoy", "topic_vocab"]},
            images_shown=set(),
            mode_state=ModeSessionState(),
        )
        self.assertEqual(d.image_concept, "bote")
        self.assertIn(d.mode, (Mode.ASSOCIATION, Mode.CONVERSATION))

    def test_gender_error_recast(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        d = select_mode(
            sheet,
            learner="Me gusta la edificios",
            observations={"blank_sheet": False, "signals": []},
            images_shown=set(),
            mode_state=ModeSessionState(),
        )
        self.assertEqual(d.mode, Mode.CF_RECAST)
        self.assertEqual(d.targets.get("error_pattern"), "gender_number_article")

    def test_esta_calor_recast_not_english_stuck(self):
        """Broken Spanish weather must recast to *hace calor*, not association."""
        from tutor.observe import probe_signals
        from tutor.character_sheet import detect_error_pattern_hits

        utt = "esta un poco calor hoy en rio dulce"
        sig = probe_signals(utt)
        self.assertNotIn("english_only", sig)
        self.assertIn("spanish_ok", sig)
        hits = detect_error_pattern_hits(utt)
        self.assertTrue(any(h[0] == "weather_hace" for h in hits), hits)

        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        state = ModeSessionState()
        state.english_only_streak = 5  # even if streak is high, form error wins
        d = select_mode(
            sheet,
            learner=utt,
            observations={"blank_sheet": False, "signals": sorted(sig)},
            images_shown=set(),
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.CF_RECAST)
        self.assertEqual(d.targets.get("error_pattern"), "weather_hace")
        self.assertTrue(d.targets.get("require_recast_tag"))

    def test_meta_comprehension_stays_on_same_try(self):
        """'What does that mean?' must re-ask same idea, not a new topic."""
        from tutor.observe import probe_signals

        utt = (
            '"Qué gusto saludarte de nuevo!" - I think this is.. saludarte is like '
            'a greeting? I dont know what you are saying. '
            '"Cómo van las cosas hoy por Río Dulce" - what things today for rio dulce?'
        )
        sig = probe_signals(utt)
        self.assertIn("meta_comprehension", sig)

        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        mem = {
            "last_tutor_try": "¿Cómo van las cosas hoy por Río Dulce?",
            "last_tutor_model": "¡Qué gusto saludarte de nuevo!",
            "last_concepts": ["rio"],
            "await_comprehension": False,
        }
        d = select_mode(
            sheet,
            learner=utt,
            observations={"blank_sheet": False, "signals": sorted(sig)},
            images_shown=set(),
            mode_state=ModeSessionState(),
            session_memory=mem,
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertTrue(d.targets.get("forbid_new_topic"))
        self.assertEqual(d.image_concept, "rio")
        # simplified rephrase of same wellbeing intent
        self.assertIn("estás", (d.targets.get("rephrase_try") or "").lower())


    def test_default_conversation(self):
        sheet = default_sheet()
        # give some evidence so not blank placement mid-session
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        d = select_mode(
            sheet,
            is_open=False,
            learner="Hola",
            observations={"blank_sheet": False, "signals": ["greet", "spanish_ok"]},
        )
        self.assertEqual(d.mode, Mode.CONVERSATION)

    def test_form_focus_on_error_streak(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.3}
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está bien", resolved=False)
        state = ModeSessionState()
        state.turns_since_hard_break = 5
        d = select_mode(
            sheet,
            learner="todo bien",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.FORM_FOCUS)
        self.assertTrue(d.hard_break)
        self.assertEqual(d.targets.get("error_pattern"), "estar_yo_estoy_vs_esta")

    def test_form_focus_cooldown_blocks(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.3}
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
        state = ModeSessionState()
        state.turns_since_hard_break = 5
        state.set_cooldown("estar_yo_estoy_vs_esta", 3)
        d = select_mode(
            sheet,
            learner="ok",
            observations={"blank_sheet": False, "signals": []},
            mode_state=state,
        )
        self.assertNotEqual(d.mode, Mode.FORM_FOCUS)

    def test_single_error_recast(self):
        sheet = default_sheet()
        sheet["skills"]["IP-04"] = {"status": "emerging", "confidence": 0.3}
        d = select_mode(
            sheet,
            learner="Yo está bien",
            observations={"blank_sheet": False, "signals": ["estoy"]},
            mode_state=ModeSessionState(),
        )
        self.assertEqual(d.mode, Mode.CF_RECAST)
        self.assertFalse(d.hard_break)

    def test_hard_break_budget(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.3}
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "a", resolved=False)
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "b", resolved=False)
        state = ModeSessionState()
        state.note_hard_break(Mode.ASSOCIATION)  # turns_since = 0
        d = select_mode(
            sheet,
            learner="hi",
            observations={"blank_sheet": False, "signals": []},
            mode_state=state,
        )
        self.assertNotEqual(d.mode, Mode.FORM_FOCUS)

    def test_english_streak_association(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.3}
        state = ModeSessionState()
        state.english_only_streak = 2
        state.turns_since_hard_break = 5
        d = select_mode(
            sheet,
            learner="I don't understand anything",
            observations={"blank_sheet": False, "signals": ["english_only"]},
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.ASSOCIATION)
        self.assertTrue(d.hard_break)

    def test_boredom_never_drill(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.3}
        sheet["affect"] = {"boredom_risk": "high", "energy": "frustrated_or_bored"}
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "a", resolved=False)
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "b", resolved=False)
        state = ModeSessionState()
        state.turns_since_hard_break = 5
        d = select_mode(
            sheet,
            learner="this is boring",
            observations={"blank_sheet": False, "signals": []},
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.CONVERSATION)
        self.assertEqual(d.reason, "boredom_new_topic")


class TestScenes(unittest.TestCase):
    def test_load_boat_scenes(self):
        scenes = load_scenes()
        ids = {s["id"] for s in scenes}
        self.assertIn("boat_meet_captain", ids)
        self.assertIn("boat_where_boat", ids)
        self.assertIn("boat_likes", ids)

    def test_open_scenes_on_blank(self):
        open_s = open_scenes_for_sheet(default_sheet())
        self.assertTrue(len(open_s) >= 1)

    def test_exit_predicate_skill(self):
        sheet = default_sheet()
        self.assertFalse(evaluate_exit_predicate(sheet, "skill:IP-06:min_conf=0.35"))
        sheet["skills"]["IP-06"] = {"status": "emerging", "confidence": 0.5}
        self.assertTrue(evaluate_exit_predicate(sheet, "skill:IP-06:min_conf=0.35"))


if __name__ == "__main__":
    unittest.main()
