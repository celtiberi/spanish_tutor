"""Teaching modes + select_mode — code owns when to break from conversation.

See docs/teaching-system.md. Conversation is the outer loop; modes are pedagogy.
"""

from __future__ import annotations

import json
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


def _new_concrete_noun(
    signals: set[str] | list[str],
    sheet: dict,
    *,
    images_shown: set[str] | None = None,
) -> str | None:
    """Return a concrete noun concept if learner/topic suggests one."""
    shown = set(images_shown or [])
    lex = sheet.get("lexicon") or {}
    if "topic_vocab" not in set(signals):
        return None
    for noun in ("cafe", "bote", "musica", "comida", "rio"):
        if noun in shown:
            continue
        entry = lex.get(noun) or {}
        conf = float((entry or {}).get("confidence") or 0) if isinstance(entry, dict) else 0
        if conf < 0.35 or noun not in shown:
            return noun
    return None


def _noun_from_text(
    text: str,
    sheet: dict,
    *,
    images_shown: set[str] | None = None,
) -> str | None:
    """First session mention of a concrete noun → associate (even if lexicon knows it)."""
    low = (text or "").lower()
    shown = set(images_shown or [])
    # longer needles first
    pairs = [
        ("río dulce", "rio"),
        ("rio dulce", "rio"),
        ("café", "cafe"),
        ("cafe", "cafe"),
        ("barco", "bote"),
        ("bote", "bote"),
        ("música", "musica"),
        ("musica", "musica"),
        ("comida", "comida"),
        ("río", "rio"),
        ("rio", "rio"),
        ("edificio", "bote"),  # no edificio asset — skip via allowlist below
    ]
    allow = {"cafe", "bote", "musica", "comida", "rio"}
    for needle, concept in pairs:
        if concept not in allow:
            continue
        if needle in low:
            # Associate first time this session even if lexicon confidence is high
            if concept not in shown:
                return concept
            entry = (sheet.get("lexicon") or {}).get(concept) or {}
            conf = float(entry.get("confidence") or 0) if isinstance(entry, dict) else 0
            if conf < 0.25:
                return concept
    return None


def _scene_for_topic(
    open_scenes: list[dict],
    state: ModeSessionState,
    *,
    learner: str = "",
    signals: set[str] | None = None,
) -> dict | None:
    """Pick open scene matching live topic (boat/location/likes) before generic next_best."""
    low = (learner or "").lower()
    sigs = set(signals or [])
    scored: list[tuple[int, dict]] = []
    for sc in open_scenes or []:
        sid = sc.get("id") or ""
        if not sid or sid in state.scene_modeled:
            # still allow modeled scenes if exit not done — soft prefer unmodeled
            pass
        score = 0
        blob = json.dumps(sc, ensure_ascii=False).lower()
        if any(w in low for w in ("bote", "barco", "río", "rio", "guatemala", "dulce")):
            if "bote" in blob or "rio" in blob or "captain" in blob or "boat" in blob:
                score += 3
        if any(w in low for w in ("gusta", "café", "cafe", "música", "musica")):
            if "gusta" in blob or "like" in blob or "cafe" in blob:
                score += 3
        if "estoy" in low or "dónde" in low or "donde" in low or "origin" in sigs:
            if "estar" in blob or "estoy" in blob or "ip-04" in blob or "ip-07" in blob:
                score += 2
        if sid and sid not in state.scene_modeled:
            score += 1
        if score:
            scored.append((score, sc))
    if not scored:
        return _scene_needs_model(open_scenes, state)
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


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
    images_shown: set[str] | list[str] | None = None,
) -> ModeDecision:
    """Deterministic mode selection — first matching guard wins.

    See docs/teaching-system.md § Break-from-conversation policy.
    """
    obs = observations or {}
    state = mode_state or ModeSessionState()
    signals = set(obs.get("signals") or [])
    open_scenes = open_scenes or []
    shown_imgs = set(images_shown or [])
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

    # Soft recast: single hit this turn (still attach image if noun present)
    if hits and not (top and int(top.get("count") or 0) >= 2):
        pid = hits[0][0]
        noun = _noun_from_text(learner, sheet, images_shown=shown_imgs)
        return ModeDecision(
            Mode.CF_RECAST,
            reason=f"single_error:{pid}",
            hard_break=False,
            image_concept=noun,
            targets={
                "error_pattern": pid,
                "snippet": hits[0][1],
                "good_models": _good_models(pid),
                "contrast": _contrast_for(pid),
            },
            instructions=(
                "Stay in conversation. Recast the form error cleanly; same-form try "
                "in meaning. If an image is attached, bind the noun too."
            ),
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

    # 6) Concrete noun first-time this session → association (+ image)
    noun = _noun_from_text(learner, sheet, images_shown=shown_imgs) or _new_concrete_noun(
        signals, sheet, images_shown=shown_imgs
    )
    if noun:
        # Prefer hard association when budget allows; always set image_concept
        hard = can_hard
        return ModeDecision(
            Mode.ASSOCIATION if hard else Mode.CONVERSATION,
            reason=f"new_noun:{noun}",
            hard_break=hard,
            image_concept=noun,
            targets={"concept": noun, "form": _form_for_concept(noun)},
            instructions=(
                f"Bind '{noun}' / {_form_for_concept(noun)} to meaning with the image. "
                "Spanish-forward; one try about the referent. Minimal English."
            ),
        )

    # 7) Topic-matched open scene (before weak next_best)
    sc = _scene_for_topic(
        open_scenes, state, learner=learner, signals=signals,
    ) or _scene_needs_model(open_scenes, state)
    if sc:
        goal = sc.get("goal") or {}
        inp = sc.get("input") or {}
        img = inp.get("image_concept")
        if img and img in shown_imgs:
            img = None  # already shown this session — don't re-wallpaper
        return ModeDecision(
            Mode.CONVERSATION,
            reason=f"scene_goal:{sc.get('id')}",
            hard_break=False,
            image_concept=img,
            targets={
                "can_do": goal.get("can_do"),
                "target_forms": goal.get("target_forms") or [],
                "model_lines": inp.get("model_lines") or [],
                "elicit": (sc.get("production") or {}).get("elicit"),
                "transfer": (sc.get("transfer") or {}).get("elicit"),
                "prefer_over_next_best": True,
            },
            scene_ids=[sc.get("id")] if sc.get("id") else [],
            instructions=(
                f"Pursue open scene goal '{sc.get('id')}' (can-do {goal.get('can_do')}) "
                "in natural chat — not a flashcard list. Prefer this over unrelated "
                "next_best stretches. Model target forms; one elicit; advance if they already can."
            ),
        )

    # 8) Default conversation (next_best is a weak guide only)
    nb = (sheet.get("next_best") or {})
    return ModeDecision(
        Mode.CONVERSATION,
        reason="default_conversation",
        hard_break=False,
        targets={
            "can_do": nb.get("can_do"),
            "next_best": nb.get("statement") or nb.get("activity"),
            "next_best_is_optional": True,
        },
        scene_ids=[s.get("id") for s in open_scenes if s.get("id")][:3],
        instructions=(
            "Real Spanish conversation. React to them first. One elicit. Teach with model+try. "
            "No re-asking covered probes. next_best is optional if the live topic is richer."
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
    if pid == "gender_number_article":
        return ["los edificios", "las casas", "Me gustan los edificios."]
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
    if pid == "gender_number_article":
        return {
            "avoid": "la edificios / me gusta los…",
            "prefer": "los edificios / me gustan los…",
            "hint": "Article and noun must match number/gender; plural often *gustan*.",
        }
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
