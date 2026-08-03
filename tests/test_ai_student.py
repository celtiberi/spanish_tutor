"""AI-student harness fixes (full-code-audit S7.14, no API).

Pins: single `state_parse_failed` note per parse failure (the historical
merge/respond/loop re-appends triple-counted every failure),
`true_ability_frozen` minted once per freeze episode, and the student call
max_tokens raised to 2048 (768 stopped fitting the growing learner_state
JSON around turn 7, silently freezing true_ability).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tutor.ai_student import (
    AIStudentAgent,
    extract_learner_output,
    get_persona,
    merge_learner_state,
)

REPO = Path(__file__).resolve().parent.parent


def _fake_agent(replies: list[str], calls: list[dict]) -> AIStudentAgent:
    class _FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            raw = replies[min(len(calls) - 1, len(replies) - 1)]
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=raw)],
                usage=SimpleNamespace(input_tokens=10, output_tokens=20),
                stop_reason="end_turn",
            )

    client = SimpleNamespace(messages=_FakeMessages())
    with mock.patch("tutor.config.make_client_for", return_value=client), \
            mock.patch(
                "tutor.config.caps_for",
                return_value=SimpleNamespace(model="fake-student"),
            ):
        return AIStudentAgent(get_persona("alex_boat"), model="fake-student")


_GOOD_STATE = (
    "Hola, estoy en el bote.\n<learner_state>"
    + json.dumps({"forms": {}, "turns": 1})
    + "</learner_state>"
)
_BROKEN_STATE = "Um… hola. <learner_state>{this is not json"


class TestParseNotesSingleCount(unittest.TestCase):
    def test_merge_mints_one_note_on_missing_state(self):
        prev = {"turns": 3, "forms": {}}
        out, notes = merge_learner_state(prev, None)
        self.assertEqual(notes, ["state_parse_failed"])
        self.assertEqual(out["turns"], 3)  # frozen: turns does not advance

    def test_extract_broken_state_reports_parse_fail(self):
        visible, state, ok = extract_learner_output(_BROKEN_STATE)
        self.assertFalse(ok)
        self.assertIsNone(state)
        self.assertNotIn("<learner_state>", visible)

    def test_respond_failure_notes_once_plus_freeze_episode(self):
        calls: list[dict] = []
        agent = _fake_agent(
            [_BROKEN_STATE, _BROKEN_STATE, _GOOD_STATE, _BROKEN_STATE], calls
        )
        # First failure: one parse note + the freeze becomes visible once
        agent.respond("¡Hola! ¿Cómo estás?")
        self.assertEqual(
            agent.last_state_notes.count("state_parse_failed"), 1
        )
        self.assertEqual(
            agent.last_state_notes.count("true_ability_frozen"), 1
        )
        self.assertNotIn("parse_miss", agent.last_state_notes)
        # Second consecutive failure: still one parse note, no repeat freeze
        agent.respond("¿Dónde estás?")
        self.assertEqual(
            agent.last_state_notes.count("state_parse_failed"), 1
        )
        self.assertNotIn("true_ability_frozen", agent.last_state_notes)
        # Success closes the episode
        agent.respond("¿Qué tal el bote?")
        self.assertNotIn("state_parse_failed", agent.last_state_notes)
        self.assertNotIn("true_ability_frozen", agent.last_state_notes)
        # A new failure opens a NEW episode: frozen note minted again
        agent.respond("¿Y el café?")
        self.assertEqual(
            agent.last_state_notes.count("true_ability_frozen"), 1
        )

    def test_sim_loop_has_no_parse_miss_alias(self):
        src = (REPO / "tutor" / "ai_student.py").read_text(encoding="utf-8")
        self.assertNotIn('"parse_miss"', src)


class TestStudentCallBudget(unittest.TestCase):
    def test_max_tokens_2048(self):
        calls: list[dict] = []
        agent = _fake_agent([_GOOD_STATE], calls)
        agent.respond("¡Hola!")
        self.assertEqual(calls[0]["max_tokens"], 2048)


class TestSmokeClampsPinned(unittest.TestCase):
    """run_student_smoke exercises the REAL grades path (S7.11): tools on,
    per-run GRADE_LOG_PATH pinned beside the other ledgers."""

    def test_smoke_source_clamps(self):
        src = (REPO / "evals" / "run_student_smoke.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('os.environ.setdefault("SHEET_TOOLS", "true")', src)
        self.assertIn("use_tools=True", src)
        self.assertNotIn("use_tools=False", src)
        self.assertIn(
            'os.environ["GRADE_LOG_PATH"] = str(outdir / "sheet_grades.jsonl")',
            src,
        )


if __name__ == "__main__":
    unittest.main()
