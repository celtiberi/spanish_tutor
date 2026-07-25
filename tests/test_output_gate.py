"""Output gate + hard observer (no live API)."""

import unittest

from tutor.character_sheet import default_sheet, process_turn
from tutor.output_gate import (
    check_output_gate,
    detect_tutor_probe_keys,
    tutor_spanish_ratio,
)


class TestOutputGate(unittest.TestCase):
    def test_spanish_ratio_high(self):
        r = tutor_spanish_ratio("¡Hola! Estoy bien. ¿Cómo estás hoy?")
        self.assertIsNotNone(r)
        self.assertGreaterEqual(r, 0.5)

    def test_spanish_ratio_english_wall(self):
        r = tutor_spanish_ratio(
            "Good job! That means how are you. Please try to say the word hello."
        )
        self.assertIsNotNone(r)
        self.assertLess(r, 0.35)

    def test_probe_keys(self):
        k = detect_tutor_probe_keys("¿Cómo te llamas?")
        self.assertIn("ask_name", k)

    def test_gate_ok_spanish_teach(self):
        parts = {
            "acknowledge": "¡Qué bien!",
            "model": "Me llamo Sofía.",
            "try": "¿Y tú? ¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¡Qué bien! Me llamo Sofía. ¿Cómo te llamas?",
            is_open=False,
            already_asked=set(),
            already_shown=set(),
        )
        self.assertTrue(g.ok, g.faults)

    def test_gate_loop_reask_name(self):
        parts = {
            "acknowledge": "¡Hola!",
            "model": "Me llamo Sofía.",
            "try": "¿Cómo te llamas?",
            "structured": True,
        }
        g = check_output_gate(
            parts,
            "¿Cómo te llamas?",
            already_asked={"ask_name"},
            already_shown={"name"},
        )
        self.assertFalse(g.ok)
        self.assertIn("gate:probe_loop", g.faults)

    def test_gate_english_wall(self):
        parts = {
            "acknowledge": "Good job you nailed it!",
            "model": "That means my name is.",
            "try": "Please say your name in Spanish now.",
            "structured": True,
        }
        g = check_output_gate(parts, "Good job...", is_open=False)
        self.assertFalse(g.ok)
        self.assertIn("gate:english_wall", g.faults)

    def test_gate_no_teach_move(self):
        parts = {
            "acknowledge": "¡Hola amigo!",
            "continue": "¿Todo bien?",
            "structured": True,
        }
        g = check_output_gate(parts, "¡Hola!", is_open=False)
        self.assertFalse(g.ok)
        self.assertTrue(any("teach" in f or "pedagogy" in f for f in g.faults))


class TestHardObserver(unittest.TestCase):
    def test_tool_path_still_bumps_from_learner_text(self):
        sheet = default_sheet()
        # Simulate tool that barely updates
        tool_delta = {
            "reason": "saw greeting",
            "skills": {
                "IP-01": {"status": "emerging", "confidence": 0.2},
            },
        }
        s, _, notes = process_turn(
            sheet,
            "Hola, estoy bien. Me llamo Patrick.",
            "¡Hola Patrick!",
            tool_delta=tool_delta,
        )
        self.assertIn("hard_observer", notes)
        self.assertIn("tool_update", notes)
        # Rule evidence should raise name / estoy even if tool was thin
        ip3 = (s.get("skills") or {}).get("IP-03") or {}
        ip4 = (s.get("skills") or {}).get("IP-04") or {}
        self.assertGreater(float(ip3.get("confidence") or 0), 0.05)
        self.assertGreater(float(ip4.get("confidence") or 0), 0.05)
        self.assertEqual(
            (s.get("identity") or {}).get("preferred_name", "").lower(),
            "patrick",
        )


if __name__ == "__main__":
    unittest.main()
