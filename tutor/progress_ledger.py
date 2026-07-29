"""ProgressLedger — append-only milestone history behind the journey rail.

Design law: docs/design-progression-view.md — the Proposal AS AMENDED by
Grok's countersign (adjudication 2026-07-28: "Grok's exact replacement
blocks are BINDING over the original proposal text"). PEDAGOGY.md §3
honesty governs: every event maps 1:1 to a code-owned evidence event that
already fired; the display invents NOTHING. §3.2: introduction is never
knowledge — a `planted` event records an encounter only, and this module
never writes the character sheet at all (history and state are different
object classes).

Amended vocabulary implemented here (thresholds are pins to existing code
gates, never softer):
- planted           introduce ledger write (encounter only)
- taking_root       retrieval ladder interval_days first reaches 3
- rooted            ladder interval_days first reaches 14 (cap) — copy is
                    "durable so far", never "yours forever"
- regression        polarity=down: ladder fail reset AFTER a prior >=3d
                    crossing (required for honesty — history stays, bells
                    are un-rung visibly, never silently)
- error_recovered   resolved_streak >= ERROR_PATTERN_HEALTHY_STREAK (3)
                    AND count == 0 (character_sheet healthy gate)
- can_do_emerging   skill confidence first crosses 0.55 with a positive
                    band (never "You can ..." copy)
- can_do_known      skill status becomes "known" under the code gate
                    (conf >= 0.80 and solid_uses >= 2) — the ONLY kind
                    allowed mastery language
- task_complete     task_runtime machine verdict

There is NO session-end / engagement milestone (streak chrome banned).

Dedup law: an up-crossing fires ONCE per (kind, key) — callers consult
`has_milestone` / `up_keys` before recording. Down events dedupe naturally
(the ladder must re-climb past 3d before another regression is possible).

Learner-epoch scope (Phase 1 batch 2, docs/reviews-architecture-refactor.md
declared delta 3): `sheet_reset` starts a NEW learner. Nothing is retracted —
the previous learner's milestones were genuinely earned and history stays
displayable — but the fresh learner must not be dedupe-suppressed by them.
`record_epoch` appends a kind="epoch" mark (append-only, never a celebration:
`record_milestone` rejects the kind); `has_milestone` / `up_keys` only
consider events AFTER the latest epoch mark, so every crossing re-mints for
the new learner. Display keeps pre-epoch days and shows the epoch row itself
as the boundary. Retraction filtering is unaffected (the mask still applies
across the whole history).

Live-state join: `build_progress_payload` joins each celebrated node to the
CURRENT sheet; a node whose live band no longer supports the celebration
gets `needs_recheck: true` (quiet badge, never silent permanence).

Single purpose, stdlib only; clock (`now`/`today`) and `ledger_path` are
injectable for tests. Default file: logs/progress.jsonl (costs.jsonl
pattern). Code-owned: the model has no write path into this ledger.

OPERATOR / VERIFICATION TRAFFIC (2026-07-28 pollution incident): any
verification chat against the live server — agent smoke checks, health
probes that open sessions, demo scripts — MUST set the PROGRESS_LEDGER_PATH
environment variable (honored by `default_ledger_path`) to a scratch file
BEFORE starting the server or harness, so machine traffic never mints
milestones into the learner's logs/progress.jsonl. The eval harness
(evals/run_conv_smoke.py) already isolates per-trajectory this way.
Operator events that do land in the live ledger are corrected with
`record_retraction` (append-only; the detail must name the incident).
"""

from __future__ import annotations

import datetime
import json
import os
import threading
from pathlib import Path
from typing import Any

# Threshold pins — imported from the owning modules so a gate change there
# cannot silently diverge from what the rail celebrates.
from .retrieval_scheduler import INTERVAL_CAP_DAYS

TAKING_ROOT_DAYS = 3
ROOTED_DAYS = INTERVAL_CAP_DAYS  # 14
EMERGING_CONF = 0.55  # character_sheet._bump_status emerging band

KINDS = (
    "planted",
    "taking_root",
    "rooted",
    "regression",
    "error_recovered",
    "can_do_emerging",
    "can_do_known",
    "task_complete",
    # Honesty correction (2026-07-28 false-planted incident): a `retracted`
    # event (polarity=down, `retracts`=<target kind>) voids every matching
    # up event of (retracts, key) for BOTH display and dedupe — the raw
    # lines stay on disk (append-only law), the rail shows neither side of
    # the pair, and a later GENUINE crossing may re-mint the milestone.
    "retracted",
)
POLARITIES = ("up", "down")

# item_kind → sheet section for the live-state join.
_ITEM_SECTION = {"lexicon": "lexicon", "grammar": "grammar", "skill": "skills"}

_LOCK = threading.Lock()


def default_ledger_path() -> Path:
    """Resolve the ledger file at call time (env-injectable for evals/tests)."""
    env = (os.environ.get("PROGRESS_LEDGER_PATH") or "").strip()
    if env:
        return Path(env)
    from . import config

    return Path(getattr(config, "LOG_DIR", Path("logs/sessions"))).parent / "progress.jsonl"


def _now(now: datetime.datetime | None) -> datetime.datetime:
    return now if now is not None else datetime.datetime.now(datetime.timezone.utc)


def _can_do_gist(key: str) -> str:
    """Human phrase for a can-do id, without the 'I can' mastery prefix."""
    try:
        from .can_dos import CAN_DOS

        statement = str((CAN_DOS.get(key) or {}).get("statement") or "")
    except Exception:
        statement = ""
    if not statement:
        return key
    s = statement.strip()
    if s.lower().startswith("i can "):
        s = s[6:]
    return s.rstrip(".")


def detail_for(kind: str, key: str, **ctx: Any) -> str:
    """Templated evidence sentence for a milestone (NO LLM prose, ever).

    Copy law (amended table): copy must match the sheet status band the
    evidence actually reaches. Mastery language ("You can ...") is allowed
    ONLY for can_do_known; "rooted" is durable SO FAR, never permanent.
    """
    if kind == "planted":
        scaffold = str(ctx.get("scaffold") or "").strip()
        via = f" (scaffold: {scaffold})" if scaffold else ""
        return f"Met «{key}»{via} — first encounter; not yet knowledge"
    if kind == "taking_root":
        interval = int(ctx.get("interval") or TAKING_ROOT_DAYS)
        return (
            f"«{key}» — recalled across days; spaced-recall interval now "
            f"{interval} days"
        )
    if kind == "rooted":
        return f"«{key}» — holding at the 2-week check (durable so far)"
    if kind == "regression":
        was = ctx.get("was")
        was_txt = f" (was {int(was)}-day interval)" if was else ""
        return f"«{key}» — recall check missed; schedule reset to 1 day{was_txt}"
    if kind == "error_recovered":
        label = str(ctx.get("label") or key)
        streak = int(ctx.get("streak") or 0)
        streak_txt = f" of {streak}" if streak else ""
        return f"{label} — clean streak{streak_txt}, error count at zero"
    if kind == "can_do_emerging":
        return f"{key} emerging — “{_can_do_gist(key)}” is starting to land"
    if kind == "can_do_known":
        return f"You can {_can_do_gist(key)} (sheet: known)"
    if kind == "task_complete":
        desc = str(ctx.get("desc") or "").strip()
        return f"Task done: {desc}" if desc else f"Task done ({key})"
    if kind == "retracted":
        target = str(ctx.get("target") or "milestone")
        reason = str(ctx.get("reason") or "recorded without evidence")
        return f"Retracted {target} «{key}» — {reason}"
    raise ValueError(f"unknown milestone kind {kind!r}")


def record_milestone(
    kind: str,
    key: str,
    detail: str = "",
    *,
    polarity: str = "up",
    session_id: str = "",
    item_kind: str = "",
    retracts: str = "",
    ledger_path: Path | str | None = None,
    now: datetime.datetime | None = None,
) -> dict | None:
    """Append one milestone event. Returns the event, or None on I/O failure.

    Code-owned; validation raises on programmer error (a typo'd kind is a
    bug, not telemetry) while disk trouble is best-effort (a progress note
    must never break a teaching turn).
    """
    if kind not in KINDS:
        raise ValueError(f"unknown milestone kind {kind!r} (expected one of {KINDS})")
    if polarity not in POLARITIES:
        raise ValueError(f"polarity must be one of {POLARITIES}, got {polarity!r}")
    if kind == "regression" and polarity != "down":
        raise ValueError("regression events must carry polarity='down' (§3 honesty)")
    if kind == "retracted":
        if polarity != "down":
            raise ValueError("retracted events must carry polarity='down'")
        if retracts not in KINDS or retracts == "retracted":
            raise ValueError(
                "retracted events must name a valid target kind in `retracts`"
            )
    elif retracts:
        raise ValueError("`retracts` is only legal on kind='retracted'")
    if not (key or "").strip():
        raise ValueError("milestone key required")
    event = {
        "ts": _now(now).isoformat(),
        "session_id": str(session_id or ""),
        "kind": kind,
        "key": str(key),
        "detail": str(detail or ""),
        "polarity": polarity,
        "item_kind": str(item_kind or ""),
    }
    if kind == "retracted":
        event["retracts"] = retracts
    path = Path(ledger_path) if ledger_path is not None else default_ledger_path()
    try:
        line = json.dumps(event, ensure_ascii=False)
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except OSError:
        return None
    return event


def record_retraction(
    target_kind: str,
    key: str,
    detail: str = "",
    *,
    session_id: str = "",
    item_kind: str = "",
    ledger_path: Path | str | None = None,
    now: datetime.datetime | None = None,
) -> dict | None:
    """Append an honesty correction voiding every (target_kind, key) up event.

    Append-only law: nothing is deleted from disk. The pair (the false
    milestone AND this correction row) disappears from read_recent and from
    dedupe (up_keys / has_milestone), so a later genuine crossing re-mints.
    `detail` must name the incident (never silent).
    """
    return record_milestone(
        "retracted",
        key,
        detail,
        polarity="down",
        session_id=session_id,
        item_kind=item_kind,
        retracts=target_kind,
        ledger_path=ledger_path,
        now=now,
    )


def record_epoch(
    detail: str = "sheet_reset: fresh learner scope",
    *,
    session_id: str = "",
    ledger_path: Path | str | None = None,
    now: datetime.datetime | None = None,
) -> dict | None:
    """Append a learner-epoch mark rotating the DEDUPE scope (append-only).

    Phase 1 batch 2 declared delta 3: a fresh learner (sheet_reset) re-earns
    milestones instead of being suppressed by the previous learner's history.
    Not a celebration kind — it bypasses `record_milestone` validation on
    purpose (KINDS excludes "epoch" so emit sites can never mint it as a
    milestone, and `record_retraction` can never target it). polarity is the
    dedicated marker value "epoch": never "up" (excluded from `up_keys`
    naturally) and never "down" (not a regression). The row rides the day
    clusters as a visible boundary; `record_retraction` is deliberately NOT
    used here — there is nothing false to retract.
    """
    event = {
        "ts": _now(now).isoformat(),
        "session_id": str(session_id or ""),
        "kind": "epoch",
        "key": "learner",
        "detail": str(detail or ""),
        "polarity": "epoch",
        "item_kind": "",
    }
    path = Path(ledger_path) if ledger_path is not None else default_ledger_path()
    try:
        line = json.dumps(event, ensure_ascii=False)
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except OSError:
        return None
    return event


def record_regression(
    kind: str,
    key: str,
    detail: str = "",
    *,
    session_id: str = "",
    item_kind: str = "",
    ledger_path: Path | str | None = None,
    now: datetime.datetime | None = None,
) -> dict | None:
    """Append a polarity=down event (required for honesty — amended (b))."""
    return record_milestone(
        kind,
        key,
        detail,
        polarity="down",
        session_id=session_id,
        item_kind=item_kind,
        ledger_path=ledger_path,
        now=now,
    )


def _read_events(ledger_path: Path | str | None = None) -> list[dict]:
    path = Path(ledger_path) if ledger_path is not None else default_ledger_path()
    events: list[dict] = []
    if not path.exists():
        return events
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return events
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict) and e.get("kind") and e.get("key"):
            events.append(e)
    return events


def _event_ts(e: dict) -> datetime.datetime:
    try:
        dt = datetime.datetime.fromisoformat(str(e.get("ts") or ""))
    except (TypeError, ValueError):
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _active_events(events: list[dict]) -> list[dict]:
    """Retraction mask: void retracted up events AND the correction rows.

    A `retracted` event (retracts=K, key=X) removes every up event of kind K
    for key X recorded AT OR BEFORE the correction from the ACTIVE view —
    display and dedupe alike — and the correction row itself is bookkeeping,
    never a rail node. Raw lines stay on disk (append-only law); a crossing
    genuinely earned AFTER the correction re-mints cleanly.
    """
    latest_retraction: dict[tuple[str, str], datetime.datetime] = {}
    for e in events:
        if e.get("kind") != "retracted":
            continue
        pair = (str(e.get("retracts") or ""), str(e.get("key") or ""))
        ts = _event_ts(e)
        if pair not in latest_retraction or ts > latest_retraction[pair]:
            latest_retraction[pair] = ts
    out: list[dict] = []
    for e in events:
        if e.get("kind") == "retracted":
            continue
        if (e.get("polarity") or "up") == "up":
            cut = latest_retraction.get(
                (str(e.get("kind")), str(e.get("key")))
            )
            if cut is not None and _event_ts(e) <= cut:
                continue
        out.append(e)
    return out


def _latest_epoch_ts(events: list[dict]) -> datetime.datetime | None:
    """Timestamp of the newest learner-epoch mark, or None (no epoch yet)."""
    best: datetime.datetime | None = None
    for e in events:
        if e.get("kind") != "epoch":
            continue
        ts = _event_ts(e)
        if best is None or ts > best:
            best = ts
    return best


def _post_epoch(events: list[dict]) -> list[dict]:
    """DEDUPE scope: only events strictly AFTER the latest epoch mark.

    Display paths never use this — pre-epoch history stays visible; only
    `has_milestone` / `up_keys` (the re-mint gate) are scoped.
    """
    cut = _latest_epoch_ts(events)
    if cut is None:
        return events
    return [
        e for e in events
        if e.get("kind") != "epoch" and _event_ts(e) > cut
    ]


def has_milestone(
    kind: str,
    key: str,
    *,
    polarity: str = "up",
    ledger_path: Path | str | None = None,
) -> bool:
    """Dedup query: is (kind, key, polarity) ACTIVE (retractions honored,
    learner-epoch scoped)?

    Querying kind='retracted' reads the raw lines (a correction is itself a
    fact, and retraction filtering is epoch-independent); everything else
    sees the retraction-masked view restricted to events AFTER the latest
    learner epoch, so a voided milestone can be honestly re-earned and a
    fresh learner (sheet_reset) re-mints instead of being suppressed.
    """
    events = _read_events(ledger_path)
    if kind != "retracted":
        events = _post_epoch(_active_events(events))
    return any(
        e.get("kind") == kind
        and e.get("key") == key
        and (e.get("polarity") or "up") == polarity
        for e in events
    )


def up_keys(ledger_path: Path | str | None = None) -> set[tuple[str, str]]:
    """ACTIVE post-epoch (kind, key) up pairs — one read for per-turn dedupe.

    Retracted pairs are excluded (a voided milestone must be re-earnable);
    pre-epoch pairs are excluded (a fresh learner re-mints)."""
    return {
        (str(e.get("kind")), str(e.get("key")))
        for e in _post_epoch(_active_events(_read_events(ledger_path)))
        if (e.get("polarity") or "up") == "up"
    }


def _local_day(ts: str) -> str:
    """UTC ISO timestamp → LOCAL calendar day (costs.py precedent)."""
    try:
        dt = datetime.datetime.fromisoformat(ts)
        return dt.astimezone().date().isoformat()
    except (ValueError, TypeError):
        return (ts or "")[:10]


def read_recent(
    *,
    limit_days: int | None = None,
    limit_clusters: int | None = None,
    ledger_path: Path | str | None = None,
    today: datetime.date | None = None,
) -> list[dict]:
    """Session-clustered events, newest cluster first.

    A cluster is a DATE CONTAINER for one session (amended (c): never an
    achievement — no streak counting here). Cluster shape:
    {session_id, date, events (chronological), summary {kind: count}}.
    Events without a session_id cluster by local calendar day. Retracted
    pairs (false milestone + correction row) never display — the raw lines
    remain on disk for audit only.
    """
    events = _active_events(_read_events(ledger_path))
    clusters: dict[str, dict] = {}
    order: list[str] = []
    for e in events:
        day = _local_day(str(e.get("ts") or ""))
        ck = str(e.get("session_id") or "") or f"day:{day}"
        c = clusters.get(ck)
        if c is None:
            c = {
                "session_id": str(e.get("session_id") or ""),
                "date": day,
                "events": [],
                "summary": {},
            }
            clusters[ck] = c
            order.append(ck)
        c["events"].append(dict(e))
        c["date"] = day  # date of the latest event in the cluster
        kind = str(e.get("kind"))
        c["summary"][kind] = int(c["summary"].get(kind, 0)) + 1
    # Newest cluster first (by last event ts, append order as tiebreak)
    def _last_ts(ck: str) -> str:
        evs = clusters[ck]["events"]
        return str(evs[-1].get("ts") or "") if evs else ""

    order.sort(key=_last_ts, reverse=True)
    out = [clusters[ck] for ck in order]
    if limit_days is not None:
        day0 = (today if today is not None else datetime.date.today()) - datetime.timedelta(
            days=max(0, int(limit_days) - 1)
        )
        out = [c for c in out if c["date"] >= day0.isoformat()]
    if limit_clusters is not None:
        out = out[: max(0, int(limit_clusters))]
    return out


def read_recent_days(
    *,
    limit_days: int | None = None,
    limit_clusters: int | None = None,
    ledger_path: Path | str | None = None,
    today: datetime.date | None = None,
) -> list[dict]:
    """Day-clustered events, newest day first — the rail's visual unit.

    2026-07-28 rail incident: per-session clusters made one afternoon of
    tinkering read as four separate journeys. The visual unit is the LOCAL
    calendar day; sessions within a day are merged (each event keeps its
    session_id for tooltip/debug). Cluster shape:
    {date, sessions (distinct ids, first-appearance order), session_count,
    events (chronological), summary {kind: count}}. Retracted pairs never
    appear (raw lines stay on disk for audit only).
    """
    events = _active_events(_read_events(ledger_path))
    events.sort(key=_event_ts)  # chronological, stable on append order
    days: dict[str, dict] = {}
    for e in events:
        day = _local_day(str(e.get("ts") or ""))
        c = days.get(day)
        if c is None:
            c = {
                "date": day,
                "sessions": [],
                "session_count": 0,
                "events": [],
                "summary": {},
            }
            days[day] = c
        c["events"].append(dict(e))
        sid = str(e.get("session_id") or "")
        if sid and sid not in c["sessions"]:
            c["sessions"].append(sid)
        kind = str(e.get("kind"))
        c["summary"][kind] = int(c["summary"].get(kind, 0)) + 1
    out = sorted(days.values(), key=lambda c: c["date"], reverse=True)
    for c in out:
        c["session_count"] = len(c["sessions"])
    if limit_days is not None:
        day0 = (today if today is not None else datetime.date.today()) - datetime.timedelta(
            days=max(0, int(limit_days) - 1)
        )
        out = [c for c in out if c["date"] >= day0.isoformat()]
    if limit_clusters is not None:
        out = out[: max(0, int(limit_clusters))]
    return out


# --- key humanization (server-side display names; §3: derived, not invented) -

def _short_phrase(s: str, max_len: int = 48) -> str:
    """First self-contained chunk of a statement/goal, chip-sized."""
    s = " ".join((s or "").split()).rstrip(".")
    cuts = [i for i in (s.find(" and "), s.find(", "), s.find(" — "),
                        s.find(" (")) if i > 0]
    if cuts:
        s = s[: min(cuts)]
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0] + "…"
    return s


def can_do_display(key: str, kind: str) -> str:
    """Chip name for a can-do id: the statement, shortened sensibly.

    Copy law: the "Can ..." mastery frame is allowed ONLY at the known band
    (can_do_known); every other kind gets the bare gist. Unknown id → raw
    key (fallback, never invented prose).
    """
    gist = _can_do_gist(key)
    if not gist or gist == key:
        return key
    short = _short_phrase(gist)
    if not short:
        return key
    if kind == "can_do_known":
        return f"Can {short[0].lower()}{short[1:]}"
    return short[0].upper() + short[1:]


def _goal_short(desc: str) -> str:
    """Scene primary_exit description → short goal phrase for a chip."""
    s = " ".join((desc or "").split())
    head = s[:80]
    if ":" in head:
        s = s.split(":", 1)[1].strip()
    low = s.lower()
    for pre in ("the learner must ", "the learner "):
        if low.startswith(pre):
            s = s[len(pre):]
            break
    s = s.split(". ", 1)[0]
    return _short_phrase(s)


def default_scene_goals() -> dict[str, str]:
    """scene_id → short goal text from the configured course pack."""
    try:
        from .scenes import load_scenes

        out: dict[str, str] = {}
        for sc in load_scenes():
            sid = str(sc.get("id") or "")
            if not sid:
                continue
            desc = str(((sc.get("primary_exit") or {}).get("description")) or "")
            short = _goal_short(desc) if desc else ""
            out[sid] = short or sid.replace("_", " ")
        return out
    except Exception:
        return {}


def humanize_event(
    event: dict,
    table: dict | None,
    scene_goals: dict | None = None,
) -> dict:
    """{'display': str, 'gloss': str} for one event — humanized server-side.

    Lexicon/grammar keys display as the Spanish itself (gloss from the
    association table for hover); can-do ids as their shortened statement;
    task keys as the scene goal; anything unknown as the raw key. Display
    names are DERIVED from existing course assets, never free prose (§3).
    """
    kind = str(event.get("kind") or "")
    key = str(event.get("key") or "")
    item_kind = str(event.get("item_kind") or "")
    if kind == "epoch":
        # Learner-epoch boundary row (sheet_reset): visible marker, not a
        # celebration — pre-epoch history above it is real and stays.
        return {"display": "Fresh start — progress reset", "gloss": ""}
    if item_kind == "skill" or kind in ("can_do_emerging", "can_do_known"):
        return {"display": can_do_display(key, kind), "gloss": ""}
    if item_kind == "task" or kind == "task_complete":
        goals = scene_goals if scene_goals is not None else default_scene_goals()
        goal = str(goals.get(key) or "").strip()
        disp = (goal[0].upper() + goal[1:]) if goal else key
        return {"display": disp, "gloss": ""}
    entry = (table or {}).get(key)
    gloss = str(((entry or {}).get("gloss_en")) or "")
    return {"display": key, "gloss": gloss}


# --- crossing detection (pure; callers own dedupe via `seen`) ---------------

def ladder_crossings(transition: dict, *, seen: set[tuple[str, str]]) -> list[dict]:
    """Progress events implied by one retrieval-outcome interval transition.

    `transition` comes from retrieval_scheduler.record_outcome_ex — READ-ONLY
    telemetry; nothing here writes the sheet (§3.2 stays with the scheduler
    allowlist). Up-crossings fire once per (kind, key) via `seen`; a
    regression needs no ledger dedupe (interval resets below 3, so another
    regression requires a re-climb).
    """
    key = str(transition.get("key") or "")
    item_kind = str(transition.get("kind") or "")
    try:
        before = int(transition.get("interval_before") or 1)
        after = int(transition.get("interval_after") or 1)
    except (TypeError, ValueError):
        return []
    out: list[dict] = []
    if transition.get("success"):
        if before < TAKING_ROOT_DAYS <= after and ("taking_root", key) not in seen:
            out.append({
                "kind": "taking_root",
                "key": key,
                "polarity": "up",
                "item_kind": item_kind,
                "detail": detail_for("taking_root", key, interval=after),
            })
        if before < ROOTED_DAYS <= after and ("rooted", key) not in seen:
            out.append({
                "kind": "rooted",
                "key": key,
                "polarity": "up",
                "item_kind": item_kind,
                "detail": detail_for("rooted", key),
            })
    elif before >= TAKING_ROOT_DAYS:
        out.append({
            "kind": "regression",
            "key": key,
            "polarity": "down",
            "item_kind": item_kind,
            "detail": detail_for("regression", key, was=before),
        })
    return out


def sheet_crossings(
    prev_sheet: dict,
    cur_sheet: dict,
    *,
    seen: set[tuple[str, str]],
) -> list[dict]:
    """Error-recovery and can-do band crossings between two sheet states.

    Change-gated AND ledger-deduped: a band already held before this turn is
    history, not a fresh milestone (prevents celebration floods from seeded
    or legacy sheets that predate the ledger).
    """
    from .character_sheet import ERROR_PATTERN_HEALTHY_STREAK

    prev_sheet = prev_sheet if isinstance(prev_sheet, dict) else {}
    cur_sheet = cur_sheet if isinstance(cur_sheet, dict) else {}
    out: list[dict] = []

    prev_eps = prev_sheet.get("error_patterns") or {}
    for pid, ent in (cur_sheet.get("error_patterns") or {}).items():
        if not isinstance(ent, dict):
            continue
        count = int(ent.get("count") or 0)
        streak = int(ent.get("resolved_streak") or 0)
        if not (count == 0 and streak >= ERROR_PATTERN_HEALTHY_STREAK):
            continue
        p = prev_eps.get(pid) if isinstance(prev_eps.get(pid), dict) else {}
        p_ok = (
            int(p.get("count") or 0) == 0
            and int(p.get("resolved_streak") or 0) >= ERROR_PATTERN_HEALTHY_STREAK
        )
        if p_ok or ("error_recovered", str(pid)) in seen:
            continue
        out.append({
            "kind": "error_recovered",
            "key": str(pid),
            "polarity": "up",
            "item_kind": "error_pattern",
            "detail": detail_for(
                "error_recovered", str(pid),
                label=ent.get("label") or pid, streak=streak,
            ),
        })

    prev_skills = prev_sheet.get("skills") or {}
    for sid, ent in (cur_sheet.get("skills") or {}).items():
        if not isinstance(ent, dict):
            continue
        try:
            conf = float(ent.get("confidence") or 0.0)
        except (TypeError, ValueError):
            conf = 0.0
        status = str(ent.get("status") or "")
        p = prev_skills.get(sid) if isinstance(prev_skills.get(sid), dict) else {}
        try:
            p_conf = float(p.get("confidence") or 0.0)
        except (TypeError, ValueError):
            p_conf = 0.0
        p_status = str(p.get("status") or "")
        if (
            conf >= EMERGING_CONF
            and status in ("emerging", "known")
            and p_conf < EMERGING_CONF
            and ("can_do_emerging", str(sid)) not in seen
        ):
            out.append({
                "kind": "can_do_emerging",
                "key": str(sid),
                "polarity": "up",
                "item_kind": "skill",
                "detail": detail_for("can_do_emerging", str(sid)),
            })
        if (
            status == "known"
            and p_status != "known"
            and ("can_do_known", str(sid)) not in seen
        ):
            out.append({
                "kind": "can_do_known",
                "key": str(sid),
                "polarity": "up",
                "item_kind": "skill",
                "detail": detail_for("can_do_known", str(sid)),
            })
    return out


# --- live-state join + API payload ------------------------------------------

def live_state_supports(event: dict, sheet: dict) -> bool | None:
    """Does CURRENT sheet state still support the celebrated band?

    None = not applicable (encounter/task history and down events never carry
    a badge — they claim nothing about current ability).
    """
    kind = str(event.get("kind") or "")
    if (event.get("polarity") or "up") == "down":
        return None
    if kind in ("planted", "task_complete"):
        return None
    key = str(event.get("key") or "")
    sheet = sheet if isinstance(sheet, dict) else {}
    if kind in ("taking_root", "rooted"):
        section = _ITEM_SECTION.get(str(event.get("item_kind") or "")) or "lexicon"
        entry = (sheet.get(section) or {}).get(key)
        if not isinstance(entry, dict):
            return False
        try:
            interval = int(entry.get("interval_days") or 0)
        except (TypeError, ValueError):
            interval = 0
        return interval >= (ROOTED_DAYS if kind == "rooted" else TAKING_ROOT_DAYS)
    if kind == "error_recovered":
        from .character_sheet import ERROR_PATTERN_HEALTHY_STREAK

        ent = (sheet.get("error_patterns") or {}).get(key)
        if not isinstance(ent, dict):
            return False
        return (
            int(ent.get("count") or 0) == 0
            and int(ent.get("resolved_streak") or 0) >= ERROR_PATTERN_HEALTHY_STREAK
        )
    if kind in ("can_do_emerging", "can_do_known"):
        ent = (sheet.get("skills") or {}).get(key)
        if not isinstance(ent, dict):
            return False
        if kind == "can_do_known":
            return str(ent.get("status") or "") == "known"
        try:
            return float(ent.get("confidence") or 0.0) >= EMERGING_CONF
        except (TypeError, ValueError):
            return False
    return None


def display_state(event: dict) -> str:
    """ONE state per node (2026-07-28 rail incident: 'known ★' + 'needs
    re-check' on the same line reads broken). Exactly one of:
    - "down"       polarity-down event (regression) — never celebrated
    - "recheck"    celebrated band no longer supported by the live sheet —
                   the re-check badge REPLACES the celebration icon/label
    - "celebrated" live state supports (or the kind carries no live claim)
    - "boundary"   learner-epoch mark (sheet_reset) — a divider, never a
                   celebration (Phase 1 batch 2)
    History stays in the ledger; the display shows current truth.
    """
    if event.get("kind") == "epoch":
        return "boundary"
    if (event.get("polarity") or "up") == "down":
        return "down"
    if event.get("needs_recheck"):
        return "recheck"
    return "celebrated"


# Rail grouping (2026-07-28 rail incident: word-level orphan nodes read as
# "I am supposed to be learning buenos dias?"): nodes cluster by association-
# table THEME; skills/can-dos under "Abilities", tasks under "Tasks",
# non-table keys under "other".
_GROUP_ABILITIES = ("abilities", "Abilities")
_GROUP_TASKS = ("tasks", "Tasks")
_GROUP_OTHER = ("other", "Other")


def _group_for(event: dict, table: dict | None) -> tuple[str, str]:
    """(theme, display label) for one event."""
    item_kind = str(event.get("item_kind") or "")
    if item_kind == "skill":
        return _GROUP_ABILITIES
    if item_kind == "task":
        return _GROUP_TASKS
    entry = (table or {}).get(str(event.get("key") or ""))
    theme = str((entry or {}).get("theme") or "").strip()
    if not theme:
        return _GROUP_OTHER
    return theme, theme.replace("_", " ").capitalize()


def group_cluster_events(events: list[dict], table: dict | None) -> list[dict]:
    """Theme groups for one cluster, in first-appearance order.

    Shape: [{theme, label, events (chronological), summary {kind: count}}].
    Pure regrouping of the SAME event dicts — invents nothing (§3).
    """
    groups: dict[str, dict] = {}
    order: list[str] = []
    for e in events:
        theme, label = _group_for(e, table)
        g = groups.get(theme)
        if g is None:
            g = {"theme": theme, "label": label, "events": [], "summary": {}}
            groups[theme] = g
            order.append(theme)
        g["events"].append(e)
        kind = str(e.get("kind"))
        g["summary"][kind] = int(g["summary"].get(kind, 0)) + 1
    return [groups[t] for t in order]


def build_progress_payload(
    sheet: dict,
    *,
    session_id: str = "",
    table: dict | None = None,
    scene_goals: dict | None = None,
    ledger_path: Path | str | None = None,
    limit_clusters: int = 20,
    today: datetime.date | None = None,
) -> dict:
    """/api/progress payload: DAY clusters + live-state join + countable header.

    The visual unit is the local calendar day (`read_recent_days`) — one
    cluster per day, sessions merged, session ids kept per event for
    tooltip/debug. Each event carries humanized `display`/`gloss` fields
    (`humanize_event`) and a single `display_state`; each cluster carries
    theme `groups` for subtle ordering (never the only visible text — the
    2026-07-28 rail incident). Header counts are the amended (e)4 join —
    countable things, not mean confidence: durable = rooted events whose
    live interval still holds >=14; known / emerging = live sheet status
    bands. The abstract 0-100 score stays in the payload for compat but is
    no longer the display.
    """
    sheet = sheet if isinstance(sheet, dict) else {}
    clusters = read_recent_days(
        limit_clusters=limit_clusters, ledger_path=ledger_path, today=today
    )
    goals = scene_goals
    if goals is None and any(
        str(e.get("item_kind") or "") == "task" or e.get("kind") == "task_complete"
        for c in clusters
        for e in c["events"]
    ):
        goals = default_scene_goals()
    total_events = 0
    for c in clusters:
        for e in c["events"]:
            total_events += 1
            e["needs_recheck"] = live_state_supports(e, sheet) is False
            e["display_state"] = display_state(e)
            e.update(humanize_event(e, table, goals))
        c["groups"] = group_cluster_events(c["events"], table)

    durable_keys = {
        (str(e.get("item_kind") or ""), str(e.get("key") or ""))
        for e in _active_events(_read_events(ledger_path))
        if e.get("kind") == "rooted" and (e.get("polarity") or "up") == "up"
    }
    durable = 0
    for item_kind, key in durable_keys:
        section = _ITEM_SECTION.get(item_kind) or "lexicon"
        entry = (sheet.get(section) or {}).get(key)
        if not isinstance(entry, dict):
            continue
        try:
            if int(entry.get("interval_days") or 0) >= ROOTED_DAYS:
                durable += 1
        except (TypeError, ValueError):
            continue

    known = 0
    emerging = 0
    for ent in (sheet.get("skills") or {}).values():
        if not isinstance(ent, dict):
            continue
        status = str(ent.get("status") or "")
        if status == "known":
            known += 1
        elif status == "emerging":
            emerging += 1

    try:
        from .retrieval_scheduler import due_items

        due_soon = len(due_items(sheet, today=today, max_due=10))
    except Exception:
        due_soon = 0
    try:
        from .character_sheet import compute_progress_score

        score = compute_progress_score(sheet)
    except Exception:
        score = {}

    return {
        "clusters": clusters,
        "counts": {"durable": durable, "known": known, "emerging": emerging},
        "due_soon": due_soon,
        "session_id": str(session_id or ""),
        "empty": total_events == 0,
        # Compat only — header displays the countable pair, not this scalar.
        "score": score,
    }
