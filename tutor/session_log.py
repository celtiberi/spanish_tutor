"""Full-fidelity session logging for tutor runs.

Three artifacts per session under ``logs/sessions/<YYYY-MM-DD>/``:
  - ``<id>.jsonl``          — machine-readable, one JSON object per event
  - ``<id>.md``             — human-readable transcript for review
  - ``<id>.requests.jsonl`` — model traffic log (full request + response)

Log hygiene (USER 2026-08-03: "There were way too many. I couldn't tell
what was going on"; full-code-audit S8):

- **Lazy creation.** Nothing touches disk until the session is REAL — the
  first user turn logged (or the first model exchange after a user turn).
  The session_start record, the opening tutor turn, and the open turn's
  model exchange are buffered in memory and flushed when the session
  becomes real. A page-load probe / reload that opens a session and never
  receives a learner turn leaves ZERO files.
- **Date subfolders.** ``config.LOG_DIR`` stays the root; the logger
  computes the dated dir once at creation, so one session's files always
  share a folder (even across midnight).
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from . import config


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _jsonable(obj: Any) -> Any:
    """Best-effort conversion for API objects / paths."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(x) for x in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _jsonable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "__dict__") and not isinstance(obj, type):
        try:
            return _jsonable({
                k: v for k, v in vars(obj).items()
                if not k.startswith("_")
            })
        except Exception:
            pass
    return str(obj)


class SessionLogger:
    def __init__(
        self,
        *,
        arch: str = "controller",
        label: str = "",
        meta: dict | None = None,
        session_id: str | None = None,
    ):
        now = datetime.datetime.now()
        stamp = now.strftime("%Y%m%d-%H%M%S")
        suffix = f"-{label}" if label else ""
        self.session_id = session_id or f"{stamp}-{arch}{suffix}"
        # Dated dir computed ONCE at creation (config.LOG_DIR is the root).
        self.log_dir = Path(config.LOG_DIR) / now.strftime("%Y-%m-%d")
        self.jsonl_path = self.log_dir / f"{self.session_id}.jsonl"
        self.md_path = self.log_dir / f"{self.session_id}.md"
        self.requests_path = self.log_dir / f"{self.session_id}.requests.jsonl"
        self.arch = arch
        self.turn_index = 0
        self._meta = {
            "session_id": self.session_id,
            "arch": arch,
            "label": label,
            "started_at": _utc_now(),
            **(meta or {}),
        }
        # Lazy creation: buffer everything until the first user turn.
        self._real = False
        self._pending_jsonl: list[dict] = [{
            "event": "session_start",
            "ts": self._meta["started_at"],
            **self._meta,
        }]
        self._pending_md: list[str] = [
            f"# Session `{self.session_id}`\n\n"
            f"- **arch:** {arch}\n"
            f"- **started:** {self._meta['started_at']}\n"
            f"- **meta:** `{json.dumps(_jsonable(meta or {}), ensure_ascii=False)}`\n\n"
            f"JSONL twin: `{self.jsonl_path.name}`\n\n---\n\n"
        ]
        self._pending_requests: list[dict] = []

    @property
    def real(self) -> bool:
        """True once files exist on disk (first user turn seen)."""
        return self._real

    def _ensure_real(self) -> None:
        """Create the dated dir + files and flush every buffered record.
        Called on the first non-open write; idempotent."""
        if self._real:
            return
        self._real = True
        self.log_dir.mkdir(parents=True, exist_ok=True)
        pending_jsonl, self._pending_jsonl = self._pending_jsonl, []
        for record in pending_jsonl:
            self._write_jsonl(record)
        pending_md, self._pending_md = self._pending_md, []
        if pending_md:
            with self.md_path.open("a", encoding="utf-8") as f:
                f.write("".join(pending_md))
        pending_requests, self._pending_requests = self._pending_requests, []
        for record in pending_requests:
            self._write_request(record)

    def log_model_exchange(self, entry: dict) -> None:
        """Full outbound request + response for ONE tutor model call, one
        JSON line, sibling file ``<session_id>.requests.jsonl`` (USER
        2026-08-03: "I want to see what is being sent and received").

        Structure is the honesty contract (incident 2026-08-03: the flat
        debug-ring entry printed router-shadow ``instructions`` next to
        ``system_blocks`` and the operator reasonably concluded scripts
        were shipping): ``sent`` holds EXACTLY what went to the model,
        ``received`` what came back.  (The ``router_shadow_NOT_SENT``
        pop-list died with the mode router, 2026-08-03 — debug entries no
        longer carry mode/reason/instructions/hard_break at all.)
        Full text, no truncation.

        Open-turn exchanges are buffered until the session becomes real
        (first user-turn exchange) — probes/reloads leave no files."""
        e = dict(entry)
        record = {
            "ts": e.pop("ts", None),
            "turn": e.pop("turn", None),
            "is_open": e.pop("is_open", None),
            "model": e.pop("model", None),
            "sent": {
                "system_blocks": e.pop("system_blocks", []),
                "history": e.pop("history", []),
                "task_message": e.pop("task_message", ""),
                "tools": e.pop("tools_sent", []),
            },
            "received": e.pop("response", {}),
            **e,  # anything future entries add stays visible, unhidden
        }
        if not self._real and record.get("is_open"):
            self._pending_requests.append(record)
            return
        self._ensure_real()
        self._write_request(record)

    def _write_request(self, record: dict) -> None:
        with self.requests_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(_jsonable(record), ensure_ascii=False) + "\n")

    def _write_jsonl(self, record: dict) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(_jsonable(record), ensure_ascii=False) + "\n")

    def _emit_jsonl(self, record: dict) -> None:
        """Write when real; buffer while the session has no user turn yet."""
        if not self._real:
            self._pending_jsonl.append(record)
            return
        self._write_jsonl(record)

    def _append_md(self, text: str) -> None:
        if not text.endswith("\n"):
            text += "\n"
        if not self._real:
            self._pending_md.append(text)
            return
        with self.md_path.open("a", encoding="utf-8") as f:
            f.write(text)

    def event(self, event: str, **payload) -> None:
        self._emit_jsonl({"event": event, "ts": _utc_now(), **payload})

    def log_simple_turn(
        self,
        *,
        learner: str,
        visible: str,
        state: dict,
        stop_reason: str = "",
        usage: dict | None = None,
        extra: dict | None = None,
        is_open: bool = False,
    ) -> None:
        """Single-model turn (thin log). ``is_open=True`` marks the opening
        tutor turn — buffered, never file-creating on its own; the first
        user turn (is_open=False) makes the session real and flushes it."""
        self.turn_index += 1
        i = self.turn_index
        if not is_open:
            self._ensure_real()
        self._emit_jsonl({
            "event": "turn",
            "ts": _utc_now(),
            "turn": i,
            "learner": learner,
            "visible": visible,
            "state": state,
            "stop_reason": stop_reason,
            "usage": usage or {},
            **(extra or {}),
        })
        self._append_md(
            f"## Turn {i}\n\n"
            f"**Learner:** {learner!r}\n\n"
            f"**Tutor:**\n\n{visible or '*(empty)*'}\n\n"
            f"**State:**\n\n```json\n"
            f"{json.dumps(state, indent=2, ensure_ascii=False)}\n```\n\n---\n\n"
        )

    def close(self, **summary) -> Path | None:
        """End the session. A session that never became real (no user turn
        logged) writes NOTHING and returns None — open-only probe/reload
        sessions leave zero files."""
        if not self._real:
            return None
        self._write_jsonl({
            "event": "session_end",
            "ts": _utc_now(),
            "turns": self.turn_index,
            **summary,
        })
        self._append_md(
            f"## Session end\n\n"
            f"- turns: {self.turn_index}\n"
            f"- ended: {_utc_now()}\n"
            f"- summary: `{json.dumps(_jsonable(summary), ensure_ascii=False)}`\n"
        )
        return self.jsonl_path
