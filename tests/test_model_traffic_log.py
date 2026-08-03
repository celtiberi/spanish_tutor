"""Model traffic log (USER 2026-08-03: "I want to see what is being sent
and received").

Every tutor model call's full request + response — system blocks, task,
history window, raw provider text (pre <plan>-harvest), visible reply,
usage — mirrors from the debug ring to
``logs/sessions/<session_id>.requests.jsonl`` when session logging is on.
Full text, no truncation.
"""

from __future__ import annotations

import json

from tutor import config
from tutor.conv_session import build_debug_entry
from tutor.session_log import SessionLogger


def test_debug_entry_carries_raw_and_reply():
    entry = build_debug_entry(
        model="fake",
        system=[{"type": "text", "text": "stance"}],
        messages=[{"role": "user", "content": "task"}],
        task="task",
        usage={"input_tokens": 10, "output_tokens": 5},
        raw="<plan>secret</plan><tutor>hola</tutor>",
        reply="hola",
    )
    assert entry["response"]["raw"] == "<plan>secret</plan><tutor>hola</tutor>"
    assert entry["response"]["reply"] == "hola"
    assert entry["system_blocks"][0]["text"] == "stance"


def test_log_model_exchange_writes_full_entry(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    logger = SessionLogger(arch="conversational", label="traffictest")
    entry = build_debug_entry(
        model="fake",
        system=[{"type": "text", "text": "S" * 5000}],  # no truncation
        messages=[],
        task="T",
        usage=None,
        raw="RAW",
        reply="VISIBLE",
    )
    logger.log_model_exchange(entry)
    logger.log_model_exchange(entry)  # appends, one JSON line each

    path = tmp_path / f"{logger.session_id}.requests.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    got = json.loads(lines[0])
    # sent / received are structurally distinct (incident 2026-08-03: flat
    # entries let shadow "instructions" read as shipped prompt text; the
    # router_shadow_NOT_SENT key died with the router — entries no longer
    # carry shadow fields at all).
    assert got["sent"]["system_blocks"][0]["text"] == "S" * 5000
    assert got["received"]["raw"] == "RAW"
    assert got["received"]["reply"] == "VISIBLE"
    assert "system_blocks" not in got and "response" not in got


def test_entries_carry_no_router_shadow_fields(monkeypatch, tmp_path):
    # Router teardown 2026-08-03: debug entries carry NO mode/reason/
    # instructions/hard_break — there is no shadow router text to leak.
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    logger = SessionLogger(arch="conversational", label="shadowtest")
    entry = build_debug_entry(
        model="fake", system=[], messages=[], task="T",
        usage=None, raw="", reply="",
    )
    for gone in ("mode", "reason", "instructions", "hard_break"):
        assert gone not in entry
    logger.log_model_exchange(entry)
    got = json.loads(
        (tmp_path / f"{logger.session_id}.requests.jsonl").read_text()
    )
    assert "router_shadow_NOT_SENT" not in got
    assert set(got["sent"]) == {"system_blocks", "history", "task_message"}
