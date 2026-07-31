"""SessionPhaseController (thin) — code-owned session practice mix.

Phase 2 of docs/build-plan-pedagogy-engine.md; r6 Rank-2 spec
(docs/pedagogy-research-r6-practice-mix.md §4 + §5) with the r6 Adjudication
amendments: profile hooks are STRUCK — content binding uses pack topic titles
and the ability-sheet lexicon only.

Laws enforced here by construction:
- The controller emits a turn-count PhasePlan and per-turn activity hints; it
  NEVER calls the model, and no engine calls the model through it (sole-
  orchestrator law: one realization path via select_mode → executor).
- The frozen adaptivity guard chain in select_mode has absolute priority; this
  layer only flavors the default/fallthrough path. Guard turns and
  comprehension_repair FREEZE the phase clock (tick(consumed=False)) — they do
  not consume phase budget (r6 §4.2 rule 1).
- cf_recast / form_focus / association / transfer are interventions WITHIN a
  phase (r6 §4.2 rule 5); they consume phase budget but are never suppressed.
- activity_type is decided by code and logged (code decides, model performs).

Single purpose, stdlib only — pack topics are passed IN (no corpus import).
"""

from __future__ import annotations

from dataclasses import dataclass, field

ACTIVITY_TYPES = ("retrieval", "new_input", "task", "free", "close")

# r6 §4.1 default mix (20/30/35/15 of active teaching turns). The close
# phase is not ratio-driven: it is a fixed 1-turn coda appended to EVERY
# plan (PEDAGOGY §1.2, USER-ratified 2026-07-28).
DEFAULT_RATIOS: dict[str, float] = {
    "retrieval": 0.20,
    "new_input": 0.30,
    "task": 0.35,
    "free": 0.15,
}

# Close-phase turn budget (one summary line + one farewell exchange).
CLOSE_TURN_BUDGET = 1

# Blank-sheet placement pathway: new_input-heavy (r6 §4.3 "Phases 1–2 only");
# the placement open itself happens before the plan engages.
BLANK_NEW_INPUT_SHARE = 0.7

# limited_time compression: first phase gets ~40%, the micro-task the rest
# (r6 §4.3 limited_time row, two-phase form).
LIMITED_TIME_FIRST_SHARE = 0.4


@dataclass
class PhaseSpec:
    """One planned phase: activity class + turn budget (+ content refs)."""

    activity: str
    turn_budget: int
    item_refs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "activity": self.activity,
            "turn_budget": int(self.turn_budget),
            "item_refs": list(self.item_refs),
        }


@dataclass
class PhasePlan:
    """Ordered phase sequence for one session."""

    phases: list[PhaseSpec] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"phases": [p.as_dict() for p in self.phases]}


def _affect(sheet: dict) -> dict:
    aff = (sheet or {}).get("affect") if isinstance(sheet, dict) else None
    return aff if isinstance(aff, dict) else {}


def _with_close(phases: list[PhaseSpec]) -> PhasePlan:
    """Append the 1-turn CLOSE phase — every plan gets one (PEDAGOGY §1.2,
    USER-ratified 2026-07-28 after the blind grade's "no arc, no close"
    defect; restores r6's original design).

    Arithmetic (documented choice): borrow the close turn from `free` when
    free has ≥ 2 turns, so the session length stays ≈ the estimate; when free
    is thin (1 turn) or absent (limited_time), close is additive (+1 to the
    estimate) — a close is never bought by zeroing free or deleting a phase.
    """
    for p in phases:
        if p.activity == "free" and p.turn_budget >= 2:
            p.turn_budget -= 1
            break
    phases.append(PhaseSpec("close", CLOSE_TURN_BUDGET))
    return PhasePlan(phases)


def build_phase_plan(
    sheet: dict,
    *,
    due_count: int,
    blank: bool,
    session_turns_estimate: int = 14,
    pack_topics: list[str] | None = None,
) -> PhasePlan:
    """Turn-wise phase plan per r6 ratios + §4.3 adaptations (adjudicated).

    Adaptations (pack topics + sheet state only — no profile hooks):
    - blank sheet → new_input-heavy placement pathway (new_input + free only).
    - affect.energy == limited_time → compress to retrieval + task (new_input
      substitutes for retrieval only when nothing is due; free is skipped).
    - due_count == 0 → park the retrieval phase; its budget moves to free
      so the session length stays ≈ the estimate.
    - due_count >= 3 → retrieval +1 turn, free -1 (min 1).
    - boredom_risk high → task phase runs first after retrieval, item_refs
      seeded from pack topic titles.
    - EVERY plan (blank / limited_time included) ends with a 1-turn close
      phase (_with_close: borrowed from free when free ≥ 2, else additive).
    """
    est = max(4, int(session_turns_estimate))
    topics = [str(t) for t in (pack_topics or []) if t]
    aff = _affect(sheet)
    energy = str(aff.get("energy") or "").lower()

    if blank:
        ni = max(1, round(est * BLANK_NEW_INPUT_SHARE))
        free = max(1, est - ni)
        return _with_close([
            PhaseSpec("new_input", ni),
            PhaseSpec("free", free),
        ])

    if energy == "limited_time":
        first = "retrieval" if due_count > 0 else "new_input"
        first_budget = max(1, round(est * LIMITED_TIME_FIRST_SHARE))
        task_budget = max(1, est - first_budget)
        return _with_close([
            PhaseSpec(first, first_budget),
            PhaseSpec("task", task_budget),
        ])

    budgets = {
        a: max(1, round(est * r)) for a, r in DEFAULT_RATIOS.items()
    }
    if due_count <= 0:
        dropped = budgets.pop("retrieval", 0)
        # Keep session length ≈ estimate: parked retrieval budget → free
        # (Grok countersign AMEND 2a, 2026-07-28: 4+5+(2+3)=14, not 11).
        budgets["free"] = budgets.get("free", 0) + dropped
    elif due_count >= 3:
        budgets["retrieval"] += 1
        budgets["free"] = max(1, budgets["free"] - 1)

    # Boredom re-ordering DELETED 2026-07-30 (junk audit): boredom_risk was
    # set in 0 of 207 real turns — a phase-order branch that never ran.
    order = list(ACTIVITY_TYPES)

    phases: list[PhaseSpec] = []
    for activity in order:
        if activity not in budgets:
            continue
        refs = []
        phases.append(PhaseSpec(activity, budgets[activity], refs))
    return _with_close(phases)


@dataclass
class PhaseState:
    """Session-scoped phase clock over a PhasePlan.

    tick(consumed=False) freezes the clock: comprehension_repair and guard
    turns never consume phase budget. When the plan is exhausted the session
    continues in "free" (current behavior — no prefix).
    """

    plan: PhasePlan
    index: int = 0
    turns_in_phase: int = 0
    frozen_turns: int = 0

    def current_activity(self) -> str:
        if 0 <= self.index < len(self.plan.phases):
            return self.plan.phases[self.index].activity
        return "free"

    def current_item_refs(self) -> list[str]:
        if 0 <= self.index < len(self.plan.phases):
            return list(self.plan.phases[self.index].item_refs)
        return []

    def tick(self, consumed: bool) -> None:
        """Advance the phase clock by one turn.

        consumed=False → guard/repair turn: freeze (budget untouched).
        """
        if not consumed:
            self.frozen_turns += 1
            return
        self.turns_in_phase += 1
        self.advance_if_exhausted()

    def advance_if_exhausted(self) -> bool:
        if self.index >= len(self.plan.phases):
            return False
        if self.turns_in_phase >= int(self.plan.phases[self.index].turn_budget):
            self.index += 1
            self.turns_in_phase = 0
            return True
        return False

    def force_advance(self) -> bool:
        """Caller-decided early exit (e.g. retrieval phase with empty queue)."""
        if self.index >= len(self.plan.phases):
            return False
        self.index += 1
        self.turns_in_phase = 0
        return True

    def snapshot(self) -> dict:
        return {
            "plan": self.plan.as_dict(),
            "index": int(self.index),
            "turns_in_phase": int(self.turns_in_phase),
            "frozen_turns": int(self.frozen_turns),
            "activity": self.current_activity(),
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "PhaseState":
        plan_d = (data or {}).get("plan") or {}
        phases = [
            PhaseSpec(
                activity=str(p.get("activity") or "free"),
                turn_budget=int(p.get("turn_budget") or 1),
                item_refs=[str(r) for r in (p.get("item_refs") or [])],
            )
            for p in (plan_d.get("phases") or [])
            if isinstance(p, dict)
        ]
        return cls(
            plan=PhasePlan(phases),
            index=int((data or {}).get("index") or 0),
            turns_in_phase=int((data or {}).get("turns_in_phase") or 0),
            frozen_turns=int((data or {}).get("frozen_turns") or 0),
        )
