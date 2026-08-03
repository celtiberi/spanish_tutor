"""Append-only log of teacher tool ability grades (Phase 3, 2026-07-31).

Replaces the Journey milestone rail as the learner-visible progress surface.
Each entry is a deliberate ``update_character_sheet`` grade with a why —
never invented by regex or silent observation.

Default path: logs/sheet_grades.jsonl (override GRADE_LOG_PATH).
Epoch on learner reset so a new learner is not mixed with prior grades.
"""

from __future__ import annotations

import datetime
import json
import os
import threading
from pathlib import Path
from typing import Any

from .can_dos import CAN_DOS

_lock = threading.Lock()


def default_grade_log_path() -> Path:
    raw = (os.environ.get("GRADE_LOG_PATH") or "").strip()
    if raw:
        return Path(raw)
    # Align with config data root when available
    try:
        from . import config

        return Path(config.LOG_DIR).parent / "sheet_grades.jsonl"
    except Exception as e:
        # No-hide (full-code-audit S5.3): the CWD-relative fallback FORKS
        # the ledger whenever the process cwd differs — never silently.
        import sys as _sys

        print(
            f"[no-hide] grade_log: config import failed — falling back to "
            f"CWD-relative logs/sheet_grades.jsonl (ledger may fork): "
            f"{type(e).__name__}: {e}", file=_sys.stderr, flush=True,
        )
        return Path("logs") / "sheet_grades.jsonl"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def record_epoch(
    *,
    session_id: str = "",
    ledger_path: Path | str | None = None,
) -> None:
    """Mark a learner reset boundary (append-only)."""
    path = Path(ledger_path) if ledger_path else default_grade_log_path()
    _append(path, {
        "kind": "epoch",
        "ts": _now_iso(),
        "session_id": session_id or "",
    })


def record_grade(
    *,
    field_id: str,
    section: str,
    direction: str,
    why: str,
    evidence: str = "",
    from_status: str = "",
    to_status: str = "",
    from_conf: float | None = None,
    to_conf: float | None = None,
    statement: str = "",
    session_id: str = "",
    ledger_path: Path | str | None = None,
) -> dict[str, Any]:
    """Append one ability grade event. Returns the row written."""
    path = Path(ledger_path) if ledger_path else default_grade_log_path()
    if not statement and section == "skills" and field_id in CAN_DOS:
        statement = str(CAN_DOS[field_id].get("statement") or "")
    row: dict[str, Any] = {
        "kind": "grade",
        "ts": _now_iso(),
        "session_id": session_id or "",
        "field_id": field_id,
        "section": section,
        "direction": direction if direction in ("up", "down", "hold") else "hold",
        "why": (why or "").strip()[:500],
        "evidence": (evidence or "").strip()[:200],
        "from_status": from_status or "",
        "to_status": to_status or "",
        "statement": statement or "",
    }
    if from_conf is not None:
        row["from_conf"] = round(float(from_conf), 3)
    if to_conf is not None:
        row["to_conf"] = round(float(to_conf), 3)
    _append(path, row)
    return row


def _iter_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        # No-hide (full-code-audit S5.3): an unreadable ledger renders as an
        # empty grade feed — say why on stderr instead of feigning "no
        # grades yet".
        import sys as _sys

        print(
            f"[no-hide] grade_log: cannot read {path} — grade feed renders "
            f"empty: {type(e).__name__}: {e}", file=_sys.stderr, flush=True,
        )
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def grades_since_epoch(
    *,
    ledger_path: Path | str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Grade events after the latest epoch, newest first."""
    path = Path(ledger_path) if ledger_path else default_grade_log_path()
    rows = _iter_rows(path)
    # Find last epoch index
    epoch_i = -1
    for i, r in enumerate(rows):
        if r.get("kind") == "epoch":
            epoch_i = i
    window = rows[epoch_i + 1 :] if epoch_i >= 0 else rows
    grades = [r for r in window if r.get("kind") == "grade"]
    grades.reverse()  # newest first
    if limit > 0:
        grades = grades[:limit]
    return grades


def counts_from_sheet(sheet: dict) -> dict[str, int]:
    """Header counts from ability sheet (no journey ledger)."""
    known = 0
    emerging = 0
    for v in (sheet.get("skills") or {}).values():
        if not isinstance(v, dict):
            continue
        st = str(v.get("status") or "")
        if st == "known":
            known += 1
        elif st == "emerging":
            emerging += 1
    durable = 0
    for sec in ("lexicon", "grammar"):
        for v in (sheet.get(sec) or {}).values():
            if not isinstance(v, dict):
                continue
            if _interval_days(v) >= 14:
                durable += 1
    return {"durable": durable, "known": known, "emerging": emerging}


def _interval_days(v: dict) -> int:
    try:
        return int(v.get("interval_days") or 0)
    except (TypeError, ValueError):
        return 0


def ability_grade_diffs(
    before: dict,
    after: dict,
) -> list[dict[str, Any]]:
    """Compare ability sections; return list of changed fields."""
    diffs: list[dict[str, Any]] = []
    for section in ("skills", "grammar", "lexicon"):
        bsec = before.get(section) if isinstance(before.get(section), dict) else {}
        asec = after.get(section) if isinstance(after.get(section), dict) else {}
        keys = set(bsec) | set(asec)
        for key in sorted(keys):
            b = bsec.get(key) if isinstance(bsec.get(key), dict) else {}
            a = asec.get(key) if isinstance(asec.get(key), dict) else {}
            b_st = str(b.get("status") or "unknown")
            a_st = str(a.get("status") or "unknown")
            try:
                b_c = float(b.get("confidence") or 0)
            except (TypeError, ValueError):
                b_c = 0.0
            try:
                a_c = float(a.get("confidence") or 0)
            except (TypeError, ValueError):
                a_c = 0.0
            if b_st == a_st and abs(b_c - a_c) < 0.001:
                continue
            if a_c > b_c + 0.02:
                direction = "up"
            elif a_c < b_c - 0.02:
                direction = "down"
            elif a_st != b_st:
                # status-only move: known > emerging > fragile > unknown
                order = {
                    "unknown": 0, "blocked": 0, "fragile": 1,
                    "emerging": 2, "known": 3,
                }
                direction = (
                    "up" if order.get(a_st, 0) > order.get(b_st, 0) else "down"
                )
            else:
                direction = "hold"
            statement = ""
            if section == "skills" and key in CAN_DOS:
                statement = str(CAN_DOS[key].get("statement") or "")
            diffs.append({
                "field_id": key,
                "section": section,
                "direction": direction,
                "from_status": b_st,
                "to_status": a_st,
                "from_conf": b_c,
                "to_conf": a_c,
                "statement": statement,
            })
    return diffs


def record_grades_from_diff(
    before: dict,
    after: dict,
    *,
    why: str,
    evidence: str = "",
    session_id: str = "",
    ledger_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Diff ability and append one grade row per changed field."""
    written: list[dict[str, Any]] = []
    for d in ability_grade_diffs(before, after):
        written.append(record_grade(
            field_id=d["field_id"],
            section=d["section"],
            direction=d["direction"],
            why=why,
            evidence=evidence,
            from_status=d["from_status"],
            to_status=d["to_status"],
            from_conf=d["from_conf"],
            to_conf=d["to_conf"],
            statement=d["statement"],
            session_id=session_id,
            ledger_path=ledger_path,
        ))
    return written


def build_grades_payload(
    sheet: dict,
    *,
    session_id: str = "",
    ledger_path: Path | str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    """Payload for GET /api/progress (grade feed + header counts)."""
    grades = grades_since_epoch(ledger_path=ledger_path, limit=limit)
    counts = counts_from_sheet(sheet or {})
    from .character_sheet import compute_progress_score

    score = compute_progress_score(sheet or {})
    return {
        "grades": grades,
        "counts": counts,
        "empty": len(grades) == 0,
        "session_id": session_id or "",
        "score": score,
        # legacy keys so old clients don't explode
        "groups": [],
        "due_soon": 0,
    }
