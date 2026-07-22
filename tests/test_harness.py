"""Harness edge cases from the Grok round-3 code review (B-3, B-4, B-5)."""

import contextlib
import io
import unittest

from tutor.cli import StreamScrubber
from tutor.student import default_state, extract_state

STATE_BLOCK = (
    '<session_state>\n{"current_unit": 4, "goal": "g", '
    '"observed_misconceptions": ["M-4.1"], "mastered": [], "struggling": [], '
    '"current_item_attempts": 1, "revisit_queue": []}\n</session_state>'
)


def scrub(chunks):
    scrubber = StreamScrubber()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        for chunk in chunks:
            scrubber.feed(chunk)
        scrubber.close()
    return out.getvalue()


class TestStreamScrubber(unittest.TestCase):
    def test_no_marker_emits_everything(self):
        self.assertEqual(scrub(["Hola, ", "¿cómo estás?"]), "Hola, ¿cómo estás?")

    def test_marker_split_across_deltas(self):
        self.assertEqual(scrub(["Bien.\n<session_st", "ate>{}</session_state>"]), "Bien.\n")

    def test_marker_at_start(self):
        self.assertEqual(scrub(["<session_state>{}</session_state>"]), "")

    def test_char_by_char(self):
        text = "Sí. " + STATE_BLOCK
        self.assertEqual(scrub(list(text)), "Sí. ")

    def test_truncated_marker_not_leaked(self):  # B-4
        self.assertEqual(scrub(["Done.\n\n", "<session_st"]), "Done.\n\n")


class TestExtractState(unittest.TestCase):
    def test_complete_block(self):
        visible, state = extract_state("Good try!\n\n" + STATE_BLOCK, default_state())
        self.assertEqual(visible, "Good try!")
        self.assertEqual(state["observed_misconceptions"], ["M-4.1"])

    def test_missing_block_keeps_previous(self):
        prev = default_state()
        visible, state = extract_state("just text", prev)
        self.assertEqual((visible, state), ("just text", prev))

    def test_malformed_json_keeps_previous(self):
        prev = default_state()
        visible, state = extract_state(
            "hi <session_state>{bad</session_state>", prev
        )
        self.assertEqual((visible, state), ("hi", prev))

    def test_unclosed_block_hidden(self):  # B-5
        prev = default_state()
        visible, state = extract_state(
            'ok\n<session_state>\n{"current_unit": 2', prev
        )
        self.assertEqual(visible, "ok")
        self.assertEqual(state, prev)


if __name__ == "__main__":
    unittest.main()
