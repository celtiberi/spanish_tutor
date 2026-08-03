"""Full-fidelity session logging for tutor runs (single-model or plan/realize).

Writes two artifacts per session under logs/sessions/:
  - <id>.jsonl  — machine-readable, one JSON object per event
  - <id>.md     — human-readable transcript for review

Controller turns should log: learner text, each planner attempt (raw + parsed),
gate findings, normalized decision, executor brief, executor raw/visible reply,
state before/after, usage, hard-fails.
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
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = f"-{label}" if label else ""
        self.session_id = session_id or f"{stamp}-{arch}{suffix}"
        self.jsonl_path = config.LOG_DIR / f"{self.session_id}.jsonl"
        self.md_path = config.LOG_DIR / f"{self.session_id}.md"
        self.arch = arch
        self.turn_index = 0
        self._meta = {
            "session_id": self.session_id,
            "arch": arch,
            "label": label,
            "started_at": _utc_now(),
            **(meta or {}),
        }
        self._write_jsonl({
            "event": "session_start",
            "ts": self._meta["started_at"],
            **self._meta,
        })
        self.md_path.write_text(
            f"# Session `{self.session_id}`\n\n"
            f"- **arch:** {arch}\n"
            f"- **started:** {self._meta['started_at']}\n"
            f"- **meta:** `{json.dumps(_jsonable(meta or {}), ensure_ascii=False)}`\n\n"
            f"JSONL twin: `{self.jsonl_path.name}`\n\n---\n\n",
            encoding="utf-8",
        )

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
        Full text, no truncation."""
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
            },
            "received": e.pop("response", {}),
            **e,  # anything future entries add stays visible, unhidden
        }
        path = config.LOG_DIR / f"{self.session_id}.requests.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(_jsonable(record), ensure_ascii=False) + "\n")

    def _write_jsonl(self, record: dict) -> None:
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(_jsonable(record), ensure_ascii=False) + "\n")

    def _append_md(self, text: str) -> None:
        with self.md_path.open("a", encoding="utf-8") as f:
            f.write(text)
            if not text.endswith("\n"):
                f.write("\n")

    def event(self, event: str, **payload) -> None:
        self._write_jsonl({"event": event, "ts": _utc_now(), **payload})

    def log_demo_example(
        self,
        name: str,
        learner: str,
        decision: dict | None,
        brief: str,
        gate_ok: bool,
        gate_errs: list,
        note: str = "",
    ) -> None:
        """Offline controller demo (no API)."""
        self.turn_index += 1
        i = self.turn_index
        self._write_jsonl({
            "event": "demo_example",
            "ts": _utc_now(),
            "turn": i,
            "name": name,
            "learner": learner,
            "note": note,
            "gate_ok": gate_ok,
            "gate_errs": gate_errs,
            "controller_decision": decision,
            "executor_brief": brief,
        })
        self._append_md(
            f"## Demo turn {i}: `{name}`\n\n"
            + (f"*{note}*\n\n" if note else "")
            + f"**Learner:** {learner!r}\n\n"
            + f"**Gate:** {'PASS' if gate_ok else 'FAIL'}"
            + (f" — {gate_errs}\n\n" if gate_errs else "\n\n")
            + "### Controller decision\n\n```json\n"
            + json.dumps(decision, indent=2, ensure_ascii=False)
            + "\n```\n\n### Executor brief\n\n```yaml\n"
            + (brief or "(none)")
            + "\n```\n\n---\n\n"
        )

    def log_controller_turn(
        self,
        *,
        learner: str,
        state_before: dict,
        state_after: dict,
        visible: str,
        extra: dict,
        stop_reason: str = "",
        executor_raw: str = "",
        history_len: int = 0,
    ) -> None:
        """One live controller (or structured) turn with full plan/realize detail."""
        self.turn_index += 1
        i = self.turn_index
        extra = extra or {}
        record = {
            "event": "controller_turn",
            "ts": _utc_now(),
            "turn": i,
            "learner": learner,
            "visible": visible,
            "executor_raw": executor_raw or visible,
            "stop_reason": stop_reason,
            "state_before": state_before,
            "state_after": state_after,
            "history_len": history_len,
            "controller_decision": extra.get("controller_decision")
            or extra.get("directive"),
            "executor_brief": extra.get("executor_brief"),
            "planner_attempts": extra.get("planner_attempts"),
            "replans": extra.get("replans", 0),
            "gate_findings": extra.get("gate_findings"),
            "hard_fail": extra.get("hard_fail", False),
            "planner_usage": extra.get("planner_usage"),
            "executor_usage": extra.get("executor_usage"),
            "arch": extra.get("arch", self.arch),
        }
        self._write_jsonl(record)

        decision = record["controller_decision"]
        attempts = record["planner_attempts"] or []
        md = [f"## Turn {i}\n"]
        md.append(f"**Learner:** {learner!r}\n")
        if record["hard_fail"]:
            md.append("**HARD FAIL** (executor not called)\n")
        md.append(f"**Replans:** {record['replans']}\n")
        if record["gate_findings"]:
            md.append(f"**Gate findings:** {record['gate_findings']}\n")
        if attempts:
            md.append("\n### Planner attempts\n")
            for j, att in enumerate(attempts):
                md.append(f"\n#### Attempt {j} "
                          f"({'ok' if att.get('gate_ok') else 'rejected'})\n")
                if att.get("raw_text"):
                    md.append("\n```text\n" + str(att["raw_text"])[:4000]
                              + "\n```\n")
                if att.get("parsed") is not None:
                    md.append("\n```json\n"
                              + json.dumps(att["parsed"], indent=2,
                                           ensure_ascii=False)[:4000]
                              + "\n```\n")
                if att.get("gate_errs"):
                    md.append(f"\nErrors: `{att['gate_errs']}`\n")
                if att.get("usage"):
                    md.append(f"\nUsage: `{att['usage']}`\n")
        if decision is not None:
            md.append("\n### Final controller decision\n\n```json\n")
            md.append(json.dumps(decision, indent=2, ensure_ascii=False))
            md.append("\n```\n")
        if record["executor_brief"]:
            md.append("\n### Executor brief\n\n```yaml\n")
            md.append(str(record["executor_brief"]))
            md.append("\n```\n")
        md.append("\n### Executor → learner (visible)\n\n")
        md.append(visible or "*(empty)*")
        md.append("\n\n")
        if executor_raw and executor_raw != visible:
            md.append("### Executor raw (pre-state strip)\n\n```text\n")
            md.append(executor_raw[:6000])
            md.append("\n```\n\n")
        md.append("### State after\n\n```json\n")
        md.append(json.dumps(state_after, indent=2, ensure_ascii=False))
        md.append("\n```\n\n")
        if record["planner_usage"] or record["executor_usage"]:
            md.append(
                f"**Usage** planner=`{record['planner_usage']}` "
                f"executor=`{record['executor_usage']}` "
                f"stop=`{stop_reason}`\n\n")
        md.append("---\n\n")
        self._append_md("".join(md))

    def log_simple_turn(
        self,
        *,
        learner: str,
        visible: str,
        state: dict,
        stop_reason: str = "",
        usage: dict | None = None,
        extra: dict | None = None,
    ) -> None:
        """Single-model turn (thin log)."""
        self.turn_index += 1
        i = self.turn_index
        self._write_jsonl({
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

    def close(self, **summary) -> Path:
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
