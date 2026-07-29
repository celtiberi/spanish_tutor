"""Reusable conversational Spanish session (CLI + web).

Sheet = learner context; tool call update_character_sheet keeps it current.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .can_dos import build_focus_panel
from .character_sheet import (
    UPDATE_CHARACTER_SHEET_TOOL,
    clear_session_scoped_affect,
    compute_progress_score,
    default_sheet,
    extract_sheet_delta,
    format_sheet_human,
    load_sheet,
    process_turn,
    save_sheet,
)
from .focus_enrich import enrich_focus_panel, focus_cache_key, focus_model_enabled
from .session_log import SessionLogger
from .pedagogy_contract import evaluate_turn
from .session_state import DEBUG_RING_SIZE, SessionState
from .turn_events import (
    TurnEventKind as EV,
    TurnEventLog,
    begin_turn_log,
    render_note,
    session_event_log,
)
from .tutor_response import compose_visible, process_tutor_raw


def compose_if_needed(parts) -> str:
    return compose_visible(parts)

DEFAULT_SHEET_PATH = config.CHARACTER_SHEET_PATH
SHEET_TOOLS = [UPDATE_CHARACTER_SHEET_TOOL]

# Per-session image-generation ceilings (novel images bill ~$0.039 each;
# cache hits are free). 8×$0.039=$0.312 hard session ceiling; the tutor-
# declared subset caps at 5×=$0.195 so model freestyle (verbs/phrases/ideas
# are all allowed) stays budget-bounded without an allowlist.
# Grok countersign 2026-07-28: a cap is a control, tracking alone is not.
MAX_IMAGE_GENERATIONS_PER_SESSION = 8
MAX_DECLARED_NOVEL_PER_SESSION = 5

# --- Retrieval scheduler soft wiring (Phase 1 pedagogy engine) --------------
# Due re-encounters ride the mode instructions as SOFT additions inside
# conversation-flavored turns only. No new hard mode; repair/guard turns and
# hard breaks keep their single focus (r2/r6 preemption rules).
DUE_ELICIT_MODES = frozenset({"conversation", "transfer"})
DUE_GUARD_REASONS = frozenset({
    "learner_topic_request",
    "learner_help_request",
    "grammar_question_inline",
})


def due_elicit_block(
    sheet: dict,
    *,
    mode: str,
    reason: str = "",
    today=None,
    max_due: int = 3,
    activity_hint: str | None = None,
):
    """Compact DUE RE-ENCOUNTERS instruction block for the tutor task.

    Returns (block_text, due_items). Empty when the mode is not a
    conversation flavor, when the turn is a help/topic guard turn, when the
    session phase is new_input (introduce owns that phase — Grok AMEND 4a,
    2026-07-28: never stack DUE + INTRODUCE on one turn), or when nothing is
    due. Code decides WHAT is due; the model only realizes ONE re-encounter
    naturally in Spanish.
    """
    from .retrieval_scheduler import due_items

    # Phase sole-orchestrator: new_input owns introduce; do not compete
    # with due.
    if activity_hint == "new_input":
        return "", []
    if mode not in DUE_ELICIT_MODES or reason in DUE_GUARD_REASONS:
        return "", []
    due = due_items(sheet, today=today, max_due=max_due)
    if not due:
        return "", []
    listing = "; ".join(
        f"«{d.key}» ({d.kind}, {d.prompt_hint})" for d in due
    )
    block = (
        "DUE RE-ENCOUNTERS (weave ONE naturally into this turn's Spanish; "
        "no flashcard framing, no re-gloss unless they fail): " + listing
    )
    return block, due


# --- Introduce router soft wiring (Phase 3 pedagogy engine, r7 S2) ----------
# The INTRODUCE plan rides the same soft path as DUE RE-ENCOUNTERS, but only
# inside the NEW INPUT phase and only on the phase-prefix-flavorable turns
# (known open / default fallthrough). Guard, repair, and recast turns keep
# their single focus. The router itself never calls the model.
INTRODUCE_FLAVORABLE_REASONS = frozenset({
    "known_open_from_sheet",
    "default_conversation",
})


def introduce_block(
    sheet: dict,
    table: dict | None,
    session_snapshot: dict,
    *,
    mode: str,
    reason: str = "",
    activity_hint: str | None = None,
):
    """INTRODUCE instruction block for the tutor task.

    Returns (block_text, IntroducePlan | None). Empty unless the session
    phase is new_input AND the mode decision is a flavorable conversation
    turn (the same condition set as modes._phase_prefix: known-open /
    default fallthrough — never guard/repair/recast turns). Code decides
    WHAT to introduce and with WHICH scaffold; the model only realizes it.
    """
    from .introduce_router import plan_introduction, plan_instructions

    if activity_hint != "new_input" or not table:
        return "", None
    if mode != "conversation" or reason not in INTRODUCE_FLAVORABLE_REASONS:
        return "", None
    plan = plan_introduction(sheet, table, session_snapshot)
    if plan is None:
        return "", None
    return plan_instructions(plan), plan


def introduce_scaffold_evidence(plan, reply: str, teach_images=None) -> bool:
    """Did the plan's INTRODUCE MOVE visibly happen in this reply?

    Honesty rule (2026-07-28 false-planted incident, PEDAGOGY §3): mere key
    presence is NOT an introduction — the tutor greets with «¡Buenas tardes!»
    naturally without teaching it. Evidence required per scaffold:
    - R-D gloss    → the "(≤6-word gloss)" parenthetical right after the key
    - R-A cognate / R-E keyword → the plan's anchor text present in-reply
    - R-B image    → a teach_image with this concept actually attached
    Detection reuses the output gate's scaffold detectors (gloss_after_key /
    anchor_in_reply) — one definition, no drift.
    """
    from .output_gate import anchor_in_reply, gloss_after_key

    payload = getattr(plan, "scaffold_payload", None) or {}
    stype = getattr(plan, "scaffold_type", "")
    if stype == "gloss":
        return gloss_after_key(plan.key, reply or "")
    if stype == "cognate":
        return anchor_in_reply({"cognate_en": payload.get("anchor")}, reply or "")
    if stype == "keyword":
        return anchor_in_reply({"keyword_en": payload.get("keyword")}, reply or "")
    if stype == "image":
        return any(
            (t.get("concept") or "") == plan.key for t in (teach_images or [])
        )
    return False


def introduce_outcome(sheet: dict, plan, reply: str, *, teach_images=None):
    """POST-turn introduce-ledger write, gated on introduce-move EVIDENCE.

    Returns (sheet, status, key) with status in ("introduced", "lapsed",
    None) — the STRUCTURED source the typed INTRODUCED / INTRODUCE_LAPSED
    events are minted from (Phase 3 batch 1: the caller no longer re-parses
    a note string). ``mark_introduced_if_visible`` below keeps the
    historical string-returning contract for existing callers/tests.

    The introduction counts (S1 mark + R-H enqueue via
    retrieval_scheduler.mark_introduced — confidence untouched, honesty law
    enforced there) ONLY when the visible reply carries the key AND the
    plan's scaffold evidence (introduce_scaffold_evidence). Key present but
    scaffold absent = the tutor used the word naturally, not as a teaching
    move (2026-07-28 «buenas tardes» incident): the plan lapses — status
    "lapsed", no ledger write, budget unconsumed; the gate's
    first_seen/flood machinery keeps owning natural bare use. Key absent
    entirely → (sheet unchanged, None, None).
    observe.word_present handles single words and MWUs alike (boundary-safe
    containment, same as the due-outcome recorder).
    """
    from .observe import word_present
    from .retrieval_scheduler import mark_introduced

    if plan is None or not word_present(plan.key, reply or ""):
        return sheet, None, None
    if not introduce_scaffold_evidence(plan, reply, teach_images):
        return sheet, "lapsed", plan.key
    updated = mark_introduced(sheet, plan.key, "lexicon", plan.scaffold_type)
    return updated, "introduced", plan.key


def mark_introduced_if_visible(sheet: dict, plan, reply: str, *, teach_images=None):
    """Historical string contract over ``introduce_outcome`` (see there)."""
    sheet, status, key = introduce_outcome(
        sheet, plan, reply, teach_images=teach_images
    )
    if status == "introduced":
        return sheet, render_note(EV.INTRODUCED, key=key)
    if status == "lapsed":
        return sheet, render_note(
            EV.INTRODUCE_LAPSED, key=key, payload={"reason": "no_scaffold"}
        )
    return sheet, None


# --- Close phase soft wiring (PEDAGOGY §1.2, USER-ratified 2026-07-28) ------
# The 1-turn CLOSE phase ends every session plan (tutor/session_phases.py).
# The summary data block rides the same flavorable-turn condition set as
# INTRODUCE (known open / default fallthrough conversation turns); guard and
# repair turns keep their single focus and the freeze rules are unchanged.
def close_summary_block(
    memory_snapshot: dict,
    *,
    resolved_forms=None,
    task_state=None,
) -> str:
    """Compact (≤2 lines) session-summary data for the CLOSE phase.

    Built ONLY from session state the code already tracks — introduced keys
    (pedagogy_memory), error patterns resolved this session (mode_state),
    task status (task_state), skills shown — the summary invents nothing
    (§3 honesty). The model turns this into ONE short English line.
    """
    mem = memory_snapshot or {}
    bits: list[str] = []
    introduced = [
        str(k) for k in (mem.get("introduced_this_session") or []) if k
    ]
    if introduced:
        bits.append("new items introduced: " + ", ".join(introduced))
    resolved = [str(p) for p in (resolved_forms or []) if p]
    if resolved:
        bits.append("errors resolved: " + ", ".join(resolved))
    if task_state is not None and getattr(task_state, "scene_id", ""):
        bits.append(
            f"task {task_state.scene_id}: "
            f"{getattr(task_state, 'status', 'open')}"
        )
    shown = sorted(str(s) for s in (mem.get("shown") or []) if s)
    if shown:
        bits.append("skills shown: " + ", ".join(shown[:6]))
    if not bits:
        bits.append("a first short Spanish exchange")
    return (
        "SESSION SUMMARY (data for your ONE short English close line): "
        + "; ".join(bits) + "."
    )


# --- §2.1a self-flag uptake, instruction path (BINDING, 2026-07-28) ---------
# The REGEX-visible cheap case only (surface-form spotting, legit per §4.2):
# the learner literally marked a token as uncertain (quoted single token or a
# "(english)?" gloss-guess like «uvia (rain)»). MEANING-level detection
# (content_offer) stays with the shadow classifier — no routing change, no
# gate (per docs/reviews-content-uptake-law.md condition (c)).
# Guard turns are excluded: help/topic/grammar guards already perform uptake.
SELF_FLAG_MODES = frozenset({"conversation", "transfer", "cf_recast"})


def self_flag_uptake_block(
    learner: str,
    *,
    mode: str,
    reason: str = "",
    mode_state=None,
) -> tuple[str, str]:
    """(instruction_text, flagged_token) for a §2.1a self-flagged form, or
    ("", "").

    Budget-tracked in ModeSessionState (content_uptake_last_turn): ≤1 per 3
    teaching turns, never consecutive — when exhausted, nothing fires and the
    agenda proceeds (§2.1a anti-starvation clause). Fires only on
    conversation-flavored turns; guard/repair turns keep their single focus.

    Phase 3 batch 2 leaf push-down: returns the RAW token (not the rendered
    "uptake_flagged:<token>" string) — the caller emits the typed
    UPTAKE_FLAGGED TurnEvent whose render is that legacy note.
    """
    from .observe import detect_self_flagged_token

    if mode not in SELF_FLAG_MODES or reason in DUE_GUARD_REASONS:
        return "", ""
    token = detect_self_flagged_token(learner or "")
    if not token:
        return "", ""
    if mode_state is not None and not mode_state.content_uptake_allowed():
        return "", ""
    if mode_state is not None:
        mode_state.note_content_uptake()
    instr = (
        f"UPTAKE (§2.1a): the learner flagged «{token}» as uncertain — give "
        "its correct pack-legal form or nearest pack paraphrase THIS turn "
        "(one model). No ledger introduce, no denylist breach, no side quest."
    )
    return instr, token


# --- Progress journey rail wiring (docs/design-progression-view.md) ---------
# Emit sites append milestone events to the code-owned progress ledger at the
# moment the underlying evidence lands (PEDAGOGY.md §3: the display invents
# nothing). Each site is a thin call; detection + templates live in
# tutor/progress_ledger.py. Dedupe: an up-crossing fires ONCE per (kind, key)
# — checked against the ledger itself (has_milestone / up_keys).
def emit_progress_events(
    events: list[dict],
    *,
    session_id: str,
    ledger_path=None,
    ev_log: TurnEventLog | None = None,
    stage: str = "record",
) -> list[str]:
    """Record pre-validated crossing events; return session-note tags.

    Phase 3 batch 1: when ``ev_log`` is given (the session's per-turn log),
    each recorded crossing also mints a typed PROGRESS_MILESTONE /
    PROGRESS_REGRESSION event; the returned strings are the rendered
    projection (byte-identical to the historical f-strings).
    """
    from . import progress_ledger as pl

    notes: list[str] = []
    for ev in events:
        pl.record_milestone(
            ev["kind"],
            ev["key"],
            ev.get("detail", ""),
            polarity=ev.get("polarity", "up"),
            session_id=session_id,
            item_kind=ev.get("item_kind", ""),
            ledger_path=ledger_path,
        )
        kind = (
            EV.PROGRESS_REGRESSION
            if ev.get("polarity") == "down"
            else EV.PROGRESS_MILESTONE
        )
        key = str(ev["key"])
        payload = {"milestone": str(ev["kind"])}
        if ev_log is not None:
            notes.append(ev_log.emit(kind, key=key, payload=payload,
                                     stage=stage))
        else:
            notes.append(render_note(kind, key=key, payload=payload))
    return notes


# --- Debug request capture (local web debug box, 2026-07-28) ----------------
# Per tutor call: the OUTBOUND request (ordered system blocks, chat history,
# the task message, model) + response metadata (usage incl. thinking/cached,
# gate faults, notes, mode/reason/activity). IN-MEMORY ONLY — a ring buffer
# of the last DEBUG_RING_SIZE calls per session, served by
# GET /api/debug/requests for the web debug box. These payloads are NEVER
# written to disk logs (session .jsonl logging is unchanged).
# DEBUG_RING_SIZE now lives in tutor.session_state (Phase 1 batch 1) and is
# re-exported above for existing importers (tests import it from here).


def _label_system_block(text: str, index: int) -> str:
    """Human label for a system block (marker-based, position fallback)."""
    # The debug entry stores the FULL block text; only the label sniffs a head.
    head = (text or "").lstrip()[:200].lower()  # truncation-ok: label sniffing only, full text kept
    if "course pack palette" in head:
        return "course_pack"
    if "student character sheet" in head or "character sheet" in head:
        return "character_sheet"
    if "tutor persona" in head:
        return "persona"
    if "you are a skilled conversational spanish tutor" in head:
        return "tutor_stance"
    if index == 0:
        return "tutor_stance"
    return f"system_block_{index}"


def _msg_text(content) -> str:
    """Message content as text (tool-use lists rendered as JSON)."""
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(content)


def build_debug_entry(
    *,
    model: str,
    system,
    messages,
    task: str,
    decision_dict: dict | None,
    activity: str | None,
    usage: dict | None,
    gate_result=None,
    notes=None,
    stop_reason: str = "",
    turn: int = 0,
    is_open: bool = False,
) -> dict:
    """One debug ring-buffer entry (JSON-safe; full text, no truncation)."""
    import datetime as _dt

    dec = decision_dict or {}
    u = usage or {}
    history = [
        {"role": str(m.get("role") or ""), "content": _msg_text(m.get("content"))}
        for m in (messages or [])
    ]
    # The final user message IS the task; keep history = everything before it.
    if history and task and history[-1]["content"] == task:
        history = history[:-1]
    gate_faults: list = []
    gate_notes: list = []
    if gate_result is not None:
        gate_faults = list(getattr(gate_result, "faults", None) or [])
        gate_notes = list(getattr(gate_result, "notes", None) or [])
    return {
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
        "turn": int(turn or 0),
        "is_open": bool(is_open),
        "model": model,
        "mode": str(dec.get("mode") or ""),
        "reason": str(dec.get("reason") or ""),
        "activity": str(activity or ""),
        "hard_break": bool(dec.get("hard_break")),
        "instructions": str(dec.get("instructions") or ""),
        "system_blocks": [
            {
                "label": _label_system_block(b.get("text") or "", i),
                "text": str(b.get("text") or ""),
                "cached": bool(b.get("cache_control")),
            }
            for i, b in enumerate(system or [])
            if isinstance(b, dict)
        ],
        "history": history,
        "task_message": task or "",
        "response": {
            "usage": {
                "input_tokens": int(u.get("input_tokens") or 0),
                "output_tokens": int(u.get("output_tokens") or 0),
                "thinking_tokens": int(u.get("thinking_tokens") or 0),
                "cached_input_tokens": int(u.get("cached_input_tokens") or 0),
            },
            "stop_reason": stop_reason or "",
            "gate_faults": gate_faults,
            "gate_notes": gate_notes,
            "notes": list(notes or []),
        },
    }


# --- Session phase layer (Phase 2 pedagogy engine) --------------------------
# The phase clock only advances on turns that CONSUME phase budget.
# comprehension_repair and guard turns freeze it (r6 §4.2 rule 1); cf_recast /
# form_focus / association / transfer are interventions WITHIN a phase and DO
# consume (r6 §4.2 rule 5).
def phase_turn_consumed(mode: str, reason: str) -> bool:
    """Did this mode decision consume phase budget? (code decides, logged)"""
    from .modes import PHASE_FREEZE_REASONS

    if mode == "comprehension_repair":
        return False
    return reason not in PHASE_FREEZE_REASONS


def build_session_phase_state(sheet: dict, pack_dir) -> "PhaseState":
    """Construct the session PhaseState from the loaded sheet + pack topics.

    Code owns the plan (due count, blank flag, affect adaptations); pack topic
    titles are passed in so session_phases stays dependency-free. The
    controller only emits hints — it never calls the model.
    """
    from .corpus import pack_topic_titles
    from .pedagogy_contract import is_blank_learner
    from .retrieval_scheduler import due_items
    from .session_phases import PhaseState, build_phase_plan

    return PhaseState(build_phase_plan(
        sheet,
        due_count=len(due_items(sheet)),
        blank=is_blank_learner(sheet),
        pack_topics=pack_topic_titles(Path(pack_dir)),
    ))


@dataclass
class TurnResult:
    reply: str
    notes: list[str] = field(default_factory=list)
    next_best: dict = field(default_factory=dict)
    skills: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    tool_delta: dict | None = None
    input_mode: str = "text"  # text | speech (for future audio pipeline)
    stop_reason: str = ""
    error: str | None = None
    focus_meta: dict = field(default_factory=dict)
    # Structured multi-part reply (recast / explain / continue / …)
    parts: dict = field(default_factory=dict)
    # Typed turn events (tutor/turn_events.py). Since Phase 3 batch 2 the
    # notes list above IS their chronological projection ([render(e) for e
    # in events], seq order — CHAR-BUG-003 resolved), and to_dict() exposes
    # the serialized timeline (web /api responses; the eval harness records
    # it per turn so evals/conv_checks.py can consume typed events).
    events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reply": self.reply,
            "notes": self.notes,
            "next_best": self.next_best,
            "skills": self.skills,
            "usage": self.usage,
            "tool_delta": self.tool_delta,
            "input_mode": self.input_mode,
            "stop_reason": self.stop_reason,
            "error": self.error,
            "focus_meta": self.focus_meta,
            "parts": self.parts,
            "events": [
                e.as_dict() if hasattr(e, "as_dict") else e
                for e in (self.events or [])
            ],
        }


def _usage_dict(final) -> dict:
    u = getattr(final, "usage", None)
    return {
        "input_tokens": getattr(u, "input_tokens", 0),
        "output_tokens": getattr(u, "output_tokens", 0),
        # Billing extras (0 when the provider doesn't report them):
        # thinking bills at the output rate; cached input at the cache rate.
        "thinking_tokens": getattr(u, "thinking_tokens", 0) or 0,
        "cached_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
    }


def _split_content(final) -> tuple[str, list]:
    texts: list[str] = []
    tools: list = []
    for b in getattr(final, "content", None) or []:
        btype = getattr(b, "type", None)
        if btype == "text":
            t = getattr(b, "text", "") or ""
            if t:
                texts.append(t)
        elif btype == "tool_use":
            tools.append(b)
    return "\n".join(texts).strip(), tools


def _tool_delta_from_blocks(tool_blocks: list) -> dict | None:
    merged: dict = {}
    for b in tool_blocks:
        name = getattr(b, "name", "") or ""
        if name != "update_character_sheet":
            continue
        inp = getattr(b, "input", None) or {}
        if not isinstance(inp, dict):
            continue
        for k, v in inp.items():
            if k in (
                "identity", "affect", "receptive", "next_best", "coverage",
            ) and isinstance(v, dict):
                base = merged.setdefault(k, {})
                if isinstance(base, dict):
                    base.update(v)
                else:
                    merged[k] = v
            elif k in ("skills", "grammar", "lexicon") and isinstance(v, dict):
                base = merged.setdefault(k, {})
                for sk, sv in v.items():
                    if isinstance(sv, dict) and isinstance(base.get(sk), dict):
                        base[sk] = {**base[sk], **sv}
                    else:
                        base[sk] = sv
            else:
                merged[k] = v
    return merged or None


def _assistant_content_blocks(final) -> list[dict]:
    out: list[dict] = []
    for b in getattr(final, "content", None) or []:
        btype = getattr(b, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(b, "text", "") or ""})
        elif btype == "tool_use":
            out.append({
                "type": "tool_use",
                "id": getattr(b, "id", "call_0"),
                "name": getattr(b, "name", ""),
                "input": getattr(b, "input", {}) or {},
            })
    return out


def _call(client, caps, system, messages, *, max_tokens=None, tools=None):
    kwargs = dict(
        model=caps.model,
        max_tokens=max_tokens
        or getattr(config, "TUTOR_MAX_TOKENS", None)
        or config.MAX_TOKENS,
        system=system,
        messages=messages,
    )
    if tools:
        kwargs["tools"] = tools
    final = client.messages.create(**kwargs)
    text, tool_blocks = _split_content(final)
    return final, text, tool_blocks


def tutor_turn(
    client,
    caps,
    system,
    messages,
    *,
    tools=None,
    max_tool_rounds: int = 1,
):
    """One learner-facing turn: text + optional sheet tool delta."""
    total_usage = {
        "input_tokens": 0, "output_tokens": 0,
        "thinking_tokens": 0, "cached_input_tokens": 0,
    }
    all_tool_blocks: list = []
    work_messages = list(messages)
    final = None
    text = ""

    for round_i in range(max_tool_rounds + 1):
        final, text, tool_blocks = _call(
            client, caps, system, work_messages, tools=tools,
        )
        u = _usage_dict(final)
        for k in total_usage:
            total_usage[k] += u.get(k, 0)
        all_tool_blocks.extend(tool_blocks)

        if text or not tool_blocks or round_i >= max_tool_rounds:
            break

        assistant_blocks = _assistant_content_blocks(final)
        result_blocks = []
        for b in tool_blocks:
            result_blocks.append({
                "type": "tool_result",
                "tool_use_id": getattr(b, "id", "call_0"),
                "content": json.dumps({
                    "ok": True,
                    "applied": getattr(b, "name", ""),
                }),
            })
        work_messages = work_messages + [
            {"role": "assistant", "content": assistant_blocks},
            {"role": "user", "content": result_blocks + [{
                "type": "text",
                "text": (
                    "(harness) Sheet update recorded. Now send the "
                    "learner-facing reply only — no JSON, no tool talk."
                ),
            }]},
        ]

    delta = _tool_delta_from_blocks(all_tool_blocks)
    return final, text, delta, total_usage, all_tool_blocks


def _skills_snapshot(sheet: dict) -> dict:
    return {
        k: {"status": v.get("status"), "confidence": v.get("confidence")}
        for k, v in (sheet.get("skills") or {}).items()
    }


def _state_delegate(field_name: str, attr_name: str | None = None) -> property:
    """Thin delegate: session.<attr> ⇄ session.state.<field>.

    Phase 1 batch 1 (docs/reviews-architecture-refactor.md): every
    pre-aggregate attribute keeps its historical name and read/write
    semantics while the value lives on the SessionState aggregate — no call
    site or test changes this batch (Phase 4's pipeline consumes state
    directly). Compatibility escape: tests that build partial sessions via
    ``ConversationalSession.__new__`` (no __init__, so no ``state``) fall
    back to plain instance attributes, exactly the pre-aggregate behavior.
    """
    attr = attr_name or field_name

    def _get(self):
        state = self.__dict__.get("state")
        if state is not None:
            return getattr(state, field_name)
        try:
            return self.__dict__[attr]
        except KeyError:
            raise AttributeError(attr) from None

    def _set(self, value) -> None:
        state = self.__dict__.get("state")
        if state is not None:
            setattr(state, field_name, value)
        else:
            self.__dict__[attr] = value

    return property(_get, _set)


class ConversationalSession:
    """Stateful chat session shared by CLI and web."""

    # --- SessionState delegates (Phase 1 batch 1) ---------------------------
    history = _state_delegate("history")
    messages_for_ui = _state_delegate("messages_for_ui")
    _focus_panel = _state_delegate("focus_panel", "_focus_panel")
    _focus_key = _state_delegate("focus_key", "_focus_key")
    _focus_meta = _state_delegate("focus_meta", "_focus_meta")
    _focus_version = _state_delegate("focus_version", "_focus_version")
    _focus_lock = _state_delegate("focus_lock", "_focus_lock")
    _focus_inflight = _state_delegate("focus_inflight", "_focus_inflight")
    _image_warm_lock = _state_delegate("image_warm_lock", "_image_warm_lock")
    _image_warm_inflight = _state_delegate(
        "image_warm_inflight", "_image_warm_inflight"
    )
    last_plan = _state_delegate("last_plan")
    pedagogy_memory = _state_delegate("pedagogy_memory")
    mode_state = _state_delegate("mode_state")
    phase_state = _state_delegate("phase_state")
    task_state = _state_delegate("task_state")
    last_mode_decision = _state_delegate("last_mode_decision")
    debug_requests = _state_delegate("debug_requests")
    costs = _state_delegate("costs")
    progress_session_id = _state_delegate("progress_session_id")

    def __init__(
        self,
        *,
        model: str | None = None,
        pack_dir: Path | None = None,
        sheet_path: Path | None = None,
        use_tools: bool = True,
        label: str = "chat",
        log: bool = True,
        focus_model: str | None = None,
    ):
        config.load_env()
        self.model = model or config.MODEL
        self.focus_model = (
            focus_model if focus_model is not None else config.FOCUS_MODEL
        )
        self.pack_dir = Path(pack_dir or config.DEFAULT_PACK_DIR)
        self.sheet_path = Path(sheet_path or DEFAULT_SHEET_PATH)
        self.use_tools = use_tools
        self.caps = config.caps_for(self.model)
        self.client = config.make_client_for(self.model)
        self.sheet = load_sheet(self.sheet_path)
        # Personal-data capture is DISABLED (2026-07-28, Patrick: "totally
        # remove saving personal data — get the teaching working first").
        # tutor/learner_profile.py stays on disk as the reference design, but
        # nothing loads, captures, or persists personal facts; the sheet is
        # ability-only. profile_path is kept solely so reset_profile can
        # delete stale files from the earlier capture era.
        from .learner_profile import profile_path_for_sheet
        self.profile: dict = {}
        self.profile_path = profile_path_for_sheet(self.sheet_path)
        # Drop stale "only a few minutes" energy from prior days/sessions
        self.sheet = clear_session_scoped_affect(self.sheet)
        save_sheet(self.sheet_path, self.sheet)
        self.tools = SHEET_TOOLS if use_tools else None
        self.logger: SessionLogger | None = None
        self.teacher_mode = (config.TEACHER_MODE or "planned").strip().lower()
        # E4/E4b deletion (docs/reviews-architecture-refactor.md, 2026-07-28):
        # the TEACHER_MODE=rules PlanCard runtime and the legacy harness were
        # DELETED — both bypassed the output gate, mode runtime, retrieval
        # scheduler and phase clock (a constitution hole reachable only by an
        # env var nothing sets). Planned aliases are the only teacher runtime;
        # anything else is a hard error here, not a silent fallthrough.
        if self.teacher_mode not in config.PLANNED_TEACHER_MODES:
            raise ValueError(
                f"TEACHER_MODE={self.teacher_mode!r} is not supported: the "
                "rules PlanCard runtime and the legacy harness were deleted "
                "(E4/E4b, docs/reviews-architecture-refactor.md, 2026-07-28). "
                f"Use one of {config.PLANNED_TEACHER_MODES} (default: planned)."
            )
        # Aggregate session state (Phase 1 batch 1,
        # docs/reviews-architecture-refactor.md): the five stores
        # (SessionMemory / ModeSessionState / PhaseState / TaskState /
        # SessionCostTracker) + the loose session attributes, constructed
        # exactly as the old inline block did — same helpers, same args,
        # same defaults (the phase-plan inputs below are what
        # build_session_phase_state computed internally). All historical
        # attribute names keep working via the delegate properties defined
        # after __init__.
        from .corpus import pack_topic_titles
        from .pedagogy_contract import is_blank_learner
        from .retrieval_scheduler import due_items

        self.state = SessionState.fresh(
            self.sheet,
            source_label=label,
            pack_topics=pack_topic_titles(Path(self.pack_dir)),
            due_count=len(due_items(self.sheet)),
            blank=is_blank_learner(self.sheet),
        )
        # Association table (Phase 3, r7 S4): loaded once per session. A
        # missing/invalid table disables the introduce router (turns note
        # introduce_table_missing) — never a crash.
        from .association_table import load_association_table
        try:
            self.association_table: dict | None = load_association_table(
                self.pack_dir
            )
        except (FileNotFoundError, ValueError, OSError):
            self.association_table = None
        if log:
            self.logger = SessionLogger(
                arch="conversational",
                label=label,
                meta={
                    "mode": "conversational",
                    "teacher_mode": self.teacher_mode,
                    "model": self.model,
                    "focus_model": self.focus_model,
                    "pack": str(self.pack_dir),
                    "sheet": str(self.sheet_path),
                    "sheet_update": "tool" if use_tools else "rules",
                    "surface": label,
                },
            )
        # Progress journey rail: cluster id for this session's ledger events.
        if self.logger is not None:
            self.progress_session_id = self.logger.session_id
        else:
            import datetime as _dt

            stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.progress_session_id = f"{stamp}-{label}-nolog"

    def _progress_note(
        self,
        kind: str,
        key: str,
        *,
        item_kind: str,
        detail_ctx: dict | None = None,
        polarity: str = "up",
        dedupe: bool = True,
    ) -> list[str]:
        """One milestone at an emit site (ledger-deduped; §3 honesty)."""
        from . import progress_ledger as pl

        try:
            if dedupe and pl.has_milestone(kind, key):
                return []
            return emit_progress_events([{
                "kind": kind,
                "key": key,
                "polarity": polarity,
                "item_kind": item_kind,
                "detail": pl.detail_for(kind, key, **(detail_ctx or {})),
            }], session_id=self.progress_session_id,
                ev_log=session_event_log(self))
        except Exception:
            return []

    def _progress_ladder(self, transition: dict) -> list[str]:
        """Ladder crossings (taking_root / rooted / regression) from one
        record_outcome_ex transition."""
        from . import progress_ledger as pl

        try:
            evs = pl.ladder_crossings(transition, seen=pl.up_keys())
            return emit_progress_events(
                evs, session_id=self.progress_session_id,
                ev_log=session_event_log(self), stage="schedule",
            )
        except Exception:
            return []

    def _progress_sheet_crossings(self, prev_sheet: dict) -> list[str]:
        """Error-recovered + can-do band crossings after process_turn."""
        from . import progress_ledger as pl

        try:
            evs = pl.sheet_crossings(
                prev_sheet, self.sheet, seen=pl.up_keys()
            )
            return emit_progress_events(
                evs, session_id=self.progress_session_id,
                ev_log=session_event_log(self), stage="sheet",
            )
        except Exception:
            return []

    def _topic_nouns(self) -> list[str]:
        """Concept palette for the asked-topic extractor — ONE derivation
        (session_memory.topic_palette) over the SESSION's association table:
        priority tier (incident nouns ciudad/casa lead) then the table's
        content keys.  CHAR-BUG-007 RESOLVED (Phase 5 batch 2): structural
        table keys — pronouns, question words, copulas, numbers, `hay` —
        are grammar infrastructure, not topics, and no longer bind as
        concepts («¿Dónde estás tú?» registers the bare ``location`` frame,
        not ``location:tu``)."""
        from .session_memory import topic_palette

        return topic_palette(self.association_table)

    def _capture_debug_request(
        self,
        *,
        system,
        messages,
        task: str,
        decision_dict: dict | None,
        activity: str | None,
        usage: dict | None,
        gate_result=None,
        notes=None,
        stop_reason: str = "",
        is_open: bool = False,
    ) -> None:
        """Append one entry to the in-memory debug ring buffer (never raises,
        never touches disk)."""
        try:
            self.debug_requests.append(build_debug_entry(
                model=self.model,
                system=system,
                messages=messages,
                task=task,
                decision_dict=decision_dict,
                activity=activity,
                usage=usage,
                gate_result=gate_result,
                notes=notes,
                stop_reason=stop_reason,
                turn=self.pedagogy_memory.turns,
                is_open=is_open,
            ))
        except Exception:
            pass

    def _sheet_for_focus(self) -> dict:
        """Ability sheet for the focus rail (no personal-name injection —
        personal-data capture is disabled)."""
        return dict(self.sheet) if isinstance(self.sheet, dict) else {}

    def _refresh_focus(
        self,
        *,
        learner: str = "",
        tutor_reply: str = "",
        use_ai: bool = True,
    ) -> None:
        """Update cached focus/morphology rail (static and/or AI)."""
        key = focus_cache_key(self.sheet)
        sheet_for_focus = self._sheet_for_focus()
        if self.last_mode_decision:
            sheet_for_focus = {**sheet_for_focus, "_last_mode_decision": self.last_mode_decision}
        panel, meta = enrich_focus_panel(
            sheet_for_focus,
            learner=learner,
            tutor_reply=tutor_reply,
            model=self.focus_model,
            force_static=(
                not use_ai or not focus_model_enabled(self.focus_model)
            ),
        )
        self._note_focus_cost(meta)
        with self._focus_lock:
            self._focus_panel = panel
            self._focus_key = key
            self._focus_meta = meta
            self._focus_version = int(self._focus_version or 0) + 1

    def _note_image_costs(self, teach_images: list | None) -> None:
        """Freshly generated teach images cost real money; cache hits are free.

        Must run after EVERY site that can resolve `miss_generated` (pre-turn
        AI path, post-reply generation, rules/planned path) — the post-reply
        and planned sites shipped untracked (Grok countersign 2026-07-28).
        """
        generated = sum(
            1 for t in (teach_images or [])
            if (t.get("cache") or "") == "miss_generated"
        )
        if not generated:
            return
        self.pedagogy_memory.images_generated += generated
        self.pedagogy_memory.images_declared_generated += sum(
            1 for t in (teach_images or [])
            if (t.get("cache") or "") == "miss_generated"
            and t.get("decision_reason") == "tutor_declared"
        )
        try:
            from .image_gen import image_model

            img_model = image_model()
        except Exception:
            img_model = "gemini-2.5-flash-image"
        self.costs.add_image(img_model, generated)

    def _may_generate_image(self, *, source: str) -> bool:
        """Novel-generation budget check (cache hits are always allowed)."""
        if self.pedagogy_memory.images_generated >= MAX_IMAGE_GENERATIONS_PER_SESSION:
            return False
        if (
            source == "tutor_declared"
            and self.pedagogy_memory.images_declared_generated
            >= MAX_DECLARED_NOVEL_PER_SESSION
        ):
            return False
        return True

    def _schedule_image_warm(
        self,
        concept: str,
        *,
        source: str,
        decision_reason: str = "async_warm",
    ) -> bool:
        """Warm a missed teach-image concept OFF the reply path.

        Latency law (audit (e) 2026-07-28; commits 2d160e0/7275bdc): the
        reply thread never pays image-API RTT. Mirrors _schedule_focus_enrich
        — daemon thread, in-flight dedupe, session caps checked at spawn AND
        inside the worker (_may_generate_image), costs recorded through the
        existing _note_image_costs path when generation completes. The
        in-flight reply is never touched — the image appears on a LATER turn
        via cache hit. Returns True when a warm thread was spawned.
        """
        from .teach_assets import cache_lookup, ensure_asset, generation_ready

        key = (concept or "").strip().lower()
        if not key or cache_lookup(key):
            return False
        if not self._may_generate_image(source=source):
            return False
        if not generation_ready():
            return False
        with self._image_warm_lock:
            if key in self._image_warm_inflight:
                return False
            self._image_warm_inflight.add(key)

        def _work() -> None:
            try:
                if not self._may_generate_image(source=source):
                    return
                hit = ensure_asset(key, generate=True)
                if hit and (hit.get("cache") or "") == "miss_generated":
                    self._note_image_costs([
                        {**hit, "decision_reason": decision_reason}
                    ])
            except Exception:
                pass
            finally:
                with self._image_warm_lock:
                    self._image_warm_inflight.discard(key)

        threading.Thread(
            target=_work, name=f"image-warm-{key}", daemon=True
        ).start()
        return True

    def _note_image_miss(
        self,
        concept: str,
        notes: list[str] | None = None,
        *,
        source: str,
        decision_reason: str,
    ) -> None:
        """Generation-miss visibility + async warm (audit (e) contract).

        Misses are NEVER silent (incident 2026-07-28): the notes say whether
        the session cap, a disabled generator, or the async-warm handoff ate
        the same-turn image. Never generates in-line.

        Phase 3 batch 2: the typed IMAGE_GEN_* event IS the record —
        result.notes is the chronological event projection, so the optional
        ``notes`` accumulator is legacy-caller compatibility only.

        CHAR-BUG-004 RESOLVED (Phase 4 batch 2): ONE miss note per concept
        per turn.  The mode-attach site and the assets_for_ai_turn fallback
        could both decide the SAME concept and double-note it (the
        known_bugs.json entry; duplicate pins regenerated with this fix in
        golden_blank_open/golden_due_turn).  Visibility is unchanged — the
        first note still lands; only the byte-identical repeat is dropped.
        Warm scheduling is unaffected: _schedule_image_warm already dedupes
        in-flight keys, so the skipped second call never did real work.
        """
        sink = notes if notes is not None else []
        ev = session_event_log(self)
        _k = str(concept)
        if any(
            e.key == _k
            for kind in (
                EV.IMAGE_GEN_CAPPED, EV.IMAGE_GEN_DISABLED,
                EV.IMAGE_GEN_ASYNC,
            )
            for e in ev.find(kind)
        ):
            return
        if not self._may_generate_image(source=source):
            sink.append(ev.emit(
                EV.IMAGE_GEN_CAPPED, key=concept, stage="image",
            ))
            return
        from .teach_assets import generation_ready

        if not generation_ready():
            sink.append(ev.emit(
                EV.IMAGE_GEN_DISABLED, key=concept, stage="image",
            ))
            return
        self._schedule_image_warm(
            concept, source=source, decision_reason=decision_reason
        )
        sink.append(ev.emit(EV.IMAGE_GEN_ASYNC, key=concept, stage="image"))

    def _attach_mode_image(
        self, decision, sched_notes: list[str] | None = None
    ) -> list[dict]:
        """Primary attach: mode-requested concept, cache-only on the reply path.

        Audit (e) 2026-07-28: the reply path never generates (latency law) —
        a cache hit attaches same-turn; a miss returns [] instantly, is noted
        visibly (capped/disabled/async), and warms in a daemon thread so the
        image exists on a later turn.
        """
        concept = decision.image_concept
        if not concept:
            return []
        from .teach_assets import ensure_asset

        hit = ensure_asset(concept, generate=False)
        if hit:
            self.pedagogy_memory.note_image(concept)
            return [{
                **hit,
                "decision_reason": f"mode:{decision.mode.value}",
                "visual_score": 1.0,
            }]
        self._note_image_miss(
            concept,
            sched_notes,
            source="mode",
            decision_reason=f"warm:mode:{decision.mode.value}",
        )
        return []

    def _record_due_outcomes(self, learner: str, sigs: set[str]) -> list[str]:
        """Conservative retrieval-outcome recording (clear evidence only).

        Lexicon: due key present in the learner's own turn = success; the
        same key named in a meta_comprehension turn = failure. Grammar: an
        error-pattern resolve mapping onto the due form (with no same-turn
        hit of that pattern) = success. Skills have no per-key surface
        evidence yet — silence records nothing (r6: never guess outcomes).
        """
        from .character_sheet import (
            ERROR_PATTERN_CATALOG,
            detect_error_pattern_hits,
            detect_error_pattern_resolves,
        )
        from .observe import word_present
        from .retrieval_scheduler import due_items, record_outcome_ex

        notes: list[str] = []
        if not (learner or "").strip():
            return notes
        due = due_items(self.sheet, max_due=10)
        if not due:
            return notes
        meta = "meta_comprehension" in set(sigs or ())
        resolves = set(detect_error_pattern_resolves(learner))
        hit_ids = {pid for pid, _ in detect_error_pattern_hits(learner)}
        resolved_forms = {
            (ERROR_PATTERN_CATALOG.get(pid) or {}).get("form_id")
            for pid in (resolves - hit_ids)
        }
        resolved_forms.discard(None)
        ev = session_event_log(self)
        for d in due:
            if d.kind == "lexicon" and word_present(d.key, learner):
                ok = not meta
                self.sheet, tr = record_outcome_ex(self.sheet, d.key, d.kind, ok)
                notes.append(ev.emit(
                    EV.DUE_OUTCOME_SUCCESS if ok else EV.DUE_OUTCOME_FAIL,
                    key=d.key, payload={"kind": d.kind}, stage="schedule",
                ))
                notes.extend(self._progress_ladder(tr))
            elif d.kind == "grammar" and d.key in resolved_forms:
                self.sheet, tr = record_outcome_ex(self.sheet, d.key, d.kind, True)
                notes.append(ev.emit(
                    EV.DUE_OUTCOME_SUCCESS,
                    key=d.key, payload={"kind": d.kind}, stage="schedule",
                ))
                notes.extend(self._progress_ladder(tr))
        return notes

    def _spawn_signal_shadow(self, learner: str, mode: str, reason: str) -> None:
        """LLM intent classifier in SHADOW: parallel to the tutor call (zero
        added latency). Audits routing disagreements to the cost ledger
        (Round-2 promotion metrics) and clears stale comprehension holds so a
        misroute cannot carry into the next turn."""
        from .signal_classifier import classifier_enabled, classify_signals

        if getattr(config, "SIGNAL_CLASSIFIER_BLOCKING", False):
            return  # blocking path already classified pre-routing
        if not classifier_enabled():
            return

        def _work() -> None:
            try:
                clf = classify_signals(learner)
                if clf is None:
                    return
                sigs, meta = clf
                u = meta.get("usage") or {}
                if u.get("input_tokens") or u.get("output_tokens"):
                    self.costs.add_llm(
                        "classifier",
                        str(meta.get("model") or ""),
                        input_tokens=u.get("input_tokens", 0),
                        output_tokens=u.get("output_tokens", 0),
                    )
                from .costs import record_event

                disagree = bool(
                    sigs & {"help_request", "topic_request"}
                    and mode in ("comprehension_repair", "form_focus")
                )
                record_event({
                    "source": self.costs.source,
                    "category": "classifier_shadow",
                    "model": str(meta.get("model") or ""),
                    "signals": sorted(sigs),
                    "routed_mode": mode,
                    "routed_reason": reason,
                    "disagree": disagree,
                    "outcome": meta.get("outcome") or "ok",
                    "usd": 0.0,
                    "priced": True,
                })
                if sigs & {"help_request", "topic_request", "spanish_ok"}:
                    self.pedagogy_memory.clear_comprehension_hold()
            except Exception:
                pass

        threading.Thread(
            target=_work, name="signal-shadow", daemon=True
        ).start()

    def _note_focus_cost(self, meta: dict | None) -> None:
        u = (meta or {}).get("usage") or {}
        if u.get("input_tokens") or u.get("output_tokens"):
            self.costs.add_llm(
                "focus",
                str((meta or {}).get("model") or u.get("model") or self.focus_model),
                input_tokens=u.get("input_tokens", 0),
                output_tokens=u.get("output_tokens", 0),
            )

    def _schedule_focus_enrich(
        self,
        *,
        learner: str = "",
        tutor_reply: str = "",
        force_ai: bool = False,
    ) -> None:
        """Static rail now; optional FOCUS_MODEL in a background thread.

        Conversation latency must not wait on the side rail. Client can
        poll GET /api/sheet and re-render when focus_version bumps.
        """
        # Always paint static immediately
        self._refresh_focus(
            learner=learner,
            tutor_reply=tutor_reply,
            use_ai=False,
        )
        if not focus_model_enabled(self.focus_model):
            return
        if getattr(config, "FOCUS_BLOCKING", False):
            # Rare: wait for AI rail (slow path for debugging)
            self._refresh_focus(
                learner=learner,
                tutor_reply=tutor_reply,
                use_ai=True,
            )
            return
        if not getattr(config, "FOCUS_ASYNC", True) and not force_ai:
            return
        with self._focus_lock:
            if self._focus_inflight:
                return
            self._focus_inflight = True
        # Snapshot for the worker (avoid racing sheet mutations)
        sheet_snap = self._sheet_for_focus()
        model = self.focus_model
        key = focus_cache_key(self.sheet)

        def _work() -> None:
            try:
                snap = dict(sheet_snap) if isinstance(sheet_snap, dict) else {}
                if self.last_mode_decision:
                    snap = {**snap, "_last_mode_decision": self.last_mode_decision}
                panel, meta = enrich_focus_panel(
                    snap,
                    learner=learner,
                    tutor_reply=tutor_reply,
                    model=model,
                    force_static=False,
                )
                self._note_focus_cost(meta)
                with self._focus_lock:
                    # Only apply if still relevant to this stretch
                    if self._focus_key == key or not self._focus_key:
                        self._focus_panel = panel
                        self._focus_key = key
                        self._focus_meta = meta
                        self._focus_version = int(self._focus_version or 0) + 1
            except Exception:
                pass
            finally:
                with self._focus_lock:
                    self._focus_inflight = False

        threading.Thread(
            target=_work, name="focus-enrich", daemon=True
        ).start()

    def _finish(
        self,
        learner: str,
        raw: str,
        tool_delta: dict | None,
        final,
        usage: dict,
        *,
        input_mode: str = "text",
        log_learner: str | None = None,
        refresh_focus: bool = True,
        is_open: bool = False,
        skip_log: bool = False,
    ) -> TurnResult:
        # Strip legacy sheet_delta, then parse multi-part tutor structure
        stripped, _ = extract_sheet_delta(raw if raw else "")
        if not stripped:
            stripped = raw or ""
        visible, tutor_parts = process_tutor_raw(stripped)
        parts_dict = tutor_parts.as_dict()
        composed = visible  # keep structured composition as learner-facing text

        if usage:
            self.costs.add_llm(
                "tutor",
                self.model,
                input_tokens=(usage or {}).get("input_tokens", 0),
                output_tokens=(usage or {}).get("output_tokens", 0),
                thinking_tokens=(usage or {}).get("thinking_tokens", 0),
                cached_input_tokens=(usage or {}).get("cached_input_tokens", 0),
            )

        # Progress rail: band snapshot BEFORE sheet maintenance so error /
        # can-do crossings this turn are change-gated (no seeded-sheet floods).
        _prog_prev = {
            "skills": json.loads(json.dumps(self.sheet.get("skills") or {})),
            "error_patterns": json.loads(
                json.dumps(self.sheet.get("error_patterns") or {})
            ),
        }
        sheet_events: list = []
        self.sheet, _sheet_visible, notes = process_turn(
            self.sheet,
            learner,
            composed,
            tool_delta=tool_delta if self.use_tools else None,
            event_sink=sheet_events,
        )
        visible = composed or _sheet_visible or compose_if_needed(tutor_parts)
        # CHAR-BUG-001 RESOLVED (Phase 4 batch 4): _finish's historical
        # mid-turn save_sheet is gone — _finish has exactly one caller (the
        # turn pipeline's stage_finish) and the turn's single durable
        # persist is stage_sheet_commit at the end of the recorder family.
        # Typed leaf emission (Phase 3 batch 2 push-down): character_sheet
        # mints (kind, key, payload) triples natively; emit them — the render
        # is byte-identical to the returned strings. absorb() stays ONLY as
        # the safety net for an un-typed emitter (e.g. a test fake replacing
        # process_turn) — golden runs must never hit it (contract-tested).
        ev = session_event_log(self)
        if len(sheet_events) == len(notes):
            notes = [
                ev.emit(kind, key=key, payload=payload, stage="sheet")
                for kind, key, payload in sheet_events
            ]
        else:  # safety net: strings without triples — classify at the bus
            notes = [ev.absorb(n, stage="sheet") for n in notes]
        notes = list(notes) + self._progress_sheet_crossings(_prog_prev)
        if refresh_focus:
            # Static rail immediately; FOCUS_MODEL enriches async (non-blocking)
            self._schedule_focus_enrich(
                learner=learner,
                tutor_reply=visible,
            )
            notes = list(notes) + [ev.emit(EV.FOCUS_ASYNC, stage="sheet")]
        if tutor_parts.has_recast() and "recast" not in notes:
            notes = list(notes) + [ev.emit(EV.RECAST, stage="sheet")]
        if parts_dict.get("structured"):
            notes = list(notes) + [ev.emit(EV.STRUCTURED_REPLY, stage="sheet")]

        # Durable pedagogy contract (code-enforced, not prompt-only)
        ped = evaluate_turn(
            parts_dict,
            is_open=is_open,
            structured=bool(parts_dict.get("structured")),
            visible=visible,
        )
        # Typed leaf emission (Phase 3 batch 2 push-down): pedagogy_contract
        # carries the bare note_keys; the PEDAGOGY render is "pedagogy:"+key.
        # absorb() only as the safety net for a keyless (test-built) check.
        if len(getattr(ped, "note_keys", []) or []) == len(ped.notes):
            notes = list(notes) + [
                ev.emit(EV.PEDAGOGY, key=k, stage="contract")
                for k in ped.note_keys
            ]
        else:  # safety net
            notes = list(notes) + [
                ev.absorb(n, stage="contract") for n in ped.notes
            ]
        parts_dict = {**parts_dict, "pedagogy": ped.as_dict()}

        result = TurnResult(
            reply=visible,
            notes=notes,
            next_best=dict(self.sheet.get("next_best") or {}),
            skills=_skills_snapshot(self.sheet),
            usage=usage,
            tool_delta=tool_delta,
            input_mode=input_mode,
            stop_reason=getattr(final, "stop_reason", "") or "",
            focus_meta=dict(self._focus_meta or {}),
            parts=parts_dict,
        )
        # Typed event log rides the result (Phase 3 batch 1). Alias, not
        # copy: emitters that run after _finish (introduce ledger, gate tail,
        # asked-topic registry, tail summary) land in the same list.
        result.events = ev.events
        # Mode runtime attaches plan/mode/images *after* finish — log then.
        if self.logger and not skip_log:
            self._log_turn_result(
                result,
                log_learner=log_learner if log_learner is not None else learner,
            )
        return result

    def _commit_sheet(self) -> None:
        """THE atomic-turn commit point (CHAR-BUG-001 RESOLVED — Phase 4
        batch 4 declared delta, Grok amendment (a)): one durable sheet
        persist per successful turn, called by stage_sheet_commit after
        every recorder stage has written its fields into the in-memory
        sheet.  Crash semantics: the turn commits or it doesn't — a crash
        mid-turn leaves the previous turn's sheet on disk, never a
        half-written turn.  Uses the module ``save_sheet`` binding so the
        characterization harness's save-call recorder keeps its seam."""
        save_sheet(self.sheet_path, self.sheet)

    def _log_turn_result(
        self,
        result: TurnResult,
        *,
        log_learner: str = "",
    ) -> None:
        """Write session log with final parts (mode/plan/gate/images included)."""
        if not self.logger:
            return
        parts = result.parts or {}
        self.logger.log_simple_turn(
            learner=log_learner,
            visible=result.reply,
            state={
                "next_best": result.next_best,
                "skills": result.skills,
                "notes": list(result.notes or []),
                "input_mode": result.input_mode,
                "focus_source": (result.focus_meta or {}).get("source")
                or (self._focus_meta or {}).get("source"),
                "parts": parts,
                "pedagogy": parts.get("pedagogy") or result.__dict__.get("pedagogy"),
                "mode": parts.get("mode"),
                "plan": parts.get("plan"),
            },
            stop_reason=result.stop_reason,
            usage=result.usage,
            extra={
                "sheet_notes": list(result.notes or []),
                "tool_delta": result.tool_delta,
                "focus_meta": result.focus_meta or self._focus_meta,
                "parts": parts,
                "pedagogy": parts.get("pedagogy"),
                "mode": parts.get("mode"),
                "mode_decision": parts.get("mode_decision"),
                "plan": parts.get("plan"),
                "output_gate": parts.get("output_gate"),
                "teach_images": parts.get("teach_images"),
            },
        )

    def _execute_planned(
        self,
        learner: str,
        *,
        is_open: bool,
        input_mode: str = "text",
        log_learner: str | None = None,
    ) -> TurnResult:
        """AI tutor with sheet + memory + pedagogy direction — the ONLY
        teacher runtime (E4/E4b deletion 2026-07-28,
        docs/reviews-architecture-refactor.md: the TEACHER_MODE=rules
        PlanCard ladder and the legacy harness were deleted; TEACHER_MODE
        validates to planned aliases at session construction)."""
        return self._execute_ai_tutor(
            learner,
            is_open=is_open,
            input_mode=input_mode,
            log_learner=log_learner,
        )

    def _execute_ai_tutor(
        self,
        learner: str,
        *,
        is_open: bool,
        input_mode: str = "text",
        log_learner: str | None = None,
    ) -> TurnResult:
        """Code selects mode; AI realizes; gate verifies; sheet hard-updates.

        Phase 4 CLOSED (docs/reviews-architecture-refactor.md): every
        region runs as named stages over a TurnContext — the stage tuples
        in tutor/turn_pipeline.py ARE the documentation.  Executor order:
        PRE_MODEL_STAGES → stage_contributors → stage_phase_tick (its
        verified real site: AFTER the contributors) → REALIZE_STAGES (a
        provider exception becomes ctx.error_result, returned immediately)
        → the GATE_REPAIR_STAGES trio (context build outside the historical
        try/except; any gate exception emits OUTPUT_GATE_ERROR and the turn
        proceeds ungated) → RECORDER_STAGES (incl. the atomic sheet commit)
        → CAPTURE_LOG_STAGES.
        """
        ev = begin_turn_log(self)
        from .turn_pipeline import (
            CAPTURE_LOG_STAGES,
            PRE_MODEL_STAGES,
            REALIZE_STAGES,
            RECORDER_STAGES,
            TurnContext,
            stage_contributors,
            stage_gate_check,
            stage_gate_context,
            stage_gate_repair,
            stage_phase_tick,
        )

        ctx = TurnContext(
            learner=learner,
            is_open=is_open,
            ev=ev,
            input_mode=input_mode,
            log_learner=log_learner,
        )
        for _stage in PRE_MODEL_STAGES:
            _stage(self, ctx)
        stage_contributors(self, ctx)
        stage_phase_tick(self, ctx)
        for _stage in REALIZE_STAGES:
            _stage(self, ctx)
        if ctx.error_result is not None:
            return ctx.error_result
        stage_gate_context(self, ctx)
        try:
            stage_gate_check(self, ctx)
            stage_gate_repair(self, ctx)
        except Exception as ge:
            ev.emit(
                EV.OUTPUT_GATE_ERROR, key=type(ge).__name__, stage="gate",
            )
        for _stage in RECORDER_STAGES:
            _stage(self, ctx)
        for _stage in CAPTURE_LOG_STAGES:
            _stage(self, ctx)
        return ctx.result

    def open_session(self) -> TurnResult:
        """Opening tutor turn (AI tutor path — the only teacher runtime)."""
        # Reload sheet so wipe/reset is visible before we choose open phase
        try:
            self.sheet = load_sheet(self.sheet_path)
            self.sheet = clear_session_scoped_affect(self.sheet)
        except Exception:
            pass

        # Unified new-chat reset (Phase 1 batch 2, docs/reviews-architecture-
        # refactor.md): EVERY session-scoped store resets — memory, mode
        # cooldowns/asked topics, phase clock (rebuilt from the CURRENT
        # sheet), task state, debug ring, focus fields, last_* — closing the
        # cross-chat leak. Costs continuity ruling: the per-chat tracker
        # resets too (the header shows THIS chat's spend); the on-disk cost
        # ledger keeps the money history. The sheet itself and
        # progress_session_id are untouched.
        self.state.reset("new_chat", sheet=self.sheet)

        # New chat ≠ new learner: seed session memory from durable sheet
        try:
            self.pedagogy_memory.seed_from_sheet(self.sheet, self.profile)
        except Exception:
            pass

        result = self._execute_planned(
            "", is_open=True, log_learner="(session open)",
        )
        if result.error:
            return result
        self.history = [
            {"role": "user", "content": "(session open)"},
            {"role": "assistant", "content": result.reply},
        ]
        self.messages_for_ui = [
            {
                "role": "tutor",
                "content": result.reply,
                "input_mode": "text",
                "parts": result.parts,
            },
        ]
        return result

    def user_turn(
        self,
        text: str,
        *,
        input_mode: str = "text",
    ) -> TurnResult:
        """Learner message → tutor reply + sheet update."""
        text = (text or "").strip()
        if not text:
            return TurnResult(reply="", error="empty message")

        result = self._execute_planned(
            text, is_open=False, input_mode=input_mode,
        )
        if result.error:
            return result
        # Keep FULL session history (do not silently drop older turns)
        self.history = self.history + [
            {"role": "user", "content": text},
            {"role": "assistant", "content": result.reply},
        ]
        self.messages_for_ui.append(
            {"role": "you", "content": text, "input_mode": input_mode})
        self.messages_for_ui.append({
            "role": "tutor",
            "content": result.reply,
            "input_mode": "text",
            "parts": result.parts,
        })
        return result

    def reset_profile(self) -> dict:
        """Delete any personal-data file left over from the capture era.

        Capture itself is disabled — this only cleans up stale
        learner_profile.json files on disk. Spanish progress (the character
        sheet) is untouched.
        """
        self.profile = {}
        try:
            if self.profile_path.exists():
                self.profile_path.unlink()
        except OSError:
            pass
        return self.profile

    def reset_sheet(self) -> dict:
        """Hard wipe of Spanish PROGRESS: new blank ability sheet + a full
        unified session-state reset (Phase 1 batch 2 kind "sheet_reset").
        (Personal data is no longer stored at all, so there is nothing else
        to keep or clear.)

        Deletes the sheet file first so nothing can merge residual state back in.
        """
        try:
            if self.sheet_path.exists():
                self.sheet_path.unlink()
        except OSError:
            pass
        self.sheet = default_sheet()
        self.sheet_path.parent.mkdir(parents=True, exist_ok=True)
        save_sheet(self.sheet_path, self.sheet)
        # Progress-ledger learner epoch (batch-2 declared delta 3): rotate
        # the DEDUPE scope so the fresh learner re-earns milestones instead
        # of being suppressed by the previous learner's history. Nothing is
        # retracted — the old milestones were genuinely earned and stay
        # displayable; the epoch row is the visible boundary. Best-effort:
        # ledger trouble must never break a reset.
        try:
            from . import progress_ledger as pl

            pl.record_epoch(session_id=self.progress_session_id)
        except Exception:
            pass
        # Unified reset (batch 2): the batch-1 twelve stores + the four
        # misses (costs, focus_version, focus_inflight, image_warm_inflight).
        # The on-disk COST ledger is append-only forever (continuity ruling).
        self.state.reset("sheet_reset", sheet=self.sheet)
        return self.sheet

    def sheet_human(self) -> str:
        return format_sheet_human(self.sheet)

    def sheet_public(self) -> dict:
        """JSON-safe sheet view for the web UI (includes focus rail cards)."""
        # Rebuild live mode titles every paint (cheap). Morph enrich may linger
        # from async FOCUS_MODEL but must not hide the real this-turn mode.
        try:
            live_panel = build_focus_panel(
                self._sheet_for_focus(),
                mode_decision=self.last_mode_decision,
            )
        except Exception:
            live_panel = None

        if self._focus_panel is None:
            try:
                self._refresh_focus(use_ai=False)
            except Exception:
                self._focus_panel = live_panel or build_focus_panel(self._sheet_for_focus())
                self._focus_meta = {"source": "live_mode"}

        panel = self._focus_panel or live_panel or build_focus_panel(self._sheet_for_focus())
        if live_panel and isinstance(panel, dict) and isinstance(live_panel, dict):
            merged = dict(panel)
            live_f = live_panel.get("focus") or {}
            old_f = dict(merged.get("focus") or {})
            old_f.update({
                k: live_f[k]
                for k in (
                    "live", "mode", "mode_reason", "hard_break", "title",
                    "activity", "why", "image_concept", "can_do",
                    "sheet_title", "sheet_activity", "sheet_reason",
                    "primary_is_form", "error_focus", "form_focus",
                    "error_pattern", "avoid", "skill_status",
                    "skill_confidence", "learner_name", "scaffold",
                )
                if k in live_f
            })
            # Prefer live blurb only if enrich didn't set one for this mode
            if live_f.get("why") and not old_f.get("blurb"):
                old_f["why"] = live_f["why"]
            merged["focus"] = old_f
            if live_panel.get("morphology"):
                merged["morphology"] = live_panel["morphology"]
            panel = merged

        focus = panel.get("focus") if isinstance(panel, dict) else {}
        morph = panel.get("morphology") if isinstance(panel, dict) else []
        lex = panel.get("lexicon_focus") if isinstance(panel, dict) else []
        from .costs import ledger_report

        try:
            today = ledger_report(days=1)
            today_usd = 0.0
            if today.get("days"):
                today_usd = list(today["days"].values())[-1].get("usd", 0.0)
        except Exception:
            today_usd = 0.0
        return {
            # UI compat shim: identity is always empty — personal-data
            # capture is disabled; the ability sheet never stores identity.
            "identity": {"preferred_name": None},
            "session_cost": {**self.costs.summary(), "today_usd": today_usd},
            "skills": self.sheet.get("skills"),
            "grammar": {
                k: {kk: vv for kk, vv in (v or {}).items() if kk != "evidence"}
                for k, v in (self.sheet.get("grammar") or {}).items()
            },
            "affect": self.sheet.get("affect"),
            "receptive": self.sheet.get("receptive"),
            "coverage": self.sheet.get("coverage"),
            "next_best": self.sheet.get("next_best"),
            "lexicon": dict(self.sheet.get("lexicon") or {}),
            "updated_at": self.sheet.get("updated_at"),
            "human": format_sheet_human(self.sheet),
            "focus": focus or {},
            "morphology": morph or [],
            "lexicon_focus": lex or [],
            "error_patterns": self.sheet.get("error_patterns") or {},
            "error_patterns_active": (
                panel.get("error_patterns_active")
                if isinstance(panel, dict) else []
            ) or [],
            "focus_source": (panel.get("source") if isinstance(panel, dict) else None)
            or (self._focus_meta or {}).get("source")
            or "static",
            "focus_model": self.focus_model,
            "focus_version": int(getattr(self, "_focus_version", 0) or 0),
            "focus_pending": bool(getattr(self, "_focus_inflight", False)),
            "score": compute_progress_score(self.sheet),
        }

    def close(self, *, persist_sheet: bool = True) -> str | None:
        """End session. If persist_sheet is False (hard reset), do not write sheet."""
        if persist_sheet:
            save_sheet(self.sheet_path, self.sheet)
        if self.logger:
            return str(self.logger.close(mode="conversational"))
        return None
