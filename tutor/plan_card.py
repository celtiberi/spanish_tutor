"""PlanCard: structured pedagogical decision (new teacher).

The planner emits a PlanCard; the gate validates it; the executor only realizes it.
See docs/new-teacher-plan.md.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PLAN_CARD_VERSION = "0.1"

PHASES = frozenset({
    "diagnostic",
    "teach_form",
    "associate",
    "transfer",
    "chat_stretch",
    "review",
})

MOVES = frozenset({
    "model_try",
    "recast_retry",
    "comprehension_check",
    "associate",
    "transfer_try",
    "english_frame",
    "praise_continue",
})

SCAFFOLDS = frozenset({"en_rescue", "es_forward", "mostly_es"})


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


@dataclass
class GateResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    card: PlanCard | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "card": self.card.as_dict() if self.card else None,
        }


def gate_plan_card(card: PlanCard | dict | None) -> GateResult:
    """Validate a PlanCard. Reject incomplete / off-policy decisions."""
    if card is None:
        return GateResult(ok=False, errors=["missing_card"])
    if isinstance(card, dict):
        try:
            card = PlanCard.from_dict(card)
        except Exception as e:
            return GateResult(ok=False, errors=[f"parse:{e}"])

    errors: list[str] = []
    if card.phase not in PHASES:
        errors.append(f"bad_phase:{card.phase}")
    if card.move not in MOVES:
        errors.append(f"bad_move:{card.move}")
    if card.scaffold not in SCAFFOLDS:
        errors.append(f"bad_scaffold:{card.scaffold}")

    models = [m.strip() for m in card.models if str(m).strip()]
    try_prompt = (card.try_prompt or "").strip()

    production_moves = {
        "model_try", "recast_retry", "transfer_try", "associate", "english_frame",
    }
    if card.move in production_moves:
        if not models:
            errors.append("models_required")
        if not try_prompt:
            errors.append("try_prompt_required")

    if card.move == "recast_retry":
        if not models:
            errors.append("recast_needs_model")
        if not try_prompt:
            errors.append("recast_needs_try")

    if card.phase == "diagnostic":
        if card.scaffold not in ("en_rescue", "es_forward"):
            errors.append("diagnostic_scaffold")
        # Diagnostic should stay tiny
        if card.allow_new_topic:
            errors.append("diagnostic_no_new_topic")

    if card.max_sentences < 1 or card.max_sentences > 12:
        errors.append("max_sentences_range")

    if errors:
        return GateResult(ok=False, errors=errors, card=card)

    # Normalize
    card.models = models
    card.try_prompt = try_prompt
    return GateResult(ok=True, errors=[], card=card)


def fallback_diagnostic_card() -> PlanCard:
    """Safe open when planner/gate fails."""
    return PlanCard(
        phase="diagnostic",
        move="english_frame",
        models=["Hola.", "Estoy bien."],
        try_prompt="Say **Hola** — or try **Estoy bien** (I am fine) if you can.",
        english_frame=(
            "Hi — I'm your Spanish tutor. We'll start tiny so I can see "
            "what you already know."
        ),
        targets=PlanTargets(
            form_id="present_estar_person",
            can_do="IP-01",
            concepts=["hola", "estoy_bien"],
        ),
        image_concept="hola",
        scaffold="en_rescue",
        allow_new_topic=False,
        max_sentences=5,
        reason="fallback_diagnostic",
        sheet_update_hints=["observe_greeting", "observe_estoy"],
    )
