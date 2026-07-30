"""Typed turn events + the note-prefix catalog (Phase 3 batch 1).

docs/reviews-architecture-refactor.md — adjudicated Phase 3 (map move 5) and
Grok E6 (BINDING): "Phase 3 needs a checked-in catalog of the ~40 prefixes
(owners, consumers, eval parsers) before additive events; otherwise
events+strings dual-write forever."  This module IS that catalog, plus the
typed event vocabulary and the dual-emit machinery.

THE MEASURED INVENTORY (2026-07-28, this batch): the ``result.notes`` bus
carries **62 catalogued prefix families** (68 distinct note constants once
the seven fixed ``pedagogy:*`` values and fixed-payload variants are counted
individually) — the review's "~40" undercounted by ~22.  Every family is a
``TurnEventKind`` member with a ``NoteSpec`` row in ``NOTE_CATALOG`` below:
emitter site(s), consumers, payload shape (the part after the separator),
stability class, and whether the exact strings are pinned inside the Phase 0
characterization goldens today.

THE EVENT CONTRACT (batch 2 — events are THE truth, strings the projection):
  - The per-turn ``TurnEventLog`` (created by the turn executors, attached to
    ``TurnResult.events``) is the truth.  ``render(event)`` produces EXACTLY
    the legacy note string for every kind, and on the AI + rules executors
    ``result.notes`` IS the seq-ordered projection ``[render(e) for e in
    events]`` — **CHAR-BUG-003 RESOLVED** (Phase 3 batch 2): note order is
    turn chronology (select → schedule/instruct → image → gate → sheet →
    contract → record → tail).  The batch-2 golden regeneration was
    verified ORDER-ONLY (note multisets byte-identical).
  - ``TurnResult.to_dict()`` exposes the serialized timeline (``events``);
    evals/run_conv_smoke.py records it per turn and evals/conv_checks.py
    consumes typed events first, note strings only as the replay fallback
    for historical result artifacts.
  - Leaf emitters are TYPED NATIVELY (batch 2 push-down):
    ``character_sheet.process_turn``/``summarize_sheet_change_events`` mint
    (kind, key, payload) triples (strings = this module's render),
    ``pedagogy_contract`` carries bare ``note_keys`` on PedagogyCheck plus
    the KEY_* constants for the phase note, and ``self_flag_uptake_block``
    returns the raw token.  ``TurnEventLog.absorb`` remains ONLY as the
    safety net for un-typed strays (e.g. a test fake replacing
    process_turn); golden runs mint ZERO absorbed events (contract-tested).
  - The three in-module re-parse sites conv_session carried (the map's
    "decision.reason string-parsed by prefix; notes re-parsed" cluster)
    read typed events: the guard-6 covered-concept site reads
    ``MODE_REASON.payload["guard6_concept"]``, the gate-context
    ``retrieval_failed_keys`` set reads ``DUE_OUTCOME_FAIL`` events, and
    the introduce-ledger branch reads the structured ``introduce_outcome``
    status.  No note-string derivation remains in conv_session (source- and
    behavior-pinned by tests/test_turn_events.py).

STABILITY CLASSES (measured, not assumed):
  - ``eval-pinned`` (14 kinds): consumed by evals/conv_checks.py — since
    Phase 3 batch 2 every checker reads the TYPED events first (recorded per
    turn by run_conv_smoke) and falls back to the note strings only for
    historical result artifacts recorded before events existed:
    ``mode`` (``_mode``), ``activity`` (``phase_adherence``),
    ``uptake_flagged`` (``uptake_flag_honored``), ``due_elicit_offered``
    (``due_elicit_fired``), ``progress_milestone``
    (``progress_milestones_fired``), ``introduce_planned``
    (``introduce_scaffolded``), ``task_goal_offered``/``task_slot_filled``
    (``task_goal_offered``), and the six ``output_gate*`` kinds
    (``recast_or_gate_attempt``: precise event-kind + fault-payload checks
    on the event path; the legacy fallback keeps the historical
    "output_gate"/"missing_recast" joined-notes substring scan).
  - ``ui-pinned`` (2 kinds): web_static/app.js ``setNotes`` warns on
    ``rules_backup``-without-``tool_update`` membership.
  - ``log-only`` (46 kinds): session .jsonl logs (``state.notes`` +
    ``extra.sheet_notes``), the web notes line, the debug ring
    (``response.notes``), and the Phase 0 goldens where flagged.
  - ``debug-only``: NONE exist — the debug ring carries the same list the
    logs get; no kind is minted for the ring alone.

OFF-BUS NOTE VOCABULARIES (documented, deliberately NOT in this catalog):
  - ``output_gate`` internal ``gate:*``/``mode:*``/``tl_ratio=`` notes and
    fault ids travel in ``parts["output_gate"]`` (and as PAYLOAD inside the
    ``output_gate_*`` bus notes), not as bus entries themselves.
  - app.js mints ``fresh_learner`` / ``reset_may_have_failed`` client-side
    on the reset flow — frontend display only, never emitted by Python.
  - ``build_debug_entry`` carries ``gate_notes`` separately (the gate's own
    list), unchanged.

Completeness law (contract-tested): every note string emitted on the golden
runs must classify to a catalogued kind — adding a new note REQUIRES a
catalog entry, or ``tests/test_turn_events.py`` fails.

Stdlib-only; imported eagerly by conv_session (no cycles).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TurnEventKind(str, Enum):
    # -- retrieval scheduler (stage "schedule") -----------------------------
    DUE_OUTCOME_SUCCESS = "due_outcome_success"
    DUE_OUTCOME_FAIL = "due_outcome_fail"
    # -- progress journey rail (stage where the evidence lands) -------------
    PROGRESS_MILESTONE = "progress_milestone"
    PROGRESS_REGRESSION = "progress_regression"
    # -- image generation misses (stage "image") ----------------------------
    IMAGE_GEN_CAPPED = "image_gen_capped"
    IMAGE_GEN_DISABLED = "image_gen_disabled"
    IMAGE_GEN_ASYNC = "image_gen_async"
    # -- pre-model instruction riders (stage "instruct") --------------------
    DUE_ELICIT_OFFERED = "due_elicit_offered"
    UPTAKE_FLAGGED = "uptake_flagged"
    INTRODUCE_TABLE_MISSING = "introduce_table_missing"
    INTRODUCE_PLANNED = "introduce_planned"
    TASK_SLOT_FILLED = "task_slot_filled"
    TASK_COMPLETE = "task_complete"
    TASK_GOAL_OFFERED = "task_goal_offered"
    CLOSE_PHASE_OFFERED = "close_phase_offered"
    INTRODUCE_DOWNGRADED = "introduce_downgraded"
    # -- mode selection (stage "select"; strings render in the tail) --------
    MODE = "mode"
    MODE_REASON = "mode_reason"
    # -- output gate (stage "gate") -----------------------------------------
    OUTPUT_GATE_OK = "output_gate_ok"
    OUTPUT_GATE_SOFT_FAIL = "output_gate_soft_fail"
    OUTPUT_GATE_FAIL = "output_gate_fail"
    OUTPUT_GATE_REPAIRED = "output_gate_repaired"
    OUTPUT_GATE_STILL_FAIL = "output_gate_still_fail"
    OUTPUT_GATE_ERROR = "output_gate_error"
    # -- post-model recorders (stage "record") ------------------------------
    INTRODUCED = "introduced"
    INTRODUCE_LAPSED = "introduce_lapsed"
    FIRST_SEEN = "first_seen"
    MORPH_CARD = "morph_card"
    FRAME_RECORDED = "frame_recorded"
    RENDER_DROPPED = "render_dropped"
    ASKED_TOPIC = "asked_topic"
    DUE_ENQUEUED = "due_enqueued"
    IMAGE_DECLARED_IRRELEVANT = "image_declared_irrelevant"
    IMAGE_DECLARED_SKIP_REPEAT = "image_declared_skip_repeat"
    IMAGE_DECLARED_COOLDOWN = "image_declared_cooldown"
    IMAGE_DECISION = "image_decision"
    TEACH_IMAGE = "teach_image"
    # -- sheet maintenance / _finish (stage "sheet") ------------------------
    FOCUS_ASYNC = "focus_async"
    RECAST = "recast"
    STRUCTURED_REPLY = "structured_reply"
    SHEET_TOOL_UPDATE = "sheet_tool_update"
    SHEET_WHY = "sheet_why"
    SHEET_HARD_OBSERVER = "sheet_hard_observer"
    SHEET_AI_UPDATE = "sheet_ai_update"
    SHEET_RULES_BACKUP = "sheet_rules_backup"
    SHEET_INLINE_DELTA = "sheet_inline_delta"
    SHEET_ERROR_PATTERN = "sheet_error_pattern"
    SHEET_CAN_DOS = "sheet_can_dos"
    SHEET_NEXT_BEST = "sheet_next_best"
    SHEET_SCAFFOLD = "sheet_scaffold"
    # -- pedagogy contract + phase note (stages "contract"/"tail") ----------
    PEDAGOGY = "pedagogy"
    # -- turn tail summary (stage "tail") -----------------------------------
    OPEN_PHASE = "open_phase"
    PHASE = "phase"
    ACTIVITY = "activity"
    PHASE_CONSUMED = "phase_consumed"
    HARD_BREAK = "hard_break"
    PLAN_SOURCE = "plan_source"
    TEACHER_MODE = "teacher_mode"
    OPEN_SCENES = "open_scenes"
    MEM_SHOWN = "mem_shown"
    MEM_ASKED = "mem_asked"
    # -- rules path — HISTORICAL-REPLAY-ONLY. The TEACHER_MODE=rules runtime
    #    (_execute_rules_planned) was DELETED (E4, docs/reviews-architecture-
    #    refactor.md, 2026-07-28); these kinds are kept solely so historical
    #    session .jsonl notes still classify on replay. No live emitter.
    PLAN_GATE_OK = "plan_gate_ok"
    PLAN_GATE_FAIL = "plan_gate_fail"
    PLAN_CARD = "plan_card"
    PLAN_REASON = "plan_reason"
    # -- sentinel: absorbed string with no catalog entry (contract tests
    #    assert this NEVER appears on golden runs; production keeps working)
    LEGACY_UNCATALOGUED = "legacy_uncatalogued"


@dataclass(frozen=True)
class NoteSpec:
    """One catalogued note-prefix family (E6 columns)."""

    kind: TurnEventKind
    match: str            # exact string, or the prefix incl. separator
    exact: bool           # True → the whole note IS ``match``
    payload: str          # shape of the part after the separator ("" if none)
    emitters: tuple[str, ...]
    consumers: tuple[str, ...]
    stability: str        # eval-pinned | ui-pinned | log-only
    golden: bool          # exact strings pinned in tests/characterizations/


# Shared consumer shorthand: EVERY bus note reaches session logs
# (state.notes + extra.sheet_notes), the web notes line (setNotes join), the
# debug ring (response.notes) and — where golden=True — the Phase 0 goldens.
_BUS = ("logs", "web-notes-line", "debug-ring")


def _spec(kind, match, exact, payload, emitters, consumers, stability,
          golden) -> NoteSpec:
    return NoteSpec(kind, match, exact, payload, tuple(emitters),
                    _BUS + tuple(consumers), stability, golden)


NOTE_CATALOG: dict[TurnEventKind, NoteSpec] = {s.kind: s for s in [
    _spec(TurnEventKind.DUE_OUTCOME_SUCCESS, "due_outcome_success:", False,
          "<sheet key>", ["conv_session._record_due_outcomes"],
          [], "log-only", True),
    _spec(TurnEventKind.DUE_OUTCOME_FAIL, "due_outcome_fail:", False,
          "<sheet key>", ["conv_session._record_due_outcomes"],
          ["conv_session gate-ctx retrieval_failed_keys (typed events since "
           "Phase 3 batch 1; was a startswith/split re-parse)"],
          "log-only", False),
    _spec(TurnEventKind.PROGRESS_MILESTONE, "progress_milestone:", False,
          "<milestone kind>:<key>", ["conv_session.emit_progress_events"],
          ["evals/conv_checks.progress_milestones_fired (exact match)"],
          "eval-pinned", True),
    _spec(TurnEventKind.PROGRESS_REGRESSION, "progress_regression:", False,
          "<milestone kind>:<key>", ["conv_session.emit_progress_events"],
          [], "log-only", False),
    _spec(TurnEventKind.IMAGE_GEN_CAPPED, "image_gen_capped:", False,
          "<concept>", ["conv_session._note_image_miss"], [],
          "log-only", False),
    _spec(TurnEventKind.IMAGE_GEN_DISABLED, "image_gen_disabled:", False,
          "<concept>  (CHAR-BUG-004: duplicated per concept per turn)",
          ["conv_session._note_image_miss"], [], "log-only", True),
    _spec(TurnEventKind.IMAGE_GEN_ASYNC, "image_gen_async:", False,
          "<concept>", ["conv_session._note_image_miss"], [],
          "log-only", False),
    _spec(TurnEventKind.DUE_ELICIT_OFFERED, "due_elicit_offered:", False,
          "<key>,<key>,…", ["conv_session._execute_ai_tutor (due_block)"],
          ["evals/conv_checks.due_elicit_fired (substring)"],
          "eval-pinned", True),
    _spec(TurnEventKind.UPTAKE_FLAGGED, "uptake_flagged:", False,
          "<flagged token>",
          ["conv_session.self_flag_uptake_block (returns the raw token; "
           "typed emit at the _execute_ai_tutor call site)"],
          ["evals/conv_checks.uptake_flag_honored (prefix + token split)"],
          "eval-pinned", True),
    _spec(TurnEventKind.INTRODUCE_TABLE_MISSING, "introduce_table_missing",
          True, "", ["conv_session._execute_ai_tutor"], [],
          "log-only", False),
    _spec(TurnEventKind.INTRODUCE_PLANNED, "introduce_planned:", False,
          "<key>:<rule id R-A…R-G>", ["conv_session._execute_ai_tutor"],
          ["evals/conv_checks.introduce_scaffolded (substring)"],
          "eval-pinned", True),
    _spec(TurnEventKind.TASK_SLOT_FILLED, "task_slot_filled:", False,
          "<slot id>", ["conv_session._execute_ai_tutor (task phase)"],
          ["evals/conv_checks.task_goal_offered (substring)"],
          "eval-pinned", False),
    _spec(TurnEventKind.TASK_COMPLETE, "task_complete:", False,
          "<scene id>", ["conv_session._execute_ai_tutor (task phase)"],
          [], "log-only", False),
    _spec(TurnEventKind.TASK_GOAL_OFFERED, "task_goal_offered:", False,
          "<scene id>", ["conv_session._execute_ai_tutor (task phase)"],
          ["evals/conv_checks.task_goal_offered (substring)"],
          "eval-pinned", True),
    _spec(TurnEventKind.CLOSE_PHASE_OFFERED, "close_phase_offered", True,
          "", ["conv_session._execute_ai_tutor (close phase)"], [],
          "log-only", True),
    _spec(TurnEventKind.INTRODUCE_DOWNGRADED, "introduce_downgraded:", False,
          "<key>:R-B_to_R-D", ["conv_session._execute_ai_tutor (AMEND 4b)"],
          [], "log-only", False),
    _spec(TurnEventKind.MODE, "mode=", False, "<mode value>",
          ["conv_session._execute_ai_tutor (minted at select, string "
           "rendered in the tail)"],
          ["evals/conv_checks._mode (fallback parser)"],
          "eval-pinned", True),
    _spec(TurnEventKind.MODE_REASON, "mode_reason=", False,
          "<reason; guard-6 reasons are new_noun:<concept> — parsed ONCE "
          "into payload.guard6_concept at mint>",
          ["conv_session._execute_ai_tutor (minted at select)"],
          ["conv_session covered-concept site (typed events since Phase 3 "
           "batch 1; was decision.reason startswith/split)"],
          "log-only", True),
    _spec(TurnEventKind.OUTPUT_GATE_OK, "output_gate_ok", True, "",
          ["conv_session._execute_ai_tutor (gate)"],
          ["evals/conv_checks.recast_or_gate_attempt (substring "
           "'output_gate')"], "eval-pinned", True),
    _spec(TurnEventKind.OUTPUT_GATE_SOFT_FAIL, "output_gate_soft_fail:",
          False, "<fault id>,<fault id>,…",
          ["conv_session._execute_ai_tutor (gate)"],
          ["evals/conv_checks.recast_or_gate_attempt (substrings "
           "'output_gate' + 'missing_recast' scan fault payloads too)"],
          "eval-pinned", False),
    _spec(TurnEventKind.OUTPUT_GATE_FAIL, "output_gate_fail:", False,
          "<fault id>,<fault id>,…",
          ["conv_session._execute_ai_tutor (gate)"],
          ["evals/conv_checks.recast_or_gate_attempt (substrings)"],
          "eval-pinned", True),
    _spec(TurnEventKind.OUTPUT_GATE_REPAIRED, "output_gate_repaired", True,
          "", ["conv_session._execute_ai_tutor (gate repair)"],
          ["evals/conv_checks.recast_or_gate_attempt (substrings)"],
          "eval-pinned", True),
    _spec(TurnEventKind.OUTPUT_GATE_STILL_FAIL, "output_gate_still_fail:",
          False, "<fault id>,…",
          ["conv_session._execute_ai_tutor (gate repair)"],
          ["evals/conv_checks.recast_or_gate_attempt (substrings)"],
          "eval-pinned", False),
    _spec(TurnEventKind.OUTPUT_GATE_ERROR, "output_gate_error:", False,
          "<exception type name>", ["conv_session._execute_ai_tutor (gate)"],
          ["evals/conv_checks.recast_or_gate_attempt (substrings)"],
          "eval-pinned", False),
    _spec(TurnEventKind.INTRODUCED, "introduced:", False, "<key>",
          ["conv_session introduce_outcome → _execute_ai_tutor (legacy "
           "string also via mark_introduced_if_visible wrapper)"],
          ["conv_session introduce branch (typed status since Phase 3 "
           "batch 1; was startswith('introduced:'))", "tests/test_introduce_router"],
          "log-only", True),
    _spec(TurnEventKind.INTRODUCE_LAPSED, "introduce_lapsed:", False,
          "<key>:no_scaffold",
          ["conv_session introduce_outcome → _execute_ai_tutor"],
          ["tests/test_introduce_router"], "log-only", False),
    _spec(TurnEventKind.FIRST_SEEN, "first_seen:", False, "<key>",
          ["conv_session._execute_ai_tutor (scaffold_saved → AMEND 1c)"],
          [], "log-only", True),
    _spec(TurnEventKind.MORPH_CARD, "morph_card:", False,
          "<lemma> (tutor-side introduction engaged the Morphology card)",
          ["turn_pipeline.stage_intro_morph"],
          ["web Morphology card (block stashed on last_mode_decision)"],
          "log-only", True),
    _spec(TurnEventKind.FRAME_RECORDED, "frame_recorded:", False,
          "<key>:<frame> (frames_seen exposure write — the revisit-bound "
          "counter, docs/design-encounter-variety.md)",
          ["turn_pipeline.stage_frame_record"],
          ["encounter-variety revisit bound (count of writes)"],
          "log-only", False),
    _spec(TurnEventKind.RENDER_DROPPED, "render_dropped:", False,
          "<kind>:<concept> (§1.1b settlement drop — operator/telemetry, "
          "never a learner-facing message; no silent kills)",
          ["turn_pipeline._settle_pixels"],
          ["design-exchange-settlement.md audits"],
          "log-only", False),
    _spec(TurnEventKind.ASKED_TOPIC, "asked_topic:", False,
          "<frame>:<concept> registry key (CHAR-BUG-007: pronouns leak in)",
          ["conv_session._execute_ai_tutor"], [], "log-only", True),
    _spec(TurnEventKind.DUE_ENQUEUED, "due_enqueued:", False, "<form id>",
          ["conv_session._execute_ai_tutor (resolve → enqueue)"], [],
          "log-only", False),
    _spec(TurnEventKind.IMAGE_DECLARED_IRRELEVANT,
          "image_declared_irrelevant:", False, "<concept>",
          ["conv_session._execute_ai_tutor (tutor-declared image)"], [],
          "log-only", False),
    _spec(TurnEventKind.IMAGE_DECLARED_SKIP_REPEAT,
          "image_declared_skip_repeat:", False, "<concept>",
          ["conv_session._execute_ai_tutor (tutor-declared image)"], [],
          "log-only", False),
    _spec(TurnEventKind.IMAGE_DECLARED_COOLDOWN, "image_declared_cooldown:",
          False, "<concept>",
          ["conv_session._execute_ai_tutor (tutor-declared image)"], [],
          "log-only", False),
    _spec(TurnEventKind.IMAGE_DECISION, "image_decision:", False,
          "<decision reason>",
          ["conv_session._execute_ai_tutor"],
          [], "log-only", True),
    _spec(TurnEventKind.TEACH_IMAGE, "teach_image:", False, "<concept>",
          ["conv_session._execute_ai_tutor"],
          [], "log-only", False),
    _spec(TurnEventKind.FOCUS_ASYNC, "focus_async", True, "",
          ["conv_session._finish"], [], "log-only", True),
    _spec(TurnEventKind.RECAST, "recast", True, "",
          ["conv_session._finish (has_recast, deduped by membership check "
           "against the sheet notes)"], [], "log-only", False),
    _spec(TurnEventKind.STRUCTURED_REPLY, "structured_reply", True, "",
          ["conv_session._finish"], [], "log-only", True),
    _spec(TurnEventKind.SHEET_TOOL_UPDATE, "tool_update", True, "",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"],
          ["web app.js setNotes (membership: suppresses the rules_backup "
           "warn)"], "ui-pinned", False),
    _spec(TurnEventKind.SHEET_WHY, "why=", False,
          "<tool reason, first 80 chars>",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"],
          ["goldens collapse to why=* (volatile family)"], "log-only", False),
    _spec(TurnEventKind.SHEET_HARD_OBSERVER, "hard_observer", True, "",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"], [],
          "log-only", True),
    _spec(TurnEventKind.SHEET_AI_UPDATE, "ai_update", True, "",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"], [],
          "log-only", False),
    _spec(TurnEventKind.SHEET_RULES_BACKUP, "rules_backup", True, "",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"],
          ["web app.js setNotes (membership: warn styling)"],
          "ui-pinned", True),
    _spec(TurnEventKind.SHEET_INLINE_DELTA, "inline_delta", True, "",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"], [],
          "log-only", False),
    _spec(TurnEventKind.SHEET_ERROR_PATTERN, "err×", False,
          "<count>:<error pattern id>",
          ["character_sheet.process_turn (typed triples; emitted at _finish)"], [],
          "log-only", False),
    _spec(TurnEventKind.SHEET_CAN_DOS, "can-dos ", False,
          "<id:conf→conf/status>, … (≤6)",
          ["character_sheet.summarize_sheet_change_events (typed; emitted at _finish)"],
          ["goldens collapse to can-dos=* (volatile family)"],
          "log-only", True),
    _spec(TurnEventKind.SHEET_NEXT_BEST, "next=", False,
          "<can_do or —> / <activity>",
          ["character_sheet.summarize_sheet_change_events (typed; emitted at _finish)"],
          ["goldens collapse to next=* (volatile family)"],
          "log-only", False),
    _spec(TurnEventKind.SHEET_SCAFFOLD, "scaffold=", False,
          "ES-forward+EN-rescue | mostly_ES",
          ["character_sheet.summarize_sheet_change_events (typed; emitted at _finish)"],
          [], "log-only", True),
    _spec(TurnEventKind.PEDAGOGY, "pedagogy:", False,
          "ok | no_teach_move | open_needs_model_try | recast_without_try | "
          "unstructured | diagnostic_open | known_learner_open (closed set: "
          "pedagogy_contract constants; first five via evaluate_turn, last "
          "two are the phase note in the turn tail)",
          ["pedagogy_contract.evaluate_turn note_keys (typed; emitted at "
           "_finish)",
           "conv_session turn tail phase note (typed KEY_* emit)"],
          [], "log-only", True),
    _spec(TurnEventKind.OPEN_PHASE, "open_phase=", False,
          "diagnostic | known",
          ["conv_session._execute_ai_tutor tail"],
          [], "log-only", True),
    _spec(TurnEventKind.PHASE, "phase=", False,
          "ai_tutor (historical replay may carry rules <card.phase> values)",
          ["conv_session._execute_ai_tutor tail"],
          [], "log-only", True),
    _spec(TurnEventKind.ACTIVITY, "activity=", False,
          "retrieval | new_input | task | free | close",
          ["conv_session._execute_ai_tutor tail"],
          ["evals/conv_checks.phase_adherence (prefix + value)"],
          "eval-pinned", True),
    _spec(TurnEventKind.PHASE_CONSUMED, "phase_consumed=", False,
          "True | False", ["conv_session._execute_ai_tutor tail"], [],
          "log-only", True),
    _spec(TurnEventKind.HARD_BREAK, "hard_break=", False, "True | False",
          ["conv_session._execute_ai_tutor tail"], [], "log-only", True),
    _spec(TurnEventKind.PLAN_SOURCE, "plan_source=", False,
          "mode_runtime ('rules' only in historical replay — E4 deletion)",
          ["conv_session._execute_ai_tutor tail"],
          [], "log-only", True),
    _spec(TurnEventKind.TEACHER_MODE, "teacher_mode=", False,
          "planned aliases ('rules'/'legacy' only in historical replay — "
          "E4/E4b deletion 2026-07-28)",
          ["conv_session._execute_ai_tutor tail"],
          [], "log-only", True),
    _spec(TurnEventKind.OPEN_SCENES, "open_scenes=", False,
          "<scene id>,… or —", ["conv_session._execute_ai_tutor tail"], [],
          "log-only", True),
    _spec(TurnEventKind.MEM_SHOWN, "mem_shown=", False,
          "<sorted memory.shown>,… or —",
          ["conv_session._execute_ai_tutor tail"],
          [], "log-only", True),
    _spec(TurnEventKind.MEM_ASKED, "mem_asked=", False,
          "<sorted memory.asked>,… or —",
          ["conv_session._execute_ai_tutor tail"],
          [], "log-only", True),
    # Rules-path kinds: HISTORICAL-REPLAY-ONLY (E4 deletion 2026-07-28).
    # No live emitter; rows kept so historical .jsonl notes classify.
    _spec(TurnEventKind.PLAN_GATE_OK, "plan_gate_ok", True, "",
          ["HISTORICAL (E4): _execute_rules_planned, deleted"], [],
          "log-only", False),
    _spec(TurnEventKind.PLAN_GATE_FAIL, "plan_gate_fail:", False,
          "<error>,…", ["HISTORICAL (E4): _execute_rules_planned, deleted"],
          [], "log-only", False),
    _spec(TurnEventKind.PLAN_CARD, "plan:", False, "<phase>/<move>",
          ["HISTORICAL (E4): _execute_rules_planned, deleted"], [],
          "log-only", False),
    _spec(TurnEventKind.PLAN_REASON, "plan_reason=", False, "<card reason>",
          ["HISTORICAL (E4): _execute_rules_planned, deleted"], [],
          "log-only", False),
]}


# ---------------------------------------------------------------------------
# The typed event + render (strings are a projection of events)
# ---------------------------------------------------------------------------


@dataclass
class TurnEvent:
    kind: TurnEventKind
    key: str = ""
    payload: dict = field(default_factory=dict)
    seq: int = 0
    stage: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind.value,
            "key": self.key,
            "payload": dict(self.payload),
            "seq": self.seq,
            "stage": self.stage,
        }


def _join(items, empty="") -> str:
    return ",".join(str(i) for i in (items or [])) or empty


_K = TurnEventKind

# Per-kind render: MUST reproduce the legacy string byte-for-byte (the
# dual-emit contract; round-trip pinned by tests/test_turn_events.py).
_RENDER = {
    _K.DUE_OUTCOME_SUCCESS: lambda e: f"due_outcome_success:{e.key}",
    _K.DUE_OUTCOME_FAIL: lambda e: f"due_outcome_fail:{e.key}",
    _K.PROGRESS_MILESTONE:
        lambda e: f"progress_milestone:{e.payload.get('milestone')}:{e.key}",
    _K.PROGRESS_REGRESSION:
        lambda e: f"progress_regression:{e.payload.get('milestone')}:{e.key}",
    _K.IMAGE_GEN_CAPPED: lambda e: f"image_gen_capped:{e.key}",
    _K.IMAGE_GEN_DISABLED: lambda e: f"image_gen_disabled:{e.key}",
    _K.IMAGE_GEN_ASYNC: lambda e: f"image_gen_async:{e.key}",
    _K.DUE_ELICIT_OFFERED:
        lambda e: "due_elicit_offered:" + _join(e.payload.get("keys")),
    _K.UPTAKE_FLAGGED: lambda e: f"uptake_flagged:{e.key}",
    _K.INTRODUCE_TABLE_MISSING: lambda e: "introduce_table_missing",
    _K.INTRODUCE_PLANNED:
        lambda e: f"introduce_planned:{e.key}:{e.payload.get('rule_id')}",
    _K.TASK_SLOT_FILLED: lambda e: f"task_slot_filled:{e.key}",
    _K.TASK_COMPLETE: lambda e: f"task_complete:{e.key}",
    _K.TASK_GOAL_OFFERED: lambda e: f"task_goal_offered:{e.key}",
    _K.CLOSE_PHASE_OFFERED: lambda e: "close_phase_offered",
    _K.INTRODUCE_DOWNGRADED:
        lambda e: f"introduce_downgraded:{e.key}:"
                  f"{e.payload.get('path', 'R-B_to_R-D')}",
    _K.MODE: lambda e: f"mode={e.key}",
    _K.MODE_REASON: lambda e: f"mode_reason={e.key}",
    _K.OUTPUT_GATE_OK: lambda e: "output_gate_ok",
    _K.OUTPUT_GATE_SOFT_FAIL:
        lambda e: "output_gate_soft_fail:" + _join(e.payload.get("faults")),
    _K.OUTPUT_GATE_FAIL:
        lambda e: "output_gate_fail:" + _join(e.payload.get("faults")),
    _K.OUTPUT_GATE_REPAIRED: lambda e: "output_gate_repaired",
    _K.OUTPUT_GATE_STILL_FAIL:
        lambda e: "output_gate_still_fail:" + _join(e.payload.get("faults")),
    _K.OUTPUT_GATE_ERROR: lambda e: f"output_gate_error:{e.key}",
    _K.INTRODUCED: lambda e: f"introduced:{e.key}",
    _K.INTRODUCE_LAPSED:
        lambda e: f"introduce_lapsed:{e.key}:"
                  f"{e.payload.get('reason', 'no_scaffold')}",
    _K.FIRST_SEEN: lambda e: f"first_seen:{e.key}",
    _K.MORPH_CARD: lambda e: f"morph_card:{e.key}",
    _K.FRAME_RECORDED: lambda e: f"frame_recorded:{e.key}",
    _K.RENDER_DROPPED: lambda e: f"render_dropped:{e.key}",
    _K.ASKED_TOPIC: lambda e: f"asked_topic:{e.key}",
    _K.DUE_ENQUEUED: lambda e: f"due_enqueued:{e.key}",
    _K.IMAGE_DECLARED_IRRELEVANT:
        lambda e: f"image_declared_irrelevant:{e.key}",
    _K.IMAGE_DECLARED_SKIP_REPEAT:
        lambda e: f"image_declared_skip_repeat:{e.key}",
    _K.IMAGE_DECLARED_COOLDOWN:
        lambda e: f"image_declared_cooldown:{e.key}",
    _K.IMAGE_DECISION: lambda e: f"image_decision:{e.key}",
    _K.TEACH_IMAGE: lambda e: f"teach_image:{e.key}",
    _K.FOCUS_ASYNC: lambda e: "focus_async",
    _K.RECAST: lambda e: "recast",
    _K.STRUCTURED_REPLY: lambda e: "structured_reply",
    _K.SHEET_TOOL_UPDATE: lambda e: "tool_update",
    _K.SHEET_WHY: lambda e: f"why={e.key}",
    _K.SHEET_HARD_OBSERVER: lambda e: "hard_observer",
    _K.SHEET_AI_UPDATE: lambda e: "ai_update",
    _K.SHEET_RULES_BACKUP: lambda e: "rules_backup",
    _K.SHEET_INLINE_DELTA: lambda e: "inline_delta",
    _K.SHEET_ERROR_PATTERN:
        lambda e: f"err×{e.payload.get('count')}:{e.key}",
    _K.SHEET_CAN_DOS: lambda e: f"can-dos {e.key}",
    _K.SHEET_NEXT_BEST: lambda e: f"next={e.key}",
    _K.SHEET_SCAFFOLD: lambda e: f"scaffold={e.key}",
    _K.PEDAGOGY: lambda e: f"pedagogy:{e.key}",
    _K.OPEN_PHASE: lambda e: f"open_phase={e.key}",
    _K.PHASE: lambda e: f"phase={e.key}",
    _K.ACTIVITY: lambda e: f"activity={e.key}",
    _K.PHASE_CONSUMED: lambda e: f"phase_consumed={e.key}",
    _K.HARD_BREAK: lambda e: f"hard_break={e.key}",
    _K.PLAN_SOURCE: lambda e: f"plan_source={e.key}",
    _K.TEACHER_MODE: lambda e: f"teacher_mode={e.key}",
    _K.OPEN_SCENES:
        lambda e: "open_scenes=" + _join(e.payload.get("ids"), "—"),
    _K.MEM_SHOWN: lambda e: "mem_shown=" + _join(e.payload.get("items"), "—"),
    _K.MEM_ASKED: lambda e: "mem_asked=" + _join(e.payload.get("items"), "—"),
    _K.PLAN_GATE_OK: lambda e: "plan_gate_ok",
    _K.PLAN_GATE_FAIL:
        lambda e: "plan_gate_fail:" + _join(e.payload.get("errors")),
    _K.PLAN_CARD:
        lambda e: f"plan:{e.payload.get('phase')}/{e.payload.get('move')}",
    _K.PLAN_REASON: lambda e: f"plan_reason={e.key}",
    _K.LEGACY_UNCATALOGUED: lambda e: e.payload.get("raw", e.key),
}


def render(event: TurnEvent) -> str:
    """The legacy note string for ``event`` — byte-exact projection."""
    return _RENDER[event.kind](event)


def render_note(kind: TurnEventKind, *, key: str = "",
                payload: dict | None = None) -> str:
    """Render without logging (compat paths outside a live turn)."""
    return render(TurnEvent(kind=kind, key=key, payload=dict(payload or {})))


# ---------------------------------------------------------------------------
# Catalog-driven classification (the absorb boundary + completeness law)
# ---------------------------------------------------------------------------

_EXACT: dict[str, TurnEventKind] = {
    s.match: s.kind for s in NOTE_CATALOG.values() if s.exact
}
# Longest prefix first so mode_reason= beats mode=, phase_consumed= beats
# phase=, introduce_* variants never shadow each other.
_PREFIXES: list[tuple[str, TurnEventKind]] = sorted(
    ((s.match, s.kind) for s in NOTE_CATALOG.values() if not s.exact),
    key=lambda p: -len(p[0]),
)


def _parse_tail(kind: TurnEventKind, tail: str) -> tuple[str, dict]:
    """(key, payload) for a classified tail — inverse of the render table."""
    if kind in (_K.PROGRESS_MILESTONE, _K.PROGRESS_REGRESSION):
        ms, _, key = tail.partition(":")
        return key, {"milestone": ms}
    if kind is _K.DUE_ELICIT_OFFERED:
        return "", {"keys": tail.split(",") if tail else []}
    if kind is _K.INTRODUCE_PLANNED:
        key, _, rule = tail.rpartition(":")
        return key, {"rule_id": rule}
    if kind is _K.INTRODUCE_DOWNGRADED:
        key, _, path = tail.rpartition(":")
        return key, {"path": path}
    if kind is _K.INTRODUCE_LAPSED:
        key, _, reason = tail.rpartition(":")
        return key, {"reason": reason}
    if kind in (_K.OUTPUT_GATE_SOFT_FAIL, _K.OUTPUT_GATE_FAIL,
                _K.OUTPUT_GATE_STILL_FAIL):
        return "", {"faults": tail.split(",") if tail else []}
    if kind is _K.PLAN_GATE_FAIL:
        return "", {"errors": tail.split(",") if tail else []}
    if kind is _K.OPEN_SCENES:
        return "", {"ids": [] if tail == "—" else tail.split(",")}
    if kind in (_K.MEM_SHOWN, _K.MEM_ASKED):
        return "", {"items": [] if tail == "—" else tail.split(",")}
    if kind is _K.PLAN_CARD:
        ph, _, mv = tail.partition("/")
        return "", {"phase": ph, "move": mv}
    if kind is _K.SHEET_ERROR_PATTERN:
        count, _, pid = tail.partition(":")
        return pid, {"count": count}
    if kind is _K.MODE_REASON:
        return tail, {"guard6_concept": _guard6_concept(tail)}
    return tail, {}


def _guard6_concept(reason: str) -> str | None:
    """Guard-6 concept from a mode reason — THE one boundary parse.

    Replaces the mid-pipeline ``decision.reason.startswith("new_noun:")`` +
    split re-parse (Phase 3 batch 1); ``None`` ⇔ not a guard-6 reason.
    """
    if (reason or "").startswith("new_noun:"):
        return reason.split(":", 1)[1]
    return None


def classify_note(note: str) -> tuple[TurnEventKind, str, dict] | None:
    """(kind, key, payload) for a legacy note string, or None if
    uncatalogued.  Completeness law: contract tests assert this never
    returns None for a runtime-emitted note on the golden runs."""
    s = str(note)
    kind = _EXACT.get(s)
    if kind is not None:
        return kind, "", {}
    for prefix, k in _PREFIXES:
        if s.startswith(prefix):
            key, payload = _parse_tail(k, s[len(prefix):])
            return k, key, payload
    return None


# ---------------------------------------------------------------------------
# The per-turn event log (dual-emit)
# ---------------------------------------------------------------------------


@dataclass
class TurnEventLog:
    """Per-turn ordered event log; ``seq`` is monotonic emission order
    (true chronology — the legacy string list keeps its own assembly order,
    CHAR-BUG-003 preserved this batch)."""

    events: list[TurnEvent] = field(default_factory=list)
    _seq: int = 0

    def emit(self, kind: TurnEventKind, *, key: str = "",
             payload: dict | None = None, stage: str = "") -> str:
        """Mint a typed event; return the legacy note string projection."""
        p = dict(payload or {})
        if kind is _K.MODE_REASON and "guard6_concept" not in p:
            p["guard6_concept"] = _guard6_concept(key)
        ev = TurnEvent(kind=kind, key=str(key), payload=p, seq=self._seq,
                       stage=stage)
        self._seq += 1
        self.events.append(ev)
        return render(ev)

    def absorb(self, note: str, *, stage: str = "") -> str:
        """Mint a typed event FROM a leaf-module legacy string (catalog
        classification); returns the ORIGINAL string unchanged (byte-safe).
        Uncatalogued strings mint LEGACY_UNCATALOGUED — production keeps
        working; the contract tests forbid it on golden runs."""
        s = str(note)
        hit = classify_note(s)
        if hit is None:
            kind, key, payload = _K.LEGACY_UNCATALOGUED, "", {"raw": s}
        else:
            kind, key, payload = hit
        ev = TurnEvent(kind=kind, key=key, payload=payload, seq=self._seq,
                       stage=stage)
        self._seq += 1
        self.events.append(ev)
        return s

    # -- typed reads (the re-parse replacements) ----------------------------
    def find(self, kind: TurnEventKind) -> list[TurnEvent]:
        return [e for e in self.events if e.kind is kind]

    def latest(self, kind: TurnEventKind) -> TurnEvent | None:
        for e in reversed(self.events):
            if e.kind is kind:
                return e
        return None


def session_event_log(session) -> TurnEventLog:
    """The live per-turn log on ``session`` (created lazily; the turn
    executors reset it via ``begin_turn_log``).  Attribute access goes
    through ``__dict__`` so partial sessions and test fakes work."""
    d = getattr(session, "__dict__", None)
    if d is None:  # exotic fake without __dict__ — unlogged but functional
        return TurnEventLog()
    log = d.get("_turn_events")
    if log is None:
        log = TurnEventLog()
        d["_turn_events"] = log
    return log


def begin_turn_log(session) -> TurnEventLog:
    """Fresh per-turn log (called at the top of each turn executor)."""
    log = TurnEventLog()
    d = getattr(session, "__dict__", None)
    if d is not None:
        d["_turn_events"] = log
    return log
