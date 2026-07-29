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
        # Placement's hola image belongs to the true session-open turn only
        self.assertEqual(d.image_concept, "hola")

    def test_blank_open_requires_english_orientation(self):
        # Incident 2026-07-28: reset beginner got 100% Spanish on open.
        # PEDAGOGY P1 + §2.3: a true-zero open must carry English scaffold.
        d = select_mode(
            default_sheet(),
            is_open=True,
            observations={"blank_sheet": True, "signals": []},
        )
        self.assertEqual(d.reason, "blank_open_placement")
        instr = d.instructions
        self.assertIn("TRUE-ZERO OPENING", instr)
        self.assertIn("English welcome sentence", instr)
        self.assertIn("English gloss (≤6 words)", instr)
        self.assertIn("most 3 Spanish items", instr)
        self.assertIn("Try: Me llamo ___ — my name is ___", instr)
        # De-escalation is in the same instructions: zero state only
        self.assertIn("ANY Spanish", instr)
        self.assertIn("mostly-Spanish register", instr)
        # Wide ceiling (placement still probes) survives the rewrite
        self.assertIn("Wide-ceiling", instr)

    def test_known_open_has_no_english_orientation(self):
        # The zero-register text must not leak to known learners' opens.
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        d = select_mode(
            sheet,
            is_open=True,
            observations={"blank_sheet": False, "signals": []},
        )
        self.assertEqual(d.reason, "known_open_from_sheet")
        self.assertNotIn("TRUE-ZERO", d.instructions)
        self.assertNotIn("English welcome sentence", d.instructions)
        # Standard known-open register unchanged
        self.assertIn("Warm SIMPLE A1 Spanish only", d.instructions)

    def test_blank_nonopen_carries_zero_register_note(self):
        # Blank persists after the open until spanish_ok — the English
        # authorization rides every decision meanwhile (graded de-escalation).
        d = select_mode(
            default_sheet(),
            is_open=False,
            learner="what?",
            observations={"blank_sheet": True, "signals": ["english_only"]},
            mode_state=ModeSessionState(),
        )
        self.assertNotEqual(d.reason, "blank_open_placement")
        self.assertIn("TRUE-ZERO REGISTER", d.instructions)
        self.assertIn("English gloss", d.instructions)

    def test_blank_nonopen_spanish_ok_drops_zero_register(self):
        # First successful Spanish reverts to the standard register even if
        # the sheet has not yet accrued evidence.
        d = select_mode(
            default_sheet(),
            is_open=False,
            learner="hola, estoy bien",
            observations={"blank_sheet": True, "signals": ["spanish_ok"]},
            mode_state=ModeSessionState(),
        )
        self.assertNotIn("TRUE-ZERO REGISTER", d.instructions)

    def test_nonblank_never_carries_zero_register(self):
        d = select_mode(
            default_sheet(),
            is_open=False,
            learner="what?",
            observations={"blank_sheet": False, "signals": ["english_only"]},
            mode_state=ModeSessionState(),
        )
        self.assertNotIn("TRUE-ZERO REGISTER", d.instructions)

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
        # New contract (2026-07-28): streak breaks need session-recent errors
        state.note_error_hits(["estar_yo_estoy_vs_esta"])
        state.tick()
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


class TestGuardSixEscapeHatchClosed(unittest.TestCase):
    """2026-07-28 repetition forensics: guard 6 (concrete noun first-time)
    had a conf<0.25 escape hatch overriding the images_shown dedup — on a
    reset sheet (empty lexicon, conf 0.0 forever) every learner mention of
    «casa» re-fired new_noun:casa with byte-identical targets/instructions/
    image (session 20260728-120335 turns 4-5). Shown/covered membership is
    now authoritative."""

    def _sheet(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        return sheet

    def test_shown_concept_never_refires_even_at_zero_conf(self):
        # Reset learner: casa has NO lexicon evidence (conf 0.0). The old
        # hatch returned casa anyway; shown membership must now win.
        d = select_mode(
            self._sheet(),
            learner="mi casa es pequena",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            images_shown={"casa"},
            mode_state=ModeSessionState(),
        )
        self.assertNotEqual(d.reason, "new_noun:casa")
        self.assertNotEqual(d.image_concept, "casa")

    def test_first_mention_still_fires(self):
        # Control: with nothing shown, guard 6 still associates on first use.
        d = select_mode(
            self._sheet(),
            learner="mi casa es pequena",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            images_shown=set(),
            mode_state=ModeSessionState(),
        )
        self.assertEqual(d.reason, "new_noun:casa")
        self.assertEqual(d.image_concept, "casa")

    def test_covered_concepts_union_blocks_refire(self):
        # conv_session passes images_shown | covered_concepts: a guard-6
        # concept recorded as covered (no image/lexicon write needed) cannot
        # re-fire this session.
        from tutor.session_memory import SessionMemory

        mem = SessionMemory()
        mem.note_concept_covered("casa")
        d = select_mode(
            self._sheet(),
            learner="mi casa es pequena",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            images_shown=mem.images_shown | mem.covered_concepts,
            mode_state=ModeSessionState(),
        )
        self.assertNotEqual(d.reason, "new_noun:casa")


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


class TestFormFocusResolve(unittest.TestCase):
    def test_correct_use_suppresses_form_focus(self):
        """Correct production of the hot form must not hard-break on it."""
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está bien", resolved=False)
        d = select_mode(
            sheet,
            learner="Estoy bien.",
            observations={"blank_sheet": False, "signals": ["estoy", "spanish_ok"]},
            mode_state=ModeSessionState(),
        )
        self.assertNotEqual(d.mode, Mode.FORM_FOCUS)

    def test_form_focus_still_fires_without_resolve(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está", resolved=False)
        note_error_pattern(sheet, "estar_yo_estoy_vs_esta", "yo está bien", resolved=False)
        state = ModeSessionState()
        state.note_error_hits(["estar_yo_estoy_vs_esta"])  # session-recent
        state.tick()
        d = select_mode(
            sheet,
            learner="Todo bien, gracias.",
            observations={"blank_sheet": False, "signals": []},
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.FORM_FOCUS)


class TestComprehensionRepair(unittest.TestCase):
    def _memory(self):
        return {
            "last_tutor_try": "¿Cómo estás hoy?",
            "last_tutor_model": "Estoy bien.",
            "last_concepts": [],
        }

    def test_no_entiendo_triggers_repair_same_topic(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        d = select_mode(
            sheet,
            learner="no entiendo",
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
            session_memory=self._memory(),
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertTrue(d.hard_break)
        self.assertTrue(d.targets.get("require_same_topic"))
        self.assertTrue(d.targets.get("forbid_new_topic"))
        self.assertEqual(d.targets.get("last_try"), "¿Cómo estás hoy?")

    def test_repair_bypasses_hard_break_budget(self):
        """Repair must fire even right after another hard break."""
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        state = ModeSessionState()
        state.hard_breaks_this_session = 1
        state.turns_since_hard_break = 0
        d = select_mode(
            sheet,
            learner="no entiendo",
            observations={"blank_sheet": False, "signals": []},
            mode_state=state,
            session_memory=self._memory(),
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)

    def test_no_repair_without_prior_tutor_turn(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        d = select_mode(
            sheet,
            learner="no entiendo",
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
            session_memory={},
        )
        self.assertNotEqual(d.mode, Mode.COMPREHENSION_REPAIR)


class TestRepairImageRelevance(unittest.TestCase):
    """Incident 2026-07-28: a dice/digo grammar question got the previous
    turn's «hola» repair-target image. Images on repair/meta turns must be
    surface-relevant to the current exchange or absent entirely (r5)."""

    # Verbatim learner turn 3 from logs/sessions/20260728-103617-conversational-web
    INCIDENT_DICE_DIGO = (
        "digo and dices.. can I get a breakdown on what these mean and how "
        'to use them? I know its around "say" and dice I think is "you say".. '
        "I just need some help"
    )

    def _turn3_memory(self):
        return {
            "last_tutor_try": "Si digo «¡**Hola**!», ¿qué dices tú?",
            "last_tutor_model": (
                "**Hola** significa hello (sounds alike). ¡**Hola**, Patrick!"
            ),
            "last_concepts": ["hola"],
            "await_comprehension": True,
        }

    def _sheet(self):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.4}
        return sheet

    def test_meta_grammar_question_no_irrelevant_image_incident_20260728(self):
        """Regression anchor: the exact incident turn must attach NO image."""
        d = select_mode(
            self._sheet(),
            learner=self.INCIDENT_DICE_DIGO,
            observations={
                "blank_sheet": False,
                "signals": ["english_only", "meta_comprehension"],
            },
            images_shown=set(),
            mode_state=ModeSessionState(),
            session_memory=self._turn3_memory(),
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertIsNone(d.image_concept)

    def test_what_does_x_mean_uses_learner_relevance(self):
        """'what does digo mean?' is a meta question about digo — the stale
        hola repair target must not ride along."""
        d = select_mode(
            self._sheet(),
            learner="what does digo mean?",
            observations={"blank_sheet": False, "signals": ["english_only"]},
            images_shown=set(),
            mode_state=ModeSessionState(),
            session_memory=self._turn3_memory(),
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertIsNone(d.image_concept)

    def test_meta_question_about_concept_keeps_its_image(self):
        """Don't over-suppress: asking about «hola» itself keeps the image."""
        d = select_mode(
            self._sheet(),
            learner='is "hola" hello or goodbye? I forget',
            observations={
                "blank_sheet": False,
                "signals": ["english_only", "meta_comprehension"],
            },
            images_shown=set(),
            mode_state=ModeSessionState(),
            session_memory=self._turn3_memory(),
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertEqual(d.image_concept, "hola")

    def test_true_noncomprehension_keeps_repair_target_image(self):
        """«no entiendo» re-teaches the prior concept — dual-coding image stays."""
        d = select_mode(
            self._sheet(),
            learner="no entiendo",
            observations={"blank_sheet": False, "signals": []},
            images_shown=set(),
            mode_state=ModeSessionState(),
            session_memory=self._turn3_memory(),
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertEqual(d.image_concept, "hola")


class TestSceneHostRules(unittest.TestCase):
    """PHASE HOST rules (Proposal A micro-batch, 2026-07-29 —
    docs/reviews-architecture-refactor.md policy round, CHAR-BUG-005
    RESOLVED-BY-DELETION): guard-7's topic scene pick is suppressed on
    new_input/close activities (introduce owns new_input, close owns close
    per PEDAGOGY §6.4); topic-matched scene_goal stays reachable on
    task/free/retrieval; the prefer-unmodeled/needs-model fallback is
    deleted — no topic match, no scene capture."""

    def _sheet(self):
        s = default_sheet()
        s["skills"]["IP-01"].update(
            {"confidence": 0.6, "status": "known", "evidence": ["said hola"]}
        )
        return s

    def _decide(self, activity_hint, learner="Me gusta mucho el pan."):
        sheet = self._sheet()
        return select_mode(
            sheet,
            is_open=False,
            learner=learner,
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            mode_state=ModeSessionState(),
            open_scenes=open_scenes_for_sheet(sheet),
            activity_hint=activity_hint,
        )

    def test_scene_goal_reachable_on_task_free_retrieval(self):
        # KEEP-5: live-topic passive scene pursuit survives the deletion on
        # every activity that may host it (golden_due_turn's retrieval case
        # end-to-end; task/free/None here).
        for hint in ("task", "free", "retrieval", None):
            d = self._decide(hint)
            self.assertEqual(d.mode, Mode.CONVERSATION, hint)
            self.assertTrue(
                d.reason.startswith("scene_goal:"), (hint, d.reason)
            )

    def test_scene_pick_suppressed_on_new_input(self):
        # Rule 6: introduce owns new_input — the same topic match falls
        # through to default_conversation so the INTRODUCE block can fire.
        d = self._decide("new_input")
        self.assertEqual(d.reason, "default_conversation")
        self.assertIn("SESSION PHASE: NEW INPUT", d.instructions)

    def test_scene_pick_suppressed_on_close(self):
        # Rule 6: close owns close — fallthrough keeps the CLOSE prefix and
        # summary path reachable (the batch-4 stopped-note's lost
        # close_phase_offered must not recur).
        d = self._decide("close")
        self.assertEqual(d.reason, "default_conversation")
        self.assertIn("SESSION PHASE: CLOSE", d.instructions)

    def test_no_topic_match_no_scene_capture(self):
        # The deleted _scene_needs_model fallback used to force the FIRST
        # unmodeled scene onto any zero-score turn (fresh state = nothing
        # marked). Now a turn without a live topic match falls through.
        d = self._decide("free", learner="Sí, hablo con mi familia cada día.")
        self.assertEqual(d.reason, "default_conversation")


if __name__ == "__main__":
    unittest.main()
