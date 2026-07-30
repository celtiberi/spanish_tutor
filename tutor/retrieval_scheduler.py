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

Phase 1.5 batch 1 (docs/reviews-architecture-refactor.md, adjudicated
round-1 (b)): this module is machine A of the two-axis item-lifecycle
design — the ENCOUNTER/SCHEDULE state machine, sole writer of
SCHEDULE_FIELDS. States: absent / first_seen / introduced / on_ladder
(ladder position — interval_days, successive_successes, next_due — is DATA
on the on_ladder state, not states), with retraction as the explicit legal
edge back. Every public writer is a thin wrapper over `transition`, which
rejects illegal edges at write time (IllegalTransition). The ability axis
(machine B: confidence/status/solid_uses, character_sheet — batch 2) is
orthogonal; cross-axis writes remain illegal via the `_write` allowlist.
Evidence QUALITY is never judged here — the FSM rejects illegal writes,
evidence gates stay (introduce_scaffold_evidence, output gate).

Single purpose, stdlib only.
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import dataclass
from typing import Literal

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
    "frames_seen",
})

# frames_seen safety cap (design-encounter-variety round, Grok OQ3 AMEND):
# NO semantic drop — a dropped frame would falsify the "not on that list"
# direction. The cap only guards against a pathological writer; the real
# frame space is far smaller.
FRAMES_SAFETY_CAP = 32

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


# --- Encounter/schedule state machine (Phase 1.5 batch 1, machine A) ---------
#
# REAL reachable states, derived from the writers (not the idealized sketch):
#
#   absent      — no entry, or an entry with no meaningful schedule marker
#                 (ability-only entries live here: the schedule axis is
#                 simply unstarted for them).
#   first_seen  — durable "seen once WITH an in-reply scaffold" bit
#                 (first_seen set; no introduced_at, no scheduled next_due).
#   introduced  — introduced_at set but NO parseable next_due. NOT produced
#                 by this module's writers: mark_introduced/enqueue write
#                 introduced_at and next_due in the same call, so an
#                 introduction lands directly on_ladder. The state exists
#                 only for external/degenerate data (hand-edited sheets;
#                 normalize_sheet coercing a garbage next_due to None while
#                 introduced_at survives) — kept so such entries still have
#                 legal repair edges back onto the ladder.
#   on_ladder   — next_due parses to a date. Ladder POSITION (interval_days,
#                 successive_successes) is data on this state. A failed
#                 outcome is the on_ladder → on_ladder re-queue (interval
#                 1d, successes 0) — "lapsed" is not a distinct state.
#
# `first_seen` the FIELD is orthogonal evidence that persists through later
# states (kept on introduce and on retraction); `first_seen` the STATE means
# that bit is the item's furthest schedule progress.

STATES = ("absent", "first_seen", "introduced", "on_ladder")

State = Literal["absent", "first_seen", "introduced", "on_ladder"]


class IllegalTransition(ValueError):
    """A schedule-state move outside the legal edge set (rejected at write)."""


def item_state(entry: dict | None) -> State:
    """Encounter/schedule state of one sheet entry (schedule axis only)."""
    if not isinstance(entry, dict):
        return "absent"
    if _parse_date(entry.get("next_due")) is not None:
        return "on_ladder"
    if entry.get("introduced_at"):
        return "introduced"
    if entry.get("first_seen"):
        return "first_seen"
    return "absent"


def _state_of(sheet: dict, key: str, kind: str) -> State:
    """item_state looked up on a sheet (kind-validated, read-only)."""
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    block = sheet.get(_SECTION[kind])
    entry = block.get(key) if isinstance(block, dict) else None
    return item_state(entry if isinstance(entry, dict) else None)


# Per-operation legal edges. `to_state` alone under-determines the write set
# (introduce/enqueue/outcome all land on_ladder with different field
# writes), so legality is checked per (via, from, to); LEGAL_TRANSITIONS is
# the union view of the same graph.
_VIA_EDGES: dict[str, frozenset] = {
    # mark_first_seen: adds the durable bit. The is_introduced/has_first_seen
    # guard STAYS at call sites (conv_session) — the writer itself has always
    # allowed the data-add on later states (self-loop), kept identical.
    "first_seen": frozenset({
        ("absent", "first_seen"), ("first_seen", "first_seen"),
        ("introduced", "introduced"), ("on_ladder", "on_ladder"),
    }),
    # mark_introduced: E0 introduce + R-H enqueue. Double-introduce (key
    # already introduced or on the ladder) is an ILLEGAL edge.
    "introduce": frozenset({
        ("absent", "on_ladder"), ("first_seen", "on_ladder"),
    }),
    # enqueue: (re-)schedule; the on_ladder self-loop is the legal re-queue.
    "enqueue": frozenset({
        ("absent", "on_ladder"), ("first_seen", "on_ladder"),
        ("introduced", "on_ladder"), ("on_ladder", "on_ladder"),
    }),
    # record_outcome: ladder move; fail = re-queue at 1d (same state, data
    # reset). An absent key is CREATED (characterized current behavior,
    # encoded): honest-zero entry with ladder fields only, no introduced_at.
    "outcome": frozenset({
        ("absent", "on_ladder"), ("first_seen", "on_ladder"),
        ("introduced", "on_ladder"), ("on_ladder", "on_ladder"),
    }),
    # retract_introduction: the explicit legal edge BACK (2026-07-28 honesty
    # correction): drops introduced_at/scaffold/next_due/interval_days/
    # successive_successes, keeps first_seen, removes the honest-zero shell.
    "retract": frozenset({
        ("absent", "absent"), ("first_seen", "first_seen"),
        ("introduced", "first_seen"), ("introduced", "absent"),
        ("on_ladder", "first_seen"), ("on_ladder", "absent"),
    }),
}

# Union graph over all operations (the machine's state-level view).
LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "absent": {"absent", "first_seen", "on_ladder"},
    "first_seen": {"first_seen", "on_ladder"},
    "introduced": {"introduced", "first_seen", "absent", "on_ladder"},
    "on_ladder": {"on_ladder", "first_seen", "absent"},
}


def _check_graph_sync() -> None:
    derived: dict[str, set[str]] = {}
    for edges in _VIA_EDGES.values():
        for f, t in edges:
            derived.setdefault(f, set()).add(t)
    if derived != LEGAL_TRANSITIONS:
        raise RuntimeError(
            "retrieval_scheduler: LEGAL_TRANSITIONS out of sync with _VIA_EDGES"
        )


_check_graph_sync()


def transition(
    sheet: dict,
    key: str,
    kind: str,
    *,
    to_state: State,
    via: str,
    evidence: dict | None = None,
    today: datetime.date | None = None,
    scaffold: str | None = None,
    success: bool | None = None,
) -> tuple[dict, dict]:
    """Central schedule-axis transition: validate the edge, write the fields.

    The ONE place a schedule-state move happens (the public writers are thin
    wrappers). Validates (via, from_state, to_state) against _VIA_EDGES /
    LEGAL_TRANSITIONS and raises IllegalTransition otherwise; performs the
    field writes through the allowlisted `_write` (honesty law: ability
    fields can never move here); returns (updated sheet copy, crossing)
    where `crossing` is READ-ONLY info for the progress-ledger PROJECTION
    (from/to states, opaque evidence, and — for via="outcome" — the interval
    ladder telemetry record_outcome_ex has always returned). The ledger is
    never the transition log; the sheet fields are.

    `evidence` is OPAQUE context for error messages and crossings — evidence
    QUALITY is validated by the gates (introduce_scaffold_evidence, output
    gate), never here ("FSM rejects illegal writes, evidence gates stay").
    """
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    if via not in _VIA_EDGES:
        raise ValueError(f"unknown transition via {via!r}")
    if to_state not in STATES:
        raise ValueError(f"unknown to_state {to_state!r}")
    day = _today(today)
    s = copy.deepcopy(sheet)
    section = s.get(_SECTION[kind])
    pre = section.get(key) if isinstance(section, dict) else None
    from_state = item_state(pre if isinstance(pre, dict) else None)
    if (
        to_state not in LEGAL_TRANSITIONS.get(from_state, set())
        or (from_state, to_state) not in _VIA_EDGES[via]
    ):
        raise IllegalTransition(
            f"illegal {via!r} transition {from_state} -> {to_state} for "
            f"{kind}:{key} (evidence: {evidence!r})"
        )
    crossing: dict = {
        "key": str(key),
        "kind": str(kind),
        "via": via,
        "from_state": from_state,
        "to_state": to_state,
        "evidence": dict(evidence or {}),
    }
    if via == "first_seen":
        entry = _entry(s, key, kind, create=True)
        updates: dict = {}
        if not entry.get("first_seen"):
            updates["first_seen"] = day.isoformat()
        if scaffold is not None and not entry.get("scaffold"):
            updates["scaffold"] = scaffold
        if updates:
            _write(entry, updates)
    elif via in ("introduce", "enqueue"):
        entry = _entry(s, key, kind, create=True)
        updates = {
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
        if via == "introduce":
            # The E0 scaffold is recorded verbatim, None included.
            _write(entry, {"scaffold": scaffold})
    elif via == "outcome":
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
        crossing.update({
            "success": bool(success),
            "interval_before": interval_before,
            "interval_after": interval,
            "successes_before": successes_before,
            "successes_after": successes,
        })
    else:  # via == "retract"
        entry = section.get(key) if isinstance(section, dict) else None
        if isinstance(entry, dict):
            # Field REMOVAL, not a `_write` update — but only ever of
            # SCHEDULE_FIELDS (first_seen deliberately kept: separate
            # evidence); ability fields untouched.
            for f in (
                "introduced_at", "scaffold", "next_due", "interval_days",
                "successive_successes",
            ):
                entry.pop(f, None)
            leftover = set(entry) - {"status", "confidence"}
            try:
                conf = float(entry.get("confidence") or 0.0)
            except (TypeError, ValueError):
                conf = 0.0
            if not leftover and conf == 0.0 and str(
                entry.get("status") or ""
            ) in ("", "unknown"):
                # The introduce write created this shell; retraction
                # removes it — restoring the pre-introduce sheet.
                del section[key]
    post_block = s.get(_SECTION[kind])
    post = post_block.get(key) if isinstance(post_block, dict) else None
    landed = item_state(post if isinstance(post, dict) else None)
    if landed != to_state:
        raise RuntimeError(
            f"transition bug: {via!r} for {kind}:{key} landed in "
            f"{landed!r}, declared {to_state!r}"
        )
    return s, crossing


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

    Thin wrapper over `transition` (via="outcome"; Phase 1.5 batch 1) —
    legal from ANY state: an absent key is created at honest zero
    (characterized current behavior, encoded as a legal edge).
    Returns (updated sheet copy, transition dict). The transition is
    READ-ONLY telemetry for the progress ledger (journey-rail crossings,
    docs/design-progression-view.md) — it is never a sheet write path; every
    sheet write still goes through the `_write` allowlist (honesty law).
    """
    s, crossing = transition(
        sheet, key, kind,
        to_state="on_ladder", via="outcome",
        evidence={"caller": "record_outcome_ex", "success": bool(success)},
        today=today, success=bool(success),
    )
    # Exact historical telemetry shape (progress-ledger contract).
    return s, {
        "key": crossing["key"],
        "kind": crossing["kind"],
        "success": crossing["success"],
        "interval_before": crossing["interval_before"],
        "interval_after": crossing["interval_after"],
        "successes_before": crossing["successes_before"],
        "successes_after": crossing["successes_after"],
    }


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

    Thin wrapper over `transition` (via="enqueue") — legal from ANY state;
    the on_ladder self-loop is the legal re-queue. Writes introduced_at
    (only if absent), scaffold (when given), next_due=today+1,
    interval_days=1. Returns an updated copy of the sheet.
    Never touches confidence/status.
    """
    s, _ = transition(
        sheet, key, kind,
        to_state="on_ladder", via="enqueue",
        evidence={"caller": "enqueue", "scaffold": scaffold},
        today=today, scaffold=scaffold,
    )
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

    Thin wrapper over `transition` (via="introduce") — legal ONLY from
    absent/first_seen: a double-introduce (key already introduced or on the
    ladder) raises IllegalTransition (Phase 1.5 FSM write rejection; the
    introduce_router's is_introduced check has always kept production off
    this edge). Records first-seen (`introduced_at`) and the scaffold used
    at E0 (written verbatim, None included), and schedules the first
    retrieval for tomorrow. Introduction NEVER grants ability:
    confidence/status are untouched (honesty law).
    """
    s, _ = transition(
        sheet, key, kind,
        to_state="on_ladder", via="introduce",
        evidence={"caller": "mark_introduced", "scaffold": scaffold},
        today=today, scaffold=scaffold,
    )
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

    Thin wrapper over `transition` (via="first_seen"). Characterized guard
    decision (Phase 1.5 batch 1): the is_introduced/has_first_seen skip
    STAYS at call sites (conv_session); the writer keeps its historical
    self-loop semantics — on an already-introduced/on_ladder entry it only
    adds the missing first_seen bit (state unchanged), on a first_seen
    entry it is a no-op (original date and scaffold kept).
    """
    cur = _state_of(sheet, key, kind)
    to: State = "first_seen" if cur == "absent" else cur
    s, _ = transition(
        sheet, key, kind,
        to_state=to, via="first_seen",
        evidence={"caller": "mark_first_seen", "scaffold": scaffold},
        today=today, scaffold=scaffold,
    )
    return s


def retract_introduction(
    sheet: dict,
    key: str,
    kind: str,
) -> dict:
    """Honesty correction: undo a FALSE introduce write (2026-07-28 incident).

    Removes exactly the fields `mark_introduced` wrote — introduced_at,
    scaffold, next_due, interval_days, successive_successes — so a key that
    was never actually introduced stops riding the retrieval ladder. The
    `first_seen` bit is NOT touched (it records a genuine in-reply scaffold
    sighting, separate evidence). Ability fields (confidence/status/
    solid_uses) are never touched — callers must verify the key has no real
    use evidence before retracting sheet state at all. If the entry was the
    honest-zero shell the introduce created (status=unknown, confidence=0.0,
    nothing else), it is removed entirely — restoring the pre-introduce
    sheet. Returns an updated copy; absent entry → unchanged copy.

    Thin wrapper over `transition` (via="retract") — the machine's explicit
    legal edge BACK: lands on first_seen when that separate evidence bit is
    set, else absent (shell removed or ability-only entry kept).
    """
    to: State = "first_seen" if has_first_seen(sheet, key, kind) else "absent"
    s, _ = transition(
        sheet, key, kind,
        to_state=to, via="retract",
        evidence={"caller": "retract_introduction"},
    )
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


def frames_seen_of(sheet: dict, key: str, kind: str) -> list[str]:
    """Query: the frames this item has been elicited in (exposure history)."""
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    block = sheet.get(_SECTION[kind])
    if not isinstance(block, dict):
        return []
    entry = block.get(key)
    if not isinstance(entry, dict):
        return []
    frames = entry.get("frames_seen")
    return [str(f) for f in frames] if isinstance(frames, list) else []


def record_frame(sheet: dict, key: str, kind: str, frame: str) -> dict:
    """Append an elicit frame to the entry's exposure history (frames_seen).

    Encounter-variety round (docs/design-encounter-variety.md, 2026-07-29,
    Grok-countersigned): exposure history, NEVER ability evidence — it
    feeds the due-elicit direction line only, no read path into promotion.
    Deduped, order-preserving, safety-capped with no semantic drop (a
    dropped frame would falsify the "not on that list" direction). Empty
    frame or an entry not on the sheet records nothing (silence records
    nothing). Mutates and returns the sheet (module idiom)."""
    f = (frame or "").strip()
    if not f:
        return sheet
    if kind not in _SECTION:
        raise ValueError(f"unknown kind {kind!r} (expected one of {KINDS})")
    block = sheet.get(_SECTION[kind])
    entry = block.get(key) if isinstance(block, dict) else None
    if not isinstance(entry, dict):
        return sheet
    frames = entry.get("frames_seen")
    if not isinstance(frames, list):
        frames = []
    frames = [str(x) for x in frames]
    if f in frames or len(frames) >= FRAMES_SAFETY_CAP:
        return sheet
    _write(entry, {"frames_seen": frames + [f]})
    return sheet
