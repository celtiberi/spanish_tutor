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

Live-state join: `build_progress_payload` joins each celebrated node to the
CURRENT sheet; a node whose live band no longer supports the celebration
gets `needs_recheck: true` (quiet badge, never silent permanence).

Single purpose, stdlib only; clock (`now`/`today`) and `ledger_path` are
injectable for tests. Default file: logs/progress.jsonl (costs.jsonl
pattern). Code-owned: the model has no write path into this ledger.
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
    raise ValueError(f"unknown milestone kind {kind!r}")


def record_milestone(
    kind: str,
    key: str,
    detail: str = "",
    *,
    polarity: str = "up",
    session_id: str = "",
    item_kind: str = "",
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


def has_milestone(
    kind: str,
    key: str,
    *,
    polarity: str = "up",
    ledger_path: Path | str | None = None,
) -> bool:
    """Dedup query: has (kind, key, polarity) ever been recorded?"""
    return any(
        e.get("kind") == kind
        and e.get("key") == key
        and (e.get("polarity") or "up") == polarity
        for e in _read_events(ledger_path)
    )


def up_keys(ledger_path: Path | str | None = None) -> set[tuple[str, str]]:
    """All (kind, key) pairs with an up event — one read for per-turn dedupe."""
    return {
        (str(e.get("kind")), str(e.get("key")))
        for e in _read_events(ledger_path)
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
    Events without a session_id cluster by local calendar day.
    """
    events = _read_events(ledger_path)
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


def build_progress_payload(
    sheet: dict,
    *,
    session_id: str = "",
    ledger_path: Path | str | None = None,
    limit_clusters: int = 20,
    today: datetime.date | None = None,
) -> dict:
    """/api/progress payload: clusters + live-state join + countable header.

    Header counts are the amended (e)4 join — countable things, not mean
    confidence: durable = rooted events whose live interval still holds >=14;
    known / emerging = live sheet status bands. The abstract 0-100 score
    stays in the payload for compat but is no longer the display.
    """
    sheet = sheet if isinstance(sheet, dict) else {}
    clusters = read_recent(
        limit_clusters=limit_clusters, ledger_path=ledger_path, today=today
    )
    total_events = 0
    for c in clusters:
        for e in c["events"]:
            total_events += 1
            e["needs_recheck"] = live_state_supports(e, sheet) is False

    durable_keys = {
        (str(e.get("item_kind") or ""), str(e.get("key") or ""))
        for e in _read_events(ledger_path)
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
