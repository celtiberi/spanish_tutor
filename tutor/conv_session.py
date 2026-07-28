"""Reusable conversational Spanish session (CLI + web).

Sheet = learner context; tool call update_character_sheet keeps it current.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from . import config
from .can_dos import build_focus_panel
from .character_sheet import (
    UPDATE_CHARACTER_SHEET_TOOL,
    clear_session_scoped_affect,
    compute_progress_score,
    default_sheet,
    extract_sheet_delta,
    format_sheet_for_prompt,
    format_sheet_human,
    load_sheet,
    process_turn,
    save_sheet,
)
from .corpus import load_pack
from .focus_enrich import enrich_focus_panel, focus_cache_key, focus_model_enabled
from .session_log import SessionLogger
from .pedagogy_contract import evaluate_turn
from .tutor_response import compose_visible, process_tutor_raw


def compose_if_needed(parts) -> str:
    return compose_visible(parts)

CONV_PROMPT = config.REPO_ROOT / "prompts" / "conversational_tutor.md"
DEFAULT_SHEET_PATH = config.CHARACTER_SHEET_PATH
SHEET_TOOLS = [UPDATE_CHARACTER_SHEET_TOOL]

# Per-session image-generation ceilings (novel images bill ~$0.039 each;
# cache hits are free). 8×$0.039=$0.312 hard session ceiling; the tutor-
# declared subset caps at 5×=$0.195 so model freestyle (verbs/phrases/ideas
# are all allowed) stays budget-bounded without an allowlist.
# Grok countersign 2026-07-28: a cap is a control, tracking alone is not.
MAX_IMAGE_GENERATIONS_PER_SESSION = 8
MAX_DECLARED_NOVEL_PER_SESSION = 5

# Known learner: sheet has evidence — still teach, but can go a bit faster
OPEN_HARNESS_KNOWN = (
    "(harness) Open a TEACHING session for a learner we already have evidence on. "
    "Use the character sheet (next_best / form_focus / scaffold / name). "
    "OPEN RECIPE: short warm open → <model> 1–2 targets → <try> one production. "
    "Do NOT dump a long Spanish monologue. Do NOT fake 'Got it' with no learner line. "
    "Skip leave-taking and multi-question stacks. "
    "LANGUAGE: Spanish-forward; English only if scaffold still true. "
    "Use structured <tutor> parts (model + try required). "
    "Do not emit sheet JSON. The app updates the learner sheet."
)

# Blank / wiped sheet: DIAGNOSTIC feel-out — we do not know their level
OPEN_HARNESS_DIAGNOSTIC = (
    "(harness) DIAGNOSTIC OPEN — character sheet is EMPTY / all can-dos unknown. "
    "You do NOT know this learner's ability. Do NOT open like an intermediate chat. "
    "Do NOT pure-Spanish monologue. Do NOT say 'cuéntame cómo va todo' or long "
    "unmodeled questions. Do NOT invent that you 'know' them. "
    "GOAL OF THIS TURN: feel-out / placement probe + first teach move. "
    "OPEN RECIPE (required): "
    "(1) 1–2 short English sentences: who you are + that you'll start tiny "
    "to see what they already know; "
    "(2) <model> only 2 ultra-short Spanish forms they can copy: "
    "**Hola.** and **Estoy bien.**; "
    "(3) <try> ONE easy production: say **Hola** — or try **Estoy bien** if they can. "
    "Optional: one plain English gloss only on the try line (not dual-subtitle walls). "
    "Keep the whole turn SHORT (TTS will speak it). "
    "No <acknowledge> pretending they already spoke. "
    "Use structured <tutor> tags. Skip sheet tools on open."
)


def open_harness_for_sheet(sheet: dict) -> str:
    from .pedagogy_contract import open_phase

    if open_phase(sheet) == "diagnostic":
        return OPEN_HARNESS_DIAGNOSTIC
    return OPEN_HARNESS_KNOWN


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


def mark_introduced_if_visible(sheet: dict, plan, reply: str):
    """POST-turn introduce-ledger write, gated on the VISIBLE reply.

    Only when the tutor's visible reply actually carries the key does the
    introduction count: S1 mark + R-H enqueue via
    retrieval_scheduler.mark_introduced (confidence untouched — honesty law
    enforced there). A reply without the key lets the plan lapse: returns
    (sheet unchanged, None) and the session budget is not consumed.
    observe.word_present handles single words and MWUs alike (boundary-safe
    containment, same as the due-outcome recorder).
    """
    from .observe import word_present
    from .retrieval_scheduler import mark_introduced

    if plan is None or not word_present(plan.key, reply or ""):
        return sheet, None
    updated = mark_introduced(sheet, plan.key, "lexicon", plan.scaffold_type)
    return updated, f"introduced:{plan.key}"


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
    """(instruction_text, note) for a §2.1a self-flagged form, or ("", "").

    Budget-tracked in ModeSessionState (content_uptake_last_turn): ≤1 per 3
    teaching turns, never consecutive — when exhausted, nothing fires and the
    agenda proceeds (§2.1a anti-starvation clause). Fires only on
    conversation-flavored turns; guard/repair turns keep their single focus.
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
    return instr, f"uptake_flagged:{token}"


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
) -> list[str]:
    """Record pre-validated crossing events; return session-note tags."""
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
        tag = (
            "progress_regression"
            if ev.get("polarity") == "down"
            else "progress_milestone"
        )
        notes.append(f"{tag}:{ev['kind']}:{ev['key']}")
    return notes


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


# Back-compat name
OPEN_HARNESS = OPEN_HARNESS_DIAGNOSTIC


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
        }


def build_conversational_system(pack_dir: Path, sheet: dict) -> list[dict]:
    """Sheet = context about the learner; pack = legal language palette."""
    from .character_sheet import active_error_patterns, now_iso

    stance = CONV_PROMPT.read_text()
    pack = load_pack(pack_dir)
    sheet_txt = format_sheet_for_prompt(sheet)
    now = now_iso()
    active = active_error_patterns(sheet)
    err_block = ""
    if active:
        lines = [
            "# ACTIVE ERROR PATTERNS (priority — do not ignore)",
            "These constructions keep failing. Recast + weave practice THIS turn "
            "before chasing a brand-new stretch.",
        ]
        for ep in active:
            lines.append(
                f"- {ep['id']} ×{ep['count']}: {ep['label']} "
                f"(last_seen={ep.get('last_seen')}) "
                f"examples={ep.get('last_examples')}"
            )
            if ep.get("teach_hint"):
                lines.append(f"  teach: {ep['teach_hint']}")
        err_block = "\n".join(lines) + "\n\n"
    return [
        {
            "type": "text",
            "text": (
                stance
                + f"\n\n# Clock\nCurrent local date/time: **{now}**\n"
                + "Use this to interpret last_seen / updated_at on the sheet "
                + "(e.g. yesterday vs today).\n\n"
                + err_block
                + "# Student character sheet (YOUR model of this learner)\n"
                + "Use this to choose Spanish level, scaffolding, and what to "
                + "weave in next. Do not ignore next_best / avoid / "
                + "active error patterns.\n\n"
                + (
                    "**BLANK LEARNER:** all can-dos unknown — still in feel-out / "
                    "placement. Keep models tiny; English frame OK; do not assume "
                    "intermediate comprehension.\n\n"
                    if _sheet_looks_blank(sheet)
                    else ""
                )
                + "The app updates the sheet from dialogue. Do NOT paste sheet "
                + "JSON, tool payloads, or can-do codes into the learner reply.\n\n"
                + sheet_txt
            ),
        },
        {
            "type": "text",
            "text": "# Course pack palette (in-scope inventory + denylist)\n\n"
                    + pack,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _sheet_looks_blank(sheet: dict) -> bool:
    from .pedagogy_contract import is_blank_learner

    return is_blank_learner(sheet)


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


class ConversationalSession:
    """Stateful chat session shared by CLI and web."""

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
        self.history: list[dict] = []
        self.tools = SHEET_TOOLS if use_tools else None
        self.messages_for_ui: list[dict] = []  # learner-visible only
        self._focus_panel: dict | None = None
        self._focus_key: str | None = None
        self._focus_meta: dict = {"source": "static"}
        self._focus_version: int = 0
        self._focus_lock = threading.Lock()
        self._focus_inflight = False
        self.logger: SessionLogger | None = None
        self.teacher_mode = (config.TEACHER_MODE or "planned").strip().lower()
        self.last_plan: dict | None = None
        from .session_memory import SessionMemory
        from .modes import ModeSessionState
        self.pedagogy_memory = SessionMemory()
        self.mode_state = ModeSessionState()
        # Session phase plan (Phase 2): built once from the loaded sheet.
        self.phase_state = build_session_phase_state(self.sheet, self.pack_dir)
        # ConvergentTaskRuntime state (Phase 5, r6 Rank-4): bound to the
        # first task-capable open scene on the first task-phase turn;
        # session-scoped, persists across turns until done.
        self.task_state = None
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
        self.last_mode_decision: dict | None = None
        from .costs import SessionCostTracker
        self.costs = SessionCostTracker(source=label)
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
            }], session_id=self.progress_session_id)
        except Exception:
            return []

    def _progress_ladder(self, transition: dict) -> list[str]:
        """Ladder crossings (taking_root / rooted / regression) from one
        record_outcome_ex transition."""
        from . import progress_ledger as pl

        try:
            evs = pl.ladder_crossings(transition, seen=pl.up_keys())
            return emit_progress_events(
                evs, session_id=self.progress_session_id
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
                evs, session_id=self.progress_session_id
            )
        except Exception:
            return []

    @property
    def system(self) -> list[dict]:
        return build_conversational_system(self.pack_dir, self.sheet)

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

    def _attach_mode_image(self, decision, sched_notes: list[str]) -> list[dict]:
        """Primary attach: mode-requested concept via ensure_asset (cap-gated).

        Same-turn: hit cache or generate (never "only if we pre-seeded it");
        novel generation respects the session budget cap. Misses are NEVER
        silent (incident 2026-07-28: the pipeline looked generation-dead
        because mode-path misses left no note): the notes say whether the
        session cap, a disabled generator, or a generation failure ate the
        image.
        """
        concept = decision.image_concept
        if not concept:
            return []
        from .teach_assets import ensure_asset, generation_ready

        may_gen = self._may_generate_image(source="mode")
        hit = ensure_asset(concept, generate=may_gen)
        if hit:
            self.pedagogy_memory.note_image(concept)
            return [{
                **hit,
                "decision_reason": f"mode:{decision.mode.value}",
                "visual_score": 1.0,
            }]
        if not may_gen:
            sched_notes.append(f"image_gen_capped:{concept}")
        elif not generation_ready():
            sched_notes.append(f"image_gen_disabled:{concept}")
        else:
            sched_notes.append(f"image_gen_failed:{concept}")
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
        for d in due:
            if d.kind == "lexicon" and word_present(d.key, learner):
                ok = not meta
                self.sheet, tr = record_outcome_ex(self.sheet, d.key, d.kind, ok)
                notes.append(
                    f"due_outcome_{'success' if ok else 'fail'}:{d.key}"
                )
                notes.extend(self._progress_ladder(tr))
            elif d.kind == "grammar" and d.key in resolved_forms:
                self.sheet, tr = record_outcome_ex(self.sheet, d.key, d.kind, True)
                notes.append(f"due_outcome_success:{d.key}")
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
        self.sheet, _sheet_visible, notes = process_turn(
            self.sheet,
            learner,
            composed,
            tool_delta=tool_delta if self.use_tools else None,
        )
        visible = composed or _sheet_visible or compose_if_needed(tutor_parts)
        save_sheet(self.sheet_path, self.sheet)
        notes = list(notes) + self._progress_sheet_crossings(_prog_prev)
        if refresh_focus:
            # Static rail immediately; FOCUS_MODEL enriches async (non-blocking)
            self._schedule_focus_enrich(
                learner=learner,
                tutor_reply=visible,
            )
            notes = list(notes) + ["focus_async"]
        if tutor_parts.has_recast() and "recast" not in notes:
            notes = list(notes) + ["recast"]
        if parts_dict.get("structured"):
            notes = list(notes) + ["structured_reply"]

        # Durable pedagogy contract (code-enforced, not prompt-only)
        ped = evaluate_turn(
            parts_dict,
            is_open=is_open,
            structured=bool(parts_dict.get("structured")),
            visible=visible,
        )
        notes = list(notes) + list(ped.notes)
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
        # Mode runtime attaches plan/mode/images *after* finish — log then.
        if self.logger and not skip_log:
            self._log_turn_result(
                result,
                log_learner=log_learner if log_learner is not None else learner,
            )
        return result

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

    def _planned_enabled(self) -> bool:
        # planned / plan / new / ai = AI-first tutor (default)
        # rules = optional PlanCard ladder (not recommended for product)
        return self.teacher_mode in ("planned", "plan", "new", "ai", "rules")

    def _rules_mode(self) -> bool:
        return self.teacher_mode == "rules"

    def _execute_planned(
        self,
        learner: str,
        *,
        is_open: bool,
        input_mode: str = "text",
        log_learner: str | None = None,
    ) -> TurnResult:
        """Default: AI tutor with sheet + memory + pedagogy direction.

        TEACHER_MODE=rules → old PlanCard ladder (optional / experiments).
        """
        if self._rules_mode():
            return self._execute_rules_planned(
                learner,
                is_open=is_open,
                input_mode=input_mode,
                log_learner=log_learner,
            )
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
        """Code selects mode; AI realizes; gate verifies; sheet hard-updates."""
        from .executor import build_ai_tutor_system, build_ai_tutor_user_message
        from .modes import Mode, select_mode
        from .observe import build_observations
        from .pedagogy_contract import (
            NOTE_DIAGNOSTIC_OPEN,
            NOTE_KNOWN_LEARNER_OPEN,
            is_blank_learner,
            open_phase,
        )
        from .scenes import open_scenes_for_sheet, scene_hints_for_prompt
        from .teach_assets import assets_for_ai_turn, cache_lookup

        # LLM intent classifier (regex retirement, phase E). BLOCKING mode
        # classifies before routing (+~2-3s/turn); default SHADOW mode runs
        # parallel to the tutor call via _spawn_signal_shadow below (zero
        # latency, audits disagreements, fixes stale holds for next turn).
        llm_signals: set[str] | None = None
        if not is_open and learner and getattr(
            config, "SIGNAL_CLASSIFIER_BLOCKING", False
        ):
            from .signal_classifier import (
                OBSERVATIONAL_SIGNALS,
                classify_signals,
            )

            clf = classify_signals(learner)
            if clf is not None:
                llm_signals, clf_meta = clf
                # §2.1a: content_offer / self_flagged_form are shadow-only
                # observations — they must not reach select_mode routing.
                llm_signals = set(llm_signals) - OBSERVATIONAL_SIGNALS
                u = clf_meta.get("usage") or {}
                if u.get("input_tokens") or u.get("output_tokens"):
                    self.costs.add_llm(
                        "classifier",
                        str(clf_meta.get("model") or ""),
                        input_tokens=u.get("input_tokens", 0),
                        output_tokens=u.get("output_tokens", 0),
                    )

        if not is_open and learner:
            sig_pre = self.pedagogy_memory.note_learner(
                learner, extra_signals=llm_signals
            )
            # Eager clears (Grok round-1 C): own Spanish, a topic request, or a
            # help request all mean "not stuck on our last try" — grammar
            # questions with own content must NOT keep the hold.
            if sig_pre & {"spanish_ok", "topic_request", "help_request"}:
                self.pedagogy_memory.clear_comprehension_hold()
        else:
            sig_pre = set()

        self.mode_state.tick()
        obs = build_observations(
            self.sheet, learner=learner, is_open=is_open,
            extra_signals=llm_signals,
        )
        # Recency memory for streak hard breaks (this turn's hits at this index)
        self.mode_state.note_error_hits(obs.get("error_hit_ids"))
        blank = bool(obs.get("blank_sheet") or is_blank_learner(self.sheet))

        sigs = set(obs.get("signals") or [])
        if "english_only" in sigs:
            self.mode_state.english_only_streak += 1
        elif learner and not is_open:
            self.mode_state.english_only_streak = 0

        # Retrieval scheduler (Phase 1): record retrieval outcomes on clear
        # evidence BEFORE building the turn, so ladders/next_due advance and
        # a just-used item is not re-offered this turn.
        sched_notes: list[str] = []
        if learner and not is_open:
            sched_notes.extend(self._record_due_outcomes(learner, sigs))

        open_scenes = open_scenes_for_sheet(self.sheet, self.pack_dir)
        self.mode_state.open_scene_ids = [
            s.get("id") for s in open_scenes if s.get("id")
        ]

        from .corpus import pack_topic_titles

        # Session phase layer (Phase 2): code decides the activity class for
        # this turn; select_mode's guard chain keeps absolute priority and
        # only the default/known-open path is flavored by the hint.
        # Resolve empty retrieval BEFORE flavoring the turn (Grok AMEND 2b,
        # 2026-07-28): a turn must never be flavored for a retrieval phase
        # with nothing due.
        if self.phase_state.current_activity() == "retrieval":
            from .retrieval_scheduler import due_items as _due_now

            if not _due_now(self.sheet):
                self.phase_state.force_advance()

        activity = self.phase_state.current_activity()

        decision = select_mode(
            self.sheet,
            observations=obs,
            is_open=is_open,
            learner=learner if not is_open else "",
            mode_state=self.mode_state,
            open_scenes=open_scenes,
            images_shown=self.pedagogy_memory.images_shown,
            session_memory=self.pedagogy_memory.snapshot(),
            pack_topics=pack_topic_titles(self.pack_dir),
            activity_hint=activity,
        )
        # Due re-encounters ride as a SOFT instruction addition on
        # conversation-flavored turns only (no new hard mode; repair and
        # guard turns keep their single focus).
        due_block, due = due_elicit_block(
            self.sheet, mode=decision.mode.value, reason=decision.reason,
            activity_hint=activity,
        )
        if due_block:
            decision.instructions = (
                (decision.instructions or "").rstrip() + "\n\n" + due_block
            ).strip()
            sched_notes.append(
                "due_elicit_offered:" + ",".join(d.key for d in due)
            )
        # §2.1a self-flag uptake (instruction path — regex-visible cheap
        # case only; shadow classifier owns meaning-level detection). Budget
        # lives in ModeSessionState; the note feeds the uptake_flag_honored
        # eval (measurement first, per the closed content-uptake review).
        if learner and not is_open:
            uptake_txt, uptake_note = self_flag_uptake_block(
                learner,
                mode=decision.mode.value,
                reason=decision.reason,
                mode_state=self.mode_state,
            )
            if uptake_txt:
                decision.instructions = (
                    (decision.instructions or "").rstrip()
                    + "\n\n" + uptake_txt
                ).strip()
                sched_notes.append(uptake_note)
        # INTRODUCE plan (Phase 3, r7 S2): new_input phase + flavorable turn
        # only. Code picks the item + scaffold; the model realizes it; the
        # ledger write happens POST-turn only if the reply shows the key.
        # R-B honesty (Grok AMEND 4b, 2026-07-28): the INTRODUCE block is
        # rendered AFTER image resolution below, so an image plan can never
        # claim an attachment that the cache/cap denied.
        intro_plan = None
        if self.association_table is None:
            if activity == "new_input" and decision.mode.value == "conversation":
                sched_notes.append("introduce_table_missing")
        else:
            _intro_txt, intro_plan = introduce_block(
                self.sheet,
                self.association_table,
                self.pedagogy_memory.snapshot(),
                mode=decision.mode.value,
                reason=decision.reason,
                activity_hint=activity,
            )
            if intro_plan is not None:
                if (
                    intro_plan.scaffold_type == "image"
                    and decision.image_concept is None
                ):
                    # Existing image pipeline (ensure_asset, cap-gated) shows it
                    decision.image_concept = intro_plan.key
                sched_notes.append(
                    f"introduce_planned:{intro_plan.key}:{intro_plan.rule_id}"
                )
        # ConvergentTaskRuntime wiring (Phase 5, r6 Rank-4): task-phase turns
        # bind the FIRST task-capable open scene (session-scoped, persists
        # until done). Slot filling is evaluated on the learner's OWN text
        # BEFORE the tutor call; the teacher-facing task block (goal, slots,
        # tutor_private_info with the never-volunteer directive) rides only
        # flavorable turns — the same set as INTRODUCE, so guards and repairs
        # keep their single focus. After done, task turns fall back to normal
        # flavor (the completing turn still carries the celebrate line).
        if activity == "task":
            from .task_runtime import (
                evaluate_turn as _task_eval,
                task_from_scene,
                task_instructions,
            )

            task_scene = None
            if self.task_state is not None:
                task_scene = next(
                    (
                        s for s in open_scenes
                        if s.get("id") == self.task_state.scene_id
                    ),
                    None,
                )
            if self.task_state is None:
                for sc in open_scenes:
                    st = task_from_scene(sc)
                    if st is not None:
                        self.task_state = st
                        task_scene = sc
                        break
            just_done = False
            if self.task_state is not None and task_scene is not None:
                if (
                    learner and not is_open
                    and self.task_state.status == "open"
                ):
                    before_slots = set(self.task_state.slots_filled)
                    self.task_state = _task_eval(
                        self.task_state, learner, task_scene
                    )
                    for sid in self.task_state.slots_filled:
                        if sid not in before_slots:
                            sched_notes.append(f"task_slot_filled:{sid}")
                    if self.task_state.status == "done":
                        just_done = True
                        sched_notes.append(
                            f"task_complete:{self.task_state.scene_id}"
                        )
                        _desc = str(((task_scene or {}).get("primary_exit") or {}).get("description") or "")
                        sched_notes.extend(self._progress_note(
                            "task_complete", self.task_state.scene_id,
                            item_kind="task", detail_ctx={"desc": _desc},
                        ))
                if (
                    decision.mode.value == "conversation"
                    and decision.reason in INTRODUCE_FLAVORABLE_REASONS
                    and (self.task_state.status == "open" or just_done)
                ):
                    decision.instructions = (
                        (decision.instructions or "").rstrip()
                        + "\n\n"
                        + task_instructions(self.task_state, task_scene)
                    ).strip()
                    sched_notes.append(
                        f"task_goal_offered:{self.task_state.scene_id}"
                    )
        # CLOSE phase (PEDAGOGY §1.2, USER-ratified 2026-07-28): flavorable
        # close turns carry the compact session summary the one-line English
        # close must be built from. Same condition set as INTRODUCE — guard
        # and repair turns keep their single focus.
        if (
            activity == "close"
            and decision.mode.value == "conversation"
            and decision.reason in INTRODUCE_FLAVORABLE_REASONS
        ):
            decision.instructions = (
                (decision.instructions or "").rstrip()
                + "\n\n"
                + close_summary_block(
                    self.pedagogy_memory.snapshot(),
                    resolved_forms=self.mode_state.resolved_this_session,
                    task_state=self.task_state,
                )
            ).strip()
            sched_notes.append("close_phase_offered")
        # Advance/freeze the phase clock: repair + guard turns freeze;
        # interventions (cf_recast/form_focus/association/transfer) consume.
        phase_consumed = phase_turn_consumed(
            decision.mode.value, decision.reason
        )
        self.phase_state.tick(phase_consumed)
        # last_mode_decision (focus rail) is snapshotted AFTER the INTRODUCE
        # render below so its instructions stay faithful to what the model
        # actually receives.
        if not is_open and learner:
            self._spawn_signal_shadow(
                learner, decision.mode.value, decision.reason
            )

        image_decision = None
        teach_images: list = self._attach_mode_image(decision, sched_notes)

        # Any mode may request association image; placement always tries open assets
        if not teach_images and (
            decision.mode in (
                Mode.PLACEMENT,
                Mode.ASSOCIATION,
                Mode.COMPREHENSION_REPAIR,
            )
            or decision.image_concept
        ):
            # Incident 2026-07-28: on comprehension_repair (incl. meta/grammar
            # questions) the fallback may only serve a concept that is
            # surface-present in the CURRENT exchange (the learner's words +
            # this turn's model lines). No relevant concept → NO image.
            relevant_to = None
            if decision.mode == Mode.COMPREHENSION_REPAIR:
                relevant_to = " ".join(
                    [learner if not is_open else ""]
                    + [str(m) for m in (
                        (decision.targets or {}).get("model_lines") or []
                    )]
                )
            teach_images, image_decision = assets_for_ai_turn(
                is_open=is_open or decision.mode == Mode.PLACEMENT,
                blank_sheet=blank,
                learner=learner if not is_open else "",
                tutor_models=list((decision.targets or {}).get("model_lines") or []),
                signals=list(sigs),
                images_shown=self.pedagogy_memory.images_shown,
                turns_since_image=self.pedagogy_memory.turns_since_image,
                session_turns=self.pedagogy_memory.turns,
                require_relevant_to=relevant_to,
            )
            if teach_images:
                self.pedagogy_memory.note_image(teach_images[0].get("concept"))

        self._note_image_costs(teach_images)

        # Render the INTRODUCE block now that image resolution is known
        # (Grok AMEND 4b, 2026-07-28): an R-B plan whose image did NOT
        # actually attach (cache miss + generation cap/denied) downgrades to
        # the R-D single ≤6-word micro-gloss — instructions must never claim
        # a dual-code image that is not there.
        if intro_plan is not None:
            from .introduce_router import IntroducePlan, plan_instructions

            if intro_plan.scaffold_type == "image":
                has_img = any(
                    (t.get("concept") or "") == intro_plan.key
                    for t in (teach_images or [])
                )
                if not has_img:
                    entry = (
                        (self.association_table or {}).get(intro_plan.key)
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
                    sched_notes.append(
                        f"introduce_downgraded:{intro_plan.key}:R-B_to_R-D"
                    )
            decision.instructions = (
                (decision.instructions or "").rstrip()
                + "\n\n"
                + plan_instructions(intro_plan)
            ).strip()

        self.last_mode_decision = {
            **decision.as_dict(),
            "phase": {
                "activity": activity,
                "consumed": phase_consumed,
                "index": self.phase_state.index,
                "turns_in_phase": self.phase_state.turns_in_phase,
                "frozen_turns": self.phase_state.frozen_turns,
            },
        }

        # System = STATIC blocks only (stance/persona/pack) so the provider
        # prefix-cache covers system + chat history. The per-turn sheet rides
        # in the task message at the request tail. No personal context —
        # personal-data capture is disabled.
        system = build_ai_tutor_system(
            pack_palette=load_pack(self.pack_dir),
        )
        task = build_ai_tutor_user_message(
            learner=learner,
            is_open=is_open,
            session_memory=self.pedagogy_memory.snapshot(),
            observations=obs,
            teach_images=teach_images,
            blank_sheet=blank,
            mode_decision=decision.as_dict(),
            open_scene_hints=scene_hints_for_prompt(open_scenes),
            sheet_summary=format_sheet_for_prompt(self.sheet),
        )
        if is_open:
            messages = [{"role": "user", "content": task}]
        else:
            # Full history in testing (HISTORY_TURNS=0). Never mutate self.history here.
            messages = config.history_for_model(self.history) + [
                {"role": "user", "content": task}
            ]

        try:
            # No tool round-trips by default (SHEET_TOOLS=0); hard_observer updates sheet
            tools = self.tools if getattr(config, "SHEET_TOOLS", False) else None
            final, raw, tool_delta, usage, _ = tutor_turn(
                self.client,
                self.caps,
                system,
                messages,
                tools=tools,
                max_tool_rounds=1 if tools else 0,
            )
        except Exception as e:
            return TurnResult(
                reply="",
                error=f"{type(e).__name__}: {e}",
                input_mode=input_mode,
            )

        from .output_gate import check_output_gate, repair_user_message
        from .tutor_response import process_tutor_raw as _ptr

        gate_notes: list[str] = []
        gate_result = None
        image_present = bool(teach_images)
        was_truncated = (getattr(final, "stop_reason", "") or "") == "max_tokens"
        # Phase 4 gate context (r7 S3): the table + live sheet + this turn's
        # IntroducePlan key + retrieval failures this turn (a failed
        # re-encounter legalizes a re-gloss).
        _failed_due = {
            n.split(":", 1)[1]
            for n in sched_notes
            if n.startswith("due_outcome_fail:")
        }
        _gate_ctx = dict(
            association_table=self.association_table,
            sheet=self.sheet,
            introduce_key=(intro_plan.key if intro_plan is not None else None),
            retrieval_failed_keys=_failed_due,
            learner_text=learner if not is_open else "",
        )
        try:
            _vis0, _parts0 = _ptr(raw or "")
            gate_result = check_output_gate(
                _parts0.as_dict(),
                _vis0,
                is_open=is_open,
                already_asked=self.pedagogy_memory.asked,
                already_shown=self.pedagogy_memory.shown,
                mode=decision.mode.value,
                image_present=image_present,
                raw=raw or "",
                truncated=was_truncated,
                **_gate_ctx,
            )
            critical = {
                "pedagogy:no_teach_move",
                "pedagogy:open_needs_model_try",
                "gate:english_wall",
                "gate:form_focus_needs_model",
                "gate:missing_recast",  # form error must surface a short correction
                "gate:sheet_leak",  # model dumped sheet/tool JSON into chat
                "gate:truncated",  # reply hit max_tokens mid-sentence
                # r7 S3: naked first exposure / cluster dump (gate:regloss
                # stays SOFT by omission)
                "gate:unscaffolded_new_item",
            }
            need_recast = bool(
                decision.mode.value in ("cf_recast", "form_focus")
                or (decision.targets or {}).get("require_recast_tag")
            )
            # Re-check with recast requirement if mode demands it
            if need_recast:
                gate_result = check_output_gate(
                    _parts0.as_dict(),
                    _vis0,
                    is_open=is_open,
                    already_asked=self.pedagogy_memory.asked,
                    already_shown=self.pedagogy_memory.shown,
                    mode=decision.mode.value,
                    image_present=image_present,
                    require_recast=True,
                    raw=raw or "",
                    truncated=was_truncated,
                    **_gate_ctx,
                )
            needs_repair = (
                getattr(config, "GATE_REPAIR", True)
                and not gate_result.ok
                and any(f in critical for f in (gate_result.faults or []))
            )
            if not gate_result.ok and not needs_repair:
                gate_notes.append(
                    "output_gate_soft_fail:" + ",".join(gate_result.faults)
                )
            elif needs_repair:
                gate_notes.append("output_gate_fail:" + ",".join(gate_result.faults))
                repair_msg = {
                    "role": "user",
                    "content": repair_user_message(gate_result, raw or ""),
                }
                final2, raw2, _td2, usage2, _ = tutor_turn(
                    self.client,
                    self.caps,
                    system,
                    messages
                    + [{"role": "assistant", "content": raw or ""}]
                    + [repair_msg],
                    tools=None,
                )
                if usage2:
                    usage = {
                        k: (usage or {}).get(k, 0) + (usage2 or {}).get(k, 0)
                        for k in (
                            "input_tokens", "output_tokens",
                            "thinking_tokens", "cached_input_tokens",
                        )
                    }
                if raw2 and raw2.strip():
                    raw = raw2
                    final = final2
                    _vis1, _parts1 = _ptr(raw or "")
                    gate2 = check_output_gate(
                        _parts1.as_dict(),
                        _vis1,
                        is_open=is_open,
                        already_asked=self.pedagogy_memory.asked,
                        already_shown=self.pedagogy_memory.shown,
                        mode=decision.mode.value,
                        image_present=image_present,
                        require_recast=need_recast,
                        raw=raw or "",
                        truncated=(
                            (getattr(final2, "stop_reason", "") or "")
                            == "max_tokens"
                        ),
                        **_gate_ctx,
                    )
                    gate_result = gate2
                    if gate2.ok:
                        gate_notes.append("output_gate_repaired")
                    else:
                        gate_notes.append(
                            "output_gate_still_fail:" + ",".join(gate2.faults)
                        )
            else:
                gate_notes.append("output_gate_ok")
        except Exception as ge:
            gate_notes.append(f"output_gate_error:{type(ge).__name__}")

        result = self._finish(
            learner if not is_open else "",
            raw or "",
            tool_delta,
            final,
            usage,
            input_mode=input_mode,
            log_learner=log_learner if log_learner is not None else (
                "(session open)" if is_open else None
            ),
            is_open=is_open,
            skip_log=True,  # log after mode/plan/images attached
        )

        # Introduce ledger (r7 S1 + R-H): mark ONLY if the visible reply
        # actually presented the key; otherwise the plan lapses and the
        # session budget is not consumed. R-I: an already-introduced table
        # key appearing in the reply needs no action (no re-gloss machinery
        # this ship — the gate owns regloss in Phase 4).
        if intro_plan is not None:
            self.sheet, intro_note = mark_introduced_if_visible(
                self.sheet, intro_plan, result.reply
            )
            if intro_note:
                save_sheet(self.sheet_path, self.sheet)
                self.pedagogy_memory.note_introduced(intro_plan.key)
                sched_notes.append(intro_note)
                sched_notes.extend(self._progress_note(
                    "planted", intro_plan.key, item_kind="lexicon",
                    detail_ctx={"scaffold": intro_plan.scaffold_type},
                ))

        # Round-2 AMEND 1c: keys the gate would have faulted but that were
        # saved solely by an in-reply scaffold (gloss/anchor) get a durable
        # first_seen bit so later bare reuse is a re-encounter, not a fresh
        # CRITICAL fault (Grok's gloss-turn1 → bare-turn2 thrash proof).
        # Deliberately NOT an introduction: no budget consumed, no retrieval
        # enqueue (router-only), confidence/status untouched (honesty law).
        saved_map = dict(
            getattr(gate_result, "scaffold_saved", None) or {}
        ) if gate_result is not None else {}
        if saved_map:
            from .retrieval_scheduler import (
                has_first_seen,
                is_introduced,
                mark_first_seen,
            )

            wrote_first_seen = False
            for fs_key, fs_kind in saved_map.items():
                if intro_plan is not None and fs_key == intro_plan.key:
                    continue  # real introduction owns this key
                if is_introduced(self.sheet, fs_key, "lexicon"):
                    continue
                if has_first_seen(self.sheet, fs_key, "lexicon"):
                    continue
                self.sheet = mark_first_seen(
                    self.sheet, fs_key, "lexicon", fs_kind
                )
                sched_notes.append(f"first_seen:{fs_key}")
                wrote_first_seen = True
            if wrote_first_seen:
                save_sheet(self.sheet_path, self.sheet)

        try_text = ""
        models: list[str] = []
        if result.parts:
            try_text = (result.parts.get("try") or result.parts.get("continue") or "")
            m = result.parts.get("model") or ""
            if m:
                models = [m]
            self.pedagogy_memory.note_plan_try(decision.mode.value, try_text)
            # Remember tutor Spanish so meta "what does that mean?" can re-ask SAME idea
            img_concepts = [
                (t.get("concept") or "")
                for t in (teach_images or [])
                if t.get("concept")
            ]
            self.pedagogy_memory.note_tutor_turn(
                model=m,
                try_=try_text,
                acknowledge=result.parts.get("acknowledge") or "",
                concepts=img_concepts or None,
            )

        # Tutor-declared image (optional <image concept="…"/> in the reply —
        # the model's pedagogical decision replaces regex noun-scanning).
        declared = ((result.parts or {}).get("image_concept") or "").strip()
        if not teach_images and declared:
            from .teach_assets import concept_in_text

            if not concept_in_text(declared, result.reply or ""):
                # Same relevance law as mode/fallback images (incident
                # 2026-07-28): a declared concept absent from the visible
                # reply is not this turn's teaching content — no image
                # beats a wrong one.
                result.notes = list(result.notes or []) + [
                    f"image_declared_irrelevant:{declared}"
                ]
            elif declared in self.pedagogy_memory.images_shown:
                result.notes = list(result.notes or []) + [
                    f"image_declared_skip_repeat:{declared}"
                ]
            elif self.pedagogy_memory.declared_image_cooldown > 0:
                result.notes = list(result.notes or []) + [
                    f"image_declared_cooldown:{declared}"
                ]
            else:
                from .teach_assets import ensure_asset

                # Cache hits always allowed; NOVEL generation is budget-capped
                may_gen = self._may_generate_image(source="tutor_declared")
                hit = None
                try:
                    hit = ensure_asset(declared, generate=may_gen)
                except Exception:
                    hit = None
                if hit:
                    teach_images = [{
                        **hit,
                        "decision_reason": "tutor_declared",
                        "visual_score": 1.0,
                    }]
                    self.pedagogy_memory.note_image(declared)
                    self.pedagogy_memory.declared_image_cooldown = 3
                    self._note_image_costs(teach_images)
                else:
                    result.notes = list(result.notes or []) + [
                        (f"image_gen_capped:{declared}" if not may_gen
                         else f"image_declared_unresolved:{declared}")
                    ]

        if decision.hard_break:
            self.mode_state.note_hard_break(decision.mode)
        if decision.mode == Mode.FORM_FOCUS:
            pid = (decision.targets or {}).get("error_pattern")
            if pid:
                self.mode_state.set_cooldown(str(pid), 4)
        elif decision.mode == Mode.CF_RECAST:
            # Recast already corrected this pattern. Under ModeSessionState
            # .tick() (decrement BEFORE select; drop at v<=1), set N suppresses
            # the next (N-1) learner turns: N=3 → 2 subsequent turns without a
            # sheet-streak form_focus re-correction (Grok countersign
            # 2026-07-28 caught the off-by-one in the original N=2).
            pid = (decision.targets or {}).get("error_pattern")
            if pid:
                self.mode_state.set_cooldown(str(pid), 3)
        if decision.scene_ids:
            for sid in decision.scene_ids:
                if sid:
                    self.mode_state.scene_modeled.add(sid)
        from .character_sheet import (
            ERROR_PATTERN_CATALOG,
            detect_error_pattern_resolves,
        )
        resolved = detect_error_pattern_resolves(learner) if learner and not is_open else []
        if resolved:
            self.mode_state.last_resolved_form = resolved[0]
            # Session-scoped resolve record for the close-phase summary.
            self.mode_state.note_resolved(resolved)
            # r6: enqueue after transfer success — durability moves to the
            # due queue. First-time scheduling only: an already-scheduled
            # form's ladder is owned by record_outcome, never reset here.
            from .retrieval_scheduler import enqueue as _sched_enqueue

            enq = False
            for pid in resolved:
                fid = (ERROR_PATTERN_CATALOG.get(pid) or {}).get("form_id")
                if not fid:
                    continue
                g_entry = (self.sheet.get("grammar") or {}).get(fid) or {}
                if g_entry.get("next_due"):
                    continue
                self.sheet = _sched_enqueue(self.sheet, fid, "grammar")
                sched_notes.append(f"due_enqueued:{fid}")
                enq = True
            if enq:
                save_sheet(self.sheet_path, self.sheet)
        elif decision.mode == Mode.TRANSFER:
            self.mode_state.last_resolved_form = None
        self.mode_state.last_mode = decision.mode.value

        phase = open_phase(self.sheet) if is_open else "ai"
        phase_note = (
            NOTE_DIAGNOSTIC_OPEN if (is_open and blank) else NOTE_KNOWN_LEARNER_OPEN
        )
        soft_plan = {
            "source": "mode_runtime",
            "mode": decision.mode.value,
            "mode_reason": decision.reason,
            "hard_break": decision.hard_break,
            "phase": "diagnostic" if (is_open and blank) else "chat",
            "open_scenes": self.mode_state.open_scene_ids,
            "observations": {
                "signals": obs.get("signals"),
                "error_hit_ids": obs.get("error_hit_ids"),
                "next_best": obs.get("next_best"),
            },
            "image": (teach_images[0].get("concept") if teach_images else None),
            "targets": decision.targets,
        }
        self.last_plan = soft_plan
        result.notes = list(result.notes or []) + gate_notes + sched_notes + [
            phase_note,
            f"open_phase={phase}" if is_open else "phase=ai_tutor",
            f"mode={decision.mode.value}",
            f"mode_reason={decision.reason}",
            f"activity={activity}",
            f"phase_consumed={phase_consumed}",
            f"hard_break={decision.hard_break}",
            "plan_source=mode_runtime",
            f"teacher_mode={self.teacher_mode}",
            f"open_scenes={','.join(self.mode_state.open_scene_ids) or '—'}",
            f"mem_shown={','.join(sorted(self.pedagogy_memory.shown)) or '—'}",
            f"mem_asked={','.join(sorted(self.pedagogy_memory.asked)) or '—'}",
        ]
        if result.parts is not None:
            result.parts = {
                **result.parts,
                "plan": soft_plan,
                "mode": decision.mode.value,
                "mode_decision": decision.as_dict(),
                "open_phase": phase if is_open else result.parts.get("open_phase"),
                "teach_images": teach_images,
            }
            if gate_result is not None:
                result.parts["output_gate"] = gate_result.as_dict()
            if image_decision is not None:
                result.parts["image_decision"] = image_decision.as_dict()
                result.notes = list(result.notes or []) + [
                    f"image_decision:{image_decision.reason}"
                ]
            if teach_images:
                result.notes = list(result.notes or []) + [
                    f"teach_image:{teach_images[0].get('concept')}"
                ]
        # Log once with full mode/plan/gate/images
        self._log_turn_result(
            result,
            log_learner=log_learner if log_learner is not None else (
                "(session open)" if is_open else (learner or "")
            ),
        )
        return result

    def _execute_rules_planned(
        self,
        learner: str,
        *,
        is_open: bool,
        input_mode: str = "text",
        log_learner: str | None = None,
    ) -> TurnResult:
        """Optional TEACHER_MODE=rules: PlanCard ladder + executor (not default)."""
        from .executor import build_executor_system, build_executor_user_message
        from .pedagogy_contract import (
            NOTE_DIAGNOSTIC_OPEN,
            NOTE_KNOWN_LEARNER_OPEN,
        )
        from .plan_card import fallback_diagnostic_card, gate_plan_card
        from .rules_planner import plan_turn
        from .teach_assets import assets_for_plan

        if not is_open and learner:
            self.pedagogy_memory.note_learner(learner)

        card = plan_turn(
            self.sheet,
            learner=learner,
            is_open=is_open,
            memory=self.pedagogy_memory,
        )
        gated = gate_plan_card(card)
        if not gated.ok or not gated.card:
            card = fallback_diagnostic_card()
            gate_notes = [f"plan_gate_fail:{','.join(gated.errors)}"]
        else:
            card = gated.card
            gate_notes = ["plan_gate_ok"]

        self.pedagogy_memory.note_plan_try(card.reason, card.try_prompt)
        self.last_plan = card.as_dict()

        teach_images = assets_for_plan(
            card,
            images_shown=self.pedagogy_memory.images_shown,
            turns_since_image=self.pedagogy_memory.turns_since_image,
            session_turns=self.pedagogy_memory.turns,
        )
        self._note_image_costs(teach_images)
        image_decision = getattr(card, "_image_decision", None)
        if teach_images:
            concept = teach_images[0].get("concept")
            card.image_concept = concept
            self.pedagogy_memory.note_image(concept)
            self.last_plan = card.as_dict()
        elif image_decision is not None and not getattr(image_decision, "want", False):
            card.image_concept = None
            self.last_plan = card.as_dict()

        system = build_executor_system(
            sheet_summary=format_sheet_for_prompt(self.sheet),
            pack_palette=load_pack(self.pack_dir),
        )
        task = build_executor_user_message(
            card,
            learner=learner,
            is_open=is_open,
            session_memory=self.pedagogy_memory.snapshot(),
            teach_images=teach_images,
        )
        if is_open:
            messages = [{"role": "user", "content": task}]
        else:
            messages = self.history + [{"role": "user", "content": task}]

        try:
            final, raw, tool_delta, usage, _ = tutor_turn(
                self.client,
                self.caps,
                system,
                messages,
                tools=self.tools,
            )
        except Exception as e:
            return TurnResult(
                reply="",
                error=f"{type(e).__name__}: {e}",
                input_mode=input_mode,
            )

        result = self._finish(
            learner if not is_open else "",
            raw or "",
            tool_delta,
            final,
            usage,
            input_mode=input_mode,
            log_learner=log_learner if log_learner is not None else (
                "(session open)" if is_open else None
            ),
            is_open=is_open,
        )
        phase = card.phase
        phase_note = (
            NOTE_DIAGNOSTIC_OPEN if phase == "diagnostic" else NOTE_KNOWN_LEARNER_OPEN
        )
        result.notes = list(result.notes or []) + gate_notes + [
            phase_note,
            f"open_phase={phase}" if is_open else f"phase={phase}",
            f"plan:{card.phase}/{card.move}",
            f"plan_reason={card.reason}",
            f"teacher_mode={self.teacher_mode}",
            "plan_source=rules",
            f"mem_shown={','.join(sorted(self.pedagogy_memory.shown)) or '—'}",
            f"mem_asked={','.join(sorted(self.pedagogy_memory.asked)) or '—'}",
        ]
        if result.parts is not None:
            result.parts = {
                **result.parts,
                "plan": card.as_dict(),
                "open_phase": phase if is_open else result.parts.get("open_phase"),
                "teach_images": teach_images,
            }
            if image_decision is not None:
                result.parts["image_decision"] = image_decision.as_dict()
                result.notes = list(result.notes or []) + [
                    f"image_decision:{image_decision.reason}"
                ]
            if teach_images:
                result.notes = list(result.notes or []) + [
                    f"teach_image:{teach_images[0].get('concept')}"
                ]
        return result

    def open_session(self) -> TurnResult:
        """Opening tutor turn — planned PlanCard path or legacy harness."""
        from .pedagogy_contract import (
            NOTE_DIAGNOSTIC_OPEN,
            NOTE_KNOWN_LEARNER_OPEN,
            open_phase,
        )

        # Fresh chat = fresh session cost (the header shows per-session spend)
        self.costs.reset()

        # Reload sheet so wipe/reset is visible before we choose open phase
        try:
            self.sheet = load_sheet(self.sheet_path)
            self.sheet = clear_session_scoped_affect(self.sheet)
        except Exception:
            pass

        # New chat ≠ new learner: seed session memory from durable sheet
        try:
            self.pedagogy_memory.seed_from_sheet(self.sheet, self.profile)
        except Exception:
            pass

        if self._planned_enabled():
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

        # --- legacy path ---
        phase = open_phase(self.sheet)
        harness = open_harness_for_sheet(self.sheet)
        try:
            final, raw, tool_delta, usage, _ = tutor_turn(
                self.client,
                self.caps,
                self.system,
                [{"role": "user", "content": harness}],
                tools=self.tools,
            )
        except Exception as e:
            return TurnResult(
                reply="",
                error=f"{type(e).__name__}: {e}",
            )
        result = self._finish(
            "", raw or "", tool_delta, final, usage,
            log_learner="(session open)",
            is_open=True,
        )
        phase_note = (
            NOTE_DIAGNOSTIC_OPEN if phase == "diagnostic" else NOTE_KNOWN_LEARNER_OPEN
        )
        result.notes = list(result.notes or []) + [
            phase_note, f"open_phase={phase}", "teacher_mode=legacy",
        ]
        if result.parts is not None:
            result.parts = {**result.parts, "open_phase": phase}
        self.history = [
            {"role": "user", "content": harness},
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

        if self._planned_enabled():
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

        # --- legacy path ---
        scaffold = (self.sheet.get("receptive") or {}).get(
            "needs_english_scaffold", True)
        scaffold_line = (
            "SCAFFOLD: needs_english_scaffold=TRUE. Still Spanish-forward: "
            "praise/react in Spanish (¡Muy bien!); model in Spanish; short "
            "Spanish questions. English only for brief rescue / form contrast "
            "if they freeze — never English cheerleading or dual-subtitle "
            "every option (*word* *(translation)* lists)."
            if scaffold else
            "SCAFFOLD: needs_english_scaffold=FALSE. Mostly Spanish; English "
            "rare. Still praise in Spanish."
        )
        mode_line = (
            f"INPUT_MODE: {input_mode}. "
            + (
                "Learner spoke (STT may have typos); treat intent generously "
                "but still recast clear form errors."
                if input_mode == "speech"
                else "Learner typed."
            )
        )
        from .character_sheet import active_error_patterns, now_iso

        active = active_error_patterns(self.sheet)
        err_line = ""
        if active:
            top = active[0]
            err_line = (
                f"ERROR_FOCUS: {top['id']} ×{top['count']} — {top['label']}. "
                f"Hint: {top.get('teach_hint') or ''} "
                f"THIS TURN: recast if they miss it, then <try> the same form again "
                f"(do not only chat past the error).\n"
            )
        nb = self.sheet.get("next_best") or {}
        form_focus = nb.get("form_focus") or nb.get("error_pattern")
        teach_line = (
            f"TEACH_TARGET: practice form_focus={form_focus!r} "
            f"(can_do={nb.get('can_do')!r}). Put it in <model> + <try> this turn.\n"
            if form_focus
            else (
                f"TEACH_TARGET: next_best can_do={nb.get('can_do')!r} "
                f"activity={nb.get('activity') or nb.get('stretch')!r}. "
                f"Still include <model> + <try> — do not only ask open questions.\n"
            )
        )
        harness = (
            f"<harness_context>\n"
            f"now={now_iso()}\n"
            f"Character sheet is your model of this student — adapt to it.\n"
            f"next_best: {json.dumps(nb, ensure_ascii=False)}\n"
            f"{err_line}"
            f"{teach_line}"
            f"{scaffold_line}\n"
            f"{mode_line}\n"
            f"TEACHING RULE: you are a tutor, not a chat buddy. "
            f"Every turn needs a teach move: <model> and/or <try> "
            f"(and <recast>+retry when they err). "
            f"If they ask what something means: explain briefly, then model+try "
            f"so they USE it. "
            f"OUTPUT: <tutor> parts "
            f"(acknowledge / recast / explain / model / try / continue). "
            f"Form/register/construction error → <recast> REQUIRED, then "
            f"<try> same form (not a new topic). "
            f"Do not praise incorrect Spanish as correct. "
            f"LANGUAGE: Spanish-first praise; Spanish models; minimal English; "
            f"no 'Good job/You nailed it'; no dual-subtitle every phrase. "
            f"Do not skip form work only to chase next_best "
            f"(especially ERROR_FOCUS).\n"
            f"The app updates the character sheet — do NOT paste sheet JSON "
            f"or tool payloads into the reply.\n"
            f"Never mention the sheet, tools, or tag names to the learner.\n"
            f"</harness_context>\n\n"
        )
        messages = config.history_for_model(self.history) + [
            {"role": "user", "content": harness + text},
        ]
        try:
            final, raw, tool_delta, usage, _ = tutor_turn(
                self.client,
                self.caps,
                self.system,
                messages,
                tools=self.tools,
            )
        except Exception as e:
            return TurnResult(
                reply="",
                error=f"{type(e).__name__}: {e}",
                input_mode=input_mode,
            )

        result = self._finish(
            text, raw or "", tool_delta, final, usage, input_mode=input_mode,
        )
        result.notes = list(result.notes or []) + ["teacher_mode=legacy"]
        # Keep FULL session history (no silent drop of older turns)
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
        """Hard wipe of Spanish PROGRESS: new blank ability sheet + empty chat
        memory. (Personal data is no longer stored at all, so there is
        nothing else to keep or clear.)

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
        self.history = []
        self.messages_for_ui = []
        self._focus_panel = None
        self._focus_key = None
        self._focus_meta = {"source": "static"}
        from .session_memory import SessionMemory
        from .modes import ModeSessionState
        self.pedagogy_memory = SessionMemory()
        self.mode_state = ModeSessionState()
        self.phase_state = build_session_phase_state(self.sheet, self.pack_dir)
        self.task_state = None
        self.last_mode_decision = None
        self.last_plan = None
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
