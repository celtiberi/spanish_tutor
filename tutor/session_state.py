"""SessionState — one aggregate owning ALL per-session runtime state.

Phase 1 of the adjudicated architecture refactor
(docs/reviews-architecture-refactor.md — "Refactor proposal" Phase 1, as
amended by Grok round-1 (a)/(f) and the closing adjudication):

- The map's state census found 5 session stores + loose session attributes
  spread across ConversationalSession, reset by **5 different paths covering
  5 different subsets** (``RESET_COVERAGE`` below is that census as code).
- Batch 1 (landed): the aggregate + the reset-coverage table WITHOUT
  behavior change — construction bit-identical to the old inline
  ``__init__`` block; existing reset paths kept their partial coverage.
- Batch 2 (landed — the DECLARED behavior deltas, pre-announced in the
  review, never silent):
  1. Unified ``reset(kind)`` for "new_chat" / "sheet_reset" /
     "open_session": every session-scoped store resets (the table's old
     ``batch2`` column became ``current`` in a visible diff, preserved as
     ``pre_batch2`` for the audit trail). This CLOSES the new-chat leak —
     intro budget, asked_topics, cooldowns, phase clock and task state no
     longer bleed between chats.
  2. Costs continuity RULING: the per-chat SessionCostTracker resets on
     new_chat AND sheet_reset (the header shows THIS chat's spend); the
     on-disk cost ledger keeps the money history — append-only forever.
  3. Progress-ledger scope: sheet_reset appends a learner-epoch mark
     (``progress_ledger.record_epoch``, called from
     ``ConversationalSession.reset_sheet``) so a fresh learner re-mints
     milestones instead of being dedupe-suppressed. ``record_retraction``
     is deliberately NOT used — nothing false to retract.
  4. E2 RULING — WIRED (not deleted): ``snapshot()`` / ``from_snapshot()``
     compose the per-store serialization APIs (ModeSessionState /
     SessionMemory ``snapshot``+``from_snapshot``, PhaseState
     ``snapshot``/``from_snapshot``, TaskState ``as_dict``/``from_dict``).
     No production caller yet BY DESIGN: this is the documented persistence
     surface for future server-restart resume, pinned by a round-trip test
     so it cannot rot into a third half-serialization.
  5. ``open_session`` kind: DEPRECATED alias for "new_chat" — its old
     3-store partial reset (costs/history/messages_for_ui) was the residual
     bug the review's map correction identified.

Until Phase 4 consumes the aggregate directly, ConversationalSession keeps
its historical attribute surface via thin @property delegates
(``self.pedagogy_memory`` → ``self.state.pedagogy_memory`` etc.).
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # imported lazily at runtime (conv_session import style)
    from .costs import SessionCostTracker
    from .modes import ModeSessionState
    from .session_memory import SessionMemory
    from .session_phases import PhaseState
    from .task_runtime import TaskState


# Debug request capture (local web debug box, 2026-07-28): per tutor call,
# the outbound request + response metadata. IN-MEMORY ONLY — a ring buffer
# of the last DEBUG_RING_SIZE calls per session, served by
# GET /api/debug/requests. Lives here (with the deque it sizes) since
# Phase 1 batch 1; conv_session re-exports it for existing importers.
DEBUG_RING_SIZE = 10


# Canonical field list of the aggregate (the census surface). Order follows
# the old ConversationalSession.__init__ construction order.
SESSION_STATE_FIELDS: tuple[str, ...] = (
    "history",
    "messages_for_ui",
    "focus_panel",
    "focus_key",
    "focus_meta",
    "focus_version",
    "focus_lock",
    "focus_inflight",
    "image_warm_lock",
    "image_warm_inflight",
    "last_plan",
    "pedagogy_memory",
    "mode_state",
    "phase_state",
    "task_state",
    "last_mode_decision",
    "debug_requests",
    "costs",
    "progress_session_id",
)

_ALL = frozenset(SESSION_STATE_FIELDS)
_LOCKS = frozenset({"focus_lock", "image_warm_lock"})

# Unified reset coverage (Phase 1 batch 2): every session-scoped field
# resets. Kept alive across resets: the two runtime locks (never swapped
# while potentially held) and progress_session_id (the ledger cluster id of
# the LIVE session object — learner scope rotates via the ledger epoch mark,
# not by renaming the session).
UNIFIED_RESET = _ALL - _LOCKS - frozenset({"progress_session_id"})

# ---------------------------------------------------------------------------
# Reset-coverage census AS CODE.
#
# Batch 2 landed the declared unification: "current" is now the UNIFIED
# coverage (asserted by tests/test_session_state.py — any change must be a
# visible diff of this table, never silent), "churn" documents NON-reset
# overwrites riding the same flow (e.g. the sheet_public focus repaint), and
# "pre_batch2" preserves the batch-1 census (the 5-paths-5-subsets bug
# class) as the audit trail of exactly what the unification changed.
# "ruling" records the batch-2 adjudicated decisions per kind.
# ---------------------------------------------------------------------------
RESET_COVERAGE: dict[str, dict[str, Any]] = {
    # ConversationalSession.__init__ → SessionState.fresh(). Reached by:
    # web session_start want_fresh (new object), /api/session/reset (new
    # object), evals construction. progress_session_id is assigned by the
    # owner right after logger creation (fresh() seeds "").
    "fresh": {
        "path": "ConversationalSession.__init__ (SessionState.fresh)",
        "current": _ALL,
        "churn": frozenset(),
        "pre_batch2": _ALL,
        "ruling": "Unchanged: the web fresh paths (session_start want_fresh, "
                  "/api/session/reset) keep constructing a new object.",
        "notes": "Everything constructed new, including locks and "
                 "progress_session_id.",
    },
    # SessionState.reset("new_chat") — called by ConversationalSession.
    # open_session(), which the web session_start resume branch and the
    # /api/chat auto-open route through. Memory is reconstructed here and
    # then seed_from_sheet()-SEEDED by open_session (new chat ≠ new learner:
    # durable knowledge rides the sheet; session-scoped state never does).
    "new-chat": {
        "path": "SessionState.reset('new_chat') via open_session() "
                "(web session_start resume branch, /api/chat auto-open)",
        "current": UNIFIED_RESET,
        # Same-response sheet_public() repaint rewrites focus_meta and bumps
        # focus_version AFTER the reset — paint, not reset (it happens on
        # every /api/chat too).
        "churn": frozenset({"focus_meta", "focus_version"}),
        "pre_batch2": frozenset({
            "history", "messages_for_ui", "focus_panel", "focus_key",
            "costs",
        }),
        "ruling": "Costs continuity: the per-chat SessionCostTracker RESETS "
                  "on new_chat — the header shows this chat's spend; the "
                  "on-disk cost ledger keeps the money history (append-only "
                  "forever).",
        "notes": "Leak CLOSED (batch 2): intro budget, asked_topics, "
                 "covered_concepts, mode cooldowns, phase clock, task state "
                 "and the debug ring no longer bleed between chats.",
    },
    # ConversationalSession.reset_sheet → SessionState.reset("sheet_reset").
    # The sheet file wipe + default_sheet rebuild and the progress-ledger
    # learner-epoch mark live in reset_sheet (the caller owns the sheet and
    # the ledger; this object owns only session runtime state).
    "sheet-reset": {
        "path": "ConversationalSession.reset_sheet "
                "(SessionState.reset('sheet_reset'))",
        "current": UNIFIED_RESET,
        "churn": frozenset(),
        "pre_batch2": frozenset({
            "history", "messages_for_ui", "focus_panel", "focus_key",
            "focus_meta", "pedagogy_memory", "mode_state", "phase_state",
            "task_state", "last_mode_decision", "last_plan",
            "debug_requests",
        }),
        "ruling": "Resets EVERYTHING including costs (the 4 batch-1 misses: "
                  "costs, focus_version, focus_inflight, "
                  "image_warm_inflight) EXCEPT the on-disk cost ledger, "
                  "which is append-only forever. Progress-ledger scope: "
                  "reset_sheet appends a learner-epoch mark "
                  "(progress_ledger.record_epoch) so the fresh learner "
                  "re-mints milestones; record_retraction is NOT used — "
                  "nothing false to retract. debug ring now RECONSTRUCTED "
                  "(batch 1 cleared it in place).",
        "notes": "Phase plan rebuilt from the new blank sheet.",
    },
    # DEPRECATED alias: reset("open_session") == reset("new_chat"). The
    # batch-1 census showed open_session's own partial reset (costs +
    # transcript replacement only) was the residual leak — open_session now
    # routes through the new_chat kind.
    "open-session": {
        "path": "DEPRECATED alias — SessionState.reset('open_session') "
                "routes to 'new_chat'",
        "current": UNIFIED_RESET,
        "churn": frozenset(),
        "pre_batch2": frozenset({"costs", "history", "messages_for_ui"}),
        "ruling": "Alias, not a fourth semantics: its 3-store partial reset "
                  "was the residual bug (review map correction).",
        "notes": "history/messages_for_ui are then REPLACED with the open "
                 "transcript by open_session itself.",
    },
}


@dataclass
class SessionState:
    """Aggregate of the 5 session stores + loose per-session attributes.

    Field order mirrors the pre-aggregate ``ConversationalSession.__init__``
    construction order; ``fresh()`` builds everything exactly the way that
    inline block did (same constructors, same arguments, same defaults).
    """

    history: list[dict]
    messages_for_ui: list[dict]  # learner-visible only
    focus_panel: dict | None
    focus_key: str | None
    focus_meta: dict
    focus_version: int
    focus_lock: threading.Lock
    focus_inflight: bool
    # Async image warm (audit (e) 2026-07-28): reply-path cache misses never
    # generate in-line; a daemon thread warms the cache instead.
    image_warm_lock: threading.Lock
    image_warm_inflight: set[str]
    last_plan: dict | None
    pedagogy_memory: "SessionMemory"
    mode_state: "ModeSessionState"
    # Session phase plan (Phase 2): built once from the loaded sheet.
    phase_state: "PhaseState"
    # ConvergentTaskRuntime state (Phase 5, r6 Rank-4): bound to the first
    # task-capable open scene on the first task-phase turn; session-scoped.
    task_state: "TaskState | None"
    last_mode_decision: dict | None
    # Debug ring buffer (web debug box): in-memory only, never disk logs.
    debug_requests: deque
    costs: "SessionCostTracker"
    # Progress journey rail: cluster id for this session's ledger events.
    # fresh() seeds "" — the owner assigns the real id after logger creation
    # (unchanged from the pre-aggregate __init__ ordering).
    progress_session_id: str
    # Construction inputs remembered so reset("full") can replay them.
    _fresh_args: dict = field(default_factory=dict, repr=False)

    @classmethod
    def fresh(
        cls,
        sheet: dict,
        *,
        source_label: str,
        pack_topics: list[str],
        due_count: int,
        blank: bool,
    ) -> "SessionState":
        """Build every store/attribute the way __init__ did pre-aggregate.

        The phase plan is ``PhaseState(build_phase_plan(sheet, due_count=…,
        blank=…, pack_topics=…))`` — identical to
        ``conv_session.build_session_phase_state`` with the inputs computed
        by the caller (they were computed from the same sheet/pack there).
        """
        args = {
            "sheet": sheet,
            "source_label": source_label,
            "pack_topics": list(pack_topics or []),
            "due_count": int(due_count),
            "blank": bool(blank),
        }
        state = cls(**cls._construct(args), _fresh_args=args)
        return state

    @staticmethod
    def _construct(args: dict) -> dict:
        """The one construction recipe (shared by fresh() and reset)."""
        from .costs import SessionCostTracker
        from .modes import ModeSessionState
        from .session_memory import SessionMemory
        from .session_phases import PhaseState, build_phase_plan

        return {
            "history": [],
            "messages_for_ui": [],
            "focus_panel": None,
            "focus_key": None,
            "focus_meta": {"source": "static"},
            "focus_version": 0,
            "focus_lock": threading.Lock(),
            "focus_inflight": False,
            "image_warm_lock": threading.Lock(),
            "image_warm_inflight": set(),
            "last_plan": None,
            "pedagogy_memory": SessionMemory(),
            "mode_state": ModeSessionState(),
            "phase_state": PhaseState(build_phase_plan(
                args["sheet"],
                due_count=args["due_count"],
                blank=args["blank"],
                pack_topics=args["pack_topics"],
            )),
            "task_state": None,
            "last_mode_decision": None,
            "debug_requests": deque(maxlen=DEBUG_RING_SIZE),
            "costs": SessionCostTracker(source=args["source_label"]),
            "progress_session_id": "",
        }

    def reset(self, kind: str, *, sheet: dict | None = None) -> None:
        """Unified session reset (Phase 1 batch 2 declared delta).

        Kinds (hyphen and underscore spellings both accepted):

        - ``"full"`` — exact replay of construction from the remembered
          fresh() inputs, including locks and progress_session_id (batch-1
          semantics, kept for tests/tools).
        - ``"new_chat"`` — every session-scoped field resets
          (``UNIFIED_RESET``): memory, mode state (cooldowns, asked scenes),
          phase clock REBUILT from the CURRENT sheet, task state, debug
          ring, focus fields, last_*, and — per the costs continuity ruling
          — the per-chat cost tracker (the on-disk cost ledger keeps the
          money history). Kept: the two runtime locks (never swapped while
          potentially held) and progress_session_id (same live session).
          The sheet itself is never touched here.
        - ``"sheet_reset"`` — identical FIELD coverage to new_chat; the
          difference lives with the caller (ConversationalSession.
          reset_sheet wipes/rebuilds the sheet file and appends the
          progress-ledger learner-epoch mark before calling this).
        - ``"open_session"`` — DEPRECATED alias for ``"new_chat"`` (its old
          3-store partial reset was the residual leak).

        ``sheet`` is the CURRENT sheet the phase plan must be rebuilt from
        (due count and blank flag are recomputed from it); omitted, the
        remembered fresh() sheet is used. The remembered inputs are updated
        so a later reset replays against the newest sheet.
        """
        canon = str(kind).replace("-", "_")
        if canon == "full":
            for name, value in self._construct(self._fresh_args).items():
                setattr(self, name, value)
            return
        if canon == "open_session":
            canon = "new_chat"  # deprecated alias (RESET_COVERAGE ruling)
        if canon not in ("new_chat", "sheet_reset"):
            raise ValueError(
                f"unknown reset kind {kind!r} — expected 'full', 'new_chat',"
                " 'sheet_reset' or the deprecated alias 'open_session' "
                "(see RESET_COVERAGE)"
            )
        from .pedagogy_contract import is_blank_learner
        from .retrieval_scheduler import due_items

        args = dict(self._fresh_args)
        if sheet is not None:
            args["sheet"] = sheet
        # Phase plan inputs recomputed from the CURRENT sheet (a new chat on
        # a learned sheet must not replay the construction-time due/blank).
        args["due_count"] = len(due_items(args["sheet"]))
        args["blank"] = is_blank_learner(args["sheet"])
        self._fresh_args = args
        new_values = self._construct(args)
        for name in SESSION_STATE_FIELDS:
            if name in _LOCKS or name == "progress_session_id":
                continue
            setattr(self, name, new_values[name])

    # ------------------------------------------------------------------
    # E2 ruling (Phase 1 batch 2): WIRED — the persistence surface.
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """JSON-serializable snapshot of the resumable session state.

        E2 ruling (docs/reviews-architecture-refactor.md, batch 2): the
        per-store serialization APIs are WIRED here rather than deleted —
        composed via ModeSessionState.snapshot / SessionMemory.snapshot
        (plus their ``from_snapshot`` restores), PhaseState.snapshot /
        from_snapshot and TaskState.as_dict / from_dict. No production
        caller yet BY DESIGN: this is the documented persistence surface
        for future server-restart resume, pinned by a round-trip test so
        it cannot rot into a third half-serialization.

        Excluded BY DESIGN (rebuilt fresh on restore): the two runtime
        locks and the inflight flags (focus_inflight, image_warm_inflight —
        transient work markers), debug_requests (in-memory-only law: debug
        payloads are never persisted), and costs (per-chat header state;
        the durable money record is the on-disk cost ledger).

        The per-store ``snapshot()`` shapes are consumed by prompt/debug
        paths and stay untouched; fields they omit (SessionMemory:
        last_learner, last_tutor_ack, image counters/cooldown;
        ModeSessionState: learner_turn_index, last_error_hit_turn) ride
        here as sibling keys and are restored by the stores'
        ``from_snapshot``.
        """
        mem = self.pedagogy_memory
        ms = self.mode_state
        return {
            "version": 1,
            "history": [dict(m) for m in self.history],
            "messages_for_ui": [dict(m) for m in self.messages_for_ui],
            "focus_panel": (
                dict(self.focus_panel)
                if isinstance(self.focus_panel, dict) else None
            ),
            "focus_key": self.focus_key,
            "focus_meta": dict(self.focus_meta or {}),
            "focus_version": int(self.focus_version or 0),
            "last_plan": (
                dict(self.last_plan)
                if isinstance(self.last_plan, dict) else None
            ),
            "last_mode_decision": (
                dict(self.last_mode_decision)
                if isinstance(self.last_mode_decision, dict) else None
            ),
            "progress_session_id": str(self.progress_session_id or ""),
            "memory": {
                **mem.snapshot(),
                "last_learner": mem.last_learner,
                "last_tutor_ack": mem.last_tutor_ack,
                "images_generated": mem.images_generated,
                "images_declared_generated": mem.images_declared_generated,
                "declared_image_cooldown": mem.declared_image_cooldown,
            },
            "mode_state": {
                **ms.snapshot(),
                "learner_turn_index": ms.learner_turn_index,
                "last_error_hit_turn": dict(ms.last_error_hit_turn),
            },
            "phase_state": self.phase_state.snapshot(),
            "task_state": (
                self.task_state.as_dict()
                if self.task_state is not None else None
            ),
        }

    @classmethod
    def from_snapshot(
        cls,
        data: dict | None,
        *,
        sheet: dict,
        source_label: str,
        pack_topics: list[str],
        due_count: int,
        blank: bool,
    ) -> "SessionState":
        """Rebuild a SessionState from ``snapshot()`` output.

        The fresh() inputs are required because the excluded runtime fields
        (locks, inflight flags, debug ring, costs) and the reset-replay args
        are constructed anew; every persisted field is then overlaid. A
        snapshot without a phase plan falls back to the freshly built one.
        """
        from .modes import ModeSessionState
        from .session_memory import SessionMemory
        from .session_phases import PhaseState
        from .task_runtime import TaskState

        state = cls.fresh(
            sheet,
            source_label=source_label,
            pack_topics=pack_topics,
            due_count=due_count,
            blank=blank,
        )
        d = data if isinstance(data, dict) else {}
        state.history = [dict(m) for m in d.get("history") or []]
        state.messages_for_ui = [
            dict(m) for m in d.get("messages_for_ui") or []
        ]
        fp = d.get("focus_panel")
        state.focus_panel = dict(fp) if isinstance(fp, dict) else None
        fk = d.get("focus_key")
        state.focus_key = str(fk) if fk else None
        state.focus_meta = dict(d.get("focus_meta") or {"source": "static"})
        state.focus_version = int(d.get("focus_version") or 0)
        lp = d.get("last_plan")
        state.last_plan = dict(lp) if isinstance(lp, dict) else None
        lmd = d.get("last_mode_decision")
        state.last_mode_decision = (
            dict(lmd) if isinstance(lmd, dict) else None
        )
        state.progress_session_id = str(d.get("progress_session_id") or "")
        state.pedagogy_memory = SessionMemory.from_snapshot(d.get("memory"))
        state.mode_state = ModeSessionState.from_snapshot(d.get("mode_state"))
        ps = d.get("phase_state")
        if isinstance(ps, dict) and ps.get("plan"):
            state.phase_state = PhaseState.from_snapshot(ps)
        ts = d.get("task_state")
        state.task_state = (
            TaskState.from_dict(ts) if isinstance(ts, dict) else None
        )
        return state
