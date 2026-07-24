"""CLI color helpers."""

import unittest

from tutor.term import Palette, paint


class TestTerm(unittest.TestCase):
    def test_disabled_is_plain(self):
        p = Palette(enabled=False)
        self.assertEqual(paint("hi", "tutor", p=p), "hi")
        self.assertEqual(p.err, "")

    def test_enabled_wraps(self):
        p = Palette(enabled=True)
        out = paint("hi", "err", p=p)
        self.assertIn("hi", out)
        self.assertTrue(out.startswith("\033["))
        self.assertTrue(out.endswith(p.reset))


if __name__ == "__main__":
    unittest.main()
