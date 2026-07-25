"""Teaching modes + select_mode — code owns when to break from conversation.

See docs/teaching-system.md. Conversation is the outer loop; modes are pedagogy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .character_sheet import (
    ERROR_PATTERN_CATALOG,
    active_error_patterns,
    detect_error_pattern_hits,
    detect_error_pattern_resolves,
)
from .pedagogy_contract import is_blank_learner

# Concrete nouns we can associate with images (must stay in teach_assets lexicon)
ASSOCIATION_NOUNS = frozenset({
    "cafe", "café", "bote", "barco", "musica", "música", "comida", "rio", "río",
})

HARD_BREAK_MODES = frozenset({
    "form_focus",
    "association",
    "comprehension_check",
    "placement",
})


class Mode(str, Enum):
    PLACEMENT = "placement"
    CONVERSATION = "conversation"
    CF_RECAST = "cf_recast"
    FORM_FOCUS = "form_focus"
    COMPREHENSION_CHECK = "comprehension_check"
    ASSOCIATION = "association"
    TRANSFER = "transfer"  # conversation with explicit transfer try


@dataclass
class ModeDecision:
    mode: Mode
    reason: str
    hard_break: bool = False
    targets: dict[str, Any] = field(default_factory=dict)
    scene_ids: list[str] = field(default_factory=list)
    image_concept: str | None = None
    instructions: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


@dataclass
class ModeSessionState:
    """Session-scoped mode runtime (not the character sheet)."""

    hard_breaks_this_session: int = 0
    turns_since_hard_break: int = 999
    last_hard_mode: str | None = None
    form_focus_cooldown: dict[str, int] = field(default_factory=dict)  # pattern_id → turns left
    english_only_streak: int = 0
    open_scene_ids: list[str] = field(default_factory=list)
    scene_modeled: set[str] = field(default_factory=set)  # scene ids that got first model
    last_mode: str | None = None
    last_resolved_form: str | None = None  # form just resolved → transfer next

    def tick(self) -> None:
        self.turns_since_hard_break = min(self.turns_since_hard_break + 1, 999)
        cooled = {}
        for k, v in self.form_focus_cooldown.items():
            if v > 1:
                cooled[k] = v - 1
        self.form_focus_cooldown = cooled

    def note_hard_break(self, mode: Mode) -> None:
        self.hard_breaks_this_session += 1
        self.turns_since_hard_break = 0
        self.last_hard_mode = mode.value

    def set_cooldown(self, pattern_id: str, turns: int = 4) -> None:
        self.form_focus_cooldown[pattern_id] = turns

    def snapshot(self) -> dict[str, Any]:
        return {
            "hard_breaks_this_session": self.hard_breaks_this_session,
            "turns_since_hard_break": self.turns_since_hard_break,
            "last_hard_mode": self.last_hard_mode,
            "form_focus_cooldown": dict(self.form_focus_cooldown),
            "english_only_streak": self.english_only_streak,
            "open_scene_ids": list(self.open_scene_ids),
            "scene_modeled": sorted(self.scene_modeled),
            "last_mode": self.last_mode,
            "last_resolved_form": self.last_resolved_form,
        }


def _affect_energy(sheet: dict) -> str:
    aff = sheet.get("affect") or {}
    return str(aff.get("energy") or "unknown").lower()


def _boredom_high(sheet: dict) -> bool:
    aff = sheet.get("affect") or {}
    return str(aff.get("boredom_risk") or "").lower() == "high"


def _can_hard_break(state: ModeSessionState) -> bool:
    # ≤1 hard break per 3 turns; never two consecutive
    if state.turns_since_hard_break < 3 and state.hard_breaks_this_session > 0:
        # Allow if never broken yet is false; if last turn was hard break, block
        if state.turns_since_hard_break == 0:
            return False
        if state.turns_since_hard_break < 3:
            return False
    return True


def _top_active_error(sheet: dict) -> dict | None:
    active = active_error_patterns(sheet, min_count=2)
    if not active:
        # also hot count ≥2 raw even if weaning logic differs
        for pid, ent in (sheet.get("error_patterns") or {}).items():
            if isinstance(ent, dict) and int(ent.get("count") or 0) >= 2:
                return {
                    "id": pid,
                    "count": int(ent["count"]),
                    "form_id": ent.get("form_id") or (ERROR_PATTERN_CATALOG.get(pid) or {}).get("form_id"),
                    "teach_hint": ent.get("teach_hint") or (ERROR_PATTERN_CATALOG.get(pid) or {}).get("teach_hint") or "",
                    "label": ent.get("label") or pid,
                }
        return None
    return active[0]


def _new_concrete_noun(signals: set[str] | list[str], sheet: dict) -> str | None:
    """Return a concrete noun concept if learner/topic suggests one not in lexicon."""
    lex = sheet.get("lexicon") or {}
    # From signals topic_vocab we don't know which noun — scan is done by caller
    # via obs or explicit. Here: check lexicon missing common boat nouns if
    # topic_vocab in signals.
    if "topic_vocab" not in set(signals):
        return None
    for noun in ("cafe", "bote", "musica", "comida", "rio"):
        entry = lex.get(noun) or lex.get(noun.replace("c", "c"))
        conf = float((entry or {}).get("confidence") or 0) if isinstance(entry, dict) else 0
        if conf < 0.15:
            return noun
    return None


def _noun_from_text(text: str, sheet: dict) -> str | None:
    low = (text or "").lower()
    mapping = {
        "café": "cafe", "cafe": "cafe",
        "bote": "bote", "barco": "bote",
        "música": "musica", "musica": "musica",
        "comida": "comida",
        "río": "rio", "rio": "rio",
    }
    lex = sheet.get("lexicon") or {}
    for needle, concept in mapping.items():
        if needle in low:
            entry = lex.get(concept) or {}
            conf = float(entry.get("confidence") or 0) if isinstance(entry, dict) else 0
            if conf < 0.2:
                return concept
    return None


def _scene_needs_model(
    open_scenes: list[dict],
    state: ModeSessionState,
) -> dict | None:
    for sc in open_scenes or []:
        sid = sc.get("id") or ""
        if sid and sid not in state.scene_modeled:
            return sc
    return None


def select_mode(
    sheet: dict,
    *,
    observations: dict | None = None,
    is_open: bool = False,
    learner: str = "",
    mode_state: ModeSessionState | None = None,
    open_scenes: list[dict] | None = None,
) -> ModeDecision:
    """Deterministic mode selection — first matching guard wins.

    See docs/teaching-system.md § Break-from-conversation policy.
    """
    obs = observations or {}
    state = mode_state or ModeSessionState()
    signals = set(obs.get("signals") or [])
    open_scenes = open_scenes or []
    blank = bool(obs.get("blank_sheet") if "blank_sheet" in obs else is_blank_learner(sheet))
    hits = detect_error_pattern_hits(learner) if learner and not is_open else []
    hit_ids = {pid for pid, _ in hits}
    resolves = set(detect_error_pattern_resolves(learner)) if learner and not is_open else set()
    can_hard = _can_hard_break(state)
    energy = _affect_energy(sheet)

    # 0) Time pressure — no hard break
    if energy == "limited_time":
        if hits:
            return ModeDecision(
                Mode.CF_RECAST,
                reason="time_pressure_inline_recast",
                hard_break=False,
                targets={"error_hits": list(hit_ids)},
                instructions="Short Spanish; recast form errors inline; no mini-lesson.",
            )
        return ModeDecision(
            Mode.CONVERSATION,
            reason="time_pressure_chat",
            instructions="Keep it short; one Spanish question; no drills.",
        )

    # 1) Boredom — new topic chat, never drill
    if _boredom_high(sheet):
        return ModeDecision(
            Mode.CONVERSATION,
            reason="boredom_new_topic",
            instructions="Change topic (boat, café, music, food). No drills. Fun adult chat.",
        )

    # 2) Placement
    if is_open and blank:
        return ModeDecision(
            Mode.PLACEMENT,
            reason="blank_open_placement",
            hard_break=True,
            image_concept="hola",
            instructions=(
                "Wide-ceiling placement: short clear Spanish they can copy, but room for "
                "a stronger learner to show multi-skill Spanish. Not a Hola worksheet."
            ),
            scene_ids=[s.get("id") for s in open_scenes if s.get("id")][:3],
        )

    # 3) Stuck English → association (picture kills English wall)
    eng_streak = state.english_only_streak
    if "english_only" in signals:
        eng_streak = eng_streak + 1
    no_entiendo = bool(
        learner and re_search_no_entiendo(learner)
    )
    if can_hard and (eng_streak >= 2 or no_entiendo):
        concept = _noun_from_text(learner, sheet) or "bote"
        return ModeDecision(
            Mode.ASSOCIATION,
            reason="english_stuck_association",
            hard_break=True,
            image_concept=concept,
            targets={"concept": concept, "form": _form_for_concept(concept)},
            instructions=(
                f"Hard break: show meaning with image for '{concept}'. Spanish form only; "
                "minimal English. Invite them to use the form about the picture."
            ),
        )

    # 4) Error streak → form_focus
    top = _top_active_error(sheet)
    if top and int(top.get("count") or 0) >= 2:
        pid = top["id"]
        if pid not in state.form_focus_cooldown and can_hard:
            cat = ERROR_PATTERN_CATALOG.get(pid) or {}
            return ModeDecision(
                Mode.FORM_FOCUS,
                reason=f"error_streak:{pid}",
                hard_break=True,
                targets={
                    "error_pattern": pid,
                    "form_id": top.get("form_id") or cat.get("form_id"),
                    "teach_hint": top.get("teach_hint") or cat.get("teach_hint") or "",
                    "label": top.get("label") or pid,
                    "good_models": _good_models(pid),
                    "contrast": _contrast_for(pid),
                },
                instructions=(
                    f"Hard break pedagogical grammar for {pid}. Show short contrast "
                    f"(wrong vs right). One choice or produce correct form. Then exit to transfer."
                ),
            )

    # Soft recast: single hit this turn, not hard-break eligible
    if hits and not (top and int(top.get("count") or 0) >= 2):
        pid = hits[0][0]
        return ModeDecision(
            Mode.CF_RECAST,
            reason=f"single_error:{pid}",
            hard_break=False,
            targets={
                "error_pattern": pid,
                "snippet": hits[0][1],
                "good_models": _good_models(pid),
            },
            instructions="Stay in conversation. Recast cleanly; same-form try in meaning.",
        )

    # 5) Just resolved focus form → transfer
    if state.last_resolved_form or (resolves & set((sheet.get("error_patterns") or {}).keys())):
        form = state.last_resolved_form
        if not form and resolves:
            form = next(iter(resolves))
        return ModeDecision(
            Mode.TRANSFER,
            reason="success_transfer",
            hard_break=False,
            targets={"form_id": form, "transfer": True},
            instructions=(
                "They just used the form well. Same form, NEW micro-context "
                "(different place/person/topic). Do not re-drill."
            ),
            scene_ids=[s.get("id") for s in open_scenes if s.get("id")][:2],
        )

    # 6) New concrete noun → association (hard if budget allows) else chat+hint
    noun = _noun_from_text(learner, sheet) or _new_concrete_noun(signals, sheet)
    if noun:
        hard = can_hard and state.turns_since_hard_break >= 3
        return ModeDecision(
            Mode.ASSOCIATION if hard else Mode.CONVERSATION,
            reason=f"new_noun:{noun}",
            hard_break=hard,
            image_concept=noun,
            targets={"concept": noun, "form": _form_for_concept(noun)},
            instructions=(
                f"Bind '{noun}' to meaning (image if present). Use Spanish form in chat; "
                "one try about the referent."
            ),
        )

    # 7) Open scene needs first model
    sc = _scene_needs_model(open_scenes, state)
    if sc and can_hard:
        goal = sc.get("goal") or {}
        inp = sc.get("input") or {}
        return ModeDecision(
            Mode.CONVERSATION,  # introduce via chat with scene models
            reason=f"scene_intro:{sc.get('id')}",
            hard_break=False,
            image_concept=inp.get("image_concept"),
            targets={
                "can_do": goal.get("can_do"),
                "target_forms": goal.get("target_forms") or [],
                "model_lines": inp.get("model_lines") or [],
                "elicit": (sc.get("production") or {}).get("elicit"),
            },
            scene_ids=[sc.get("id")] if sc.get("id") else [],
            instructions=(
                f"Open scene '{sc.get('id')}': model the target lines in natural chat, "
                "then elicit production. Not a flashcard list."
            ),
        )

    # 8) Default conversation
    nb = (sheet.get("next_best") or {})
    return ModeDecision(
        Mode.CONVERSATION,
        reason="default_conversation",
        hard_break=False,
        targets={
            "can_do": nb.get("can_do"),
            "next_best": nb.get("statement") or nb.get("activity"),
        },
        scene_ids=[s.get("id") for s in open_scenes if s.get("id")][:3],
        instructions=(
            "Real Spanish conversation. React to them. One elicit. Teach with model+try. "
            "No re-asking covered probes. Advance or deepen."
        ),
    )


def re_search_no_entiendo(text: str) -> bool:
    import re
    low = (text or "").lower()
    return bool(
        re.search(r"\bno\s+entiendo\b|\bdon'?t\s+understand\b|\bwhat\s+does\s+.+\s+mean\b", low)
    )


def _form_for_concept(concept: str) -> str:
    return {
        "cafe": "el café",
        "bote": "el bote",
        "musica": "la música",
        "comida": "la comida",
        "rio": "el río",
        "hola": "Hola",
        "estoy_bien": "Estoy bien",
        "me_llamo": "Me llamo…",
    }.get(concept, concept)


def _good_models(pid: str) -> list[str]:
    if pid == "estar_yo_estoy_vs_esta":
        return ["Estoy bien.", "Estoy en el bote."]
    if pid == "me_llamo_es":
        return ["Me llamo…"]
    if pid == "soy_de_origin":
        return ["Soy de…"]
    if pid == "ser_estar_confuse":
        return ["Estoy bien.", "Soy de Colombia."]
    return ["Estoy bien."]


def _contrast_for(pid: str) -> dict[str, str]:
    if pid == "estar_yo_estoy_vs_esta":
        return {"avoid": "Yo está bien", "prefer": "Estoy bien", "hint": "With yo use estoy."}
    if pid == "ser_estar_confuse":
        return {"avoid": "Soy bien", "prefer": "Estoy bien", "hint": "Feelings/location → estar."}
    if pid == "me_llamo_es":
        return {"avoid": "Me llamo es…", "prefer": "Me llamo…", "hint": "No es after me llamo."}
    if pid == "soy_de_origin":
        return {"avoid": "Estoy de…", "prefer": "Soy de…", "hint": "Origin → ser de."}
    return {"prefer": "Estoy bien.", "hint": ""}


def mode_executor_brief(decision: ModeDecision) -> str:
    """Short instructions block for the AI tutor."""
    lines = [
        f"MODE: {decision.mode.value}",
        f"REASON: {decision.reason}",
        f"HARD_BREAK: {decision.hard_break}",
        decision.instructions,
    ]
    if decision.targets:
        lines.append(f"TARGETS: {decision.targets}")
    if decision.image_concept:
        lines.append(f"IMAGE_CONCEPT: {decision.image_concept}")
    if decision.scene_ids:
        lines.append(f"OPEN_SCENES: {decision.scene_ids}")
    return "\n".join(lines)
