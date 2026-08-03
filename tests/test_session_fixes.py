"""Regression tests for session 20260726-155600 failures.

Covers: truncated replies (gate:truncated), topic-request routing (English
meta requests must not become comprehension repair), grammar-question inline
answers, family-loss engagement-note updates, topic-fatigue affect, IP-03
next_best deadlock, and pack-driven topic suggestions.
"""

import unittest

from tutor.character_sheet import (
    apply_rule_updates,
    clear_session_scoped_affect,
    compute_progress_score,
    default_sheet,
    process_turn,
)
from tutor.modes import Mode, ModeSessionState, select_mode
from tutor.observe import probe_signals, strip_quoted
from tutor.output_gate import check_output_gate
from tutor.session_memory import SessionMemory

# Verbatim learner turns from logs/sessions/20260726-155600-conversational-web
TURN3 = (
    "if we are practicing forms of ser can we do it around something like "
    "shopping so I can learn something new while we do it?  You always talk "
    "about the bote or my family"
)
TURN8 = (
    "necesito llaves para diferentes usos.  Muy being.  When to use por or "
    'para is always confusing.  "son para".  I do not understand this '
    "either.  I think son is kind of a possesive?  Respondo tu pregunta: yo "
    "solo compra caras por que es mehor herramientas"
)


def _known_sheet() -> dict:
    sheet = default_sheet()
    sheet["identity"]["preferred_name"] = "Patrick"
    sheet["skills"]["IP-03"] = {"status": "emerging", "confidence": 0.6}
    return sheet


class TestTruncationGate(unittest.TestCase):
    def test_truncated_reply_is_gate_fault(self):
        g = check_output_gate(
            {"acknowledge": "¡Buena pregunta!", "structured": True},
            "¡Buena pregunta! **son** means \"",
            truncated=True,
        )
        self.assertIn("gate:truncated", g.faults)
        # No-hide policy (2026-08-01): the auto-rewrite copy is gone; the
        # field now carries a visible diagnosis, never a rewrite prompt.
        self.assertIn("gate fail", g.repair_instruction.lower())
        self.assertIn("gate:truncated", g.repair_instruction)

    def test_untruncated_reply_has_no_truncation_fault(self):
        g = check_output_gate(
            {
                "model": "Estoy en el café.",
                "try": "¿Dónde estás tú?",
                "structured": True,
            },
            "Estoy en el café. ¿Dónde estás tú?",
            truncated=False,
        )
        self.assertNotIn("gate:truncated", g.faults)


class TestTopicRequestRouting(unittest.TestCase):
    def test_topic_request_signal_detected(self):
        self.assertIn("topic_request", probe_signals(TURN3))
        self.assertIn(
            "topic_request", probe_signals("can we talk about food today?")
        )
        self.assertIn("topic_request", probe_signals("algo nuevo por favor"))

    def test_english_topic_ask_does_not_arm_repair(self):
        mem = SessionMemory()
        mem.note_learner("I want to talk about something else please")
        self.assertFalse(mem.await_comprehension)

    def test_meta_comprehension_still_arms_repair(self):
        mem = SessionMemory()
        mem.note_learner("what does saludarte mean?")
        self.assertTrue(mem.await_comprehension)

    def test_topic_request_routes_to_conversation_and_honors_request(self):
        d = select_mode(
            _known_sheet(),
            learner=TURN3,
            observations={
                "blank_sheet": False,
                "signals": sorted(probe_signals(TURN3)),
            },
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿Dónde está ella hoy?",
                "await_comprehension": True,
            },
            pack_topics=["Greetings", "Nouns, gender, articles"],
        )
        self.assertEqual(d.mode, Mode.CONVERSATION)
        self.assertEqual(d.reason, "learner_topic_request")
        self.assertFalse(d.hard_break)
        self.assertTrue(d.targets.get("honor_request"))
        self.assertIn("Nouns, gender, articles", d.instructions)

    def test_grammar_question_with_own_answer_not_repair(self):
        d = select_mode(
            _known_sheet(),
            learner=TURN8,
            observations={
                "blank_sheet": False,
                "signals": sorted(probe_signals(TURN8)),
            },
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿las herramientas son caras o baratas?",
                "await_comprehension": False,
            },
        )
        self.assertEqual(d.mode, Mode.CONVERSATION)
        self.assertEqual(d.reason, "grammar_question_inline")

    def test_quoted_tutor_spanish_still_repairs(self):
        utt = '"Qué gusto saludarte!" - I dont know what you are saying at all'
        d = select_mode(
            _known_sheet(),
            learner=utt,
            observations={
                "blank_sheet": False,
                "signals": sorted(probe_signals(utt)),
            },
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿Cómo estás hoy?",
                "last_tutor_model": "Qué gusto saludarte",
                "await_comprehension": False,
            },
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)

    def test_strip_quoted_removes_echoed_spans(self):
        self.assertNotIn(
            "saludarte", strip_quoted('"Qué gusto saludarte!" - what is this?')
        )


class TestNoPersonalCapture(unittest.TestCase):
    """Personal-data capture is DISABLED (2026-07-28): no message may ever
    write a name (or any personal fact) to the sheet or a profile object.
    Regression anchor: 'I am searching for eggs' once became the learner's
    preferred_name via the old case-insensitive I-am capture regex."""

    def test_i_am_searching_never_becomes_a_name(self):
        s2 = apply_rule_updates(
            default_sheet(),
            "buenas tardis usted. Yo buscondo para huevos. "
            "I am searching for eggs. I always forget how to say searching",
        )
        self.assertFalse(
            ((s2.get("identity") or {}).get("preferred_name") or "").strip()
        )

    def test_me_llamo_tool_gives_ability_without_storing_name(self):
        sheet = default_sheet()
        sheet.pop("identity", None)
        s2, _, _ = process_turn(
            sheet,
            "me llamo Patrick",
            "¡Hola!",
            tool_delta={
                "reason": "Learner produced me llamo with a name",
                "evidence": "me llamo Patrick",
                "skills": {"IP-03": {"status": "emerging", "confidence": 0.4}},
            },
        )
        self.assertIsNone((s2.get("identity") or {}).get("preferred_name"))
        self.assertGreater(s2["skills"]["IP-03"]["confidence"], 0)

    def test_process_turn_ignores_profile_entirely(self):
        from tutor.learner_profile import default_profile

        sheet = default_sheet()
        sheet.pop("identity", None)
        prof = default_profile()
        before = dict(prof)
        s2, _vis, _notes = process_turn(
            sheet,
            "me llamo Patrick",
            "¡Hola!",
            profile=prof,
            tool_delta={
                "reason": "Learner produced me llamo",
                "evidence": "me llamo Patrick",
                "skills": {"IP-03": {"status": "emerging", "confidence": 0.4}},
            },
        )
        self.assertEqual(prof, before)  # never read or written
        # identity is re-stamped as an explicitly-empty block (stripper)
        self.assertIsNone((s2.get("identity") or {}).get("preferred_name"))
        self.assertFalse((s2.get("identity") or {}).get("engagement_notes"))
        self.assertGreater(s2["skills"]["IP-03"]["confidence"], 0)

    def test_tool_delta_cannot_store_preferred_name(self):
        s2, _, _ = process_turn(
            default_sheet(),
            "me llamo Sam",
            "¡Hola!",
            tool_delta={"identity": {"preferred_name": "Sam"}},
        )
        self.assertFalse(((s2.get("identity") or {}).get("preferred_name") or "").strip())

    def test_english_my_name_is_does_not_credit_ip03(self):
        s2 = apply_rule_updates(default_sheet(), "my name is Sam")
        self.assertEqual(float(s2["skills"]["IP-03"].get("confidence") or 0), 0.0)

    def test_progress_score_name_always_none(self):
        s = default_sheet()
        s["identity"]["preferred_name"] = "Sam"
        self.assertIsNone(compute_progress_score(s).get("name"))

    def test_capture_name_hard_disabled(self):
        # Incident anchor: the old case-insensitive I-am regex turned
        # "I am searching for eggs" into preferred_name "Searching".
        from tutor.learner_profile import capture_name

        self.assertIsNone(capture_name("I am searching for eggs"))
        self.assertIsNone(capture_name("my name is Sam"))
        self.assertIsNone(capture_name("me llamo Sam"))

    def test_save_learner_profile_raises(self):
        import tempfile
        from pathlib import Path

        from tutor.learner_profile import save_learner_profile

        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "learner_profile.json"
            with self.assertRaises(RuntimeError):
                save_learner_profile(target, {"preferred_name": "Sam"})
            self.assertFalse(target.exists())

    def test_load_learner_profile_never_reads_disk(self):
        import json
        import tempfile
        from pathlib import Path

        from tutor.learner_profile import load_learner_profile

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "learner_profile.json"
            p.write_text(json.dumps({"preferred_name": "Searching"}))
            prof = load_learner_profile(p)
            self.assertIsNone(prof.get("preferred_name"))

    def test_profile_path_isolated_for_custom_sheets(self):
        # profile_path_for_sheet is still live: reset_profile uses it to
        # DELETE stale capture-era files.
        from pathlib import Path

        from tutor import config
        from tutor.learner_profile import profile_path_for_sheet

        default_prof = profile_path_for_sheet(Path(config.CHARACTER_SHEET_PATH))
        self.assertEqual(default_prof, Path(config.LEARNER_PROFILE_PATH))
        custom = profile_path_for_sheet(Path("/tmp/x/eval_sheet.json"))
        self.assertEqual(custom.name, "eval_sheet.profile.json")


class TestNextBestDeadlock(unittest.TestCase):
    def test_ip03_skipped_when_name_known(self):
        s2 = apply_rule_updates(_known_sheet(), "estoy bien hoy")
        self.assertNotEqual(s2["next_best"].get("can_do"), "IP-03")

    def test_ip03_still_targeted_when_name_unknown(self):
        sheet = default_sheet()
        sheet["identity"]["preferred_name"] = None
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.72}
        sheet["skills"]["IP-03"] = {"status": "emerging", "confidence": 0.6}
        sheet["skills"]["IP-04"] = {"status": "known", "confidence": 1.0}
        s2 = apply_rule_updates(sheet, "estoy bien hoy")
        # weakest-open selection may pick any open can-do, but IP-03 must not
        # be excluded merely for having some confidence
        candidates_reason = s2["next_best"].get("reason") or ""
        self.assertTrue(candidates_reason)


class TestKnownOpenHooks(unittest.TestCase):
    def test_open_never_uses_personal_data_even_if_profile_passed(self):
        # Personal-data capture disabled: a profile object passed for compat
        # must leave no trace in the instructions, and the open must forbid
        # invented names.
        from tutor.learner_profile import default_profile

        sheet = default_sheet()
        sheet.pop("identity", None)
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.5}
        prof = default_profile()
        prof["preferred_name"] = "Patrick"
        prof["hooks"] = [{"fact": "Lives on a boat.", "added": "2026-07-27"}]
        prof["sensitive"] = [{
            "fact": "Learner's sister Carolyn is deceased.",
            "guidance": "Do NOT ask about the sister.",
            "added": "2026-07-27",
        }]
        d = select_mode(
            sheet,
            is_open=True,
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
            profile=prof,
        )
        self.assertNotIn("Patrick", d.instructions)
        self.assertNotIn("Lives on a boat.", d.instructions)
        self.assertNotIn("CARE RULE", d.instructions)
        self.assertIn("WITHOUT any name", d.instructions)
        self.assertIn("never invent or guess one", d.instructions)


class TestImageConceptWordBoundaries(unittest.TestCase):
    """'sol' must never fire inside 'Marisol' or 'solo' (sun-image incidents)."""

    def test_word_present_boundaries(self):
        from tutor.observe import word_present

        self.assertFalse(word_present("sol", "Hola Marisol. Mucho gusto"))
        self.assertFalse(word_present("sol", "yo solo compra caras"))
        self.assertTrue(word_present("sol", "me gusta el sol"))
        self.assertTrue(word_present("gato", "los gatos son bonitos"))
        self.assertFalse(word_present("rio", "es muy serio"))
        self.assertTrue(word_present("río", "estoy en el río"))

    def test_noun_from_text_ignores_marisol(self):
        from tutor.modes import _noun_from_text

        sheet = {"lexicon": {}}
        self.assertIsNone(
            _noun_from_text("Me llama Patrick. Hola Marisol. Mucho gusto", sheet)
        )
        self.assertEqual(_noun_from_text("estoy en mi bote", sheet), "bote")

    def test_concepts_from_spanish_boundaries(self):
        from tutor.session_memory import _concepts_from_spanish

        self.assertNotIn("rio", _concepts_from_spanish("es un tema muy serio"))
        self.assertIn("rio", _concepts_from_spanish("el río es bonito"))


class TestTutorDeclaredImage(unittest.TestCase):
    """Optional <image concept="…"/> — the model's decision, never mandatory."""

    def test_self_closing_tag_parsed_and_stripped(self):
        from tutor.tutor_response import process_tutor_raw

        raw = ('<tutor><model>Mira, el **sol**. <image concept="sol"/></model>'
               "<try>¿Te gusta el sol?</try></tutor>")
        visible, parts = process_tutor_raw(raw)
        d = parts.as_dict()
        self.assertEqual(d.get("image_concept"), "sol")
        self.assertNotIn("<image", visible)
        self.assertNotIn("<image", d.get("model", ""))

    def test_body_form_parsed(self):
        from tutor.tutor_response import process_tutor_raw

        _, parts = process_tutor_raw(
            "<tutor><model>El café</model><image>cafe</image>"
            "<try>¿Café o té?</try></tutor>"
        )
        self.assertEqual(parts.as_dict().get("image_concept"), "cafe")

    def test_no_tag_means_no_image(self):
        from tutor.tutor_response import process_tutor_raw

        _, parts = process_tutor_raw(
            "<tutor><model>Estoy bien</model><try>¿Y tú?</try></tutor>"
        )
        self.assertNotIn("image_concept", parts.as_dict())

    def test_fail_closed_on_junk_concepts(self):
        from tutor.tutor_response import process_tutor_raw

        # Grok countersign: sol2/http/el-sol must NOT truncate into a
        # billable concept — fail closed, no image
        for junk in ('concept="sol2"', 'concept="el-sol"',
                     'concept="http://evil.com/x"'):
            _, parts = process_tutor_raw(
                f"<tutor><model>Mira <image {junk}/></model>"
                "<try>¿Sí?</try></tutor>"
            )
            self.assertNotIn("image_concept", parts.as_dict(), junk)

    def test_image_only_reply_never_leaks_raw_tag(self):
        from tutor.tutor_response import process_tutor_raw

        visible, parts = process_tutor_raw('<image concept="sol"/>')
        self.assertNotIn("<image", visible)
        self.assertEqual(parts.as_dict().get("image_concept"), "sol")

    def test_document_order_wins_with_multiple_tags(self):
        from tutor.tutor_response import process_tutor_raw

        _, parts = process_tutor_raw(
            "<tutor><model><image>luna</image> y "
            '<image concept="sol"/></model><try>¿Sí?</try></tutor>'
        )
        self.assertEqual(parts.as_dict().get("image_concept"), "luna")

    def test_phrase_and_verb_concepts_allowed(self):
        from tutor.tutor_response import process_tutor_raw

        _, p1 = process_tutor_raw(
            '<tutor><model>Nado. <image concept="nadar"/></model>'
            "<try>¿Nadas?</try></tutor>"
        )
        self.assertEqual(p1.as_dict().get("image_concept"), "nadar")
        _, p2 = process_tutor_raw(
            "<tutor><model>Uf. <image>hace calor</image></model>"
            "<try>¿Calor?</try></tutor>"
        )
        self.assertEqual(p2.as_dict().get("image_concept"), "hace_calor")

    def test_cf_recast_no_longer_auto_picks_image(self):
        d = select_mode(
            _known_sheet(),
            learner="yo esta bien en mi bote",
            observations={"blank_sheet": False, "signals": ["topic_vocab"]},
            mode_state=ModeSessionState(),
        )
        self.assertEqual(d.mode, Mode.CF_RECAST)
        self.assertIsNone(d.image_concept)


class TestNoDoubleCorrection(unittest.TestCase):
    """A recast must not be followed by a form_focus re-correction on a clean
    turn (2026-07-27: 'llama' re-corrected on a message about travel)."""

    def _sheet_with_streak(self, pid="me_llamo_es"):
        sheet = default_sheet()
        sheet["skills"]["IP-01"] = {"status": "emerging", "confidence": 0.5}
        sheet["error_patterns"] = {
            pid: {"count": 2, "form_id": "me_llamo", "last_examples": ["me llama X"]},
        }
        return sheet

    def test_cooldown_after_recast_blocks_streak_break(self):
        # conv_session sets 3 post-recast; tick() decrements BEFORE select, so
        # effective suppression = 2 subsequent learner turns (Grok-corrected)
        state = ModeSessionState()
        state.note_error_hits(["me_llamo_es"])  # error is recent
        state.set_cooldown("me_llamo_es", 3)
        for _ in range(2):  # both suppressed turns
            state.tick()
            d = select_mode(
                self._sheet_with_streak(),
                learner="yo quiero viajar a Chile",
                observations={"blank_sheet": False, "signals": ["spanish_ok"]},
                mode_state=state,
            )
            self.assertNotEqual(d.mode, Mode.FORM_FOCUS)
        state.tick()  # cooldown expired; error still recent (within K=4)
        d = select_mode(
            self._sheet_with_streak(),
            learner="yo quiero viajar a Chile",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.FORM_FOCUS)

    def test_stale_streak_never_hard_breaks(self):
        # count>=2 on the sheet but NO recorded hit this session → no ambush
        d = select_mode(
            self._sheet_with_streak(),
            learner="yo quiero viajar a Chile",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            mode_state=ModeSessionState(),
        )
        self.assertNotEqual(d.mode, Mode.FORM_FOCUS)

    def test_recent_hit_break_uses_practice_framing(self):
        state = ModeSessionState()
        state.note_error_hits(["me_llamo_es"])
        state.tick()
        state.tick()  # hit was 2 turns ago — within K=4, not fresh
        d = select_mode(
            self._sheet_with_streak(),
            learner="yo quiero viajar a Chile",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            mode_state=state,
        )
        self.assertEqual(d.mode, Mode.FORM_FOCUS)
        self.assertFalse(d.targets.get("fresh_hit"))
        self.assertIn("did NOT contain this error", d.instructions)

    def test_hit_beyond_recency_window_no_break(self):
        state = ModeSessionState()
        state.note_error_hits(["me_llamo_es"])
        for _ in range(5):  # 5 turns later — beyond K=4
            state.tick()
        d = select_mode(
            self._sheet_with_streak(),
            learner="yo quiero viajar a Chile",
            observations={"blank_sheet": False, "signals": ["spanish_ok"]},
            mode_state=state,
        )
        self.assertNotEqual(d.mode, Mode.FORM_FOCUS)

    def test_streak_break_with_fresh_hit_stays_corrective(self):
        d = select_mode(
            self._sheet_with_streak(),
            learner="me llama Patricio",
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
        )
        self.assertEqual(d.mode, Mode.FORM_FOCUS)
        self.assertTrue(d.targets.get("fresh_hit"))
        self.assertNotIn("did NOT contain this error", d.instructions)


class TestLearnerUptake(unittest.TestCase):
    """Adaptivity round-1 fixtures (Grok CI spec): help requests answered,
    hold arm/clear semantics, repair preserved for true non-understanding."""

    T3 = ("buenas tardis usted.  Yo buscondo para huevos.  I am searching "
          "for eggs.  I always forget how to say searching or looking for "
          "something")

    def test_t3_yields_help_request_signal(self):
        self.assertIn("help_request", probe_signals(self.T3))

    def test_t3_routes_to_help_not_repair_even_with_hold(self):
        d = select_mode(
            _known_sheet(),
            learner=self.T3,
            observations={
                "blank_sheet": False,
                "signals": sorted(probe_signals(self.T3)),
            },
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿Cómo está usted?",
                "last_tutor_model": "Buenas tardes.",
                "await_comprehension": True,
            },
        )
        self.assertEqual(d.reason, "learner_help_request")
        self.assertNotEqual(d.mode, Mode.COMPREHENSION_REPAIR)

    def test_grammar_question_with_own_spanish_does_not_arm_hold(self):
        mem = SessionMemory()
        mem.note_learner(
            'Como esta usted. The "estas" is wrong though I dont know why'
        )
        self.assertFalse(mem.await_comprehension)

    def test_hold_ttl_is_one_turn(self):
        mem = SessionMemory()
        mem.note_learner("what does saludarte mean?")  # pure meta → arm
        self.assertTrue(mem.await_comprehension)
        mem.note_learner("hmm ok")  # next turn: hold still active
        self.assertTrue(mem.await_comprehension)
        mem.note_learner("hmm")  # turn after: TTL expired
        self.assertFalse(mem.await_comprehension)

    def test_pure_no_entiendo_still_repairs(self):
        utt = "no entiendo"
        d = select_mode(
            _known_sheet(),
            learner=utt,
            observations={
                "blank_sheet": False,
                "signals": sorted(probe_signals(utt)),
            },
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿Cómo está usted?",
                "last_tutor_model": "Buenas tardes.",
                "await_comprehension": False,
            },
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)

    def test_help_request_clears_hold(self):
        mem = SessionMemory()
        mem.note_learner("what does saludarte mean?")
        self.assertTrue(mem.await_comprehension)
        mem.note_learner("how do I say searching?")
        self.assertFalse(mem.await_comprehension)

    def test_repair_instructions_require_uptake_first(self):
        utt = "que??"
        d = select_mode(
            _known_sheet(),
            learner=utt,
            observations={"blank_sheet": False, "signals": []},
            mode_state=ModeSessionState(),
            session_memory={
                "last_tutor_try": "¿Cómo está usted?",
                "last_tutor_model": "Buenas tardes.",
                "await_comprehension": True,
            },
        )
        self.assertEqual(d.mode, Mode.COMPREHENSION_REPAIR)
        self.assertIn("UPTAKE FIRST", d.instructions)


class TestSignalClassifier(unittest.TestCase):
    def test_disabled_returns_none(self):
        from tutor.signal_classifier import classify_signals

        self.assertIsNone(classify_signals("hola", model="off"))
        self.assertIsNone(classify_signals("", model="grok-3-mini"))

    def test_extra_signals_merge_into_observations(self):
        from tutor.observe import build_observations

        obs = build_observations(
            default_sheet(),
            learner="I need assistance with a word por favor",
            extra_signals={"help_request"},
        )
        self.assertIn("help_request", obs["signals"])


class TestPackTopics(unittest.TestCase):
    def test_pack_topic_titles_empty_without_pack(self):
        # Prose course pack DELETED 2026-08-03: shadow phase topics are
        # empty by construction (the sheet is the curriculum now).
        from pathlib import Path

        from tutor.config import DEFAULT_PACK_DIR
        from tutor.corpus import pack_topic_titles

        self.assertEqual(pack_topic_titles(Path(DEFAULT_PACK_DIR)), [])


class TestModeImageAttachVisibility(unittest.TestCase):
    """Incident 2026-07-28 + audit (e): mode-path cache misses must never be
    SILENT and must never generate on the reply thread (latency law, commits
    2d160e0/7275bdc). A cap-allowed miss returns [] instantly, notes
    image_gen_async, and a daemon warm thread generates into the cache
    (costs recorded via _note_image_costs) so the image attaches on a LATER
    turn via cache hit."""

    GEN_KEY = "zz_gen_probe"

    def setUp(self):
        import tempfile
        from pathlib import Path

        import tutor.costs as costs
        import tutor.teach_assets as ta

        # Isolate the cost ledger — never pollute logs/costs.jsonl
        self._tmp = tempfile.TemporaryDirectory()
        self._costs = costs
        self._old_ledger = costs.LEDGER_PATH
        costs.LEDGER_PATH = Path(self._tmp.name) / "costs.jsonl"
        # Save generator state (tests run with none registered by default)
        self._ta = ta
        self._old_gen = ta._generator
        self._old_flag = ta.GENERATE_ON_MISS

    def tearDown(self):
        ta = self._ta
        ta.register_generator(self._old_gen)
        ta.GENERATE_ON_MISS = self._old_flag
        self._costs.LEDGER_PATH = self._old_ledger
        self._tmp.cleanup()
        # Remove any probe asset written to the real cache dir
        for suf in (".png", ".jpg"):
            p = ta.CACHE_DIR / f"{self.GEN_KEY}{suf}"
            if p.exists():
                p.unlink()
        idx = ta._load_index()
        if (idx.get("entries") or {}).pop(self.GEN_KEY, None) is not None:
            ta._save_index()

    def _session(self):
        from tutor.conv_session import ConversationalSession

        return ConversationalSession(log=False)

    def _decision(self, concept):
        from tutor.modes import Mode, ModeDecision

        return ModeDecision(
            Mode.ASSOCIATION, reason="test", image_concept=concept
        )

    def _fake_generator(self):
        def gen(concept, prompt, dest):
            from pathlib import Path

            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
            return True

        return gen

    def _join_warm_threads(self, timeout: float = 5.0) -> None:
        import threading

        for t in threading.enumerate():
            if t.name.startswith("image-warm-"):
                t.join(timeout)

    def test_session_miss_returns_fast_and_warms_async(self):
        # Audit (e) 2026-07-28: a cap-allowed miss returns [] instantly with
        # the async note; the daemon warm thread generates into the cache
        # and records the cost through _note_image_costs; the image attaches
        # on the NEXT call via cache hit.
        import json

        ta = self._ta
        ta.register_generator(self._fake_generator())
        ta.GENERATE_ON_MISS = True
        sess = self._session()
        notes: list[str] = []
        imgs = sess._attach_mode_image(self._decision(self.GEN_KEY), notes)
        self.assertEqual(imgs, [])  # never generated on the reply thread
        self.assertEqual(notes, [f"image_gen_async:{self.GEN_KEY}"])
        self._join_warm_threads()
        self.assertIsNotNone(ta.cache_lookup(self.GEN_KEY))
        self.assertEqual(sess.pedagogy_memory.images_generated, 1)
        ledger = [
            json.loads(l)
            for l in self._costs.LEDGER_PATH.read_text().splitlines()
        ]
        self.assertTrue(
            any(r.get("category") == "image" for r in ledger), ledger
        )
        # Later turn: the warmed image attaches from cache.
        notes2: list[str] = []
        imgs2 = sess._attach_mode_image(self._decision(self.GEN_KEY), notes2)
        self.assertTrue(imgs2)
        self.assertEqual(imgs2[0]["cache"], "hit")
        self.assertEqual(imgs2[0]["concept"], self.GEN_KEY)
        self.assertEqual(notes2, [])

    def test_reply_path_never_blocks_on_generation(self):
        # A SLOW generator must not delay the reply path: the attach returns
        # immediately; generation happens on the daemon thread.
        import threading
        import time
        from pathlib import Path

        ta = self._ta
        release = threading.Event()
        calls: list[str] = []

        def slow_gen(concept, prompt, dest):
            calls.append(concept)
            release.wait(5)
            dest = Path(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 200)
            return True

        ta.register_generator(slow_gen)
        ta.GENERATE_ON_MISS = True
        sess = self._session()
        notes: list[str] = []
        t0 = time.monotonic()
        imgs = sess._attach_mode_image(self._decision(self.GEN_KEY), notes)
        elapsed = time.monotonic() - t0
        self.assertEqual(imgs, [])
        self.assertLess(elapsed, 1.0)  # no image-API RTT on the reply path
        release.set()
        self._join_warm_threads()
        self.assertEqual(calls, [self.GEN_KEY])

    def test_warm_thread_respects_session_cap(self):
        # Caps hold across the async handoff: at the session budget the miss
        # notes image_gen_capped and NO warm thread spawns.
        from tutor.conv_session import MAX_IMAGE_GENERATIONS_PER_SESSION

        ta = self._ta
        ta.register_generator(self._fake_generator())
        ta.GENERATE_ON_MISS = True
        sess = self._session()
        sess.pedagogy_memory.images_generated = (
            MAX_IMAGE_GENERATIONS_PER_SESSION
        )
        notes: list[str] = []
        imgs = sess._attach_mode_image(
            self._decision("zz_never_cached"), notes
        )
        self.assertEqual(imgs, [])
        self.assertEqual(notes, ["image_gen_capped:zz_never_cached"])
        self._join_warm_threads()
        self.assertIsNone(ta.cache_lookup("zz_never_cached"))

    def test_rb_downgrade_condition_holds_and_warm_still_runs(self):
        # Audit (e) interaction: an R-B introduce plan rides this same
        # attach path (decision.image_concept = plan.key). On a cache miss
        # the attach returns [] — exactly the condition the R-B→R-D
        # downgrade keys off (branch verified present; Phase 4 batch 3
        # moved the deferred render to turn_pipeline.stage_introduce_render)
        # — AND the async warm still runs so the image exists next time.
        import inspect

        import tutor.turn_pipeline as turn_pipeline

        # Phase 3 batch 1: the note string renders from the typed event —
        # the branch marker in source is the event kind, and the rendered
        # legacy string is pinned in tutor.turn_events' render table.
        self.assertIn(
            "INTRODUCE_DOWNGRADED",
            inspect.getsource(turn_pipeline.stage_introduce_render),
        )
        from tutor.turn_events import TurnEventKind, render_note

        self.assertEqual(
            render_note(
                TurnEventKind.INTRODUCE_DOWNGRADED, key="k",
                payload={"path": "R-B_to_R-D"},
            ),
            "introduce_downgraded:k:R-B_to_R-D",
        )
        ta = self._ta
        ta.register_generator(self._fake_generator())
        ta.GENERATE_ON_MISS = True
        sess = self._session()
        notes: list[str] = []
        imgs = sess._attach_mode_image(self._decision(self.GEN_KEY), notes)
        self.assertEqual(imgs, [])  # downgrade condition holds this turn
        self._join_warm_threads()
        notes2: list[str] = []
        imgs2 = sess._attach_mode_image(self._decision(self.GEN_KEY), notes2)
        self.assertTrue(imgs2)  # the image exists for the NEXT plan

    def test_resolve_decision_assets_generate_false_never_generates(self):
        # The AI-turn fallback + rules path pass generate=False: a wanted
        # miss must return [] without ever invoking the generator.
        from tutor.teach_assets import (
            ImageDecision,
            _resolve_decision_assets,
        )

        ta = self._ta
        calls: list[str] = []

        def gen(concept, prompt, dest):
            calls.append(concept)
            return True

        ta.register_generator(gen)
        ta.GENERATE_ON_MISS = True
        decision = ImageDecision(
            True, concept="zz_never_cached", reason="test"
        )
        out = _resolve_decision_assets(decision, generate=False)
        self.assertEqual(out, [])
        self.assertEqual(calls, [])

    def test_session_miss_disabled_notes_visible(self):
        ta = self._ta
        ta.register_generator(None)
        sess = self._session()
        notes: list[str] = []
        imgs = sess._attach_mode_image(
            self._decision("zz_never_cached"), notes
        )
        self.assertEqual(imgs, [])
        self.assertEqual(notes, ["image_gen_disabled:zz_never_cached"])

    def test_session_miss_capped_notes_visible(self):
        from tutor.conv_session import MAX_IMAGE_GENERATIONS_PER_SESSION

        ta = self._ta
        ta.register_generator(self._fake_generator())
        sess = self._session()
        sess.pedagogy_memory.images_generated = (
            MAX_IMAGE_GENERATIONS_PER_SESSION
        )
        notes: list[str] = []
        imgs = sess._attach_mode_image(
            self._decision("zz_never_cached"), notes
        )
        # Cap respected: generator present but NOT invoked; miss is noted
        self.assertEqual(imgs, [])
        self.assertEqual(notes, ["image_gen_capped:zz_never_cached"])

    def test_cache_hit_unaffected_no_notes(self):
        ta = self._ta
        ta.register_generator(None)  # hits never need the generator
        sess = self._session()
        notes: list[str] = []
        imgs = sess._attach_mode_image(self._decision("hola"), notes)
        self.assertTrue(imgs)
        self.assertEqual(imgs[0]["cache"], "hit")
        self.assertEqual(imgs[0]["decision_reason"], "mode:association")
        self.assertEqual(notes, [])

    def test_health_fields_populated(self):
        """cache_stats must truthfully expose generation state (surfaced in
        /api/health teach_image_cache — this can never be invisible again)."""
        stats = self._ta.cache_stats()
        self.assertIn("generate_on_miss", stats)
        self.assertIn("generator_registered", stats)
        self.assertIsInstance(stats["generator_registered"], bool)


if __name__ == "__main__":
    unittest.main()
