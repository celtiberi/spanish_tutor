"""Debug request capture (web debug box): ring buffer, entry shape, endpoint.

Item source: user request 2026-07-28 ("I want to see what we are sending to
the ai server"). The ring is IN-MEMORY only — nothing here touches disk logs.
"""

import time
import unittest
from collections import deque
from types import SimpleNamespace

from tutor.conv_session import (
    DEBUG_RING_SIZE,
    ConversationalSession,
    build_debug_entry,
)
from tutor.session_memory import SessionMemory


def _system_blocks():
    return [
        {
            "type": "text",
            "text": "# You are a skilled conversational Spanish tutor\n\nstance…",
        },
        {"type": "text", "text": "# Tutor persona — Marisol\n\npersona…"},
        {
            "type": "text",
            "text": "# Course pack palette (stay in scope)\nPACK…",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _make_entry(turn=0):
    task = '<tutor_turn_task>\n{"turn": {}}\n</tutor_turn_task>\n'
    return build_debug_entry(
        model="claude-test",
        system=_system_blocks(),
        messages=[
            {"role": "user", "content": "(session open)"},
            {"role": "assistant", "content": "¡Hola! Me llamo Marisol."},
            {"role": "user", "content": task},
        ],
        task=task,
        decision_dict={
            "mode": "conversation",
            "reason": "default_conversation",
            "hard_break": False,
            "instructions": "SESSION PHASE: NEW INPUT — introduce at most ONE…",
        },
        usage={
            "input_tokens": 1000 + turn,
            "output_tokens": 200,
            "thinking_tokens": 30,
            "cached_input_tokens": 900,
        },
        gate_result=SimpleNamespace(
            faults=["gate:probe_loop"], notes=["tl_ratio=0.80"]
        ),
        notes=["output_gate_soft_fail:gate:probe_loop", "mode=conversation"],
        stop_reason="end_turn",
        turn=turn,
        is_open=(turn == 0),
    )


class TestDebugEntryShape(unittest.TestCase):
    def test_entry_has_labeled_system_blocks_and_instructions(self):
        e = _make_entry(turn=3)
        labels = [b["label"] for b in e["system_blocks"]]
        self.assertEqual(labels, ["tutor_stance", "persona", "course_pack"])
        # Full text kept (local debug tool — no truncation)
        self.assertIn("stance…", e["system_blocks"][0]["text"])
        self.assertTrue(e["system_blocks"][2]["cached"])
        # The mode-decision instruction stack is its own field
        self.assertIn("SESSION PHASE", e["instructions"])
        self.assertEqual(e["mode"], "conversation")
        self.assertEqual(e["reason"], "default_conversation")
        self.assertEqual(e["model"], "claude-test")

    def test_entry_history_excludes_task_message(self):
        e = _make_entry(turn=2)
        self.assertEqual(len(e["history"]), 2)
        self.assertEqual(e["history"][0]["role"], "user")
        self.assertEqual(e["history"][1]["role"], "assistant")
        self.assertIn("tutor_turn_task", e["task_message"])

    def test_entry_response_meta(self):
        e = _make_entry(turn=1)
        r = e["response"]
        self.assertEqual(r["usage"]["input_tokens"], 1001)
        self.assertEqual(r["usage"]["thinking_tokens"], 30)
        self.assertEqual(r["usage"]["cached_input_tokens"], 900)
        self.assertEqual(r["gate_faults"], ["gate:probe_loop"])
        self.assertIn("tl_ratio=0.80", r["gate_notes"])
        self.assertIn("mode=conversation", r["notes"])
        self.assertEqual(r["stop_reason"], "end_turn")

    def test_entry_is_json_safe(self):
        import json

        json.dumps(_make_entry(turn=5))


class TestDebugRingBuffer(unittest.TestCase):
    def test_ring_caps_at_ten(self):
        self.assertEqual(DEBUG_RING_SIZE, 10)
        sess = ConversationalSession.__new__(ConversationalSession)
        sess.model = "claude-test"
        sess.pedagogy_memory = SessionMemory()
        sess.debug_requests = deque(maxlen=DEBUG_RING_SIZE)
        for i in range(13):
            sess.pedagogy_memory.turns = i
            sess._capture_debug_request(
                system=_system_blocks(),
                messages=[{"role": "user", "content": f"task {i}"}],
                task=f"task {i}",
                decision_dict={"mode": "conversation", "reason": "r"},
                usage={"input_tokens": i},
                gate_result=None,
                notes=[],
                stop_reason="end_turn",
                is_open=False,
            )
        self.assertEqual(len(sess.debug_requests), 10)
        # Oldest 3 dropped; newest kept
        self.assertEqual(sess.debug_requests[0]["turn"], 3)
        self.assertEqual(sess.debug_requests[-1]["turn"], 12)

    def test_capture_never_raises(self):
        sess = ConversationalSession.__new__(ConversationalSession)
        sess.model = "claude-test"
        sess.pedagogy_memory = SessionMemory()
        sess.debug_requests = deque(maxlen=DEBUG_RING_SIZE)
        # Hostile inputs must not break the turn
        sess._capture_debug_request(
            system=None,
            messages=None,
            task=None,
            decision_dict=None,
            usage=None,
            gate_result=None,
            notes=None,
            stop_reason="",
            is_open=False,
        )
        self.assertEqual(len(sess.debug_requests), 1)


class TestDebugEndpoint(unittest.TestCase):
    """GET /api/debug/requests: valid JSON always; newest first."""

    def setUp(self):
        from tutor import web_app

        self.web_app = web_app
        self._saved = dict(web_app._sessions)
        web_app._sessions.clear()

    def tearDown(self):
        self.web_app._sessions.clear()
        self.web_app._sessions.update(self._saved)

    def _client(self):
        from fastapi.testclient import TestClient

        return TestClient(self.web_app.app)

    def test_no_session_returns_valid_empty_json(self):
        r = self._client().get("/api/debug/requests")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["entries"], [])
        self.assertFalse(data["session"])

    def test_entries_newest_first(self):
        sess = SimpleNamespace(
            debug_requests=deque(
                [_make_entry(turn=1), _make_entry(turn=2), _make_entry(turn=3)],
                maxlen=DEBUG_RING_SIZE,
            )
        )
        self.web_app._sessions["sid-debug-test"] = {
            "session": sess,
            "touched": time.time(),
            "opened": True,
        }
        client = self._client()
        client.cookies.set(self.web_app.COOKIE, "sid-debug-test")
        r = client.get("/api/debug/requests")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["session"])
        self.assertEqual(data["count"], 3)
        self.assertEqual([e["turn"] for e in data["entries"]], [3, 2, 1])
        # Shape: system blocks + instructions ride through the endpoint
        first = data["entries"][0]
        self.assertIn("system_blocks", first)
        self.assertIn("instructions", first)
        self.assertIn("task_message", first)
        self.assertIn("response", first)


if __name__ == "__main__":
    unittest.main()
