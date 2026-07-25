"""AI student harness helpers (no live API)."""

import unittest

from tutor.ai_student import (
    ABILITY_LEVELS,
    PERSONAS,
    TrueAbility,
    clean_student_utterance,
    extract_learner_output,
    get_ability_level,
    get_persona,
    initial_learner_state,
    merge_learner_state,
    _sheet_diff,
    _verification_checks,
)
from tutor.ai_student import SimTurn


class TestAiStudent(unittest.TestCase):
    def test_personas(self):
        self.assertIn("alex_boat", PERSONAS)
        self.assertIn("jordan_travel", PERSONAS)
        p = get_persona("alex_boat")
        self.assertEqual(p["name"], "Alex")
        self.assertTrue(p["error_tendencies"])

    def test_ability_levels(self):
        self.assertIn("novice_low", ABILITY_LEVELS)
        ab = get_ability_level("intermediate_low")
        self.assertEqual(ab["id"], "intermediate_low")
        self.assertLess(ab["english_ratio"], 0.3)

    def test_initial_learner_state_seeds_errors(self):
        p = get_persona("alex_boat")
        ab = get_ability_level(p["ability"], p)
        st = initial_learner_state(p, ab)
        self.assertIn("forms", st)
        self.assertIn("estoy_yo", st["forms"])
        self.assertEqual(st["forms"]["estoy_yo"]["status"], "error_prone")
        self.assertLess(st["forms"]["estoy_yo"]["confidence"], 0.5)

    def test_extract_learner_output_tags(self):
        raw = (
            'Um… yo está en el bote.\n\n'
            '<learner_state>\n'
            '{"level": "novice_low", "forms": {"estoy_yo": '
            '{"status": "error_prone", "confidence": 0.2, '
            '"attempts": 1, "successes": 0}}, '
            '"noticed_this_session": [], "can_try_now": [], '
            '"still_hard": ["yo/estoy"], "recent_recasts": [], '
            '"topic_intent": "boat", "self_check": "relapsed"}\n'
            '</learner_state>'
        )
        utt, state, ok = extract_learner_output(raw)
        self.assertTrue(ok)
        self.assertIn("está", utt.lower())
        self.assertNotIn("learner_state", utt.lower())
        self.assertEqual(state["forms"]["estoy_yo"]["attempts"], 1)

    def test_extract_hides_truncated_tag(self):
        raw = "Hola café\n\n<learner_state>\n{\"forms\": {"
        utt, state, ok = extract_learner_output(raw)
        self.assertFalse(ok)
        self.assertIsNone(state)
        self.assertEqual(utt.strip(), "Hola café")

    def test_merge_learner_state_clamps_jump(self):
        p = get_persona("alex_boat")
        ab = get_ability_level(p["ability"], p)
        prev = initial_learner_state(p, ab)
        old_c = prev["forms"]["estoy_yo"]["confidence"]
        incoming = {
            "forms": {
                "estoy_yo": {
                    "status": "usable",
                    "confidence": 0.99,  # magical jump
                    "attempts": 2,
                    "successes": 1,
                }
            },
            "can_try_now": ["Estoy en el bote"],
            "noticed_this_session": ["tutor said estoy"],
            "self_check": "tried estoy",
        }
        merged, notes = merge_learner_state(prev, incoming)
        new_c = merged["forms"]["estoy_yo"]["confidence"]
        self.assertLessEqual(new_c, old_c + 0.35 + 1e-6)
        self.assertEqual(merged["turns"], 1)
        self.assertIn("Estoy en el bote", merged["can_try_now"])
        self.assertTrue(any("clamp" in n or "form:estoy_yo" in n for n in notes))

    def test_true_ability_sync_from_state(self):
        p = get_persona("alex_boat")
        t = TrueAbility.from_persona(p)
        eid = "estar_yo_estoy_vs_esta"
        before = t.error_strength[eid]
        st = copy_state_with_boost(t.learner_state, "estoy_yo", 0.7)
        t.sync_from_state(st, p)
        self.assertLess(t.error_strength[eid], before)
        self.assertEqual(t.learner_state["forms"]["estoy_yo"]["confidence"], 0.7)

    def test_true_ability_on_tutor_reply_logs_model(self):
        p = get_persona("alex_boat")
        t = TrueAbility.from_persona(p)
        notes = t.on_tutor_reply(
            "Try this: **Estoy en el bote.** For yo we use estoy.",
            p,
        )
        self.assertTrue(any("tutor_modeled:" in n for n in notes))
        self.assertGreaterEqual(
            t.recasts_seen.get("estar_yo_estoy_vs_esta", 0), 1
        )

    def test_clean_student_strips_tutor_leak(self):
        raw = (
            "Um… estoy en mi barco?"
            "¡Muy bien, Alex! **Estoy en mi barco.** Perfect!"
        )
        cleaned = clean_student_utterance(raw, persona_name="Alex")
        self.assertIn("estoy", cleaned.lower())
        self.assertNotIn("Perfect", cleaned)
        self.assertNotIn("Muy bien", cleaned)

    def test_sheet_diff_error_count(self):
        before = {"error_patterns": {}, "skills": {}, "next_best": {}}
        after = {
            "error_patterns": {
                "estar_yo_estoy_vs_esta": {
                    "count": 2,
                    "last_examples": ["Yo está bien"],
                }
            },
            "skills": {"IP-04": {"status": "fragile", "confidence": 0.3}},
            "next_best": {"can_do": "IP-04"},
        }
        diff = _sheet_diff(before, after)
        self.assertTrue(any("estar_yo_estoy_vs_esta" in d for d in diff))
        self.assertTrue(any("IP-04" in d for d in diff))

    def test_verification_sheet_name(self):
        sheet = {"identity": {"name": "Alex"}, "error_patterns": {"active": {}}}
        true = TrueAbility(error_strength={"x": 0.5})
        log = [
            SimTurn(
                n=1,
                tutor_prompt="Hola",
                student="hola",
                tutor_reply="¡Hola!",
                sheet_notes=[],
                next_best={},
                learn_notes=[],
                parts={},
                true_ability=true.snapshot(),
            )
        ]
        checks = _verification_checks(sheet, true, log)
        by_id = {c["id"]: c for c in checks}
        self.assertTrue(by_id["sheet_has_name"]["ok"])
        self.assertTrue(by_id["teacher_replied"]["ok"])


def copy_state_with_boost(state: dict, form_key: str, conf: float) -> dict:
    import copy

    st = copy.deepcopy(state)
    forms = st.setdefault("forms", {})
    f = dict(forms.get(form_key) or {})
    f["confidence"] = conf
    f["status"] = "usable"
    f["successes"] = int(f.get("successes") or 0) + 1
    forms[form_key] = f
    return st


if __name__ == "__main__":
    unittest.main()
