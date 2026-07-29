"""PlanCard: structured DTO for the teach-image decision (AI path).

Historical: the rules planner/gate/executor runtime that emitted and
validated PlanCards was DELETED (E4, docs/reviews-architecture-refactor.md,
2026-07-28). The dataclasses survive because the live AI path's image stack
(teach_assets.assets_for_ai_turn / decide_teach_image /
extract_concept_candidates) uses PlanCard/PlanTargets as its decision DTO
until Phase 5 inventory work replaces that shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PLAN_CARD_VERSION = "0.1"


@dataclass
class PlanTargets:
    form_id: str | None = None
    error_pattern: str | None = None
    can_do: str | None = None
    concepts: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "form_id": self.form_id,
            "error_pattern": self.error_pattern,
            "can_do": self.can_do,
            "concepts": list(self.concepts),
        }


@dataclass
class PlanCard:
    """Machine decision for one tutor turn."""

    phase: str
    move: str
    models: list[str]
    try_prompt: str
    version: str = PLAN_CARD_VERSION
    targets: PlanTargets = field(default_factory=PlanTargets)
    english_frame: str = ""
    recast_of: str | None = None
    scaffold: str = "es_forward"
    max_sentences: int = 6
    allow_new_topic: bool = False
    sheet_updates_required: bool = True
    sheet_update_hints: list[str] = field(default_factory=list)
    image_concept: str | None = None
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "phase": self.phase,
            "move": self.move,
            "targets": self.targets.as_dict(),
            "models": list(self.models),
            "try_prompt": self.try_prompt,
            "english_frame": self.english_frame,
            "recast_of": self.recast_of,
            "scaffold": self.scaffold,
            "max_sentences": self.max_sentences,
            "allow_new_topic": self.allow_new_topic,
            "sheet_updates": {
                "required": self.sheet_updates_required,
                "hints": list(self.sheet_update_hints),
            },
            "assets": {"image_concept": self.image_concept},
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PlanCard":
        t = d.get("targets") or {}
        su = d.get("sheet_updates") or {}
        assets = d.get("assets") or {}
        return cls(
            version=str(d.get("version") or PLAN_CARD_VERSION),
            phase=str(d.get("phase") or "diagnostic"),
            move=str(d.get("move") or "model_try"),
            targets=PlanTargets(
                form_id=t.get("form_id"),
                error_pattern=t.get("error_pattern"),
                can_do=t.get("can_do"),
                concepts=list(t.get("concepts") or []),
            ),
            models=[str(x) for x in (d.get("models") or []) if x],
            try_prompt=str(d.get("try_prompt") or ""),
            english_frame=str(d.get("english_frame") or ""),
            recast_of=d.get("recast_of"),
            scaffold=str(d.get("scaffold") or "es_forward"),
            max_sentences=int(d.get("max_sentences") or 6),
            allow_new_topic=bool(d.get("allow_new_topic")),
            sheet_updates_required=bool(su.get("required", True)),
            sheet_update_hints=[str(x) for x in (su.get("hints") or [])],
            image_concept=assets.get("image_concept"),
            reason=str(d.get("reason") or ""),
        )
