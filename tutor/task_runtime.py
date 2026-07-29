"""ConvergentTaskRuntime — pure task state for single-exit info-gap scenes.

r6 Rank-4 spec (docs/pedagogy-research-r6-practice-mix.md §5): each scene runs
ONE primary task with a machine-checkable exit. Info-gap/jigsaw tasks beat
open opinion chat for interaction quality (Pica, Kanagy & Falodun task
typology; Ellis 2003/2009), and the r6 adjudication (C6/AMEND) ruled the old
opportunistic multi-goal scenes a weak opinion-gap — hence a single convergent
exit with slots the learner must OBTAIN by asking in Spanish, against info the
tutor privately holds. Per the r6 adjudication, profile hooks are STRUCK:
content binds to pack topics + sheet lexicon only.

Authority exceeds perception: this module (pure code, stdlib only, NO model
calls) owns slot filling, exit evaluation and the teacher-facing task
contract; the model performs the Spanish — role-playing the holder of the
private info without volunteering it. Integration wiring into the session
loop happens in a later pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Historical home of phrase_present — the implementation now lives in
# tutor/textnorm.py (Phase 2, docs/reviews-architecture-refactor.md);
# re-exported here because tests and callers import it from task_runtime.
# noqa: F401 (re-export façade).
from .textnorm import phrase_present  # noqa: F401


@dataclass
class TaskState:
    """Code-owned state of one convergent task (JSON-serializable)."""

    scene_id: str
    status: str = "open"  # "open" | "done"
    slots_filled: dict[str, str] = field(default_factory=dict)
    turns_on_task: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "status": self.status,
            "slots_filled": dict(self.slots_filled),
            "turns_on_task": self.turns_on_task,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> "TaskState":
        d = d or {}
        status = d.get("status")
        if status not in ("open", "done"):
            status = "open"
        slots = d.get("slots_filled")
        try:
            turns = int(d.get("turns_on_task") or 0)
        except (TypeError, ValueError):
            turns = 0
        return cls(
            scene_id=str(d.get("scene_id") or ""),
            status=status,
            slots_filled=(
                {str(k): str(v) for k, v in slots.items()}
                if isinstance(slots, dict) else {}
            ),
            turns_on_task=turns,
        )


def _slots(scene: dict | None) -> list[dict]:
    pe = (scene or {}).get("primary_exit")
    if not isinstance(pe, dict):
        return []
    return [
        s for s in (pe.get("slots") or [])
        if isinstance(s, dict) and isinstance(s.get("id"), str) and s.get("id")
    ]


def required_slot_ids(scene: dict | None) -> list[str]:
    """The info-gap slots that gate completion (learner_must_obtain).

    Falls back to all slot ids when learner_must_obtain is absent/empty.
    """
    slot_ids = [s["id"] for s in _slots(scene)]
    lmo = (scene or {}).get("learner_must_obtain")
    if isinstance(lmo, list):
        wanted = [str(x) for x in lmo if str(x) in slot_ids]
        if wanted:
            return wanted
    return slot_ids


def task_from_scene(scene: dict | None) -> TaskState | None:
    """Open a TaskState for a scene, or None for legacy scenes without a
    primary_exit (they keep working on the old opportunistic path)."""
    if not isinstance(scene, dict):
        return None
    if not _slots(scene):
        return None
    return TaskState(scene_id=str(scene.get("id") or ""))


def evaluate_turn(state: TaskState, learner_text: str, scene: dict) -> TaskState:
    """Pure per-turn evaluation: fill slots whose evidence_any matches the
    learner's text (boundary-disciplined), mark done when every
    learner_must_obtain slot is filled. Returns a NEW TaskState; always
    increments turns_on_task. Never model-called; never un-fills a slot."""
    filled = dict(state.slots_filled)
    for slot in _slots(scene):
        sid = slot["id"]
        if sid in filled:
            continue
        for ev in (slot.get("evidence_any") or []):
            if isinstance(ev, str) and phrase_present(ev, learner_text):
                filled[sid] = ev
                break
    required = required_slot_ids(scene)
    done = state.status == "done" or (
        bool(required) and all(r in filled for r in required)
    )
    return TaskState(
        scene_id=state.scene_id,
        status="done" if done else "open",
        slots_filled=filled,
        turns_on_task=state.turns_on_task + 1,
    )


def task_instructions(state: TaskState, scene: dict) -> str:
    """Teacher-facing task block: the goal, remaining slots, and the private
    info the tutor holds (with the never-volunteer directive). On done, the
    celebrate-and-close line replaces the slot machinery."""
    pe = (scene or {}).get("primary_exit") or {}
    desc = str(pe.get("description") or "").strip()
    lines = ["TASK (single convergent exit — r6 Rank-4):"]
    if desc:
        lines.append(f"Goal: {desc}")
    if state.status == "done":
        lines.append("TASK COMPLETE — celebrate briefly, then close the scene.")
        return "\n".join(lines)
    slots = _slots(scene)
    filled_ids = [s["id"] for s in slots if s["id"] in state.slots_filled]
    remaining_ids = [s["id"] for s in slots if s["id"] not in state.slots_filled]
    if filled_ids:
        lines.append("Slots already filled: " + ", ".join(filled_ids) + ".")
    if remaining_ids:
        lines.append("Slots remaining: " + ", ".join(remaining_ids) + ".")
    private = (scene or {}).get("tutor_private_info")
    if isinstance(private, dict) and private:
        lines.append(
            "You privately hold the answers below — "
            "reveal ONLY when the learner asks in Spanish; never volunteer:"
        )
        for sid in [s["id"] for s in slots if s["id"] in private]:
            lines.append(f"- {sid}: {private[sid]}")
    lines.append(f"Turns on task so far: {state.turns_on_task}.")
    return "\n".join(lines)
