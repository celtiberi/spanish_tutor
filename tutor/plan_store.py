"""Per-learner session-plan persistence (USER 2026-08-04: "we need to
store the users sheet, plan, etc so that they do not need to be reloaded
when the user comes back. This will speed things up").

The sheet already persists (per-uid file in tester mode). This stores the
model's OWN session plan next to that sheet, so a returning learner's
open turn runs as a cheap ROUND turn on the restored plan instead of the
expensive full-context plan turn. Same invalidation rule as the blank
cache: the plan is stamped with the code fingerprint (model + pedagogy +
plan instructions + stance + persona) and dropped when the server's
teaching inputs change — the model then writes a fresh plan. §1.1: code
stores and replays the plan verbatim, never edits it.

Storage: <sheet-dir>/<sheet-stem>.plan.json (rides wherever the sheet
lives — /data volume on Fly, repo-local for the operator).
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path


def _plan_path(sheet_path: str | Path) -> Path:
    p = Path(sheet_path)
    return p.with_name(p.stem + ".plan.json")


def save_plan(sheet_path: str | Path, plan: str) -> None:
    """Persist the model's current session plan for this learner.
    Failures are visible ([no-hide]) and non-fatal — the turn already
    succeeded; losing persistence only costs the next visit a plan turn."""
    if not plan or not plan.strip():
        return
    from .plan_cache import blank_plan_fingerprint

    try:
        p = _plan_path(sheet_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "fingerprint": blank_plan_fingerprint(),
            "plan": plan,
            "saved_at": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[no-hide] plan persist FAILED for {sheet_path}: "
              f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)


def load_plan(sheet_path: str | Path) -> str | None:
    """The learner's stored plan, iff its fingerprint still matches the
    current teaching inputs (server update ⇒ stale ⇒ None)."""
    from .plan_cache import blank_plan_fingerprint

    try:
        d = json.loads(_plan_path(sheet_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if d.get("fingerprint") != blank_plan_fingerprint():
        return None
    plan = d.get("plan")
    return plan if isinstance(plan, str) and plan.strip() else None


def delete_plan(sheet_path: str | Path) -> None:
    """Reset learner ⇒ the stored plan describes a student who no longer
    exists — delete it with the sheet."""
    try:
        _plan_path(sheet_path).unlink(missing_ok=True)
    except OSError as e:
        print(f"[no-hide] plan delete FAILED for {sheet_path}: "
              f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
