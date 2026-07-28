"""ConvergentTaskRuntime (r6 Rank-4) — pure runtime + scene task schema (no live API)."""

import json
import tempfile
import unicodedata
import unittest
from pathlib import Path

from tutor.scenes import load_scenes, scene_hints_for_prompt, validate_scene
from tutor.task_runtime import (
    TaskState,
    evaluate_turn,
    phrase_present,
    task_from_scene,
    task_instructions,
)

# ---------------------------------------------------------------------------
# Hand-derived pack-legal allowlist for evidence_any tokens, accent-folded.
# Source: course_packs/spanish_a1/pack.md closed inventories + unit files.
# The section each word comes from is documented inline. gustar and hacer are
# denylisted by pack.md "Scope boundaries" and must never appear here.
# ---------------------------------------------------------------------------
PACK_EVIDENCE_ALLOWLIST = {
    # Unit 1 — "Greetings by time of day" table: Hola / Buenos días /
    # Buenas tardes / Buenas noches.
    "hola", "buenos", "dias", "buenas", "tardes", "noches",
    # Unit 1 — "Introductions" table: ¿Cómo te llamas? / ¿Cómo se llama
    # (usted)?  (cómo also in Unit 6 question-word table).
    "como", "te", "llamas", "se", "llama",
    # Unit 1 — "How are you?" table + Unit 4 estar frozen form inventory
    # (estoy, estás, está, ...): ¿Cómo estás? / ¿Cómo está (usted)?
    "esta", "estas",
    # Unit 3 — ser frozen form inventory (soy, eres, es, ...) and origin
    # use "¿De dónde eres? — Soy de Perú."; de also in Unit 6 ¿De dónde?
    "es", "eres", "de",
    # Unit 6 — "Question words" table: ¿Qué? / ¿Dónde?
    "que", "donde",
    # Unit 5 — regular present, frozen ending inventory applied to the core
    # verbs beber and comer (bebes/bebe, comes/come).
    "bebes", "bebe", "comes", "come",
}


def _fold(s: str) -> str:
    """Lowercase + strip accents so 'qué'/'que' both check against 'que'."""
    return "".join(
        c for c in unicodedata.normalize("NFD", (s or "").lower())
        if unicodedata.category(c) != "Mn"
    )


def _cafe_scene() -> dict:
    """Fixture task scene. 'leche' is fixture-only (boundary test), NOT
    shipped content — shipped evidence is checked against the allowlist."""
    return {
        "id": "test_cafe",
        "goal": {"can_do": "IP-04"},
        "primary_exit": {
            "description": "Find out what the captain drinks and about the milk.",
            "slots": [
                {"id": "drink", "evidence_any": ["qué bebes", "que bebes"]},
                {"id": "milk", "evidence_any": ["leche"]},
                {"id": "greet", "evidence_any": ["hola"]},
            ],
        },
        "tutor_private_info": {"drink": "Bebo café.", "milk": "Bebo leche."},
        "learner_must_obtain": ["drink", "milk"],
    }


class TestTaskFromScene(unittest.TestCase):
    def test_legacy_scene_without_primary_exit_is_none(self):
        legacy = {
            "id": "boat_old",
            "goal": {"can_do": "IP-06", "exit_predicate": "skill:IP-06:min_conf=0.35"},
            "production": {"elicit": "¿Qué te gusta?"},
        }
        self.assertIsNone(task_from_scene(legacy))
        self.assertIsNone(task_from_scene({}))
        self.assertIsNone(task_from_scene(None))

    def test_task_scene_opens(self):
        st = task_from_scene(_cafe_scene())
        self.assertIsNotNone(st)
        self.assertEqual(st.scene_id, "test_cafe")
        self.assertEqual(st.status, "open")
        self.assertEqual(st.slots_filled, {})
        self.assertEqual(st.turns_on_task, 0)


class TestEvaluateTurn(unittest.TestCase):
    def test_fill_on_exact_word_and_alternative(self):
        scene = _cafe_scene()
        st = task_from_scene(scene)
        # exact single-word evidence
        st = evaluate_turn(st, "¡Hola, capitán!", scene)
        self.assertIn("greet", st.slots_filled)
        # accented phrase alternative
        st2 = evaluate_turn(st, "¿Qué bebes?", scene)
        self.assertIn("drink", st2.slots_filled)
        # unaccented evidence_any alternative fills the same slot
        st3 = evaluate_turn(st, "que bebes tu", scene)
        self.assertIn("drink", st3.slots_filled)

    def test_boundary_discipline_no_substring_hits(self):
        scene = _cafe_scene()
        st = task_from_scene(scene)
        # 'leche' inside another word must NOT count
        st = evaluate_turn(st, "el lechero está aquí", scene)
        self.assertNotIn("milk", st.slots_filled)
        # word_present-style plural tolerance still hits
        st = evaluate_turn(st, "¿Hay leches?", scene)
        self.assertIn("milk", st.slots_filled)
        self.assertTrue(phrase_present("leche", "quiero leche"))
        self.assertFalse(phrase_present("leche", "lechero"))
        # phrase boundaries: 'que bebes' must not match inside 'porque bebes...'
        self.assertFalse(phrase_present("que bebe", "porque bebemos agua"))

    def test_done_only_when_all_must_obtain_filled(self):
        scene = _cafe_scene()
        st = task_from_scene(scene)
        st = evaluate_turn(st, "¿Qué bebes?", scene)
        self.assertEqual(st.status, "open")  # milk still missing
        st = evaluate_turn(st, "¿Hay leche?", scene)
        # greet (not in learner_must_obtain) is unfilled — still done
        self.assertNotIn("greet", st.slots_filled)
        self.assertEqual(st.status, "done")

    def test_turns_increment_and_done_sticky(self):
        scene = _cafe_scene()
        st = task_from_scene(scene)
        st = evaluate_turn(st, "no entiendo", scene)
        st = evaluate_turn(st, "¿Qué bebes? ¿Hay leche?", scene)
        self.assertEqual(st.turns_on_task, 2)
        self.assertEqual(st.status, "done")
        st = evaluate_turn(st, "adiós", scene)
        self.assertEqual(st.status, "done")
        self.assertEqual(st.turns_on_task, 3)

    def test_state_roundtrip(self):
        scene = _cafe_scene()
        st = evaluate_turn(task_from_scene(scene), "¿Qué bebes?", scene)
        again = TaskState.from_dict(st.as_dict())
        self.assertEqual(again, st)
        # tolerant defaults on garbage
        blank = TaskState.from_dict({"status": "weird"})
        self.assertEqual(blank.status, "open")
        self.assertEqual(blank.slots_filled, {})


class TestTaskInstructions(unittest.TestCase):
    def test_open_block_lists_remaining_and_never_volunteer(self):
        scene = _cafe_scene()
        st = evaluate_turn(task_from_scene(scene), "¿Qué bebes?", scene)
        block = task_instructions(st, scene)
        self.assertIn("milk", block)      # remaining slot id
        self.assertIn("greet", block)     # remaining slot id
        self.assertIn("drink", block)     # filled slot id still reported
        self.assertIn(
            "reveal ONLY when the learner asks in Spanish; never volunteer", block
        )
        self.assertIn("Bebo leche.", block)  # tutor-held value visible to teacher
        self.assertNotIn("TASK COMPLETE", block)

    def test_done_block_celebrates_and_closes(self):
        scene = _cafe_scene()
        st = evaluate_turn(task_from_scene(scene), "¿Qué bebes? ¿Hay leche?", scene)
        self.assertEqual(st.status, "done")
        block = task_instructions(st, scene)
        self.assertIn(
            "TASK COMPLETE — celebrate briefly, then close the scene.", block
        )


class TestSceneValidation(unittest.TestCase):
    def test_errors_name_scene_id_and_field(self):
        bad = {
            "id": "bad1",
            "primary_exit": {"description": "", "slots": [{"id": "a"}]},
            "tutor_private_info": {"zzz": "x"},
            "learner_must_obtain": ["a", "missing"],
        }
        errs = validate_scene(bad)
        joined = "\n".join(errs)
        self.assertTrue(all("bad1" in e for e in errs))
        self.assertIn("primary_exit.description", joined)
        self.assertIn("evidence_any", joined)
        self.assertIn("tutor_private_info key 'zzz'", joined)
        self.assertIn("learner_must_obtain id 'missing'", joined)
        # 'a' is a real slot but has no tutor_private_info value (info-gap)
        self.assertIn("learner_must_obtain id 'a'", joined)

    def test_companion_fields_without_primary_exit_flagged(self):
        errs = validate_scene({"id": "bad2", "learner_must_obtain": ["x"]})
        self.assertTrue(any("bad2" in e and "learner_must_obtain" in e for e in errs))

    def test_legacy_scene_validates_clean(self):
        self.assertEqual(validate_scene({"id": "old", "goal": {}}), [])

    def test_loader_strips_invalid_task_fields_and_names_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            scenes_dir = Path(tmp) / "scenes"
            scenes_dir.mkdir()
            (scenes_dir / "broken.json").write_text(
                json.dumps({
                    "id": "broken_task",
                    "goal": {"can_do": "IP-04"},
                    "primary_exit": {"description": "x", "slots": []},
                }),
                encoding="utf-8",
            )
            loaded = load_scenes(Path(tmp))
            self.assertEqual(len(loaded), 1)
            sc = loaded[0]
            self.assertNotIn("primary_exit", sc)  # half-valid schema stripped
            self.assertTrue(any(
                "broken_task" in e and "primary_exit.slots" in e
                for e in sc.get("_task_errors") or []
            ))


class TestShippedScenes(unittest.TestCase):
    """The three shipped boat scenes carry valid, pack-legal task schemas."""

    TASK_SCENE_IDS = {"boat_meet_captain", "boat_where_boat", "boat_likes"}

    def _shipped(self):
        scenes = [s for s in load_scenes() if s.get("id") in self.TASK_SCENE_IDS]
        self.assertEqual({s["id"] for s in scenes}, self.TASK_SCENE_IDS)
        return scenes

    def test_all_shipped_scenes_validate_and_open_tasks(self):
        for sc in self._shipped():
            self.assertEqual(validate_scene(sc), [], sc["id"])
            self.assertNotIn("_task_errors", sc)
            st = task_from_scene(sc)
            self.assertIsNotNone(st, sc["id"])
            for slot_id in sc["learner_must_obtain"]:
                self.assertIn(slot_id, sc["tutor_private_info"], sc["id"])

    def test_shipped_evidence_is_pack_legal(self):
        for sc in self._shipped():
            for slot in sc["primary_exit"]["slots"]:
                for ev in slot["evidence_any"]:
                    for token in _fold(ev).split():
                        self.assertIn(
                            token,
                            PACK_EVIDENCE_ALLOWLIST,
                            f"{sc['id']}.{slot['id']}: '{token}' (from '{ev}') "
                            "is not in the pack-derived allowlist",
                        )

    def test_no_denylisted_forms_in_evidence(self):
        # pack.md scope boundaries: gustar-type constructions and hacer are out.
        for sc in self._shipped():
            for slot in sc["primary_exit"]["slots"]:
                for ev in slot["evidence_any"]:
                    folded = _fold(ev)
                    self.assertNotIn("gust", folded, sc["id"])
                    self.assertNotIn("hace", folded, sc["id"])

    def test_meet_captain_task_flow(self):
        scene = next(s for s in self._shipped() if s["id"] == "boat_meet_captain")
        st = task_from_scene(scene)
        st = evaluate_turn(st, "¡Hola! ¿Cómo te llamas?", scene)
        self.assertIn("greet", st.slots_filled)
        self.assertIn("captain_name", st.slots_filled)
        self.assertEqual(st.status, "open")
        st = evaluate_turn(st, "¿Como estas hoy?", scene)  # unaccented learner
        self.assertEqual(st.status, "done")
        self.assertIn("TASK COMPLETE", task_instructions(st, scene))

    def test_hints_expose_task_fields(self):
        hints = scene_hints_for_prompt(self._shipped())
        for h in hints:
            self.assertIsInstance(h["primary_exit"], dict)
            self.assertIsInstance(h["tutor_private_info"], dict)
            self.assertIsInstance(h["learner_must_obtain"], list)


if __name__ == "__main__":
    unittest.main()
