"""Structured multi-part tutor replies."""

import unittest

from tutor.tutor_response import (
    compose_visible,
    parse_tutor_response,
    process_tutor_raw,
)


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


if __name__ == "__main__":
    unittest.main()
