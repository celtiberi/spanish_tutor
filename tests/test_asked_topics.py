"""Asked-topic registry + covered concepts (2026-07-28 repetition forensics).

The old `asked` set stored MODE NAMES ("conversation", "association") — the
executor payload "topics_tutor_already_asked" told the model nothing. The
registry stores semantic keys ("size:ciudad", "location:casa") derived from
the composed try by a code-owned surface-form extractor (§4.2 legit use).
"""

import unittest

from tutor.executor import build_ai_tutor_user_message
from tutor.session_memory import (
    SessionMemory,
    compose_topic_key,
    topic_key_for_try,
)


class TestTopicExtractor(unittest.TestCase):
    """Frame patterns: dónde/where→location, grande|pequeñ|size→size,
    cómo estás→wellbeing, cómo te llamas→name, qué+verb→what:<verb>."""

    def test_location_frame_with_concept(self):
        self.assertEqual(
            topic_key_for_try("¿Dónde está tu casa?"), ("location", "casa")
        )

    def test_size_frame_with_concept(self):
        self.assertEqual(
            topic_key_for_try("¿Es grande tu ciudad?"), ("size", "ciudad")
        )

    def test_verbatim_incident_turn3_is_size_ciudad(self):
        # Session 20260728-120335 turn 3 (the re-asked city-size question)
        frame, concept = topic_key_for_try(
            "¿Y tu casa? ¿Está en una ciudad grande o en una ciudad pequeña?"
        )
        self.assertEqual(compose_topic_key(frame, concept), "size:ciudad")

    def test_wellbeing_frame(self):
        # Gate retune 2026-08-03: SOCIAL_FORMULA_THEMES left the topic
        # palette — «cómo estás» is a conversational move, not a topic
        # concept («location:y tu» derivation bug).  The frame alone is
        # the registry key.
        self.assertEqual(
            topic_key_for_try("¿Cómo estás hoy?"), ("wellbeing", "")
        )

    def test_name_frame(self):
        # Same retune delta: «cómo te llamas» no longer binds as a concept.
        self.assertEqual(
            topic_key_for_try("¿Cómo te llamas?"), ("name", "")
        )

    def test_social_formula_never_binds_as_concept(self):
        # The location:y tu incident verbatim (baseline run
        # 20260803-104618 turn 10): «y tú» must not be the concept of a
        # location try.
        frame, concept = topic_key_for_try("¿Y tú? ¿Dónde bebes tu café?")
        self.assertEqual(frame, "location")
        self.assertEqual(concept, "cafe")

    def test_what_verb_frame(self):
        frame, concept = topic_key_for_try("¿Qué hay en tu casa?")
        self.assertEqual(frame, "what:hay")
        self.assertEqual(concept, "casa")

    def test_what_frame_skips_clitic_pronouns(self):
        # Baseline run 20260803-104618 turns 8/9: «¿Qué te gusta…?» keyed
        # "what:te" (the pronoun) — the verb is the frame.
        frame, concept = topic_key_for_try(
            "¿Qué te gusta más en el bote: el café, la música o la comida?"
        )
        self.assertEqual(frame, "what:gusta")
        self.assertEqual(concept, "bote")

    def test_no_frame_returns_empty(self):
        self.assertEqual(topic_key_for_try("Me gusta el café."), ("", ""))
        self.assertEqual(topic_key_for_try(""), ("", ""))

    def test_compose_key_deaccents(self):
        self.assertEqual(compose_topic_key("size", "ciudad"), "size:ciudad")
        self.assertEqual(compose_topic_key("location", "café"), "location:cafe")
        self.assertEqual(compose_topic_key("wellbeing"), "wellbeing")
        self.assertEqual(compose_topic_key(""), "")

    def test_table_keys_extend_noun_palette(self):
        frame, concept = topic_key_for_try(
            "¿Dónde está el mercado?", nouns=["mercado"]
        )
        self.assertEqual((frame, concept), ("location", "mercado"))


class TestSessionMemoryRegistry(unittest.TestCase):
    def test_note_asked_topic_and_snapshot(self):
        mem = SessionMemory()
        key = mem.note_asked_topic("size", "ciudad")
        self.assertEqual(key, "size:ciudad")
        mem.note_asked_topic("wellbeing", "")
        snap = mem.snapshot()
        self.assertEqual(snap["asked_topics"], ["size:ciudad", "wellbeing"])

    def test_note_asked_topic_empty_frame_noops(self):
        mem = SessionMemory()
        self.assertEqual(mem.note_asked_topic("", "casa"), "")
        self.assertEqual(mem.asked_topics, set())

    def test_covered_concepts_recorded_and_exposed(self):
        # Guard-6 coverage: recorded even when no lexicon/image write lands,
        # so new_noun:<c> cannot re-fire this session.
        mem = SessionMemory()
        mem.note_concept_covered("casa")
        mem.note_concept_covered("  ")
        self.assertEqual(mem.covered_concepts, {"casa"})
        self.assertEqual(mem.snapshot()["covered_concepts"], ["casa"])


class TestExecutorPayload(unittest.TestCase):
    def test_do_not_re_ask_replaces_mode_name_garbage(self):
        msg = build_ai_tutor_user_message(
            learner="mi casa es pequena",
            is_open=False,
            session_memory={
                "shown": ["estoy"],
                "asked": ["conversation", "association"],  # legacy mode names
                "asked_topics": ["size:ciudad", "location:casa"],
                "turns": 4,
            },
            blank_sheet=False,
        )
        self.assertIn("do_not_re_ask", msg)
        self.assertIn("size:ciudad", msg)
        self.assertIn("location:casa", msg)
        # The useless mode-name list is gone from the payload
        self.assertNotIn("topics_tutor_already_asked", msg)


if __name__ == "__main__":
    unittest.main()
