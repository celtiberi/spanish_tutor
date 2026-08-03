"""Model traffic log + session-log hygiene (USER 2026-08-03: "I want to
see what is being sent and received" / "There were way too many. I
couldn't tell what was going on").

Every tutor model call's full request + response — system blocks, task,
history window, raw provider text (pre <plan>-harvest), visible reply,
usage — mirrors from the debug ring to
``logs/sessions/<YYYY-MM-DD>/<session_id>.requests.jsonl`` when session
logging is on.  Full text, no truncation.

Hygiene contract (full-code-audit S8): creation is LAZY — an open-only
session (page-load probe / reload) leaves ZERO files; the first user
turn creates the dated files and flushes the buffered open exchange.
"""

from __future__ import annotations

import json

from tutor import config
from tutor.conv_session import build_debug_entry
from tutor.session_log import SessionLogger


def _entry(*, is_open=False, raw="RAW", reply="VISIBLE", system=None, task="T"):
    return build_debug_entry(
        model="fake",
        system=[{"type": "text", "text": "stance"}] if system is None else system,
        messages=[],
        task=task,
        usage=None,
        raw=raw,
        reply=reply,
        is_open=is_open,
    )


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


def test_log_model_exchange_writes_full_entry_in_dated_dir(monkeypatch, tmp_path):
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

    # Dated layout: logs/sessions/<YYYY-MM-DD>/<id>.requests.jsonl
    assert logger.requests_path.parent.parent == tmp_path
    day = logger.requests_path.parent.name
    assert len(day) == 10 and day[4] == "-" and day[7] == "-"
    lines = logger.requests_path.read_text(encoding="utf-8").splitlines()
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
    entry = _entry(raw="", reply="", system=[])
    for gone in ("mode", "reason", "instructions", "hard_break"):
        assert gone not in entry
    logger.log_model_exchange(entry)
    got = json.loads(logger.requests_path.read_text())
    assert "router_shadow_NOT_SENT" not in got
    assert set(got["sent"]) == {"system_blocks", "history", "task_message"}


# --- Lazy creation (full-code-audit S8 log hygiene) -----------------------


def test_open_only_session_leaves_zero_files(monkeypatch, tmp_path):
    """A session that opens and never receives a learner turn writes
    NOTHING — no jsonl, no md, no requests, no dated dir."""
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    logger = SessionLogger(arch="conversational", label="probe")
    # Opening tutor turn: model exchange + turn record, both open-tagged.
    logger.log_model_exchange(_entry(is_open=True, reply="¡Hola!"))
    logger.log_simple_turn(
        learner="(session open)", visible="¡Hola!", state={}, is_open=True,
    )
    assert logger.close(mode="conversational") is None
    assert not logger.real
    assert list(tmp_path.rglob("*")) == []


def test_first_user_turn_creates_dated_files_with_buffered_open(
    monkeypatch, tmp_path
):
    """The first user turn makes the session real: dated files appear,
    session_start + the buffered open turn + open exchange flush FIRST,
    in order."""
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    logger = SessionLogger(arch="conversational", label="real")
    logger.log_model_exchange(_entry(is_open=True, reply="¡Hola!"))
    logger.log_simple_turn(
        learner="(session open)", visible="¡Hola!", state={}, is_open=True,
    )
    assert list(tmp_path.rglob("*")) == []  # still nothing on disk

    # First user turn: exchange first (mirrors the pipeline order), then turn.
    logger.log_model_exchange(_entry(is_open=False, reply="¿Cómo estás?"))
    logger.log_simple_turn(
        learner="hola", visible="¿Cómo estás?", state={},
    )
    assert logger.real
    day = logger.log_dir.name
    assert logger.log_dir.parent == tmp_path
    assert len(day) == 10 and day[4] == "-" and day[7] == "-"

    # Main log: session_start, buffered open turn, user turn — in order.
    events = [
        json.loads(line)
        for line in logger.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [e["event"] for e in events] == ["session_start", "turn", "turn"]
    assert events[1]["learner"] == "(session open)"
    assert events[2]["learner"] == "hola"

    # Traffic log: buffered open exchange present, before the user one.
    reqs = [
        json.loads(line)
        for line in logger.requests_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [r["is_open"] for r in reqs] == [True, False]
    assert reqs[0]["received"]["reply"] == "¡Hola!"

    # Markdown twin exists in the same dated dir with the header.
    md = logger.md_path.read_text(encoding="utf-8")
    assert md.startswith(f"# Session `{logger.session_id}`")
    assert "## Turn 1" in md and "## Turn 2" in md

    # Close now writes session_end (session was real).
    assert logger.close(mode="conversational") == logger.jsonl_path
    tail = json.loads(
        logger.jsonl_path.read_text(encoding="utf-8").splitlines()[-1]
    )
    assert tail["event"] == "session_end"


def test_all_three_files_share_one_dated_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    logger = SessionLogger(arch="conversational", label="layout")
    logger.log_model_exchange(_entry(is_open=False))
    logger.log_simple_turn(learner="hola", visible="hola", state={})
    assert logger.jsonl_path.parent == logger.log_dir
    assert logger.md_path.parent == logger.log_dir
    assert logger.requests_path.parent == logger.log_dir
    assert {p.name for p in logger.log_dir.iterdir()} == {
        f"{logger.session_id}.jsonl",
        f"{logger.session_id}.md",
        f"{logger.session_id}.requests.jsonl",
    }


def test_buffered_events_flush_with_realness(monkeypatch, tmp_path):
    """Generic events emitted before the first user turn buffer with the
    session_start record and flush in order once the session is real."""
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    logger = SessionLogger(arch="conversational", label="events")
    logger.event("early", detail="pre-real")
    assert list(tmp_path.rglob("*")) == []
    logger.log_simple_turn(learner="hola", visible="ok", state={})
    events = [
        json.loads(line)
        for line in logger.jsonl_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [e["event"] for e in events] == ["session_start", "early", "turn"]
