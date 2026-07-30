"""Turn pipeline — TurnContext + the pre-model stage families (Phase 4).

The adjudicated architecture refactor (docs/reviews-architecture-refactor.md,
Phase 4) breaks ``ConversationalSession._execute_ai_tutor`` into explicit
stages.  Batch 1: the ``TurnContext`` working set plus the PRE-MODEL HEAD
extracted as plain named functions.  Batch 2: the CONTRIBUTORS family —
the five instruction contributors as uniform ``InstructionContributor``
instances run by ``stage_contributors``, with ONE shared eligibility
predicate (``flavorable``) and ONE instruction-mutation site
(``append_instruction``).  No framework, no registry magic — the executor
calls a named-function sequence.

Stage protocol
--------------
``stage_xxx(session, ctx) -> None`` — ``session`` is the live
``ConversationalSession`` (state reads/writes go through its aggregate
delegates exactly as the inline code did); ``ctx`` is the per-turn
``TurnContext``.  Stages mutate ``ctx`` and session state; they return
nothing.  Ordering is LAW: the goldens pin state mutations and note order,
so the sequence below must match the historical inline order byte-for-byte
in effect.

The head sequence (``PRE_MODEL_STAGES``, in order)::

    stage_classify_signals   blocking LLM intent classifier (opt-in)
    stage_memory_intake      note_learner + eager comprehension-hold clears
    stage_observe            mode_state.tick + observations + error-hit
                             recording + blank/sigs derivation
    stage_english_streak     english-only streak update — SINGLE streak
                             owner (CHAR-BUG-002 RESOLVED, batch 3: modes
                             guard 4 reads state only)
    stage_due_outcomes       pre-turn retrieval-outcome recording
    stage_open_scenes        open-scene assembly + mode_state binding
    stage_bind_activity      empty-retrieval force_advance + activity bind
    stage_select_mode        select_mode + MODE/MODE_REASON typed events
    stage_guard6_covered     guard-6 covered-concept session memory

The CONTRIBUTORS family (batch 2) runs next: ``stage_contributors``
iterates ``CONTRIBUTORS`` — due_elicit → self_flag_uptake → introduce →
task → close_summary, the EXACT historical inline order.  Each contributor
is {name, eligible(ctx), build(session, ctx)}; ``build`` wraps the
module-level builder functions in conv_session (due_elicit_block etc. —
signatures unchanged, their direct tests untouched) and returns the
instruction text (or None); the loop appends it via ``append_instruction``.
The introduce contributor returns None by design — its render is DEFERRED
to the realize region (R-B honesty: an image plan must not claim an
attachment the cache/cap denied); it parks the plan on ``ctx.intro_plan``.
The zero-register overlay is NOT a contributor: it lives inside
``modes.select_mode`` (select stage) and joins with a single ``"\\n"``,
not the contributor idiom — verified against the family markers, left
in place.

``stage_phase_tick`` is part of the phase family but is NOT in the head
sequence: in the real post-E4 code the phase clock ticks AFTER the
contributor region (due/uptake/introduce/task/close instruction assembly),
not between select and contributors as the amended plan sketch drew it.
The goldens pin that order; the executor calls it at the true site.

The REALIZE family (batch 3) runs after the phase tick, at the exact
historical inline order (``REALIZE_STAGES``)::

    stage_signal_shadow      parallel signal classifier spawn (default)
    stage_mode_image         mode-decision image attach (cache-only)
    stage_fallback_image     placement/association/repair fallback +
                             comprehension-repair relevance law
    stage_image_costs        image cost notes
    stage_introduce_render   DEFERRED introduce render (consumes
                             ctx.intro_plan; R-B→R-D downgrade when the
                             planned image did not attach — Grok AMEND 4b)
    stage_mode_snapshot      last_mode_decision focus-rail snapshot
                             (AFTER the render so instructions are faithful
                             to what the model actually receives)
    stage_prompt_build       system + task message + FULL-history assembly
    stage_model_call         tutor_turn; provider exceptions become
                             ctx.error_result (the executor returns it)

The GATE/REPAIR family (batch 3, E3): ``stage_gate_context`` builds the
turn-constant ``output_gate.GateContext`` from the TurnContext — the
historical 18-argument call-site seam dies there; ``stage_gate_check``
parses the reply and runs the gate (+ the recast re-check);
``stage_gate_repair`` owns the verdict events and the single bounded
repair round + re-gate.  The executor wraps check+repair in the
historical try/except (any gate exception → OUTPUT_GATE_ERROR, turn
proceeds ungated) — context build stays outside it, as inline.

The RECORDERS family (batch 4) runs after gate/repair — the post-model
turn recorders at the exact historical inline order (``RECORDER_STAGES``)::

    stage_finish             sheet process_turn + TurnResult assembly
                             (session._finish; the region's sheet writer)
    stage_introduce_ledger   introduce_outcome → ledger/memory/milestone
                             writes (r7 S1 + R-H scaffold-evidence law)
    stage_first_seen         gate scaffold_saved → durable first_seen bits
                             (Round-2 AMEND 1c)
    stage_intro_morph        introduced/first-seen verb keys engage the
                             Morphology card (2026-07-29 review: tutor-side
                             introductions had no home)
    stage_memory_notes       note_plan_try + asked-topic registry +
                             note_tutor_turn memory writes
    stage_frame_record       frames_seen exposure writes for realized due
                             elicits + introductions (encounter-variety
                             round, 2026-07-29)
    stage_declared_image     tutor-declared <image concept="…"/> resolution
                             (relevance law, repeat/cooldown gates)
    stage_mode_record        mode-state recorders: hard-break note, form
                             cooldowns, error-resolve + retrieval enqueue,
                             last_mode (scene_modeled marks DELETED —
                             CHAR-BUG-005 resolved-by-deletion)
    stage_soft_plan          soft_plan snapshot (focus rail / debug)
    stage_tail_events        tail summary events (pedagogy/phase/activity/
                             hard_break/plan_source/mem_* emits)
    stage_parts_notes        result.parts enrichment + THE notes projection
                             (seq-ordered render of the typed event log)
    stage_sheet_commit       THE atomic-turn sheet commit — the single
                             durable persist of a successful turn
                             (CHAR-BUG-001 RESOLVED, batch 4 declared
                             delta per Grok amendment (a))

``stage_sheet_commit`` is the declared behavior delta: the historical
mid-turn ``save_sheet`` sites (_finish, introduce ledger, first_seen,
resolve-enqueue) are REMOVED — the in-memory sheet still mutates through
every stage, disk persists ONCE at the commit point.  Crash semantics
changed deliberately: a turn commits or it doesn't (no partial mid-turn
states on disk); the ``__init__``/reset/close saves outside the turn stay.

The CAPTURE/LOG family (batch 5) closes the stage inventory
(``CAPTURE_LOG_STAGES``): ``stage_debug_capture`` (the in-memory debug
ring entry — never disk-logged) then ``stage_log_turn`` (the single
session-log write, carrying the result the recorder family fully
enriched).  No new TurnContext fields were needed — batches 3/4 already
carry every capture input (the keep-it-lean law held).
``_execute_ai_tutor`` is now: build ctx → run the families → return
ctx.result; the batch-1 locals-unpack shim is retired (batch 5 cleanup).

Import discipline: module level is stdlib-only; every tutor import is lazy
inside the stage that needs it (mirrors the historical method-top lazy
imports and keeps conv_session ↔ turn_pipeline acyclic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class TurnContext:
    """Per-turn working set threaded between stages.

    Lean by design: fields exist only for what the extracted stages
    produce/consume today.  The contributor/realize/gate/recorder batches
    add their fields (due list, intro plan, task snapshot, teach_images,
    request/response artifacts, gate result) when those regions migrate.
    """

    # -- turn inputs (executor args) ----------------------------------------
    learner: str
    is_open: bool
    ev: Any  # TurnEventLog handle (begin_turn_log(session))
    input_mode: str = "text"
    log_learner: str | None = None

    # -- produced by the pre-model head -------------------------------------
    llm_signals: set[str] | None = None   # blocking classifier (opt-in)
    sig_pre: set[str] = field(default_factory=set)  # note_learner signals
    obs: dict = field(default_factory=dict)         # build_observations
    blank: bool = False                             # blank-sheet learner
    sigs: set[str] = field(default_factory=set)     # observation signals
    open_scenes: list = field(default_factory=list)
    activity: str = ""                              # phase activity hint
    decision: Any = None                            # select_mode decision

    # -- produced by the contributor family (batch 2) -----------------------
    # IntroducePlan parked for the DEFERRED render in the realize region
    # (R-B honesty: rendered only after image resolution is known).
    intro_plan: Any = None

    # -- produced by stage_phase_tick (post-contributors — see module doc) --
    phase_consumed: bool | None = None

    # -- produced by the realize family (batch 3) ---------------------------
    teach_images: list = field(default_factory=list)
    image_decision: Any = None                      # ImageDecision | None
    system: str = ""                                # static system blocks
    task: str = ""                                  # per-turn task message
    messages: list = field(default_factory=list)    # full request messages
    final: Any = None                               # provider response obj
    raw: str = ""                                   # raw model text
    tool_delta: Any = None                          # sheet tool blocks
    usage: dict | None = None                       # token usage (merged)
    error_result: Any = None                        # TurnResult on call error

    # -- produced by the gate/repair family (batch 3, E3) -------------------
    gate_ctx: Any = None                            # output_gate.GateContext
    gate_result: Any = None                         # OutputGateResult | None
    need_recast: bool = False

    # -- produced by settlement (§1.1b, 2026-07-29) --------------------------
    render_drops: list = field(default_factory=list)  # (kind, concept, reason)

    # -- produced by the recorder family (batch 4) --------------------------
    result: Any = None                              # TurnResult (stage_finish)
    phase_label: str = ""                           # open_phase(...) or "ai"
    phase_note_key: str = ""                        # pedagogy tail note key
    soft_plan: dict | None = None                   # focus/debug plan snapshot


# ---------------------------------------------------------------------------
# The pre-model head stages (extracted verbatim from _execute_ai_tutor)
# ---------------------------------------------------------------------------


def stage_classify_signals(session, ctx: TurnContext) -> None:
    """LLM intent classifier (regex retirement, phase E). BLOCKING mode
    classifies before routing (+~2-3s/turn); default SHADOW mode runs
    parallel to the tutor call via _spawn_signal_shadow in the realize
    region (zero latency, audits disagreements, fixes stale holds for
    next turn)."""
    from . import config

    if not ctx.is_open and ctx.learner and getattr(
        config, "SIGNAL_CLASSIFIER_BLOCKING", False
    ):
        from .signal_classifier import (
            OBSERVATIONAL_SIGNALS,
            classify_signals,
        )

        clf = classify_signals(ctx.learner)
        if clf is not None:
            llm_signals, clf_meta = clf
            # §2.1a: content_offer / self_flagged_form are shadow-only
            # observations — they must not reach select_mode routing.
            ctx.llm_signals = set(llm_signals) - OBSERVATIONAL_SIGNALS
            u = clf_meta.get("usage") or {}
            if u.get("input_tokens") or u.get("output_tokens"):
                session.costs.add_llm(
                    "classifier",
                    str(clf_meta.get("model") or ""),
                    input_tokens=u.get("input_tokens", 0),
                    output_tokens=u.get("output_tokens", 0),
                )


def stage_memory_intake(session, ctx: TurnContext) -> None:
    """note_learner intake + eager comprehension-hold clears (Grok round-1
    C): own Spanish, a topic request, or a help request all mean "not
    stuck on our last try" — grammar questions with own content must NOT
    keep the hold."""
    if not ctx.is_open and ctx.learner:
        sig_pre = session.pedagogy_memory.note_learner(
            ctx.learner, extra_signals=ctx.llm_signals
        )
        if sig_pre & {"spanish_ok", "topic_request", "help_request"}:
            session.pedagogy_memory.clear_comprehension_hold()
    else:
        sig_pre = set()
    ctx.sig_pre = sig_pre


def stage_observe(session, ctx: TurnContext) -> None:
    """mode_state tick + observations + error-hit recency recording, plus
    the blank/sigs derivations the rest of the turn reads."""
    from .observe import build_observations
    from .pedagogy_contract import is_blank_learner

    session.mode_state.tick()
    obs = build_observations(
        session.sheet, learner=ctx.learner, is_open=ctx.is_open,
        extra_signals=ctx.llm_signals,
    )
    # Recency memory for streak hard breaks (this turn's hits at this index)
    session.mode_state.note_error_hits(obs.get("error_hit_ids"))
    ctx.obs = obs
    ctx.blank = bool(obs.get("blank_sheet") or is_blank_learner(session.sheet))
    ctx.sigs = set(obs.get("signals") or [])


def stage_english_streak(session, ctx: TurnContext) -> None:
    """english_only streak update — the streak's SINGLE owner
    (CHAR-BUG-002 RESOLVED, Phase 4 batch 3): this stage counts the
    CURRENT turn before select_mode runs; modes guard 4 reads the state
    only.  The association hard break therefore requires a GENUINE >=2
    streak (second consecutive English-only turn) or no_entiendo."""
    if "english_only" in ctx.sigs:
        session.mode_state.english_only_streak += 1
    elif ctx.learner and not ctx.is_open:
        session.mode_state.english_only_streak = 0


def stage_due_outcomes(session, ctx: TurnContext) -> None:
    """Retrieval scheduler (Phase 1): record retrieval outcomes on clear
    evidence BEFORE building the turn, so ladders/next_due advance and a
    just-used item is not re-offered this turn.  The typed DUE_OUTCOME_*
    events land in the log; result.notes is the chronological event
    projection (Phase 3 batch 2 — CHAR-BUG-003 resolved)."""
    if ctx.learner and not ctx.is_open:
        session._record_due_outcomes(ctx.learner, ctx.sigs)


def stage_open_scenes(session, ctx: TurnContext) -> None:
    """Open-scene assembly + the mode_state open_scene_ids binding."""
    from .scenes import open_scenes_for_sheet

    ctx.open_scenes = open_scenes_for_sheet(session.sheet, session.pack_dir)
    session.mode_state.open_scene_ids = [
        s.get("id") for s in ctx.open_scenes if s.get("id")
    ]


def stage_bind_activity(session, ctx: TurnContext) -> None:
    """Session phase layer (Phase 2): code decides the activity class for
    this turn.  Resolve empty retrieval BEFORE flavoring the turn (Grok
    AMEND 2b, 2026-07-28): a turn must never be flavored for a retrieval
    phase with nothing due."""
    if session.phase_state.current_activity() == "retrieval":
        from .retrieval_scheduler import due_items as _due_now

        if not _due_now(session.sheet):
            session.phase_state.force_advance()

    ctx.activity = session.phase_state.current_activity()


def stage_select_mode(session, ctx: TurnContext) -> None:
    """select_mode call — the guard chain keeps absolute priority; only the
    default/known-open path is flavored by the activity hint.  Emits the
    MODE/MODE_REASON typed events at stage "select" (since the CHAR-BUG-003
    fix result.notes renders in seq order, so mode=/mode_reason= appear at
    their true chronological position)."""
    from .corpus import pack_topic_titles
    from .modes import select_mode
    from .turn_events import TurnEventKind as EV

    decision = select_mode(
        session.sheet,
        observations=ctx.obs,
        is_open=ctx.is_open,
        learner=ctx.learner if not ctx.is_open else "",
        mode_state=session.mode_state,
        open_scenes=ctx.open_scenes,
        # covered_concepts rides with images_shown: a guard-6 concept is
        # covered for the session even when no image/lexicon write landed
        # (2026-07-28 repetition forensics — the conf<0.25 escape hatch).
        images_shown=(
            session.pedagogy_memory.images_shown
            | session.pedagogy_memory.covered_concepts
        ),
        session_memory=session.pedagogy_memory.snapshot(),
        pack_topics=pack_topic_titles(session.pack_dir),
        activity_hint=ctx.activity,
    )
    ctx.decision = decision
    ctx.ev.emit(EV.MODE, key=decision.mode.value, stage="select")
    ctx.ev.emit(EV.MODE_REASON, key=decision.reason, stage="select")


def stage_guard6_covered(session, ctx: TurnContext) -> None:
    """Guard 6 fired: record the concept as covered THIS session so the
    same concept cannot re-fire even if no image/lexicon write happens.
    Reads the typed MODE_REASON payload — the "new_noun:" prefix parse
    lives ONCE at the event boundary (Phase 3 batch 1)."""
    from .turn_events import TurnEventKind as EV

    _g6 = ctx.ev.latest(EV.MODE_REASON).payload.get("guard6_concept")
    if _g6 is not None:
        session.pedagogy_memory.note_concept_covered(_g6)


# The documented head sequence — the executor calls these in order.
PRE_MODEL_STAGES: tuple = (
    stage_classify_signals,
    stage_memory_intake,
    stage_observe,
    stage_english_streak,
    stage_due_outcomes,
    stage_open_scenes,
    stage_bind_activity,
    stage_select_mode,
    stage_guard6_covered,
)


# ---------------------------------------------------------------------------
# CONTRIBUTORS family (Phase 4 batch 2) — runs between the head and the
# phase tick, at the exact historical inline order.
# ---------------------------------------------------------------------------


def flavorable(
    ctx: TurnContext,
    *,
    modes: frozenset | set,
    exclude_reasons: frozenset | set = frozenset(),
    include_reasons: frozenset | set | None = None,
    activities: frozenset | set | None = None,
    exclude_activities: frozenset | set = frozenset(),
) -> bool:
    """THE shared eligibility predicate over (mode, reason, activity).

    Replaces the map's three inline spellings.  Characterization (Phase 4
    batch 2 — the spellings genuinely differ, so the differences are
    EXPLICIT parameters, never silent unification):

    Spelling A — due_elicit_block's internal gate:
        mode in DUE_ELICIT_MODES ({conversation, transfer}) AND
        reason NOT in DUE_GUARD_REASONS AND activity != new_input
        (sole-orchestrator: introduce owns new_input — Grok AMEND 4a)
        → modes=DUE_ELICIT_MODES, exclude_reasons=DUE_GUARD_REASONS,
          exclude_activities={"new_input"}
    Spelling B — self_flag_uptake_block's internal gate:
        mode in SELF_FLAG_MODES ({conversation, transfer, cf_recast}) AND
        reason NOT in DUE_GUARD_REASONS; NO activity term (uptake may fire
        in any phase, including new_input)
        → modes=SELF_FLAG_MODES, exclude_reasons=DUE_GUARD_REASONS
    Spelling C — the "flavorable turn" predicate, spelled THREE times
        (introduce_block internal / task inline / close inline) and
        IDENTICAL on (mode, reason) in all three:
        mode == "conversation" AND reason in INTRODUCE_FLAVORABLE_REASONS;
        only the activity term differs per contributor (new_input / task /
        close — the introduce/close activity gate rides eligibility; the
        task activity gate selects the whole contributor, see _task_*)
        → modes={"conversation"}, include_reasons=INTRODUCE_FLAVORABLE_
          REASONS, activities={...}

    A and B are reason-EXCLUDING (broad conversation flavors minus guard
    turns); C is reason-INCLUDING (only the known-open/default fallthrough
    reasons).  Guard/repair/recast turns keep their single focus under
    every spelling.
    """
    mode = ctx.decision.mode.value
    reason = ctx.decision.reason
    if mode not in modes:
        return False
    if reason in exclude_reasons:
        return False
    if include_reasons is not None and reason not in include_reasons:
        return False
    if activities is not None and ctx.activity not in activities:
        return False
    if ctx.activity in exclude_activities:
        return False
    return True


def append_instruction(decision, text: str | None) -> None:
    """THE instruction-mutation site (replaces the 5 idiom copies).

    Historical idiom, byte-identical in effect::

        decision.instructions = (
            (decision.instructions or "").rstrip() + "\\n\\n" + text
        ).strip()

    Empty/None text is a no-op.  (The zero-register overlay in
    modes.select_mode joins with a single "\\n" — a different idiom at a
    different stage; deliberately NOT unified here.)
    """
    if not text:
        return
    decision.instructions = (
        (decision.instructions or "").rstrip() + "\n\n" + text
    ).strip()


@dataclass(frozen=True)
class InstructionContributor:
    """One soft instruction contributor: ``eligible`` gates on the
    (mode, reason, activity) working set via ``flavorable``; ``build``
    wraps the module-level builder (side effects included: budget writes,
    typed events, ctx products) and returns the instruction text to append
    (or None)."""

    name: str
    eligible: Callable[[TurnContext], bool]
    build: Callable[[Any, TurnContext], str | None]


# -- due_elicit (spelling A) -------------------------------------------------


def _due_elicit_eligible(ctx: TurnContext) -> bool:
    from .conv_session import DUE_ELICIT_MODES, DUE_GUARD_REASONS

    return flavorable(
        ctx,
        modes=DUE_ELICIT_MODES,
        exclude_reasons=DUE_GUARD_REASONS,
        exclude_activities=frozenset({"new_input"}),
    )


def _due_elicit_build(session, ctx: TurnContext) -> str | None:
    """Due re-encounters ride as a SOFT instruction addition on
    conversation-flavored turns only (no new hard mode; repair and guard
    turns keep their single focus)."""
    from .conv_session import due_elicit_block
    from .turn_events import TurnEventKind as EV

    due_block, due = due_elicit_block(
        session.sheet,
        mode=ctx.decision.mode.value,
        reason=ctx.decision.reason,
        activity_hint=ctx.activity,
    )
    if not due_block:
        return None
    ctx.ev.emit(
        EV.DUE_ELICIT_OFFERED,
        payload={"keys": [d.key for d in due], "kinds": [d.kind for d in due]},
        stage="instruct",
    )
    return due_block


# -- self_flag_uptake (spelling B) -------------------------------------------


def _self_flag_uptake_eligible(ctx: TurnContext) -> bool:
    from .conv_session import DUE_GUARD_REASONS, SELF_FLAG_MODES

    return (
        bool(ctx.learner)
        and not ctx.is_open
        and flavorable(
            ctx, modes=SELF_FLAG_MODES, exclude_reasons=DUE_GUARD_REASONS
        )
    )


def _self_flag_uptake_build(session, ctx: TurnContext) -> str | None:
    """§2.1a self-flag uptake (instruction path — regex-visible cheap case
    only; shadow classifier owns meaning-level detection).  Budget lives in
    ModeSessionState; the note feeds the uptake_flag_honored eval
    (measurement first, per the closed content-uptake review)."""
    from .conv_session import self_flag_uptake_block
    from .turn_events import TurnEventKind as EV

    uptake_txt, uptake_token = self_flag_uptake_block(
        ctx.learner,
        mode=ctx.decision.mode.value,
        reason=ctx.decision.reason,
        mode_state=session.mode_state,
    )
    if not uptake_txt:
        return None
    # Typed natively (Phase 3 batch 2 push-down; was absorb).
    ctx.ev.emit(EV.UPTAKE_FLAGGED, key=uptake_token, stage="instruct")
    return uptake_txt


# -- introduce (spelling C, activity=new_input; DEFERRED render) -------------


def _introduce_eligible(ctx: TurnContext) -> bool:
    # No reason term here: the INTRODUCE_TABLE_MISSING telemetry emit has
    # no reason test in the historical code (new_input conversation turns
    # with a missing table always note it); introduce_block applies the
    # spelling-C reason gate internally for the plan path.
    return flavorable(
        ctx,
        modes=frozenset({"conversation"}),
        activities=frozenset({"new_input"}),
    )


def _introduce_build(session, ctx: TurnContext) -> None:
    """INTRODUCE plan (Phase 3, r7 S2): new_input phase + flavorable turn
    only.  Code picks the item + scaffold; the model realizes it; the
    ledger write happens POST-turn only if the reply shows the key.
    R-B honesty (Grok AMEND 4b, 2026-07-28): returns None ALWAYS — the
    INTRODUCE block is rendered in the realize region AFTER image
    resolution, so an image plan can never claim an attachment that the
    cache/cap denied.  The plan parks on ``ctx.intro_plan``."""
    from .conv_session import introduce_block
    from .turn_events import TurnEventKind as EV

    if session.association_table is None:
        ctx.ev.emit(EV.INTRODUCE_TABLE_MISSING, stage="instruct")
        return None
    _intro_txt, intro_plan = introduce_block(
        session.sheet,
        session.association_table,
        session.pedagogy_memory.snapshot(),
        mode=ctx.decision.mode.value,
        reason=ctx.decision.reason,
        activity_hint=ctx.activity,
    )
    if intro_plan is None:
        return None
    if (
        intro_plan.scaffold_type == "image"
        and ctx.decision.image_concept is None
    ):
        # Existing image pipeline (ensure_asset, cap-gated) shows it
        ctx.decision.image_concept = intro_plan.key
    ctx.ev.emit(
        EV.INTRODUCE_PLANNED,
        key=intro_plan.key,
        payload={"rule_id": intro_plan.rule_id,
                 "scaffold_type": intro_plan.scaffold_type},
        stage="instruct",
    )
    ctx.intro_plan = intro_plan
    return None


# -- task (activity gate selects the contributor; spelling C gates the text) -


def _task_eligible(ctx: TurnContext) -> bool:
    # The whole contributor (scene bind + slot eval + completion) runs on
    # EVERY task-phase turn — repair/guard turns included, exactly as the
    # historical inline block did; only the instruction TEXT is gated by
    # spelling C inside build.
    return ctx.activity == "task"


def _task_build(session, ctx: TurnContext) -> str | None:
    """ConvergentTaskRuntime wiring (Phase 5, r6 Rank-4): task-phase turns
    bind the FIRST task-capable open scene (session-scoped, persists until
    done).  Slot filling is evaluated on the learner's OWN text BEFORE the
    tutor call; the teacher-facing task block (goal, slots,
    tutor_private_info with the never-volunteer directive) rides flavorable
    turns — the exact INTRODUCE set, PLUS (PHASE HOST rule 7, Proposal A
    2026-07-29) conversation turns whose reason is a topic-matched
    ``scene_goal:*`` — the task phase hosts scene pursuit, so a scene pick
    during task activity must not withhold the task block (the seam Grok's
    countersign caught).  Guards and repairs keep their single focus.
    Close/introduce gating stays exact-set only.  After done, task turns
    fall back to normal flavor (the completing turn still carries the
    celebrate line)."""
    from .conv_session import INTRODUCE_FLAVORABLE_REASONS
    from .task_runtime import (
        evaluate_turn as _task_eval,
        task_from_scene,
        task_instructions,
    )
    from .turn_events import TurnEventKind as EV

    task_scene = None
    if session.task_state is not None:
        task_scene = next(
            (
                s for s in ctx.open_scenes
                if s.get("id") == session.task_state.scene_id
            ),
            None,
        )
    if session.task_state is None:
        for sc in ctx.open_scenes:
            st = task_from_scene(sc)
            if st is not None:
                session.task_state = st
                task_scene = sc
                break
    just_done = False
    if session.task_state is None or task_scene is None:
        return None
    if (
        ctx.learner and not ctx.is_open
        and session.task_state.status == "open"
    ):
        before_slots = set(session.task_state.slots_filled)
        session.task_state = _task_eval(
            session.task_state, ctx.learner, task_scene
        )
        for sid in session.task_state.slots_filled:
            if sid not in before_slots:
                ctx.ev.emit(EV.TASK_SLOT_FILLED, key=sid, stage="instruct")
        if session.task_state.status == "done":
            just_done = True
            ctx.ev.emit(
                EV.TASK_COMPLETE,
                key=session.task_state.scene_id,
                stage="instruct",
            )
            _desc = str(((task_scene or {}).get("primary_exit") or {}).get("description") or "")
            session._progress_note(
                "task_complete", session.task_state.scene_id,
                item_kind="task", detail_ctx={"desc": _desc},
            )
    if (
        (
            flavorable(
                ctx,
                modes=frozenset({"conversation"}),
                include_reasons=INTRODUCE_FLAVORABLE_REASONS,
            )
            # PHASE HOST rule 7 (Proposal A, 2026-07-29): scene_goal:* is
            # task-block flavorable under task activity only.  ctx.activity
            # == "task" is structurally true here (_task_eligible), asserted
            # explicitly to match the binding text.
            or (
                ctx.activity == "task"
                and ctx.decision.mode.value == "conversation"
                and ctx.decision.reason.startswith("scene_goal:")
            )
        )
        and (session.task_state.status == "open" or just_done)
    ):
        ctx.ev.emit(
            EV.TASK_GOAL_OFFERED,
            key=session.task_state.scene_id,
            stage="instruct",
        )
        return task_instructions(session.task_state, task_scene)
    return None


# -- close_summary (spelling C, activity=close) ------------------------------


def _close_summary_eligible(ctx: TurnContext) -> bool:
    from .conv_session import INTRODUCE_FLAVORABLE_REASONS

    return flavorable(
        ctx,
        modes=frozenset({"conversation"}),
        include_reasons=INTRODUCE_FLAVORABLE_REASONS,
        activities=frozenset({"close"}),
    )


def _close_summary_build(session, ctx: TurnContext) -> str:
    """CLOSE phase (PEDAGOGY §1.2, USER-ratified 2026-07-28): flavorable
    close turns carry the compact session summary the one-line English
    close must be built from.  Same condition set as INTRODUCE — guard and
    repair turns keep their single focus."""
    from .conv_session import close_summary_block
    from .turn_events import TurnEventKind as EV

    ctx.ev.emit(EV.CLOSE_PHASE_OFFERED, stage="instruct")
    return close_summary_block(
        session.pedagogy_memory.snapshot(),
        resolved_forms=session.mode_state.resolved_this_session,
        task_state=session.task_state,
    )


# The contributor census, at the EXACT historical inline call order.
CONTRIBUTORS: tuple[InstructionContributor, ...] = (
    InstructionContributor(
        "due_elicit", _due_elicit_eligible, _due_elicit_build
    ),
    InstructionContributor(
        "self_flag_uptake",
        _self_flag_uptake_eligible,
        _self_flag_uptake_build,
    ),
    InstructionContributor(
        "introduce", _introduce_eligible, _introduce_build
    ),
    InstructionContributor("task", _task_eligible, _task_build),
    InstructionContributor(
        "close_summary", _close_summary_eligible, _close_summary_build
    ),
)


def stage_contributors(session, ctx: TurnContext) -> None:
    """Run the contributor family in order (the single mutation site)."""
    for contributor in CONTRIBUTORS:
        if not contributor.eligible(ctx):
            continue
        append_instruction(ctx.decision, contributor.build(session, ctx))


# ---------------------------------------------------------------------------
# Phase family (called at its REAL site — after the contributor region)
# ---------------------------------------------------------------------------


def stage_phase_tick(session, ctx: TurnContext) -> None:
    """Advance/freeze the phase clock: repair + guard turns freeze;
    interventions (cf_recast/form_focus/association/transfer) consume.

    NOT part of ``PRE_MODEL_STAGES``: the tick sits AFTER the contributor
    region in the real code (verified 2026-07-28, Phase 4 batch 1) — the
    goldens pin that ordering, so the executor calls this at the true
    mid-method site."""
    from .conv_session import phase_turn_consumed

    ctx.phase_consumed = phase_turn_consumed(
        ctx.decision.mode.value, ctx.decision.reason
    )
    session.phase_state.tick(ctx.phase_consumed)


# ---------------------------------------------------------------------------
# REALIZE family (Phase 4 batch 3) — runs after the phase tick, at the exact
# historical inline order.  last_mode_decision (focus rail) is snapshotted
# AFTER the INTRODUCE render so its instructions stay faithful to what the
# model actually receives.
# ---------------------------------------------------------------------------


def stage_signal_shadow(session, ctx: TurnContext) -> None:
    """Default SHADOW classifier: runs parallel to the tutor call (zero
    latency, audits disagreements, fixes stale holds for next turn)."""
    if not ctx.is_open and ctx.learner:
        session._spawn_signal_shadow(
            ctx.learner, ctx.decision.mode.value, ctx.decision.reason
        )


def stage_mode_image(session, ctx: TurnContext) -> None:
    """Mode-decision image attach (cache-only on the reply path)."""
    ctx.image_decision = None
    ctx.teach_images = session._attach_mode_image(ctx.decision)


def stage_fallback_image(session, ctx: TurnContext) -> None:
    """Any mode may request an association image; placement always tries
    open assets.  Incident 2026-07-28: on comprehension_repair (incl.
    meta/grammar questions) the fallback may only serve a concept that is
    surface-present in the CURRENT exchange (the learner's words + the
    tutor's ACTUAL prior Spanish remembered in the repair targets'
    last_model / last_try).  No relevant concept → NO image.

    CHAR-BUG-006 RESOLVED (Proposal B pin-first batch, 2026-07-29):
    authored scene scripts are BANNED from the image path.  The scene's
    suggested lines (decision targets, copied from scene input) are
    direction for the model, not evidence of this turn's content — they
    are never passed as tutor_models or relevance text.  Image relevance
    base: the code-owned ``decision.image_concept`` (primary — mode attach
    owns its cache hit/miss + single miss note) and the learner's own
    words (secondary).  A scene image the learner has not typed arrives
    only via ``image_concept`` (accepted narrowing, adjudicated)."""
    from .modes import Mode
    from .teach_assets import assets_for_ai_turn

    if ctx.teach_images or not (
        ctx.decision.mode in (
            Mode.PLACEMENT,
            Mode.ASSOCIATION,
            Mode.COMPREHENSION_REPAIR,
        )
        or ctx.decision.image_concept
    ):
        return
    relevant_to = None
    if ctx.decision.mode == Mode.COMPREHENSION_REPAIR:
        # Repair exception (Proposal B item 4): actual prior performance
        # only — never authored scripts.
        targets = ctx.decision.targets or {}
        relevant_to = " ".join(
            [ctx.learner if not ctx.is_open else ""]
            + [str(targets.get(k) or "") for k in ("last_model", "last_try")]
        )
    ctx.teach_images, ctx.image_decision = assets_for_ai_turn(
        is_open=ctx.is_open or ctx.decision.mode == Mode.PLACEMENT,
        blank_sheet=ctx.blank,
        learner=ctx.learner if not ctx.is_open else "",
        signals=list(ctx.sigs),
        images_shown=session.pedagogy_memory.images_shown,
        turns_since_image=session.pedagogy_memory.turns_since_image,
        session_turns=session.pedagogy_memory.turns,
        require_relevant_to=relevant_to,
        # Audit (e) 2026-07-28: cache-only on the reply path; a wanted
        # miss warms async below.
        generate=False,
    )
    # §1.1b: attach produces a CANDIDATE — note_image moved to
    # settle_chrome (confirmed display only). Miss notes stay here (a
    # miss is a generation-warming fact, not a display fact).
    if not ctx.teach_images and (
        ctx.image_decision is not None
        and getattr(ctx.image_decision, "want", False)
        and ctx.image_decision.concept
    ):
        session._note_image_miss(
            ctx.image_decision.concept,
            source="mode",
            decision_reason=f"warm:{ctx.image_decision.reason}",
        )


def stage_introduce_render(session, ctx: TurnContext) -> None:
    """Render the INTRODUCE block now that image resolution is known
    (Grok AMEND 4b, 2026-07-28): an R-B plan whose image did NOT actually
    attach (cache miss + generation cap/denied) downgrades to the R-D
    single ≤6-word micro-gloss — instructions must never claim a
    dual-code image that is not there.  Rebinds ``ctx.intro_plan`` on
    downgrade: the post-turn introduce ledger must see the plan that was
    actually rendered."""
    from .turn_events import TurnEventKind as EV

    if ctx.intro_plan is None:
        return
    from .introduce_router import IntroducePlan, plan_instructions

    intro_plan = ctx.intro_plan
    if intro_plan.scaffold_type == "image":
        has_img = any(
            (t.get("concept") or "") == intro_plan.key
            for t in (ctx.teach_images or [])
        )
        if not has_img:
            entry = (
                (session.association_table or {}).get(intro_plan.key)
                or {}
            )
            gloss = str(entry.get("gloss_en") or intro_plan.key)
            intro_plan = IntroducePlan(
                key=intro_plan.key,
                rule_id="R-D",
                scaffold_type="gloss",
                scaffold_payload={
                    "gloss": gloss,
                    "format": f"**{intro_plan.key}** ({gloss})",
                },
                forbid_cluster_with=list(
                    intro_plan.forbid_cluster_with
                ),
            )
            ctx.intro_plan = intro_plan
            ctx.ev.emit(
                EV.INTRODUCE_DOWNGRADED,
                key=intro_plan.key,
                payload={"path": "R-B_to_R-D"},
                stage="image",
            )
    append_instruction(ctx.decision, plan_instructions(intro_plan))


def stage_mode_snapshot(session, ctx: TurnContext) -> None:
    """last_mode_decision (focus rail) snapshot — after the render."""
    session.last_mode_decision = {
        **ctx.decision.as_dict(),
        "phase": {
            "activity": ctx.activity,
            "consumed": ctx.phase_consumed,
            "index": session.phase_state.index,
            "turns_in_phase": session.phase_state.turns_in_phase,
            "frozen_turns": session.phase_state.frozen_turns,
        },
    }


def stage_prompt_build(session, ctx: TurnContext) -> None:
    """System = STATIC blocks only (stance/persona/pack) so the provider
    prefix-cache covers system + chat history.  The per-turn sheet rides
    in the task message at the request tail.  No personal context —
    personal-data capture is disabled.  Full history in testing
    (HISTORY_TURNS=0); never mutates session.history."""
    from . import config
    from .character_sheet import format_sheet_for_prompt
    from .corpus import load_pack
    from .executor import build_ai_tutor_system, build_ai_tutor_user_message
    from .scenes import scene_hints_for_prompt

    ctx.system = build_ai_tutor_system(
        pack_palette=load_pack(session.pack_dir),
    )
    ctx.task = build_ai_tutor_user_message(
        learner=ctx.learner,
        is_open=ctx.is_open,
        session_memory=session.pedagogy_memory.snapshot(),
        observations=ctx.obs,
        teach_images=ctx.teach_images,
        blank_sheet=ctx.blank,
        mode_decision=ctx.decision.as_dict(),
        open_scene_hints=scene_hints_for_prompt(ctx.open_scenes),
        sheet_summary=format_sheet_for_prompt(session.sheet),
    )
    if ctx.is_open:
        ctx.messages = [{"role": "user", "content": ctx.task}]
    else:
        ctx.messages = config.history_for_model(session.history) + [
            {"role": "user", "content": ctx.task}
        ]


def stage_model_call(session, ctx: TurnContext) -> None:
    """The tutor model call.  A provider exception becomes
    ``ctx.error_result`` (the executor returns it immediately) — the
    historical early-return semantics."""
    from . import config
    from .conv_session import TurnResult, tutor_turn

    try:
        # No tool round-trips by default (SHEET_TOOLS=0); hard_observer
        # updates the sheet.
        tools = (
            session.tools if getattr(config, "SHEET_TOOLS", False) else None
        )
        final, raw, tool_delta, usage, _ = tutor_turn(
            session.client,
            session.caps,
            ctx.system,
            ctx.messages,
            tools=tools,
            max_tool_rounds=1 if tools else 0,
        )
    except Exception as e:
        ctx.error_result = TurnResult(
            reply="",
            error=f"{type(e).__name__}: {e}",
            input_mode=ctx.input_mode,
        )
        return
    ctx.final = final
    ctx.raw = raw
    ctx.tool_delta = tool_delta
    ctx.usage = usage


# The realize census, at the EXACT historical inline order.
# stage_image_costs DELETED (§1.1b P-3, 2026-07-29): display bookkeeping
# (note_image, image costs) fires at settle_chrome for CONFIRMED images
# only — an image the learner never saw must not be billed or counted
# as shown.
REALIZE_STAGES: tuple = (
    stage_signal_shadow,
    stage_mode_image,
    stage_fallback_image,
    stage_introduce_render,
    stage_mode_snapshot,
    stage_prompt_build,
    stage_model_call,
)


# ---------------------------------------------------------------------------
# GATE/REPAIR family (Phase 4 batch 3, E3) — context build outside the
# executor's try/except; check + repair inside it (any exception →
# OUTPUT_GATE_ERROR, the turn proceeds ungated — historical semantics).
# ---------------------------------------------------------------------------

# Faults that force the single bounded repair round (everything else is a
# SOFT fail: noted, never re-asked).
GATE_CRITICAL_FAULTS = frozenset({
    "pedagogy:no_teach_move",
    "pedagogy:open_needs_model_try",
    "gate:english_wall",
    "gate:form_focus_needs_model",
    "gate:missing_recast",  # form error must surface a short correction
    "gate:sheet_leak",  # model dumped sheet/tool JSON into chat
    "gate:truncated",  # reply hit max_tokens mid-sentence
    # r7 S3: naked first exposure / cluster dump (gate:regloss stays SOFT
    # by omission)
    "gate:unscaffolded_new_item",
})


def stage_gate_context(session, ctx: TurnContext) -> None:
    """Build the turn-constant GateContext from the TurnContext — the
    historical 18-argument call-site seam dies here (E3).  Phase 4 gate
    context (r7 S3): the table + live sheet + this turn's IntroducePlan
    key + retrieval failures this turn (a failed re-encounter legalizes a
    re-gloss).  Phase 3 batch 1: reads the typed DUE_OUTCOME_FAIL events —
    no note-string re-parsing.  parts/visible/raw ride per attempt via
    ``dataclasses.replace`` in check/repair."""
    from .output_gate import GateContext
    from .turn_events import TurnEventKind as EV

    ctx.gate_ctx = GateContext(
        raw=ctx.raw or "",
        truncated=(
            (getattr(ctx.final, "stop_reason", "") or "") == "max_tokens"
        ),
        is_open=ctx.is_open,
        already_asked=session.pedagogy_memory.asked,
        already_shown=session.pedagogy_memory.shown,
        mode=ctx.decision.mode.value,
        image_present=bool(ctx.teach_images),
        association_table=session.association_table,
        sheet=session.sheet,
        introduce_key=(
            ctx.intro_plan.key if ctx.intro_plan is not None else None
        ),
        retrieval_failed_keys={
            e.key for e in ctx.ev.find(EV.DUE_OUTCOME_FAIL)
        },
        learner_text=ctx.learner if not ctx.is_open else "",
        # True-zero register (2026-07-28 zero-English incident): the
        # overlay turns run as conversation/repair modes where the
        # placement english_wall exemption cannot reach — thread the same
        # condition the ZERO_REGISTER_NOTE overlay uses.
        blank_zero=bool(ctx.blank and "spanish_ok" not in ctx.sigs),
        # Asked-topic registry (repetition forensics): keys from PRIOR
        # turns — this turn's try is noted post-gate.
        asked_topics=set(session.pedagogy_memory.asked_topics),
        topic_nouns=session._topic_nouns(),
    )


def _settle_pixels(session, ctx: TurnContext) -> None:
    """Shared pixel-settlement pass (§1.1b; run ≤2× per turn — post-
    generation and again after a gate-repair rewrite). Confirms image
    candidates against the REALIZED exchange and shrinks ctx.teach_images
    to the confirmed set, so GateContext.image_present, introduce
    scaffold evidence, memory notes, parts and costs all see truth. Every
    drop emits a typed event — never a silent kill."""
    from .exchange_render import exchange_surface, settle_images
    from .turn_events import TurnEventKind as EV
    from .tutor_response import process_tutor_raw as _ptr

    if not ctx.teach_images:
        return
    visible, _parts = _ptr(ctx.raw or "")
    surface = exchange_surface(
        ctx.learner if not ctx.is_open else "", visible
    )
    confirmed, drops = settle_images(ctx.teach_images, surface)
    ctx.teach_images = confirmed
    for concept, reason in drops:
        ctx.render_drops.append(("image", concept, reason))
        ctx.ev.emit(
            EV.RENDER_DROPPED, key=f"image:{concept}",
            payload={"reason": reason}, stage="settle",
        )


def stage_settle_pixels(session, ctx: TurnContext) -> None:
    """settle_pixels₀ — the commit phase for pre-call image candidates
    (mode/scene attach, fallback, R-B introduce). Runs BEFORE the gate
    context is built (design-exchange-settlement.md, Grok OQ3: a doomed
    image must not license a scaffold or exempt a probe)."""
    _settle_pixels(session, ctx)


def stage_gate_check(session, ctx: TurnContext) -> None:
    """Parse the reply and run the gate; re-check with the recast
    requirement if the mode demands it."""
    from dataclasses import replace

    from .output_gate import check_output_gate
    from .tutor_response import process_tutor_raw as _ptr

    _vis0, _parts0 = _ptr(ctx.raw or "")
    ctx.gate_result = check_output_gate(
        replace(ctx.gate_ctx, parts=_parts0.as_dict(), visible=_vis0)
    )
    ctx.need_recast = bool(
        ctx.decision.mode.value in ("cf_recast", "form_focus")
        or (ctx.decision.targets or {}).get("require_recast_tag")
    )
    if ctx.need_recast:
        ctx.gate_result = check_output_gate(
            replace(
                ctx.gate_ctx,
                parts=_parts0.as_dict(),
                visible=_vis0,
                require_recast=True,
            )
        )


def stage_gate_repair(session, ctx: TurnContext) -> None:
    """Verdict events + the single bounded repair round.  A critical fault
    (GATE_CRITICAL_FAULTS) re-asks once with the specific fault; the
    rewrite is re-gated (require_recast sticky, truncation re-derived from
    the NEW response) and the verdict lands as a typed event."""
    from dataclasses import replace

    from . import config
    from .conv_session import tutor_turn
    from .output_gate import check_output_gate, repair_user_message
    from .tutor_response import process_tutor_raw as _ptr
    from .turn_events import TurnEventKind as EV

    gate_result = ctx.gate_result
    needs_repair = (
        getattr(config, "GATE_REPAIR", True)
        and not gate_result.ok
        and any(
            f in GATE_CRITICAL_FAULTS for f in (gate_result.faults or [])
        )
    )
    if not gate_result.ok and not needs_repair:
        ctx.ev.emit(
            EV.OUTPUT_GATE_SOFT_FAIL,
            payload={"faults": list(gate_result.faults)},
            stage="gate",
        )
    elif needs_repair:
        ctx.ev.emit(
            EV.OUTPUT_GATE_FAIL,
            payload={"faults": list(gate_result.faults)},
            stage="gate",
        )
        repair_msg = {
            "role": "user",
            "content": repair_user_message(gate_result, ctx.raw or ""),
        }
        final2, raw2, _td2, usage2, _ = tutor_turn(
            session.client,
            session.caps,
            ctx.system,
            ctx.messages
            + [{"role": "assistant", "content": ctx.raw or ""}]
            + [repair_msg],
            tools=None,
        )
        if usage2:
            ctx.usage = {
                k: (ctx.usage or {}).get(k, 0) + (usage2 or {}).get(k, 0)
                for k in (
                    "input_tokens", "output_tokens",
                    "thinking_tokens", "cached_input_tokens",
                )
            }
        if raw2 and raw2.strip():
            ctx.raw = raw2
            ctx.final = final2
            # settle_pixels₁ (§1.1b, Grok OQ3): the rewrite may have
            # dropped the concept — re-settle BEFORE the re-gate so
            # image_present cannot license a scaffold the learner will
            # not see. Shrink-only; ≤2 settlements per turn, no loop.
            _settle_pixels(session, ctx)
            _vis1, _parts1 = _ptr(ctx.raw or "")
            gate2 = check_output_gate(
                replace(
                    ctx.gate_ctx,
                    parts=_parts1.as_dict(),
                    visible=_vis1,
                    raw=ctx.raw or "",
                    require_recast=ctx.need_recast,
                    image_present=bool(ctx.teach_images),
                    truncated=(
                        (getattr(final2, "stop_reason", "") or "")
                        == "max_tokens"
                    ),
                )
            )
            ctx.gate_result = gate2
            if gate2.ok:
                ctx.ev.emit(EV.OUTPUT_GATE_REPAIRED, stage="gate")
            else:
                ctx.ev.emit(
                    EV.OUTPUT_GATE_STILL_FAIL,
                    payload={"faults": list(gate2.faults)},
                    stage="gate",
                )
    else:
        ctx.ev.emit(EV.OUTPUT_GATE_OK, stage="gate")


# The gate/repair census — the executor calls settle_pixels then
# context-build first (both outside the historical try/except), then
# check + repair inside it. settle_pixels precedes context build so
# image_present is settled truth (§1.1b, 2026-07-29).
GATE_REPAIR_STAGES: tuple = (
    stage_settle_pixels,
    stage_gate_context,
    stage_gate_check,
    stage_gate_repair,
)


# ---------------------------------------------------------------------------
# RECORDERS family (Phase 4 batch 4) — post-gate turn recorders at the exact
# historical inline order, then the SINGLE atomic sheet commit (CHAR-BUG-001
# RESOLVED: the batch's declared behavior delta per Grok amendment (a)).
# The in-memory sheet mutates through the stages; disk persists once.
# ---------------------------------------------------------------------------


def stage_finish(session, ctx: TurnContext) -> None:
    """Sheet process_turn + TurnResult assembly (``session._finish``): parse
    the raw reply, bill usage, run the hard sheet observer, emit the typed
    sheet/contract events, build the TurnResult.  The historical save_sheet
    inside _finish is gone — persistence moved to stage_sheet_commit
    (CHAR-BUG-001 RESOLVED)."""
    ctx.result = session._finish(
        ctx.learner if not ctx.is_open else "",
        ctx.raw or "",
        ctx.tool_delta,
        ctx.final,
        ctx.usage,
        input_mode=ctx.input_mode,
        log_learner=ctx.log_learner if ctx.log_learner is not None else (
            "(session open)" if ctx.is_open else None
        ),
        is_open=ctx.is_open,
        skip_log=True,  # log after mode/plan/images attached
    )


def stage_introduce_ledger(session, ctx: TurnContext) -> None:
    """Introduce ledger (r7 S1 + R-H): mark ONLY if the visible reply
    presented the key WITH the plan's scaffold evidence (2026-07-28
    false-planted incident: key presence alone is natural use, not a
    teaching move — no ledger write, no milestone, budget unconsumed).
    R-I: an already-introduced table key appearing in the reply needs
    no action (no re-gloss machinery this ship — the gate owns regloss
    in Phase 4)."""
    from .conv_session import introduce_outcome
    from .turn_events import TurnEventKind as EV

    intro_plan = ctx.intro_plan
    if intro_plan is None:
        return
    # Phase 3 batch 1: the structured introduce_outcome status
    # replaces the startswith("introduced:") note re-parse.
    session.sheet, _intro_status, _intro_key = introduce_outcome(
        session.sheet, intro_plan, ctx.result.reply,
        teach_images=ctx.teach_images,
    )
    if _intro_status == "introduced":
        # CHAR-BUG-001 RESOLVED: the historical mid-turn save_sheet here is
        # gone — the write persists at stage_sheet_commit.
        session.pedagogy_memory.note_introduced(intro_plan.key)
        ctx.ev.emit(
            EV.INTRODUCED, key=_intro_key,
            payload={"scaffold_type": intro_plan.scaffold_type},
            stage="record",
        )
        session._progress_note(
            "planted", intro_plan.key, item_kind="lexicon",
            detail_ctx={"scaffold": intro_plan.scaffold_type},
        )
    elif _intro_status == "lapsed":
        # introduce_lapsed:<key>:no_scaffold — logged, nothing else.
        ctx.ev.emit(
            EV.INTRODUCE_LAPSED, key=_intro_key,
            payload={"reason": "no_scaffold"},
            stage="record",
        )


def stage_first_seen(session, ctx: TurnContext) -> None:
    """Round-2 AMEND 1c: keys the gate would have faulted but that were
    saved solely by an in-reply scaffold (gloss/anchor) get a durable
    first_seen bit so later bare reuse is a re-encounter, not a fresh
    CRITICAL fault (Grok's gloss-turn1 → bare-turn2 thrash proof).
    Deliberately NOT an introduction: no budget consumed, no retrieval
    enqueue (router-only), confidence/status untouched (honesty law)."""
    from .turn_events import TurnEventKind as EV

    gate_result = ctx.gate_result
    saved_map = dict(
        getattr(gate_result, "scaffold_saved", None) or {}
    ) if gate_result is not None else {}
    if not saved_map:
        return
    from .retrieval_scheduler import (
        has_first_seen,
        is_introduced,
        mark_first_seen,
    )

    for fs_key, fs_kind in saved_map.items():
        if is_introduced(session.sheet, fs_key, "lexicon"):
            continue
        if has_first_seen(session.sheet, fs_key, "lexicon"):
            continue
        # Do NOT skip intro_plan.key (audit (a4) 2026-07-28): if the
        # introduce lapsed (wrong scaffold type), first_seen must
        # still stick so the glossed exposure is not forgotten. A
        # successful introduce already hits is_introduced above.
        session.sheet = mark_first_seen(
            session.sheet, fs_key, "lexicon", fs_kind
        )
        ctx.ev.emit(
            EV.FIRST_SEEN, key=fs_key,
            payload={"scaffold_kind": fs_kind},
            stage="record",
        )
    # CHAR-BUG-001 RESOLVED: the historical wrote_first_seen → save_sheet
    # here is gone — the writes persist at stage_sheet_commit.


def stage_settle_chrome(session, ctx: TurnContext) -> None:
    """settle_chrome — the commit phase for non-pixel chrome (§1.1b,
    design-exchange-settlement.md; replaces the stage_intro_morph stash).
    Runs post-recorders because its projection legally consumes the
    INTRODUCED / FIRST_SEEN events those stages emit (the ordering
    contradiction Grok caught in the single-stage draft). Derives the
    card view (learner engagement beats introduction — one priority
    ladder in exchange_render.card_engagement), freezes the TurnRender
    (single-assignment; replaced whole next turn), and does the
    confirmed-display bookkeeping (P-3): note_image / image costs fire
    HERE, for what the learner actually sees — never at attach."""
    from .exchange_render import (
        PROJECTION_EVENT_ALLOWLIST,
        TurnRender,
        card_engagement,
    )
    from .turn_events import TurnEventKind as EV
    from .tutor_response import process_tutor_raw as _ptr

    visible, _parts = _ptr(ctx.raw or "")
    events = tuple(
        (e.kind.value, e.key)
        for e in ctx.ev.events
        if e.kind.value in PROJECTION_EVENT_ALLOWLIST
    )
    card = card_engagement(
        ctx.learner if not ctx.is_open else "", visible, events
    )
    if card:
        ctx.ev.emit(
            EV.MORPH_CARD, key=card.get("lemma") or card.get("form_id") or "",
            payload={"engaged_by": card.get("engaged_by") or ""},
            stage="settle",
        )
    for img in ctx.teach_images or []:
        concept = (img or {}).get("concept")
        if concept:
            session.pedagogy_memory.note_image(concept)
    session._note_image_costs(ctx.teach_images)
    session.last_turn_render = TurnRender(
        images=tuple(ctx.teach_images or []),
        card=card,
        drops=tuple(ctx.render_drops),
    )


def stage_memory_notes(session, ctx: TurnContext) -> None:
    """Session-memory recorders: plan-try memory, the asked-topic registry
    (2026-07-28 repetition forensics) and note_tutor_turn so meta "what
    does that mean?" can re-ask the SAME idea."""
    from .turn_events import TurnEventKind as EV

    result = ctx.result
    try_text = ""
    models: list[str] = []
    if result.parts:
        try_text = (result.parts.get("try") or result.parts.get("continue") or "")
        m = result.parts.get("model") or ""
        if m:
            models = [m]
        session.pedagogy_memory.note_plan_try(ctx.decision.mode.value, try_text)
        # Asked-topic registry (2026-07-28 repetition forensics): derive
        # the semantic key of THIS turn's composed try — next turn's gate
        # and the do_not_re_ask payload both read it.
        from .session_memory import topic_key_for_try

        _frame, _concept = topic_key_for_try(
            try_text, nouns=session._topic_nouns()
        )
        if _frame:
            _tkey = session.pedagogy_memory.note_asked_topic(_frame, _concept)
            if _tkey:
                ctx.ev.emit(EV.ASKED_TOPIC, key=_tkey, stage="record")
        # Remember tutor Spanish so meta "what does that mean?" can re-ask SAME idea
        img_concepts = [
            (t.get("concept") or "")
            for t in (ctx.teach_images or [])
            if t.get("concept")
        ]
        session.pedagogy_memory.note_tutor_turn(
            model=m,
            try_=try_text,
            acknowledge=result.parts.get("acknowledge") or "",
            concepts=img_concepts or None,
        )


def stage_frame_record(session, ctx: TurnContext) -> None:
    """frames_seen exposure recorder (docs/design-encounter-variety.md,
    Grok-countersigned 2026-07-29): when THIS turn's realized try/model
    actually exercised a due-offered key — verbatim or via a conjugated
    surface form («¿Cómo estás?» fires «estar», the Grok constraint) — or
    introduced a key, record the turn's topic frame on that sheet entry.
    Exposure history, never ability evidence (§3.2 untouched); no topic
    frame this turn records nothing; the FRAME_RECORDED event fires only
    on a genuine new write (it is the revisit-bound counter)."""
    from .turn_events import TurnEventKind as EV

    parts = ctx.result.parts or {}
    try_text = parts.get("try") or parts.get("continue") or ""
    model = parts.get("model") or ""
    text = f"{model} {try_text}".strip()
    if not text:
        return
    from .session_memory import compose_topic_key, topic_key_for_try

    frame, concept = topic_key_for_try(try_text, nouns=session._topic_nouns())
    if not frame:
        return
    fkey = compose_topic_key(frame, concept)
    from .retrieval_scheduler import frames_seen_of, record_frame
    from .turn_morph import lemma_engaged_by_text

    targets: list[tuple[str, str]] = []
    for e in ctx.ev.find(EV.DUE_ELICIT_OFFERED):
        keys = list((e.payload or {}).get("keys") or [])
        kinds = list((e.payload or {}).get("kinds") or [])
        for i, k in enumerate(keys):
            if lemma_engaged_by_text(text, k):
                targets.append((k, kinds[i] if i < len(kinds) else "lexicon"))
    for e in ctx.ev.find(EV.INTRODUCED):
        if e.key:
            targets.append((e.key, "lexicon"))
    for k, kind in targets:
        before = frames_seen_of(session.sheet, k, kind)
        session.sheet = record_frame(session.sheet, k, kind, fkey)
        if frames_seen_of(session.sheet, k, kind) != before:
            ctx.ev.emit(
                EV.FRAME_RECORDED, key=f"{k}:{fkey}", stage="record",
            )


def stage_declared_image(session, ctx: TurnContext) -> None:
    """Tutor-declared image (optional <image concept="…"/> in the reply —
    the model's pedagogical decision replaces regex noun-scanning)."""
    from .turn_events import TurnEventKind as EV

    declared = ((ctx.result.parts or {}).get("image_concept") or "").strip()
    if ctx.teach_images or not declared:
        return
    from .teach_assets import concept_in_text

    if not concept_in_text(declared, ctx.result.reply or ""):
        # Same relevance law as mode/fallback images (incident
        # 2026-07-28): a declared concept absent from the visible
        # reply is not this turn's teaching content — no image
        # beats a wrong one.
        ctx.ev.emit(EV.IMAGE_DECLARED_IRRELEVANT, key=declared,
                    stage="record")
    elif declared in session.pedagogy_memory.images_shown:
        ctx.ev.emit(EV.IMAGE_DECLARED_SKIP_REPEAT, key=declared,
                    stage="record")
    elif session.pedagogy_memory.declared_image_cooldown > 0:
        ctx.ev.emit(EV.IMAGE_DECLARED_COOLDOWN, key=declared,
                    stage="record")
    else:
        from .teach_assets import ensure_asset

        # Cache hits attach same-turn; a miss NEVER generates on the
        # reply path (audit (e) 2026-07-28) — it is noted visibly and
        # warmed async (the declared cooldown above already gated
        # this branch; the novel budget is checked in the miss note).
        hit = None
        try:
            hit = ensure_asset(declared, generate=False)
        except Exception:
            hit = None
        if hit:
            ctx.teach_images = [{
                **hit,
                "decision_reason": "tutor_declared",
                "visual_score": 1.0,
            }]
            # §1.1b: note_image + costs moved to settle_chrome (the
            # declared image is exchange-confirmed by construction —
            # concept_in_text gated this branch above). Cooldown stays:
            # pacing state, not display bookkeeping.
            session.pedagogy_memory.declared_image_cooldown = 3
        else:
            session._note_image_miss(
                declared,
                source="tutor_declared",
                decision_reason="tutor_declared",
            )


def stage_mode_record(session, ctx: TurnContext) -> None:
    """Mode-state recorders: hard-break note, form-focus/recast cooldowns,
    error-resolve bookkeeping + first-time retrieval enqueue (r6), and
    last_mode. The scene_modeled mark loop (the CHAR-BUG-005 site) is
    DELETED — Proposal A, 2026-07-29: CHAR-BUG-005 RESOLVED-BY-DELETION,
    see known_bugs.json."""
    from .character_sheet import (
        ERROR_PATTERN_CATALOG,
        detect_error_pattern_resolves,
    )
    from .modes import Mode
    from .turn_events import TurnEventKind as EV

    decision = ctx.decision
    if decision.hard_break:
        session.mode_state.note_hard_break(decision.mode)
    if decision.mode == Mode.FORM_FOCUS:
        pid = (decision.targets or {}).get("error_pattern")
        if pid:
            session.mode_state.set_cooldown(str(pid), 4)
    elif decision.mode == Mode.CF_RECAST:
        # Recast already corrected this pattern. Under ModeSessionState
        # .tick() (decrement BEFORE select; drop at v<=1), set N suppresses
        # the next (N-1) learner turns: N=3 → 2 subsequent turns without a
        # sheet-streak form_focus re-correction (Grok countersign
        # 2026-07-28 caught the off-by-one in the original N=2).
        pid = (decision.targets or {}).get("error_pattern")
        if pid:
            session.mode_state.set_cooldown(str(pid), 3)
    resolved = detect_error_pattern_resolves(ctx.learner) if (
        ctx.learner and not ctx.is_open
    ) else []
    if resolved:
        session.mode_state.last_resolved_form = resolved[0]
        # Session-scoped resolve record for the close-phase summary.
        session.mode_state.note_resolved(resolved)
        # r6: enqueue after transfer success — durability moves to the
        # due queue. First-time scheduling only: an already-scheduled
        # form's ladder is owned by record_outcome, never reset here.
        from .retrieval_scheduler import enqueue as _sched_enqueue

        for pid in resolved:
            fid = (ERROR_PATTERN_CATALOG.get(pid) or {}).get("form_id")
            if not fid:
                continue
            g_entry = (session.sheet.get("grammar") or {}).get(fid) or {}
            if g_entry.get("next_due"):
                continue
            session.sheet = _sched_enqueue(session.sheet, fid, "grammar")
            ctx.ev.emit(EV.DUE_ENQUEUED, key=fid, stage="record")
        # CHAR-BUG-001 RESOLVED: the historical enq → save_sheet here is
        # gone — the writes persist at stage_sheet_commit.
    elif decision.mode == Mode.TRANSFER:
        session.mode_state.last_resolved_form = None
    session.mode_state.last_mode = decision.mode.value


def stage_soft_plan(session, ctx: TurnContext) -> None:
    """soft_plan snapshot (focus rail / debug) + the pedagogy phase keys the
    tail events render from."""
    from .pedagogy_contract import (
        KEY_DIAGNOSTIC_OPEN,
        KEY_KNOWN_LEARNER_OPEN,
        open_phase,
    )

    decision = ctx.decision
    ctx.phase_label = open_phase(session.sheet) if ctx.is_open else "ai"
    ctx.phase_note_key = (
        KEY_DIAGNOSTIC_OPEN if (ctx.is_open and ctx.blank)
        else KEY_KNOWN_LEARNER_OPEN
    )
    ctx.soft_plan = {
        "source": "mode_runtime",
        "mode": decision.mode.value,
        "mode_reason": decision.reason,
        "hard_break": decision.hard_break,
        "phase": "diagnostic" if (ctx.is_open and ctx.blank) else "chat",
        "open_scenes": session.mode_state.open_scene_ids,
        "observations": {
            "signals": ctx.obs.get("signals"),
            "error_hit_ids": ctx.obs.get("error_hit_ids"),
            "next_best": ctx.obs.get("next_best"),
        },
        "image": (
            ctx.teach_images[0].get("concept") if ctx.teach_images else None
        ),
        "targets": decision.targets,
    }
    session.last_plan = ctx.soft_plan


def stage_tail_events(session, ctx: TurnContext) -> None:
    """Tail summary events (typed; the pedagogy phase note is emitted from
    its bare key — Phase 3 batch 2 push-down, was absorb).  The final
    result.notes is built ONCE in stage_parts_notes as the seq-ordered
    projection of the event log — chronological truth (CHAR-BUG-003
    RESOLVED: pre-call plan/schedule notes render BEFORE the gate verdict,
    mode=/mode_reason= at their select-time position)."""
    from .turn_events import TurnEventKind as EV

    ev = ctx.ev
    decision = ctx.decision
    ev.emit(EV.PEDAGOGY, key=ctx.phase_note_key, stage="tail")
    if ctx.is_open:
        ev.emit(EV.OPEN_PHASE, key=ctx.phase_label, stage="tail")
    else:
        ev.emit(EV.PHASE, key="ai_tutor", stage="tail")
    ev.emit(EV.ACTIVITY, key=ctx.activity, stage="tail")
    ev.emit(EV.PHASE_CONSUMED, key=str(ctx.phase_consumed),
            payload={"value": bool(ctx.phase_consumed)}, stage="tail")
    ev.emit(EV.HARD_BREAK, key=str(decision.hard_break),
            payload={"value": bool(decision.hard_break)},
            stage="tail")
    ev.emit(EV.PLAN_SOURCE, key="mode_runtime", stage="tail")
    ev.emit(EV.TEACHER_MODE, key=session.teacher_mode, stage="tail")
    ev.emit(EV.OPEN_SCENES,
            payload={"ids": list(session.mode_state.open_scene_ids)},
            stage="tail")
    ev.emit(EV.MEM_SHOWN,
            payload={"items": sorted(session.pedagogy_memory.shown)},
            stage="tail")
    ev.emit(EV.MEM_ASKED,
            payload={"items": sorted(session.pedagogy_memory.asked)},
            stage="tail")


def stage_parts_notes(session, ctx: TurnContext) -> None:
    """result.parts enrichment (plan/mode/decision/images/gate) + THE notes
    assembly (Phase 3 batch 2): the chronological projection of the typed
    event log — every note is render(event), in seq order."""
    from .turn_events import TurnEventKind as EV, render

    result = ctx.result
    decision = ctx.decision
    if result.parts is not None:
        result.parts = {
            **result.parts,
            "plan": ctx.soft_plan,
            "mode": decision.mode.value,
            "mode_decision": decision.as_dict(),
            "open_phase": (
                ctx.phase_label if ctx.is_open
                else result.parts.get("open_phase")
            ),
            "teach_images": ctx.teach_images,
        }
        if ctx.gate_result is not None:
            result.parts["output_gate"] = ctx.gate_result.as_dict()
        if ctx.image_decision is not None:
            result.parts["image_decision"] = ctx.image_decision.as_dict()
            ctx.ev.emit(EV.IMAGE_DECISION, key=ctx.image_decision.reason,
                        stage="record")
        if ctx.teach_images:
            ctx.ev.emit(EV.TEACH_IMAGE,
                        key=ctx.teach_images[0].get("concept"),
                        stage="record")
    result.notes = [render(e) for e in ctx.ev.events]


def stage_sheet_commit(session, ctx: TurnContext) -> None:
    """THE atomic-turn commit point (CHAR-BUG-001 RESOLVED — Phase 4
    batch 4 declared delta, Grok amendment (a) BINDING text): at most one
    durable sheet persist per successful turn, here, after every recorder
    stage has written its fields into the in-memory sheet.  Partial
    mid-turn saves are removed deliberately; crash recovery semantics are
    "the turn commits or it doesn't" (a crash before this point leaves the
    previous turn's sheet on disk — never a half-written turn).  The
    ``__init__``/reset/close saves OUTSIDE the turn are untouched."""
    session._commit_sheet()


# The recorder census (9 stages, batch-1 re-derived inventory; +1
# post-campaign: stage_intro_morph, 2026-07-29 morph-card review) + the
# atomic commit point as the family's final member.
# stage_intro_morph DELETED, stage_settle_chrome ADDED (§1.1b,
# design-exchange-settlement.md, 2026-07-29): the card view is a
# projection settled AFTER the recorder events it consumes and AFTER
# declared images join the confirmed set; parts_notes then projects the
# full event log including settlement events.
RECORDER_STAGES: tuple = (
    stage_finish,
    stage_introduce_ledger,
    stage_first_seen,
    stage_memory_notes,
    stage_frame_record,
    stage_declared_image,
    stage_mode_record,
    stage_soft_plan,
    stage_tail_events,
    stage_settle_chrome,
    stage_parts_notes,
    stage_sheet_commit,
)


# ---------------------------------------------------------------------------
# CAPTURE/LOG family (Phase 4 batch 5) — the final family, at the exact
# historical inline order.  The Phase 4 stage inventory is COMPLETE with
# these two stages (batch-1 re-derived census: CAPTURE/LOG = 2).
# ---------------------------------------------------------------------------


def stage_debug_capture(session, ctx: TurnContext) -> None:
    """Debug ring buffer (web debug box): the outbound request + response
    metadata for this tutor call.  In-memory only — a ring of the last
    DEBUG_RING_SIZE calls served by GET /api/debug/requests; these payloads
    are never written to disk logs."""
    session._capture_debug_request(
        system=ctx.system,
        messages=ctx.messages,
        task=ctx.task,
        decision_dict=ctx.decision.as_dict(),
        activity=ctx.activity,
        usage=ctx.usage,
        gate_result=ctx.gate_result,
        notes=ctx.result.notes,
        stop_reason=getattr(ctx.final, "stop_reason", "") or "",
        is_open=ctx.is_open,
    )


def stage_log_turn(session, ctx: TurnContext) -> None:
    """The single session-log write — once per turn, AFTER the recorder
    family attached mode/plan/gate/images to the result (stage_finish
    passes skip_log=True by design; this stage is the one .jsonl write).
    A logger-less session (log=False) is a no-op inside
    ``_log_turn_result``."""
    session._log_turn_result(
        ctx.result,
        log_learner=ctx.log_learner if ctx.log_learner is not None else (
            "(session open)" if ctx.is_open else (ctx.learner or "")
        ),
    )


# The capture/log census — the final family; the stage inventory closes here.
CAPTURE_LOG_STAGES: tuple = (
    stage_debug_capture,
    stage_log_turn,
)
