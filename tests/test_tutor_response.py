"""Structured multi-part tutor replies."""

import unittest

from tutor.tutor_response import (
    compose_visible,
    parse_tutor_response,
    process_tutor_raw,
)
from tutor.output_gate import check_output_gate, detect_sheet_leak


class TestTutorResponse(unittest.TestCase):
    def test_unstructured_passthrough(self):
        p = parse_tutor_response("Hola! How are you?")
        self.assertFalse(p.raw_had_structure)
        self.assertEqual(p.continue_, "Hola! How are you?")
        self.assertEqual(compose_visible(p), "Hola! How are you?")

    def test_full_structure_with_recast(self):
        raw = """
        <tutor>
          <acknowledge>Got it — things are fine.</acknowledge>
          <recast>**Todo va bien** (or **Todo está bien**).</recast>
          <explain depth="brief">Pick va or está — not both.</explain>
          <continue>¿Y tú?</continue>
        </tutor>
        """
        p = parse_tutor_response(raw)
        self.assertTrue(p.raw_had_structure)
        self.assertTrue(p.has_recast())
        self.assertIn("Todo va bien", p.recast)
        self.assertEqual(p.explain_depth, "brief")
        self.assertIn("¿Y tú?", p.continue_)
        visible = compose_visible(p)
        self.assertIn("Got it", visible)
        self.assertIn("Todo va bien", visible)
        self.assertIn("¿Y tú?", visible)
        # Tags must not leak
        self.assertNotIn("<recast>", visible)
        self.assertNotIn("</tutor>", visible)

    def test_process_tutor_raw(self):
        raw = "<tutor><continue>¡Hola!</continue></tutor>"
        vis, parts = process_tutor_raw(raw)
        self.assertEqual(vis, "¡Hola!")
        self.assertTrue(parts.as_dict().get("structured"))

    def test_deep_explain_attr(self):
        raw = '<explain depth="deep">Longer why…</explain><continue>Go on.</continue>'
        p = parse_tutor_response(raw)
        self.assertEqual(p.explain_depth, "deep")

    def test_model_and_try_parts(self):
        raw = """
        <tutor>
          <model>**Estoy bien.** / **Estoy más o menos.**</model>
          <try>¿Cómo estás hoy?</try>
        </tutor>
        """
        p = parse_tutor_response(raw)
        self.assertTrue(p.raw_had_structure)
        self.assertIn("Estoy bien", p.model)
        self.assertIn("Cómo estás", p.try_)
        self.assertTrue(p.has_teach_move())
        vis = compose_visible(p)
        self.assertIn("Estoy bien", vis)
        self.assertIn("Cómo estás", vis)
        d = p.as_dict()
        self.assertIn("model", d)
        self.assertIn("try", d)

    def test_sheet_json_is_gate_fault_not_silent_success(self):
        """Root fault: model dumps sheet JSON. Gate must fail; do not hide it."""
        raw = """
        <tutor>
          <acknowledge>¡Qué bien, Patrick! Es genial estar en el bote.</acknowledge>
          <model>Yo estoy en mi casa hoy con un café.</model>
        ```json { "active_error_focus": [ { "id": "estar_yo_estoy_vs_esta", "resolved_streak": 1, "correct_uses": 1 } ], "grammar": { "present_estar_person": { "confidence": 0.82, "solid_uses": 7 } } } ```
        <try>Y tu hermana Carolyn, ¿cómo está?
        </tutor>
        """
        self.assertTrue(detect_sheet_leak(raw))
        vis, parts = process_tutor_raw(raw)
        # Parser may still extract real parts (try unclosed) — that is fine
        self.assertIn("Qué bien", parts.acknowledge)
        self.assertIn("Carolyn", parts.try_ or "")
        # Leftover sheet dump must not be promoted into continue as "content"
        self.assertNotIn("active_error_focus", parts.continue_ or "")
        # Gate on raw must fail so session will repair
        gate = check_output_gate(
            parts.as_dict(), vis, mode="transfer", raw=raw,
        )
        self.assertFalse(gate.ok)
        self.assertIn("gate:sheet_leak", gate.faults)
        self.assertIn("sheet", gate.repair_instruction.lower())

    def test_clean_turn_no_false_sheet_leak(self):
        raw = """
        <tutor>
          <acknowledge>¡Muy bien!</acknowledge>
          <model>Estoy en el bote.</model>
          <try>¿Dónde estás tú?</try>
        </tutor>
        """
        self.assertFalse(detect_sheet_leak(raw))
        vis, parts = process_tutor_raw(raw)
        gate = check_output_gate(parts.as_dict(), vis, mode="conversation", raw=raw)
        self.assertNotIn("gate:sheet_leak", gate.faults)


if __name__ == "__main__":
    unittest.main()
