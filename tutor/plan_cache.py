"""Precreated blank-sheet session plan (USER 2026-08-04: "for a new
character sheet the plan should always be the same. So we can precreate
that instead of requesting it").

The plan turn for a BLANK sheet has identical inputs every time —
pedagogy rules, plan instructions, the default sheet, the stance, the
model. So one real plan is generated (warmed at server start, off the
request path) and every new learner's first turn skips the expensive
full-context call. The cache is FINGERPRINTED over exactly those
inputs: deploy a change to any of them and the cache invalidates
itself ("updated when we update the server").

Storage: <data>/plan_cache/blank.json next to the character sheet.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

from . import config


def _cache_path() -> Path:
    return config.CHARACTER_SHEET_PATH.parent / "plan_cache" / "blank.json"


def blank_plan_fingerprint() -> str:
    """Hash of every input that shapes a blank-sheet plan."""
    from .character_sheet import default_sheet, format_sheet_for_prompt
    from .executor import CONV_PROMPT, load_persona
    from .session_plan import PLAN_INSTRUCTIONS, load_pedagogy

    try:
        stance = CONV_PROMPT.read_text(encoding="utf-8")
    except OSError:
        stance = ""
    blob = "\n".join([
        config.MODEL,
        load_pedagogy(),
        PLAN_INSTRUCTIONS,
        stance,
        load_persona() or "",
        format_sheet_for_prompt(default_sheet()),
    ])
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def get_cached_blank_plan() -> str | None:
    """The precreated plan, iff its fingerprint still matches the code."""
    try:
        d = json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if d.get("fingerprint") != blank_plan_fingerprint():
        return None
    plan = d.get("plan")
    return plan if isinstance(plan, str) and plan.strip() else None


def store_blank_plan(plan: str) -> None:
    p = _cache_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "fingerprint": blank_plan_fingerprint(),
        "plan": plan,
        "model": config.MODEL,
        "created_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def warm_blank_plan() -> bool:
    """Generate + store the blank plan via the REAL pipeline (one model
    call) if the cache is stale. Returns True when a valid plan is
    cached afterwards. Failures are visible, never raised (called from
    a startup thread — serving never blocks on this)."""
    if get_cached_blank_plan():
        return True
    try:
        import tempfile

        from .conv_session import ConversationalSession

        with tempfile.TemporaryDirectory() as tmp:
            s = ConversationalSession(
                log=False,
                sheet_path=Path(tmp) / "warm-sheet.json",
                use_tools=False,
            )
            s.open_session()
            plan = s.session_plan
        if plan and plan.strip():
            store_blank_plan(plan)
            print("[plan-cache] blank plan warmed "
                  f"({len(plan)} chars, model={config.MODEL})", flush=True)
            return True
        print("[no-hide] plan-cache warm produced NO plan "
              "(session_plan empty after open)", file=sys.stderr, flush=True)
        return False
    except Exception as e:
        print(f"[no-hide] plan-cache warm FAILED: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return False
