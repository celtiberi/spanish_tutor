"""AI student harness helpers (no live API)."""

import unittest

from tutor.ai_student import (
    PERSONAS,
    TrueAbility,
    get_persona,
    _verification_checks,
)
from tutor.ai_student import SimTurn


class TestAiStudent(unittest.TestCase):
    def test_personas(self):
        self.assertIn("alex_boat", PERSONAS)
        p = get_persona("alex_boat")
        self.assertEqual(p["name"], "Alex")
        self.assertTrue(p["error_tendencies"])

    def test_true_ability_learning(self):
        p = get_persona("alex_boat")
        t = TrueAbility.from_persona(p)
        eid = "estar_yo_estoy_vs_esta"
        before = t.error_strength[eid]
        notes = t.on_tutor_reply(
            "Try this: **Estoy en el bote.** For yo we use estoy.",
            p,
        )
        self.assertTrue(any("learn:" in n for n in notes))
        self.assertLess(t.error_strength[eid], before)

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


if __name__ == "__main__":
    unittest.main()
