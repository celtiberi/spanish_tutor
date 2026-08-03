"""Turn pipeline — TurnContext + the pre-model stage families (Phase 4).

The adjudicated architecture refactor (docs/reviews-architecture-refactor.md,
Phase 4) breaks ``ConversationalSession._execute_ai_tutor`` into explicit
stages: the ``TurnContext`` working set plus plain named functions.  No
framework, no registry magic — the executor calls a named-function
sequence.  (The CONTRIBUTORS instruction family — flavorable /
append_instruction / InstructionContributor — was DELETED with the mode
router, 2026-08-03: instructions no longer exist to contribute to.)

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
    stage_uptake_flag        §2.1a self-flag OBSERVATION (typed
                             UPTAKE_FLAGGED event; re-keyed off the dead
                             router 2026-08-03)
    stage_observe            observations + blank/sigs derivation
    stage_due_outcomes       pre-turn retrieval-outcome recording
    stage_introduce_plan     SHADOW introduce planner (r7 S2) — parks the
                             plan on ctx.intro_plan; instructions never
                             ship (§1.1)

(Scenes, the session-phase clock and the task runtime were DELETED
2026-08-03 — full-code-audit S9.  The MODE ROUTER — select_mode, the
guard chain, ModeSessionState, the english-only streak, guard-6 covered
concepts, MODE/MODE_REASON events, the instruction-contributor family —
was DELETED 2026-08-03, full-code-audit S4: it was shadow-only after the
§1.1 strip; the model is the teacher.)

The REALIZE family (batch 3) runs next (``REALIZE_STAGES``)::

    stage_signal_shadow      parallel signal classifier spawn (default)
    stage_intro_image        introduce R-B image attach (cache-only) —
                             the surviving code-side attach wire (Grok
                             AMEND: no silent loss of image attach)
    stage_fallback_image     open/blank-turn scene-setting image
    stage_introduce_render   R-B→R-D downgrade when the planned image did
                             not attach (Grok AMEND 4b); ledger sees the
                             realizable plan.  No instruction render.
    stage_prompt_build       system + task message + FULL-history assembly
    stage_model_call         tutor_turn; provider exceptions become
                             ctx.error_result (the executor returns it)

The GATE/REPAIR family (batch 3, E3): ``stage_gate_context`` builds the
turn-constant ``output_gate.GateContext`` from the TurnContext — the
historical 18-argument call-site seam dies there; ``stage_gate_check``
parses the reply and runs the gate;
``stage_gate_verdict`` owns audit events only (no rewrite).  The executor
wraps check+verdict in the
historical try/except (any gate exception → OUTPUT_GATE_ERROR, turn
proceeds ungated) — context build stays outside it, as inline.

The RECORDERS family (batch 4) runs after gate/repair — the post-model
turn recorders at the exact historical inline order (``RECORDER_STAGES``)::

    stage_finish             sheet process_turn + TurnResult assembly
                             (session._finish; the region's sheet writer)
    stage_introduce_ledger   introduce_outcome → ledger/memory/milestone
                             writes (r7 S1 + R-H scaffold-evidence law)
    stage_first_seen         gate scaffold_saved → durable first_seen bits
                             (exposure ledger — every visibly-used key,
                             gate retune 2026-08-03)
    stage_memory_notes       note_plan_try + asked-topic registry +
                             note_tutor_turn memory writes
    stage_frame_record       frames_seen exposure writes for realized due
                             elicits + introductions (encounter-variety
                             round, 2026-07-29)
    stage_declared_image     tutor-declared <image concept="…"/> resolution
                             (relevance law, repeat/cooldown gates)
    stage_resolve_enqueue    error-resolve → first-time retrieval enqueue
                             (r6; the surviving wire of the deleted
                             stage_mode_record)
    stage_soft_plan          soft_plan snapshot (focus rail / debug)
    stage_tail_events        tail summary events (pedagogy/phase/
                             plan_source/mem_* emits)
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
from typing import Any


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

    # -- produced by stage_introduce_plan -----------------------------------
    # SHADOW IntroducePlan (r7 S2): drives the R-B image attach, the
    # R-B→R-D downgrade and the post-turn introduce ledger.  Its
    # instruction text never ships (§1.1).
    intro_plan: Any = None

    # -- produced by the realize family (batch 3) ---------------------------
    teach_images: list = field(default_factory=list)
    image_decision: Any = None                      # ImageDecision | None
    system: str = ""                                # static system blocks
    task: str = ""                                  # per-turn task message
    messages: list = field(default_factory=list)    # full request messages
    # (realization_artifact DELETED 2026-08-03, full-code-audit S2: the B0
    # brief path died with the course pack — nothing produced it.)
    final: Any = None                               # provider response obj
    raw: str = ""                                   # raw model text
    model_raw: str = ""                             # untouched provider text
    #   (pre <plan>-strip — what was RECEIVED, for the traffic log)
    plan_turn: bool = False                         # this call was a PLAN turn
    tool_delta: Any = None                          # sheet tool blocks
    usage: dict | None = None                       # token usage (merged)
    error_result: Any = None                        # TurnResult on call error

    # -- produced by the gate/repair family (batch 3, E3) -------------------
    gate_ctx: Any = None                            # output_gate.GateContext
    gate_result: Any = None                         # OutputGateResult | None
    gate_hold: bool = False   # legacy blank-hold (deprecated; prefer gate_fail)
    # Loud surface of gate failure (2026-08-01): raw ships; client must show faults.
    gate_fail: bool = False

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
    classifies before the turn builds (+~2-3s/turn); default SHADOW mode
    runs parallel to the tutor call via _spawn_signal_shadow in the
    realize region (zero latency, fixes stale holds for next turn)."""
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
            # observations — they stay out of the memory/observation sets.
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


def stage_uptake_flag(session, ctx: TurnContext) -> None:
    """§2.1a self-flag OBSERVATION (re-keyed 2026-08-03, router teardown):
    the learner literally marked a token as uncertain («uvia (rain)»,
    quoted single token) — emit the typed UPTAKE_FLAGGED event.  Pure
    telemetry for the uptake_flag_honored eval; no instruction ships (the
    model reads the learner's words itself, §1.1).  The old instruction
    path, its mode/reason gates and the ModeSessionState uptake budget
    died with the router (the budget paced instruction injections; an
    observation needs no pacing)."""
    from .observe import detect_self_flagged_token
    from .turn_events import TurnEventKind as EV

    if ctx.is_open or not ctx.learner:
        return
    token = detect_self_flagged_token(ctx.learner)
    if token:
        ctx.ev.emit(EV.UPTAKE_FLAGGED, key=token, stage="instruct")


def stage_observe(session, ctx: TurnContext) -> None:
    """Observations + the blank/sigs derivations the rest of the turn
    reads.  (The mode_state tick / error-hit recency memory died with the
    router — their only reader was the deleted guard chain.)"""
    from .observe import build_observations
    from .pedagogy_contract import is_blank_learner

    obs = build_observations(
        session.sheet, learner=ctx.learner, is_open=ctx.is_open,
        extra_signals=ctx.llm_signals,
    )
    ctx.obs = obs
    ctx.blank = bool(obs.get("blank_sheet") or is_blank_learner(session.sheet))
    ctx.sigs = set(obs.get("signals") or [])


def stage_due_outcomes(session, ctx: TurnContext) -> None:
    """Retrieval scheduler (Phase 1): record retrieval outcomes on clear
    evidence BEFORE building the turn, so ladders/next_due advance and a
    just-used item is not re-offered this turn.  The typed DUE_OUTCOME_*
    events land in the log; result.notes is the chronological event
    projection (Phase 3 batch 2 — CHAR-BUG-003 resolved)."""
    if ctx.learner and not ctx.is_open:
        session._record_due_outcomes(ctx.learner, ctx.sigs)


def stage_introduce_plan(session, ctx: TurnContext) -> None:
    """SHADOW introduce planner (Phase 3, r7 S2).  Code picks the item +
    scaffold; the ledger write happens POST-turn only if the reply shows
    the key WITH scaffold evidence.  Instructions never ship (§1.1) — the
    plan drives only the R-B image attach, the R-B→R-D downgrade and the
    post-turn ledger.  The mode-flavor eligibility gate (conversation +
    flavorable reason) died with the router (2026-08-03): introduce_block
    owns budget/eligibility and runs on every turn."""
    from .conv_session import introduce_block
    from .turn_events import TurnEventKind as EV

    if session.association_table is None:
        ctx.ev.emit(EV.INTRODUCE_TABLE_MISSING, stage="instruct")
        return
    intro_plan = introduce_block(
        session.sheet,
        session.association_table,
        session.pedagogy_memory.snapshot(),
    )
    if intro_plan is None:
        return
    ctx.ev.emit(
        EV.INTRODUCE_PLANNED,
        key=intro_plan.key,
        payload={"rule_id": intro_plan.rule_id,
                 "scaffold_type": intro_plan.scaffold_type},
        stage="instruct",
    )
    ctx.intro_plan = intro_plan


# The documented head sequence — the executor calls these in order.
PRE_MODEL_STAGES: tuple = (
    stage_classify_signals,
    stage_memory_intake,
    stage_uptake_flag,
    stage_observe,
    stage_due_outcomes,
    stage_introduce_plan,
)


# ---------------------------------------------------------------------------
# REALIZE family (Phase 4 batch 3) — runs after the head.
# ---------------------------------------------------------------------------


def stage_signal_shadow(session, ctx: TurnContext) -> None:
    """Default SHADOW classifier: runs parallel to the tutor call (zero
    latency, fixes stale holds for next turn)."""
    if not ctx.is_open and ctx.learner:
        session._spawn_signal_shadow(ctx.learner)


def stage_intro_image(session, ctx: TurnContext) -> None:
    """Introduce R-B image attach (cache-only on the reply path).

    The mode-decision attach died with the router (2026-08-03); this is
    the surviving code-side attach wire (Grok AMEND: no silent loss of
    image attach) — an R-B dual-coding introduce plan requests its key's
    image.  A cache miss attaches nothing now, is noted visibly, and
    warms async; stage_introduce_render then downgrades the plan to R-D."""
    ctx.image_decision = None
    ctx.teach_images = []
    if ctx.intro_plan is not None and ctx.intro_plan.scaffold_type == "image":
        ctx.teach_images = session._attach_concept_image(
            ctx.intro_plan.key, decision_reason="introduce:R-B",
        )


def stage_fallback_image(session, ctx: TurnContext) -> None:
    """Open/blank-turn scene-setting image (cache-only).

    The association / comprehension-repair fallback arms died with the
    router (2026-08-03) — on a non-open turn an image now arrives only
    via the introduce R-B plan (stage_intro_image) or the model's own
    ``<image concept="…"/>`` declaration (stage_declared_image): the
    evidence-based triggers.  What survives here is the true-zero open
    illustration (a BLANK open orients with the greeting scene image —
    blank-sheet evidence, not a mode; a known open ships no code-picked
    image, exactly as before the teardown)."""
    from .teach_assets import assets_for_ai_turn

    if ctx.teach_images or not (
        ctx.blank
        and (ctx.is_open or not (ctx.learner or "").strip())
    ):
        return
    ctx.teach_images, ctx.image_decision = assets_for_ai_turn(
        is_open=ctx.is_open,
        blank_sheet=ctx.blank,
        learner=ctx.learner if not ctx.is_open else "",
        signals=list(ctx.sigs),
        images_shown=session.pedagogy_memory.images_shown,
        turns_since_image=session.pedagogy_memory.turns_since_image,
        session_turns=session.pedagogy_memory.turns,
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
            source="open",
            decision_reason=f"warm:{ctx.image_decision.reason}",
        )


def stage_introduce_render(session, ctx: TurnContext) -> None:
    """Settle the INTRODUCE plan now that image resolution is known
    (Grok AMEND 4b, 2026-07-28): an R-B plan whose image did NOT actually
    attach (cache miss + generation cap/denied) downgrades to the R-D
    single ≤6-word micro-gloss.  Rebinds ``ctx.intro_plan`` on downgrade:
    the post-turn introduce ledger must see the plan that was actually
    realizable.  (The instruction render died with the router — the plan
    is shadow telemetry + ledger wiring, §1.1.)"""
    from .turn_events import TurnEventKind as EV

    if ctx.intro_plan is None:
        return
    from .introduce_router import IntroducePlan

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


def stage_prompt_build(session, ctx: TurnContext) -> None:
    """System = STATIC blocks only (stance/persona) so the provider
    prefix-cache covers system + chat history.  The per-turn sheet rides
    in the task message at the request tail.  No personal context —
    personal-data capture is disabled.  Full history in testing
    (HISTORY_TURNS=0); never mutates session.history.

    The only branch point is plan-mode (TEACHER_CONTEXT, below): PLAN
    turns append the pedagogy guide + plan instructions as extra system
    blocks; ROUND turns append the round note and run on the sanctioned
    12-message window.  (The B0 "brief" arm and its realization_artifact
    DIED 2026-08-03 with the course pack — full-code-audit S1f/S2.)"""
    from . import config
    from .character_sheet import format_sheet_for_prompt
    from .executor import build_ai_tutor_system, build_ai_tutor_user_message
    from .turn_events import TurnEventKind as EV

    # Course pack DELETED 2026-08-03 (USER: "the character sheet IS the
    # course pack") — the sheet carries the target inventory; no palette.
    ctx.system = build_ai_tutor_system()
    # §1.1 REWRITE (USER 2026-08-03): the model gets FACTS, never the
    # routers' scripted opinions. Due items ride as data (key + gloss +
    # frames already used) so the model can schedule review by judgment;
    # mode/phase/introduce machinery still runs as SHADOW telemetry
    # (notes/debug show what code would have said) but ships nothing.
    from .retrieval_scheduler import due_items, frames_seen_of

    table = getattr(session, "association_table", None) or {}
    due_facts = [
        {
            "key": d.key,
            "kind": d.kind,
            "gloss": str((table.get(d.key) or {}).get("gloss_en") or ""),
            "frames_already_used": list(
                frames_seen_of(session.sheet, d.key, d.kind)
            ),
        }
        for d in due_items(session.sheet, max_due=5)
    ]
    if due_facts:
        # The DUE offer event — fired from the due-DATA path (the facts the
        # model actually receives), not a phase-gated contributor (the
        # session-phase machinery died 2026-08-03).  stage_frame_record
        # reads these events for the frames_seen exposure writes.
        ctx.ev.emit(
            EV.DUE_ELICIT_OFFERED,
            payload={
                "keys": [d["key"] for d in due_facts],
                "kinds": [d["kind"] for d in due_facts],
            },
            stage="instruct",
        )
    # Two-phase context (USER architecture 2026-08-03; default): PLAN
    # turns carry everything (pedagogy + pack + sheet + history) and the
    # model writes its own session plan; ROUND turns carry the model's
    # plan + sheet + facts + a recent window. TEACHER_CONTEXT=full keeps
    # the historical every-turn-everything path for comparison.
    plan_mode = getattr(config, "TEACHER_CONTEXT", "plan") == "plan"
    needs_plan = plan_mode and (
        getattr(session, "session_plan", None) is None
        or getattr(session, "replan_requested", False)
    )
    ctx.task = build_ai_tutor_user_message(
        learner=ctx.learner,
        is_open=ctx.is_open,
        session_memory=session.pedagogy_memory.snapshot(),
        teach_images=ctx.teach_images,
        blank_sheet=ctx.blank,
        sheet_summary=format_sheet_for_prompt(session.sheet),
        teaching_data={"due_for_review": due_facts},
        session_plan=(
            None if (not plan_mode or needs_plan)
            else getattr(session, "session_plan", None)
        ),
    )
    if plan_mode:
        from .session_plan import (
            PLAN_INSTRUCTIONS,
            ROUND_HISTORY_MESSAGES,
            ROUND_NOTE,
            load_pedagogy,
        )

        if needs_plan:
            # PLAN turn: full picture. Pedagogy + plan instructions ride
            # as additional cache-stable system blocks after the pack.
            pedagogy = load_pedagogy()
            extra = []
            if pedagogy:
                extra.append({
                    "type": "text",
                    "text": "# The teaching guide (yours)\n\n" + pedagogy,
                })
            extra.append({"type": "text", "text": PLAN_INSTRUCTIONS})
            ctx.system = list(ctx.system) + extra
            # replan_requested is cleared AFTER a successful model call
            # (stage_model_call) — clearing here would swallow the replan
            # when the provider call fails (audit D finding 3).
            ctx.plan_turn = True
            ctx.ev.emit(EV.SESSION_PLAN, key="requested", stage="plan")
            history = session.history
        else:
            # ROUND turn: the pedagogy guide stays out of the system; the
            # model's plan already digested it.  ctx.system is the plain
            # stance/persona build from above — reuse it (the duplicate
            # build_ai_tutor_system call DELETED 2026-08-03, S2).
            ctx.system = list(ctx.system) + [
                {"type": "text", "text": ROUND_NOTE}
            ]
            # truncation-ok: plan-mode ROUND window — USER architecture
            # 2026-08-03, not a silent latency slice. PLAN turns carry
            # full history; the model escapes to full context any turn
            # with <replan/>.
            history = session.history[-ROUND_HISTORY_MESSAGES:]  # truncation-ok: plan-mode round window (see above)
    else:
        history = session.history

    if ctx.is_open:
        ctx.messages = [{"role": "user", "content": ctx.task}]
    else:
        ctx.messages = config.history_for_model(history) + [
            {"role": "user", "content": ctx.task}
        ]


def stage_model_call(session, ctx: TurnContext) -> None:
    """The tutor model call.  A provider exception becomes
    ``ctx.error_result`` (the executor returns it immediately) — the
    historical early-return semantics."""
    from . import config
    from .conv_session import TurnResult, tutor_turn

    try:
        # Ability grades via update_character_sheet when SHEET_TOOLS
        # (default on). No regex hard-observer ability path (2026-07-31).
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
            # PLAN turns carry plan + reply in one response and the
            # request already paid for the full context — give them the
            # full output budget (USER 2026-08-03: "lets not be so
            # limiting on the first request"). Rounds stay on the
            # default TUTOR_MAX_TOKENS.
            max_tokens=config.MAX_TOKENS if ctx.plan_turn else None,
        )
    except Exception as e:
        ctx.error_result = TurnResult(
            reply="",
            error=f"{type(e).__name__}: {e}",
            input_mode=ctx.input_mode,
        )
        return
    ctx.final = final
    # Two-phase context (2026-08-03): harvest the model's OWN <plan> /
    # <replan/> from the raw reply BEFORE anything parses it, so plan
    # text can never leak into the learner-visible message. Code stores
    # the plan verbatim — never writes or edits one (§1.1).
    from .session_plan import extract_plan
    from .turn_events import TurnEventKind as EV_

    ctx.model_raw = raw
    _plan, _replan, _cleaned = extract_plan(raw)
    if _plan is not None:
        session.session_plan = _plan
        ctx.ev.emit(EV_.SESSION_PLAN, key="updated", stage="plan")
    if _replan:
        session.replan_requested = True
        ctx.ev.emit(EV_.SESSION_PLAN, key="replan_requested", stage="plan")
    if ctx.plan_turn:
        # The call succeeded: the requested re-plan (if any) is consumed.
        session.replan_requested = _replan
        if _plan is None:
            # Plan turn produced no plan — VISIBLE, and next turn will be
            # another (expensive) full-context plan turn (audit D f.2).
            ctx.ev.emit(EV_.SESSION_PLAN, key="missing", stage="plan")
    # Always the stripped text: an EMPTY <plan></plan> yields _plan=None
    # but must still never leak tags to the learner (audit D finding 1).
    ctx.raw = _cleaned
    ctx.tool_delta = tool_delta
    ctx.usage = usage


# The realize census.
# stage_image_costs DELETED (§1.1b P-3, 2026-07-29): display bookkeeping
# (note_image, image costs) fires at settle_chrome for CONFIRMED images
# only.  stage_mode_image + stage_mode_snapshot DELETED with the router
# (2026-08-03); stage_intro_image is the surviving code-side attach wire.
REALIZE_STAGES: tuple = (
    stage_signal_shadow,
    stage_intro_image,
    stage_fallback_image,
    stage_introduce_render,
    stage_prompt_build,
    stage_model_call,
)


# ---------------------------------------------------------------------------
# GATE/REPAIR family (Phase 4 batch 3, E3) — context build outside the
# executor's try/except; check + repair inside it (any exception →
# OUTPUT_GATE_ERROR, the turn proceeds ungated — historical semantics).
# ---------------------------------------------------------------------------

# CRITICAL faults (S11, USER-ruled 2026-08-03): the gate is a PLUMBING
# auditor — the two faults below are its ENTIRE vocabulary.  Every
# teaching-opinion fault (cluster_veto / probe_loop / english_wall /
# pedagogy:* / unscaffolded / regloss) was DELETED from the runtime and
# lives only as eval checks (evals/student_checks.py).  Both plumbing
# faults surface as gate_fail + raw reply (no-hide, 2026-08-01).
GATE_CRITICAL_FAULTS = frozenset({
    "gate:sheet_leak",  # model dumped sheet/tool JSON into chat
    "gate:truncated",  # reply hit max_tokens mid-sentence
})

# The still_fail floor: faults in this set mark the shipped turn
# OUTPUT_GATE_STILL_FAIL (visible banner + raw reply).
GATE_SHIP_BAN_FAULTS = GATE_CRITICAL_FAULTS


def stage_gate_context(session, ctx: TurnContext) -> None:
    """Build the turn-constant GateContext from the TurnContext — the
    historical 18-argument call-site seam dies here (E3).  S11
    (2026-08-03): the fields only teaching checks read are GONE
    (already_asked / asked_topics / topic_nouns / introduce_key /
    retrieval_failed_keys / blank_zero / is_open) — what remains feeds the
    two plumbing checks and the first-exposure scan.  parts/visible ride
    per attempt via ``dataclasses.replace`` in stage_gate_check."""
    from .output_gate import GateContext

    ctx.gate_ctx = GateContext(
        raw=ctx.raw or "",
        truncated=(
            (getattr(ctx.final, "stop_reason", "") or "") == "max_tokens"
        ),
        # AMEND 2b (gate retune): a same-turn teach image for a key counts
        # as its scaffold — thread the attached concepts.
        image_concepts={
            str(t.get("concept") or "")
            for t in (ctx.teach_images or [])
            if t.get("concept")
        },
        association_table=session.association_table,
        sheet=session.sheet,
        learner_text=ctx.learner if not ctx.is_open else "",
    )


def _settle_pixels(session, ctx: TurnContext) -> None:
    """Shared pixel-settlement pass (§1.1b; run ≤2× per turn — post-
    generation and again after a gate-repair rewrite). Confirms image
    candidates against the REALIZED exchange and shrinks ctx.teach_images
    to the confirmed set, so GateContext.image_concepts, introduce
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
    image must not license a scaffold in the exposure map)."""
    _settle_pixels(session, ctx)


def stage_gate_check(session, ctx: TurnContext) -> None:
    """Parse the reply and run the gate.  (The require_recast re-check was
    DELETED with the mode-keyed contracts, gate retune 2026-08-03 — its
    only sources were the shadow router's mode + targets.)"""
    from dataclasses import replace

    from .output_gate import check_output_gate
    from .tutor_response import process_tutor_raw as _ptr

    _vis0, _parts0 = _ptr(ctx.raw or "")
    ctx.gate_result = check_output_gate(
        replace(ctx.gate_ctx, parts=_parts0.as_dict(), visible=_vis0)
    )


def _surface_gate_fail(session, ctx: TurnContext, faults: list | set) -> None:
    """Mark and ship the raw attempt — never rewrite, strip, scrub, or blank.

    2026-08-01 user directive: repair/hold/scrub hide prompt failures.
    """
    from .turn_events import TurnEventKind as EV

    fault_list = sorted(set(faults or []))
    session.gate_still_fail_count = (
        getattr(session, "gate_still_fail_count", 0) + 1
    )
    ctx.gate_hold = False
    ctx.gate_fail = True
    ctx.ev.emit(
        EV.OUTPUT_GATE_STILL_FAIL,
        payload={"faults": fault_list, "surface": "visible", "no_hide": True},
        stage="gate",
    )
    _settle_pixels(session, ctx)


def stage_gate_verdict(session, ctx: TurnContext) -> None:
    """Audit-only gate: log faults, never rewrite or hide the model reply.

    S11 (2026-08-03): every remaining gate fault is a critical plumbing
    fault (truncated / sheet_leak) — the soft-fault branch and its
    OUTPUT_GATE_SOFT_FAIL event died with the teaching-opinion checks.
    Any fault → gate_fail banner + raw reply ships as-is.
    """
    from .turn_events import TurnEventKind as EV

    gate_result = ctx.gate_result
    faults = list(gate_result.faults or [])

    if gate_result.ok:
        ctx.ev.emit(EV.OUTPUT_GATE_OK, stage="gate")
        return

    ctx.ev.emit(
        EV.OUTPUT_GATE_FAIL,
        payload={"faults": faults},
        stage="gate",
    )

    # Critical: surface raw + loud fail. No second model call, no surgery.
    residual = set(faults) & GATE_SHIP_BAN_FAULTS
    _surface_gate_fail(session, ctx, residual or faults)


# Backward-compatible name (old repair path deleted 2026-08-01; the
# stage_gate_repair alias was DELETED 2026-08-03, full-code-audit S2 —
# conv_session calls stage_gate_verdict directly).
_gate_floor = _surface_gate_fail

# Gate audit census: settle → context → check → verdict (no rewrite stage).
# (Renamed from GATE_REPAIR_STAGES 2026-08-03 — no repair exists.)
GATE_AUDIT_STAGES: tuple = (
    stage_settle_pixels,
    stage_gate_context,
    stage_gate_check,
    stage_gate_verdict,
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
    no action (re-gloss judgment lives in evals — S11 2026-08-03)."""
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
    """Exposure-ledger writes (gate retune 2026-08-03, Grok AMEND 2a):
    EVERY not-yet-introduced table key the tutor visibly used this turn —
    scaffolded ("gloss"/"anchor"/"image") or "bare" — gets a durable
    first_seen bit, so bare-but-used keys stop re-faulting forever (the
    «bien» fired-5× pathology; only code-planned introduces used to write
    first_seen).  Deliberately NOT an introduction: no budget consumed, no
    retrieval enqueue, confidence/status untouched (honesty law)."""
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
        # Reason "" since the router died (2026-08-03): the mode name it
        # used to pass polluted the asked registry with mode-name keys;
        # note_plan_try's content matching reads the try text itself.
        session.pedagogy_memory.note_plan_try("", try_text)
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


def stage_resolve_enqueue(session, ctx: TurnContext) -> None:
    """Error-resolve → first-time retrieval enqueue (r6) — the surviving
    wire of the deleted stage_mode_record (router teardown 2026-08-03:
    the hard-break note, form cooldowns and last_mode had no reader left).
    First-time scheduling only: an already-scheduled form's ladder is
    owned by record_outcome, never reset here."""
    from .character_sheet import (
        ERROR_PATTERN_CATALOG,
        detect_error_pattern_resolves,
    )
    from .turn_events import TurnEventKind as EV

    resolved = detect_error_pattern_resolves(ctx.learner) if (
        ctx.learner and not ctx.is_open
    ) else []
    if not resolved:
        return
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


def stage_soft_plan(session, ctx: TurnContext) -> None:
    """soft_plan snapshot (focus rail / debug) + the pedagogy phase keys the
    tail events render from.  Mode fields DELETED with the router
    (2026-08-03); source is honest — the model plans its own teaching."""
    from .pedagogy_contract import (
        KEY_DIAGNOSTIC_OPEN,
        KEY_KNOWN_LEARNER_OPEN,
        open_phase,
    )

    ctx.phase_label = open_phase(session.sheet) if ctx.is_open else "ai"
    ctx.phase_note_key = (
        KEY_DIAGNOSTIC_OPEN if (ctx.is_open and ctx.blank)
        else KEY_KNOWN_LEARNER_OPEN
    )
    ctx.soft_plan = {
        "source": "model",
        "phase": "diagnostic" if (ctx.is_open and ctx.blank) else "chat",
        "observations": {
            "signals": ctx.obs.get("signals"),
            "error_hit_ids": ctx.obs.get("error_hit_ids"),
            "next_best": ctx.obs.get("next_best"),
        },
        "image": (
            ctx.teach_images[0].get("concept") if ctx.teach_images else None
        ),
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
    ev.emit(EV.PEDAGOGY, key=ctx.phase_note_key, stage="tail")
    if ctx.is_open:
        ev.emit(EV.OPEN_PHASE, key=ctx.phase_label, stage="tail")
    else:
        ev.emit(EV.PHASE, key="ai_tutor", stage="tail")
    # HARD_BREAK emit DELETED with the router (2026-08-03).  plan_source
    # is honest post-teardown: the model authors its own plan.
    ev.emit(EV.PLAN_SOURCE, key="model", stage="tail")
    ev.emit(EV.TEACHER_MODE, key=session.teacher_mode, stage="tail")
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
    if result.parts is not None:
        # parts["mode"] / parts["mode_decision"] DELETED with the router
        # (2026-08-03) — the UI mode badge died with them.
        result.parts = {
            **result.parts,
            "plan": ctx.soft_plan,
            "open_phase": (
                ctx.phase_label if ctx.is_open
                else result.parts.get("open_phase")
            ),
            "teach_images": ctx.teach_images,
        }
        if ctx.gate_result is not None:
            result.parts["output_gate"] = ctx.gate_result.as_dict()
        if ctx.gate_hold:
            # Legacy blank-hold flag (should be rare after 2026-08-01).
            result.parts["gate_hold"] = True
        if ctx.gate_fail or (
            ctx.gate_result is not None and not ctx.gate_result.ok
        ):
            # Loud failure: client must show faults + the raw attempt.
            result.parts["gate_fail"] = True
            if ctx.gate_result is not None:
                result.parts["gate_faults"] = list(
                    ctx.gate_result.faults or []
                )
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
    stage_resolve_enqueue,
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
    for this tutor call — a ring of the last DEBUG_RING_SIZE calls served
    by GET /api/debug/requests.  When session logging is on, each entry is
    also mirrored verbatim to ``<session_id>.requests.jsonl`` (USER
    2026-08-03: "I want to see what is being sent and received")."""
    session._capture_debug_request(
        system=ctx.system,
        messages=ctx.messages,
        task=ctx.task,
        usage=ctx.usage,
        gate_result=ctx.gate_result,
        notes=ctx.result.notes,
        stop_reason=getattr(ctx.final, "stop_reason", "") or "",
        is_open=ctx.is_open,
        raw=ctx.model_raw or ctx.raw,
        reply=getattr(ctx.result, "reply", "") or "",
        tool_delta=ctx.tool_delta if isinstance(ctx.tool_delta, dict) else None,
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
        is_open=ctx.is_open,
    )


# The capture/log census — the final family; the stage inventory closes here.
CAPTURE_LOG_STAGES: tuple = (
    stage_debug_capture,
    stage_log_turn,
)
