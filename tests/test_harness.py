"""Harness edge cases from the Grok code reviews (scrubber, state, profile)."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tutor.cli import StreamScrubber
from tutor.student import (
    default_state,
    extract_state,
    load_profile,
    save_profile,
    state_message,
)

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
        visible, state, ok = extract_state(
            "Good try!\n\n" + STATE_BLOCK, default_state()
        )
        self.assertEqual(visible, "Good try!")
        self.assertEqual(state["observed_misconceptions"], ["M-4.1"])
        self.assertTrue(ok)

    def test_missing_block_keeps_previous(self):
        prev = default_state()
        visible, state, ok = extract_state("just text", prev)
        self.assertEqual((visible, state), ("just text", prev))
        self.assertFalse(ok)

    def test_malformed_json_keeps_previous(self):
        prev = default_state()
        visible, state, ok = extract_state(
            "hi <session_state>{bad</session_state>", prev
        )
        self.assertEqual((visible, state), ("hi", prev))
        self.assertFalse(ok)

    def test_unclosed_block_hidden(self):  # B-5
        prev = default_state()
        visible, state, ok = extract_state(
            'ok\n<session_state>\n{"current_unit": 2', prev
        )
        self.assertEqual(visible, "ok")
        self.assertEqual(state, prev)
        self.assertFalse(ok)


class TestProfilePersistence(unittest.TestCase):
    def test_durable_fields_carry_session_locals_reset(self):
        state = default_state()
        state.update(
            current_unit=4,
            goal="ser vs estar",
            current_item_attempts=2,
            revisit_queue=["P-4.1"],
            observed_misconceptions=["M-4.1"],
            review_schedule=[
                {"item": "location estar", "misconception": "M-4.1",
                 "due": "2026-07-23", "successes": 0}
            ],
        )
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "profile.json"
            save_profile(path, state)
            loaded = load_profile(path)
        self.assertEqual(loaded["current_unit"], 4)
        self.assertEqual(loaded["observed_misconceptions"], ["M-4.1"])
        self.assertEqual(loaded["review_schedule"][0]["due"], "2026-07-23")
        self.assertIsNone(loaded["goal"])
        self.assertEqual(loaded["current_item_attempts"], 0)
        self.assertEqual(loaded["revisit_queue"], [])

    def test_missing_and_corrupt_profile_fall_back_to_default(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_profile(Path(d) / "nope.json"), default_state())
            bad = Path(d) / "bad.json"
            bad.write_text("{not json")
            self.assertEqual(load_profile(bad), default_state())

    def test_state_message_carries_iso_date(self):
        content = state_message(default_state())["content"]
        self.assertRegex(content, r"^Today's date: \d{4}-\d{2}-\d{2}\.")

    def test_state_message_parse_failed_warning(self):
        content = state_message(default_state(), parse_failed=True)["content"]
        self.assertIn("state parse failed", content)
        self.assertNotIn(
            "state parse failed", state_message(default_state())["content"]
        )

    def test_state_message_due_warmup_note(self):
        state = default_state()
        state["review_schedule"] = [
            {"item": "x", "misconception": None, "due": "2000-01-01",
             "successes": 0}
        ]
        self.assertIn(
            "due-item warm-up",
            state_message(state, session_open=True)["content"],
        )
        # not at session open -> no nag
        self.assertNotIn(
            "due-item warm-up", state_message(state)["content"]
        )
        # nothing due -> no note
        state["review_schedule"][0]["due"] = "9999-01-01"
        self.assertNotIn(
            "due-item warm-up",
            state_message(state, session_open=True)["content"],
        )


if __name__ == "__main__":
    unittest.main()
