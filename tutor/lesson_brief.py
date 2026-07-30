"""LessonBrief — typed packaging of code router decisions (B0, schema v2).

PEDAGOGY §3.3 (amended 2026-07-30): the teaching-decision path is CODE
ONLY. This module adds NO authority and NO LLM call — it PACKAGES what the
routers already decided (mode decision, IntroducePlan, due queue, phase
state, pedagogy memory, budgets) into the typed brief the realization path
consumes (docs/design-planner-rounds.md, round-1 M1 partial REJECT
accepted: "code-assembled brief FIRST"; retired-planner history: what died
in E4 was an LLM deciding the lesson; this is a FORMAT for what code
decides).

Schema v2 (round-2 Q4 table, adopted verbatim in the adjudication):
phase, targets[{key, gloss, anchor, move}], allowed_new[{key, rule_id,
anchor}], banned_asks[], due_frames[{key, kind, avoid_frames[]}],
budgets{introduce_left, form_focus_cooldown, content_uptake_left,
checker_left}, must_not[], cf_target?, register, scene_goal,
exit_criteria, output_shape, session_manifest. No free-prose "intent"
that ghostwrites the turn (§1.1a).

``parse_lesson_brief`` is the trap-#13 closure (elfric: planner naming
unknowable fields): unknown keys rejected; every key validated against
association table ∪ sheet ∪ error-pattern catalog; ``allowed_new`` ⊆ the
router introduce plan. Stdlib only; never calls the model.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

# --- schema v2 field allowlists (unknown keys are validation faults) --------
BRIEF_FIELDS = frozenset({
    "phase", "targets", "allowed_new", "banned_asks", "due_frames",
    "budgets", "must_not", "cf_target", "register", "scene_goal",
    "exit_criteria", "output_shape", "session_manifest",
})
TARGET_FIELDS = frozenset({"key", "gloss", "anchor", "move"})
ALLOWED_NEW_FIELDS = frozenset({"key", "rule_id", "anchor"})
# kind is scheduler identity (lexicon|grammar|skill) — carried so the
# realization slice and the gate judge the same entry the scheduler owns.
DUE_FRAME_FIELDS = frozenset({"key", "kind", "avoid_frames"})
BUDGET_FIELDS = frozenset({
    "introduce_left", "form_focus_cooldown", "content_uptake_left",
    "checker_left",
})
CF_TARGET_FIELDS = frozenset({"pattern", "form_id", "move"})
MANIFEST_FIELDS = frozenset({
    "introduced_this_session", "cf_targets", "still_fail_count", "phase_id",
})

# Required output shape (the tutor tag census in executor.AI_TUTOR_SYSTEM):
# structured parts expectation — SHAPE, never a token cap (elfric regret #5).
OUTPUT_SHAPE = (
    "acknowledge", "recast", "explain", "model", "try", "continue",
)

# Code-owned must_not census (round-2 item 4.2: replaces the probe/re-ask
# policy essays with data; the law core carries the operative clauses).
MUST_NOT = (
    "no flashcard chrome on due re-encounters",
    "no re-gloss of an introduced item without a same-turn retrieval failure",
    "no A/B or yes/no English-meaning quiz on sheet-known material",
    "no dual-subtitle English walls",
    "no conjugation-table dumps in chat",
    "introduce nothing beyond allowed_new",
)


@dataclass
class LessonBrief:
    """One turn's typed co-agenda (multi-constraint, NOT a sequential todo
    — round-1 M2 AMEND). Every field is a packaging of a code decision."""

    phase: str
    targets: list[dict] = field(default_factory=list)
    allowed_new: list[dict] = field(default_factory=list)
    banned_asks: list[str] = field(default_factory=list)
    due_frames: list[dict] = field(default_factory=list)
    budgets: dict = field(default_factory=dict)
    must_not: list[str] = field(default_factory=list)
    cf_target: dict | None = None
    register: str = ""
    scene_goal: dict | None = None
    exit_criteria: str = ""
    output_shape: list[str] = field(default_factory=lambda: list(OUTPUT_SHAPE))
    session_manifest: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)

    def to_compact_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False,
                          separators=(",", ":"))


# ---------------------------------------------------------------------------
# Validation (parse_lesson_brief)
# ---------------------------------------------------------------------------


def known_sheet_keys(sheet: dict | None) -> set[str]:
    """Every key the sheet holds (lexicon ∪ grammar ∪ skills ∪
    error_patterns) — the sheet half of the key allowlist."""
    keys: set[str] = set()
    for section in ("lexicon", "grammar", "skills", "error_patterns"):
        block = (sheet or {}).get(section)
        if isinstance(block, dict):
            keys.update(str(k) for k in block)
    return keys


def _key_allowlist(table: dict | None, sheet: dict | None) -> set[str]:
    from .character_sheet import ERROR_PATTERN_CATALOG

    allow = set((table or {}).keys()) | known_sheet_keys(sheet)
    # Catalog pattern ids + their form ids are code inventory (cf targets /
    # grammar due keys exist before the sheet holds an entry).
    for pid, cat in ERROR_PATTERN_CATALOG.items():
        allow.add(pid)
        fid = (cat or {}).get("form_id")
        if fid:
            allow.add(str(fid))
    return allow


def _check_item_fields(
    items: Any, allowed: frozenset, label: str, problems: list[str]
) -> list[dict]:
    out: list[dict] = []
    if items is None:
        return out
    if not isinstance(items, list):
        problems.append(f"{label}: must be a list")
        return out
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            problems.append(f"{label}[{i}]: must be an object")
            continue
        unknown = set(it) - allowed
        if unknown:
            problems.append(f"{label}[{i}]: unknown fields {sorted(unknown)}")
        out.append(it)
    return out


def parse_lesson_brief(
    data: dict,
    *,
    table: dict | None,
    sheet: dict | None,
    intro_plan_keys: list[str] | None = None,
) -> LessonBrief:
    """Validate a brief dict → LessonBrief; ValueError lists ALL faults.

    Faults: unknown keys at any level; a target/allowed_new/due_frame key
    outside association table ∪ sheet ∪ error-pattern catalog (invented
    inventory — elfric trap #13); allowed_new ⊄ the router introduce plan
    (the brief may never widen what code decided); malformed budgets.
    """
    problems: list[str] = []
    if not isinstance(data, dict):
        raise ValueError("lesson_brief: top level must be an object")

    unknown = set(data) - BRIEF_FIELDS
    if unknown:
        problems.append(f"unknown fields {sorted(unknown)}")

    allow = _key_allowlist(table, sheet)

    targets = _check_item_fields(
        data.get("targets"), TARGET_FIELDS, "targets", problems)
    allowed_new = _check_item_fields(
        data.get("allowed_new"), ALLOWED_NEW_FIELDS, "allowed_new", problems)
    due_frames = _check_item_fields(
        data.get("due_frames"), DUE_FRAME_FIELDS, "due_frames", problems)

    for label, items in (
        ("targets", targets), ("allowed_new", allowed_new),
        ("due_frames", due_frames),
    ):
        for it in items:
            k = str(it.get("key") or "")
            if not k:
                problems.append(f"{label}: entry missing key")
            elif k not in allow:
                problems.append(
                    f"{label}: key {k!r} not in association table ∪ sheet"
                )

    plan_keys = {str(k) for k in (intro_plan_keys or [])}
    for it in allowed_new:
        k = str(it.get("key") or "")
        if k and k not in plan_keys:
            problems.append(
                f"allowed_new: {k!r} not in the router introduce plan"
            )

    budgets = data.get("budgets")
    if not isinstance(budgets, dict):
        problems.append("budgets: must be an object")
        budgets = {}
    else:
        unknown_b = set(budgets) - BUDGET_FIELDS
        if unknown_b:
            problems.append(f"budgets: unknown fields {sorted(unknown_b)}")
        missing_b = BUDGET_FIELDS - set(budgets)
        if missing_b:
            problems.append(f"budgets: missing fields {sorted(missing_b)}")
        for bk, bv in budgets.items():
            if not isinstance(bv, int):
                problems.append(f"budgets.{bk}: must be an int (code number)")

    cf_target = data.get("cf_target")
    if cf_target is not None:
        if not isinstance(cf_target, dict):
            problems.append("cf_target: must be an object or null")
        else:
            unknown_cf = set(cf_target) - CF_TARGET_FIELDS
            if unknown_cf:
                problems.append(
                    f"cf_target: unknown fields {sorted(unknown_cf)}")
            pid = str(cf_target.get("pattern") or "")
            if pid and pid not in allow:
                problems.append(f"cf_target: pattern {pid!r} not in catalog")

    manifest = data.get("session_manifest")
    if not isinstance(manifest, dict):
        problems.append("session_manifest: must be an object")
        manifest = {}
    else:
        unknown_m = set(manifest) - MANIFEST_FIELDS
        if unknown_m:
            problems.append(
                f"session_manifest: unknown fields {sorted(unknown_m)}")

    scene_goal = data.get("scene_goal")
    if scene_goal is not None and not isinstance(scene_goal, dict):
        problems.append("scene_goal: must be an object or null")

    if problems:
        raise ValueError(
            f"lesson_brief schema errors ({len(problems)}):\n"
            + "\n".join(f"- {p}" for p in problems)
        )

    return LessonBrief(
        phase=str(data.get("phase") or ""),
        targets=targets,
        allowed_new=allowed_new,
        banned_asks=[str(x) for x in (data.get("banned_asks") or [])],
        due_frames=due_frames,
        budgets=dict(budgets),
        must_not=[str(x) for x in (data.get("must_not") or [])],
        cf_target=dict(cf_target) if isinstance(cf_target, dict) else None,
        register=str(data.get("register") or ""),
        scene_goal=dict(scene_goal) if isinstance(scene_goal, dict) else None,
        exit_criteria=str(data.get("exit_criteria") or ""),
        output_shape=[str(x) for x in (
            data.get("output_shape") or OUTPUT_SHAPE)],
        session_manifest=dict(manifest),
    )


# ---------------------------------------------------------------------------
# Assembly (pure packaging of existing router decisions — NO new authority)
# ---------------------------------------------------------------------------


def _anchor_text(table: dict, key: str) -> str:
    """Compact anchor string from the association table (R-A/R-E path)."""
    from .association_table import anchor_for

    if key not in (table or {}):
        return ""
    a = anchor_for(table, key)
    if a.get("type") == "cognate":
        return f"cognate:{a.get('cognate_en')}"
    if a.get("type") == "keyword":
        return f"keyword:{a.get('keyword_en')}"
    return ""


def _gloss_text(table: dict, sheet: dict, key: str) -> str:
    from .character_sheet import ERROR_PATTERN_CATALOG

    entry = (table or {}).get(key)
    if isinstance(entry, dict):
        return str(entry.get("gloss_en") or "")
    cat = ERROR_PATTERN_CATALOG.get(key)
    if isinstance(cat, dict):
        return str(cat.get("label") or "")
    for section in ("grammar", "skills"):
        ent = ((sheet or {}).get(section) or {}).get(key)
        if isinstance(ent, dict):
            return str(ent.get("label") or ent.get("name") or "")
    return ""


def _due_for_turn(session, ctx) -> list[tuple[str, str]]:
    """(key, kind) pairs: the DUE_ELICIT_OFFERED event when this turn's
    router offered a due block (the actual decision), else the current due
    queue (max 3, same cap as the router) so the slice still carries due
    inventory on non-flavorable turns."""
    ev = getattr(ctx, "ev", None)
    if ev is not None:
        try:
            from .turn_events import TurnEventKind as EV

            events = ev.find(EV.DUE_ELICIT_OFFERED)
        except Exception:
            events = []
        for e in events:
            keys = list((e.payload or {}).get("keys") or [])
            kinds = list((e.payload or {}).get("kinds") or [])
            if keys:
                return [
                    (str(k), str(kinds[i]) if i < len(kinds) else "lexicon")
                    for i, k in enumerate(keys)
                ]
    from .retrieval_scheduler import due_items

    return [(d.key, d.kind) for d in due_items(session.sheet, max_due=3)]


def _budgets(session, ctx) -> dict:
    """The four budget numbers, from code truth only (round-2 item 4.2:
    'if a budget is 0, inject the number')."""
    mem = session.pedagogy_memory
    ms = session.mode_state
    cooldowns = getattr(ms, "form_focus_cooldown", None) or {}
    try:
        ff_cooldown = max(int(v) for v in cooldowns.values())
    except (ValueError, TypeError):
        ff_cooldown = 0
    # §2.1a: ≤1 content-uptake deferral per 3 teaching turns, never
    # consecutive — the ≥3-turn gap field in ModeSessionState is the truth.
    gap = int(getattr(ms, "learner_turn_index", 0)) - int(
        getattr(ms, "content_uptake_last_turn", -999))
    # checker_left mirrors code's hard-break gate (B0 countersign AMEND #1,
    # 2026-07-30): CC is always a hard break (HARD_BREAK_MODES), so residual
    # slots are 0 whenever ANOTHER hard break is still inside the shared
    # ≤1-per-3-turns window. Do NOT key only on last_hard_mode ==
    # comprehension_check (that over-reports 1 after form_focus /
    # association / repair while select_mode still blocks CC — a DATA lie
    # vs code).
    ts = int(getattr(ms, "turns_since_hard_break", 999))
    hb = int(getattr(ms, "hard_breaks_this_session", 0) or 0)
    checker_left = 0 if (hb > 0 and ts < 3) else 1
    return {
        "introduce_left": int(mem.intro_budget_remaining()),
        "form_focus_cooldown": ff_cooldown,
        "content_uptake_left": 1 if gap >= 3 else 0,
        "checker_left": checker_left,
    }


def assemble_lesson_brief(session, ctx) -> LessonBrief:
    """Package this turn's code decisions into a validated LessonBrief.

    Inputs are EXISTING router products only: ctx.decision (select_mode),
    ctx.intro_plan (introduce router), the due queue / DUE_ELICIT_OFFERED
    event, phase state, pedagogy memory, mode-state budgets, task state.
    No model call; no invented targets (§3.3 path A).
    """
    from .retrieval_scheduler import frames_seen_of

    table = getattr(session, "association_table", None) or {}
    sheet = session.sheet
    mem = session.pedagogy_memory
    decision = ctx.decision
    dec_mode = decision.mode.value if decision is not None else "conversation"
    dec_targets = (decision.targets or {}) if decision is not None else {}

    due = _due_for_turn(session, ctx)
    due_frames = [
        {
            "key": k,
            "kind": kind,
            "avoid_frames": list(frames_seen_of(sheet, k, kind)),
        }
        for k, kind in due
    ]

    targets: list[dict] = []
    seen_keys: set[str] = set()
    for k, kind in due:
        if k in seen_keys:
            continue
        seen_keys.add(k)
        targets.append({
            "key": k,
            "gloss": _gloss_text(table, sheet, k),
            "anchor": _anchor_text(table, k),
            "move": "elicit",
        })

    intro_plan = getattr(ctx, "intro_plan", None)
    allowed_new: list[dict] = []
    if intro_plan is not None:
        allowed_new.append({
            "key": intro_plan.key,
            "rule_id": intro_plan.rule_id,
            "anchor": _anchor_text(table, intro_plan.key),
        })
        if intro_plan.key not in seen_keys:
            seen_keys.add(intro_plan.key)
            targets.append({
                "key": intro_plan.key,
                "gloss": _gloss_text(table, sheet, intro_plan.key),
                "anchor": _anchor_text(table, intro_plan.key),
                "move": "introduce",
            })

    # CF target: only when the router made it this turn's move (§1.1 —
    # mode decision, never a fresh judgment here).
    cf_target: dict | None = None
    if dec_mode in ("cf_recast", "form_focus"):
        pid = str(dec_targets.get("error_pattern") or "")
        if pid:
            from .character_sheet import ERROR_PATTERN_CATALOG

            cf_target = {
                "pattern": pid,
                "form_id": (ERROR_PATTERN_CATALOG.get(pid) or {}).get(
                    "form_id"),
                "move": "recast" if dec_mode == "cf_recast"
                else "form_focus_contrast",
            }
            if pid not in seen_keys:
                seen_keys.add(pid)
                targets.append({
                    "key": pid,
                    "gloss": _gloss_text(table, sheet, pid),
                    "anchor": "",
                    "move": cf_target["move"],
                })

    # Register: the zero-register overlay condition the gate already
    # threads (blank sheet, no spanish_ok yet) — else adult informal A1.
    blank_zero = bool(
        getattr(ctx, "blank", False)
        and "spanish_ok" not in set(getattr(ctx, "sigs", set()) or set())
    )
    register = (
        "true-zero: English orientation, glossed tiny Spanish"
        if blank_zero else "adult informal A1 (tú), Spanish-first"
    )

    # Scene goal (task runtime state — code-owned).
    scene_goal: dict | None = None
    task_state = getattr(session, "task_state", None)
    if task_state is not None:
        scene_goal = {
            "scene_id": str(getattr(task_state, "scene_id", "") or ""),
            "status": str(getattr(task_state, "status", "") or ""),
        }

    phase_state = session.phase_state
    activity = str(getattr(ctx, "activity", "") or
                   phase_state.current_activity())
    try:
        budget_total = int(
            phase_state.plan.phases[phase_state.index].turn_budget)
    except (AttributeError, IndexError, TypeError, ValueError):
        budget_total = 0
    exit_criteria = (
        f"phase {activity}: {int(phase_state.turns_in_phase)}"
        f"/{budget_total} consuming turns used"
    )

    from .character_sheet import active_error_patterns

    manifest = {
        "introduced_this_session": list(mem.introduced_this_session),
        "cf_targets": [
            str(e.get("id")) for e in (active_error_patterns(sheet) or [])
            if isinstance(e, dict) and e.get("id")
        ],
        "still_fail_count": int(
            getattr(session, "gate_still_fail_count", 0) or 0),
        "phase_id": f"{int(phase_state.index)}:{activity}",
    }

    data = {
        "phase": activity,
        "targets": targets,
        "allowed_new": allowed_new,
        "banned_asks": sorted(set(mem.asked_topics) | set(mem.asked)),
        "due_frames": due_frames,
        "budgets": _budgets(session, ctx),
        "must_not": list(MUST_NOT),
        "cf_target": cf_target,
        "register": register,
        "scene_goal": scene_goal,
        "exit_criteria": exit_criteria,
        "output_shape": list(OUTPUT_SHAPE),
        "session_manifest": manifest,
    }
    return parse_lesson_brief(
        data,
        table=table,
        sheet=sheet,
        intro_plan_keys=[intro_plan.key] if intro_plan is not None else [],
    )
