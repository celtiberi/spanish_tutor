"""RetrievalScheduler — code-owned spaced retrieval + introduce ledger.

Phase 1 of docs/build-plan-pedagogy-engine.md:
- r6 Rank-1 spec (docs/pedagogy-research-r6-practice-mix.md §5): code decides
  WHICH items are due and records outcomes; the tutor model only realizes
  the elicit in Spanish inside the live topic (no flashcard chrome).
- r7 S1 ledger (docs/pedagogy-research-r7-association-intro.md §7):
  `mark_introduced` writes first-seen facts and enqueues (R-H: introduce
  success → next_due tomorrow). Keys may be multiword units ("hasta luego").

Interval policy (r3/r6, code-owned): success → successive_successes+=1 with
interval 1d (first), 3d (second), then min(interval*2, 14). Fail → interval
1d, next_due tomorrow, successive_successes reset.

HONESTY LAW (enforced in code, not convention): scheduling/introduction may
never change `confidence`, `status`, or `solid_uses` — every sheet write in
this module goes through `_write`, which allowlists the schedule fields and
restores ability fields even if a future edit slips one in.

Single purpose, stdlib only.
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import dataclass

KINDS = ("lexicon", "grammar", "skill")
_SECTION = {"lexicon": "lexicon", "grammar": "grammar", "skill": "skills"}
INTERVAL_CAP_DAYS = 14

# The ONLY fields this module may write on a sheet entry (honesty law).
SCHEDULE_FIELDS = frozenset({
    "introduced_at",
    "first_seen",
    "scaffold",
    "next_due",
    "interval_days",
    "successive_successes",
})

# Ability fields the scheduler must never move.
_PROTECTED_FIELDS = ("confidence", "status", "solid_uses")


@dataclass
class DueItem:
    """One item due for a retrieval re-encounter."""

    key: str
    kind: str  # "lexicon" | "grammar" | "skill"
    next_due: datetime.date
    interval_days: int
    prompt_hint: str


def _today(today: datetime.date | None) -> datetime.date:
    return today if today is not None else datetime.date.today()


def _parse_date(value) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    try:
        return datetime.date.fromisoformat(str(value).strip()[:10])
    except (TypeError, ValueError):
        return None


def _entry(sheet: dict, key: str, kind: str, *, create: bool = False) -> dict:
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    section = sheet.setdefault(_SECTION[kind], {})
    entry = section.get(key)
    if not isinstance(entry, dict):
        if not create:
            raise KeyError(f"{kind}:{key} not on sheet")
        # Honest zero — a ledger write is NOT ability evidence.
        entry = {"status": "unknown", "confidence": 0.0}
        section[key] = entry
    return entry


def _write(entry: dict, updates: dict) -> None:
    """Allowlisted schedule write; ability fields restored even if touched."""
    illegal = set(updates) - SCHEDULE_FIELDS
    if illegal:
        raise ValueError(
            f"scheduler may not write {sorted(illegal)} (honesty law)"
        )
    before = {k: entry[k] for k in _PROTECTED_FIELDS if k in entry}
    entry.update(updates)
    for k, v in before.items():
        entry[k] = v


def _prompt_hint(key: str, kind: str) -> str:
    if kind == "lexicon":
        return f"weave «{key}» into the live topic"
    if kind == "grammar":
        return f"elicit the form {key} in context"
    return f"re-elicit can-do {key} in conversation"


def due_items(
    sheet: dict,
    *,
    today: datetime.date | None = None,
    max_due: int = 3,
) -> list[DueItem]:
    """Items with next_due <= today, oldest-due first, kinds interleaved.

    Interleaving (Nakata & Suzuki note in r6): never return `max_due` of one
    kind while another kind also has due items — round-robin across kind
    buckets (each oldest-first), then order the picked set oldest-due first.
    """
    day = _today(today)
    buckets: dict[str, list[DueItem]] = {}
    for kind, section in _SECTION.items():
        block = sheet.get(section)
        if not isinstance(block, dict):
            continue
        for key, entry in block.items():
            if not isinstance(entry, dict):
                continue
            nd = _parse_date(entry.get("next_due"))
            if nd is None or nd > day:
                continue
            try:
                interval = max(1, int(entry.get("interval_days") or 1))
            except (TypeError, ValueError):
                interval = 1
            buckets.setdefault(kind, []).append(DueItem(
                key=str(key),
                kind=kind,
                next_due=nd,
                interval_days=interval,
                prompt_hint=_prompt_hint(str(key), kind),
            ))
    for items in buckets.values():
        items.sort(key=lambda d: (d.next_due, d.key))
    if max_due <= 0 or not buckets:
        return []
    # Round-robin over kinds, kinds ordered by their oldest due date.
    order = sorted(buckets, key=lambda k: (buckets[k][0].next_due, k))
    picked: list[DueItem] = []
    while len(picked) < max_due and any(buckets.get(k) for k in order):
        for kind in order:
            if buckets.get(kind):
                picked.append(buckets[kind].pop(0))
                if len(picked) >= max_due:
                    break
    picked.sort(key=lambda d: (d.next_due, d.kind, d.key))
    return picked


def record_outcome_ex(
    sheet: dict,
    key: str,
    kind: str,
    success: bool,
    *,
    today: datetime.date | None = None,
) -> tuple[dict, dict]:
    """record_outcome + the interval transition it caused.

    Returns (updated sheet copy, transition dict). The transition is
    READ-ONLY telemetry for the progress ledger (journey-rail crossings,
    docs/design-progression-view.md) — it is never a sheet write path; every
    sheet write still goes through the `_write` allowlist (honesty law).
    """
    day = _today(today)
    s = copy.deepcopy(sheet)
    entry = _entry(s, key, kind, create=True)
    try:
        successes = max(0, int(entry.get("successive_successes") or 0))
    except (TypeError, ValueError):
        successes = 0
    try:
        interval = max(1, int(entry.get("interval_days") or 1))
    except (TypeError, ValueError):
        interval = 1
    successes_before = successes
    interval_before = interval
    if success:
        successes += 1
        if successes == 1:
            interval = 1
        elif successes == 2:
            interval = 3
        else:
            interval = min(interval * 2, INTERVAL_CAP_DAYS)
    else:
        successes = 0
        interval = 1
    _write(entry, {
        "successive_successes": successes,
        "interval_days": interval,
        "next_due": (day + datetime.timedelta(days=interval)).isoformat(),
    })
    transition = {
        "key": str(key),
        "kind": str(kind),
        "success": bool(success),
        "interval_before": interval_before,
        "interval_after": interval,
        "successes_before": successes_before,
        "successes_after": successes,
    }
    return s, transition


def record_outcome(
    sheet: dict,
    key: str,
    kind: str,
    success: bool,
    *,
    today: datetime.date | None = None,
) -> dict:
    """Record a retrieval outcome; returns an updated copy of the sheet.

    Success ladder: 1d (first success), 3d (second), then min(interval*2, 14).
    Fail: interval 1d, next_due tomorrow, successive_successes reset to 0.
    Never touches confidence/status.
    """
    s, _ = record_outcome_ex(sheet, key, kind, success, today=today)
    return s


def enqueue(
    sheet: dict,
    key: str,
    kind: str,
    *,
    today: datetime.date | None = None,
    scaffold: str | None = None,
) -> dict:
    """Schedule an item for its first re-encounter tomorrow.

    Writes introduced_at (only if absent), scaffold (when given),
    next_due=today+1, interval_days=1. Returns an updated copy of the sheet.
    Never touches confidence/status.
    """
    day = _today(today)
    s = copy.deepcopy(sheet)
    entry = _entry(s, key, kind, create=True)
    updates: dict = {
        "next_due": (day + datetime.timedelta(days=1)).isoformat(),
        "interval_days": 1,
    }
    if not entry.get("introduced_at"):
        updates["introduced_at"] = day.isoformat()
    if scaffold is not None:
        updates["scaffold"] = scaffold
    if "successive_successes" not in entry:
        updates["successive_successes"] = 0
    _write(entry, updates)
    return s


def mark_introduced(
    sheet: dict,
    key: str,
    kind: str,
    scaffold: str | None,
    *,
    today: datetime.date | None = None,
) -> dict:
    """S1 introduce-ledger write (+ enqueue per r7 R-H).

    Records first-seen (`introduced_at`) and the scaffold used at E0, and
    schedules the first retrieval for tomorrow. Introduction NEVER grants
    ability: confidence/status are untouched (honesty law).
    """
    day = _today(today)
    s = enqueue(sheet, key, kind, today=day, scaffold=scaffold)
    entry = _entry(s, key, kind, create=True)
    _write(entry, {"scaffold": scaffold})
    return s


def mark_first_seen(
    sheet: dict,
    key: str,
    kind: str,
    scaffold: str | None,
    *,
    today: datetime.date | None = None,
) -> dict:
    """Round-2 AMEND 1c: durable "seen once WITH an in-reply scaffold" bit.

    Written when the tutor volunteered a scaffold (gloss parenthetical or
    cognate/keyword anchor) for a key the router never planned — the learner
    HAS met the item, so later bare reuse must not re-fault as a naked first
    exposure. Deliberately weaker than `mark_introduced`: no `introduced_at`
    (the introduce budget stays router-only), no retrieval enqueue (no
    next_due/interval), and — honesty law via `_write` — confidence/status
    untouched. Returns an updated copy of the sheet.
    """
    day = _today(today)
    s = copy.deepcopy(sheet)
    entry = _entry(s, key, kind, create=True)
    updates: dict = {}
    if not entry.get("first_seen"):
        updates["first_seen"] = day.isoformat()
    if scaffold is not None and not entry.get("scaffold"):
        updates["scaffold"] = scaffold
    if updates:
        _write(entry, updates)
    return s


def has_first_seen(sheet: dict, key: str, kind: str) -> bool:
    """Query: has this key a durable first_seen (incidental-scaffold) bit?"""
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    block = sheet.get(_SECTION[kind])
    if not isinstance(block, dict):
        return False
    entry = block.get(key)
    return isinstance(entry, dict) and bool(entry.get("first_seen"))


def is_introduced(sheet: dict, key: str, kind: str) -> bool:
    """Ledger query: has this key ever had an E0 introduce write?"""
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    block = sheet.get(_SECTION[kind])
    if not isinstance(block, dict):
        return False
    entry = block.get(key)
    return isinstance(entry, dict) and bool(entry.get("introduced_at"))
