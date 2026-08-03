"""Encounter-variety round (docs/design-encounter-variety.md, 2026-07-29).

Grok-required pins: (1) the hola-incident replay — an avoid=…greetings…
next_best must NOT promote the greetings theme (narrowed match blob);
(2) mid-stream sheets get no greetings priority (dual-axis zero test);
(3) true zeros still open with hola; (4) conjugated surfaces fire the due
key («estás» → estar) so frames_seen never silently under-counts.
frames_seen is exposure history, never ability evidence.
"""

import datetime
import unittest
from types import SimpleNamespace

from tutor import turn_pipeline as tp
from tutor.character_sheet import default_sheet
from tutor.introduce_router import _true_zero_sheet, candidate_keys
from tutor.retrieval_scheduler import (
    FRAMES_SAFETY_CAP,
    frames_seen_of,
    record_frame,
)
from tutor.turn_events import TurnEventKind as EV, TurnEventLog
from tutor.turn_morph import lemma_engaged_by_text

TABLE = {
    "hola": {"theme": "greetings"},
    "adiós": {"theme": "farewells"},
    "me llamo": {"theme": "introductions"},
    "quiero": {"theme": "wants"},
    "agua": {"theme": "food_drink"},
}

# The live next_best from the 2026-07-29 hola incident (session
# 20260729-163623): the avoid/reason strings contain "greetings".
INCIDENT_NEXT_BEST = {
    "can_do": "IP-03",
    "stretch": "introduce_in_conversation",
    "activity": "introduce_in_conversation",
    "statement": "I can say my name and ask another person's name.",
    "avoid": "return_to_greetings_when_already_emerging",
    "reason": "weakest open interpersonal can-do IP-03",
    "method": "CLT/TBLT + CI + focus_on_form",
    "primary": "can_do",
}


def _midstream_sheet() -> dict:
    s = default_sheet()
    s["skills"]["IP-03"] = {"status": "emerging", "confidence": 0.12}
    return s


class TestGreetingsDemotion(unittest.TestCase):
    def test_avoid_greetings_does_not_promote_greetings(self):
        # Incident replay: before the fix, word_present("greetings", blob)
        # over the FULL next_best dump put every greetings key in the
        # first bucket — the instruction to avoid greetings caused hola.
        s = _midstream_sheet()
        s["next_best"] = dict(INCIDENT_NEXT_BEST)
        cands = candidate_keys(s, TABLE)
        self.assertTrue(cands)
        self.assertNotEqual(cands[0], "hola")
        self.assertNotIn(TABLE[cands[0]]["theme"], ("greetings", "farewells"))

    def test_midstream_sheet_sorts_openers_last(self):
        # Dual-axis zero test: a skill at emerging kills the opener bias
        # even with an empty schedule axis (no introduced_at anywhere) —
        # and openers sort AFTER content (adjudication counter-amendment:
        # merely merging them into rest left hola first by table order).
        s = _midstream_sheet()
        self.assertFalse(_true_zero_sheet(s))
        cands = candidate_keys(s, TABLE)
        self.assertEqual(cands, ["me llamo", "quiero", "agua", "hola", "adiós"])

    def test_true_zero_still_opens_with_hola(self):
        s = default_sheet()
        self.assertTrue(_true_zero_sheet(s))
        cands = candidate_keys(s, TABLE)
        self.assertEqual(cands[0], "hola")

    def test_schedule_axis_alone_also_kills_priority(self):
        s = default_sheet()
        s["lexicon"]["agua"] = {
            "status": "unknown", "confidence": 0.0,
            "introduced_at": "2026-07-29",
        }
        self.assertFalse(_true_zero_sheet(s))


class TestRecordFrame(unittest.TestCase):
    def _sheet_with(self, key: str) -> dict:
        s = default_sheet()
        s["lexicon"][key] = {"status": "unknown", "confidence": 0.0}
        return s

    def test_appends_dedupes_and_keeps_order(self):
        s = self._sheet_with("estar")
        s = record_frame(s, "estar", "lexicon", "wellbeing")
        s = record_frame(s, "estar", "lexicon", "wellbeing")
        s = record_frame(s, "estar", "lexicon", "location")
        self.assertEqual(
            frames_seen_of(s, "estar", "lexicon"), ["wellbeing", "location"]
        )

    def test_silence_and_absent_entries_record_nothing(self):
        s = self._sheet_with("estar")
        s = record_frame(s, "estar", "lexicon", "")
        s = record_frame(s, "ghost", "lexicon", "wellbeing")
        self.assertEqual(frames_seen_of(s, "estar", "lexicon"), [])
        self.assertNotIn("ghost", s["lexicon"])

    def test_ability_fields_untouched_and_cap_never_drops(self):
        s = self._sheet_with("estar")
        s["lexicon"]["estar"]["confidence"] = 0.4
        s["lexicon"]["estar"]["frames_seen"] = [
            f"f{i}" for i in range(FRAMES_SAFETY_CAP)
        ]
        s = record_frame(s, "estar", "lexicon", "wellbeing")
        # safety cap: no write, and crucially NO drop of older frames
        self.assertEqual(len(frames_seen_of(s, "estar", "lexicon")),
                         FRAMES_SAFETY_CAP)
        self.assertEqual(frames_seen_of(s, "estar", "lexicon")[0], "f0")
        self.assertEqual(s["lexicon"]["estar"]["confidence"], 0.4)


class TestConjugatedSurfaceFires(unittest.TestCase):
    def test_estas_fires_estar(self):
        self.assertTrue(lemma_engaged_by_text("¿Cómo estás hoy?", "estar"))

    def test_verbatim_phrase_fires(self):
        self.assertTrue(
            lemma_engaged_by_text("Di: **estoy bien**", "estoy bien")
        )

    def test_ambiguous_tokens_stay_silent(self):
        # "esta"/"como" are deliberately absent from the token index.
        self.assertFalse(lemma_engaged_by_text("esta bien, como tú", "estar"))
        self.assertFalse(lemma_engaged_by_text("como tú dices", "comer"))


class _StubSession:
    def __init__(self, sheet):
        self.sheet = sheet

    def _topic_nouns(self):
        return ()


def _ctx(parts, ev):
    return SimpleNamespace(result=SimpleNamespace(parts=parts), ev=ev)


class TestStageFrameRecord(unittest.TestCase):
    def test_due_estar_elicited_as_estas_records_wellbeing(self):
        # THE Grok-required pin: due «estar» + try «¿Cómo estás?» must
        # record wellbeing — bare word_present(lemma) would miss it.
        s = default_sheet()
        s["lexicon"]["estar"] = {"status": "unknown", "confidence": 0.0}
        session = _StubSession(s)
        ev = TurnEventLog()
        ev.emit(EV.DUE_ELICIT_OFFERED,
                payload={"keys": ["estar"], "kinds": ["lexicon"]},
                stage="instruct")
        ctx = _ctx({"try": "¿Cómo estás hoy?", "model": ""}, ev)
        tp.stage_frame_record(session, ctx)
        self.assertEqual(
            frames_seen_of(session.sheet, "estar", "lexicon"), ["wellbeing"]
        )
        notes = [str(e.key) for e in ev.find(EV.FRAME_RECORDED)]
        self.assertEqual(notes, ["estar:wellbeing"])

    def test_offered_but_not_realized_records_nothing(self):
        s = default_sheet()
        s["lexicon"]["estar"] = {"status": "unknown", "confidence": 0.0}
        session = _StubSession(s)
        ev = TurnEventLog()
        ev.emit(EV.DUE_ELICIT_OFFERED,
                payload={"keys": ["estar"], "kinds": ["lexicon"]},
                stage="instruct")
        ctx = _ctx({"try": "¿Dónde vives tú?", "model": ""}, ev)
        tp.stage_frame_record(session, ctx)
        self.assertEqual(frames_seen_of(session.sheet, "estar", "lexicon"), [])
        self.assertFalse(ev.find(EV.FRAME_RECORDED))

    def test_no_topic_frame_records_nothing(self):
        s = default_sheet()
        s["lexicon"]["estar"] = {"status": "unknown", "confidence": 0.0}
        session = _StubSession(s)
        ev = TurnEventLog()
        ev.emit(EV.DUE_ELICIT_OFFERED,
                payload={"keys": ["estar"], "kinds": ["lexicon"]},
                stage="instruct")
        ctx = _ctx({"try": "Di: estoy bien.", "model": ""}, ev)
        tp.stage_frame_record(session, ctx)
        self.assertEqual(frames_seen_of(session.sheet, "estar", "lexicon"), [])

    def test_introduced_key_records_frame(self):
        s = default_sheet()
        s["lexicon"]["hola"] = {"status": "unknown", "confidence": 0.0}
        session = _StubSession(s)
        ev = TurnEventLog()
        ev.emit(EV.INTRODUCED, key="hola", stage="record")
        ctx = _ctx({"try": "¿Qué significa «hola»?", "model": ""}, ev)
        tp.stage_frame_record(session, ctx)
        self.assertEqual(
            frames_seen_of(session.sheet, "hola", "lexicon"),
            ["what:significa"],
        )


# (TestDirectionLine DELETED 2026-08-03: the DUE RE-ENCOUNTERS text builder
# (due_elicit_block) died with the session-phase machinery — full-code-audit
# S9. frames_seen still ships to the model as data: teaching_data
# due_for_review carries frames_already_used per key, and the
# DUE_ELICIT_OFFERED event now fires from turn_pipeline.stage_prompt_build;
# TestStageFrameRecord above proves the event → frames_seen write wire.)


if __name__ == "__main__":
    unittest.main()
