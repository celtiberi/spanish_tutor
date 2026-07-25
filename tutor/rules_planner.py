"""Rules-only pedagogical planner → PlanCard (soft constraints).

Picks *what to elicit next* and what to avoid. Does **not** script the dialogue —
the executor LLM writes natural conversation under these constraints.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from .character_sheet import (
    ERROR_PATTERN_CATALOG,
    active_error_patterns,
    detect_error_pattern_hits,
)
from .pedagogy_contract import is_blank_learner
from .plan_card import (
    PlanCard,
    PlanTargets,
    fallback_diagnostic_card,
    gate_plan_card,
)

if TYPE_CHECKING:
    from .session_memory import SessionMemory


def _scaffold_for_sheet(sheet: dict) -> str:
    rec = sheet.get("receptive") or {}
    if not rec.get("needs_english_scaffold", True):
        return "mostly_es"
    return "es_forward"


def probe_signals(learner: str) -> set[str]:
    """What the *current utterance* already shows."""
    low = (learner or "").lower()
    s: set[str] = set()
    if not low.strip():
        return s
    if re.search(r"\b(hola|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches)\b", low):
        s.add("greet")
    if re.search(r"\bestoy\b", low):
        s.add("estoy")
    if re.search(r"\bme\s+llamo\b", low):
        s.add("name")
    if re.search(r"\bc[oó]mo\s+te\s+llamas\b", low):
        s.add("ask_name")
    if re.search(r"\bc[oó]mo\s+est[aá]s\b", low):
        s.add("ask_how")
    if re.search(r"\bme\s+gusta\b", low):
        s.add("gusta")
    if re.search(r"\bsoy\s+de\b", low):
        s.add("origin")
    if re.search(r"\b(gracias|por\s+favor|adi[oó]s|hasta\s+luego)\b", low):
        s.add("polite")
    if re.search(r"\b(caf[eé]|bote|barco|r[ií]o|comida|m[uú]sica)\b", low):
        s.add("topic_vocab")
    es_hits = len(re.findall(
        r"\b(hola|estoy|llamo|llamas|gracias|gusta|soy|tengo|bien|sí|si|no|"
        r"buenos|buenas|adiós|adios|dónde|donde|cómo|como)\b",
        low,
    ))
    en_words = len(re.findall(r"\b[a-z]{3,}\b", low))
    if en_words >= 3 and es_hits == 0:
        s.add("english_only")
    if es_hits >= 2 or (es_hits >= 1 and len(low.split()) <= 6):
        s.add("spanish_ok")
    if len(s & {"greet", "estoy", "name", "ask_name", "gusta", "origin"}) >= 2:
        s.add("multi_skill")
    # Meta: they noticed a loop
    if re.search(r"\balready\s+asked\b|\bya\s+(me\s+)?pregunt", low):
        s.add("loop_complaint")
    return s


def plan_turn(
    sheet: dict,
    *,
    learner: str = "",
    is_open: bool = False,
    memory: SessionMemory | None = None,
) -> PlanCard:
    """Produce a gated PlanCard: next elicit intent + constraints (not a script)."""
    learner = (learner or "").strip()
    hits = detect_error_pattern_hits(learner) if learner else []
    hit_ids = [pid for pid, _ in hits]
    scaffold = _scaffold_for_sheet(sheet)
    blank = is_blank_learner(sheet)
    active = active_error_patterns(sheet)
    nb = sheet.get("next_best") or {}
    sig = probe_signals(learner)

    shown = set(memory.shown) if memory else set()
    asked = set(memory.asked) if memory else set()
    # Merge this turn's signals into local view for branching
    for s in sig:
        if s in (
            "greet", "estoy", "name", "ask_name", "gusta", "origin",
            "spanish_ok", "multi_skill",
        ):
            shown.add(s if s != "ask_name" else "ask_name")
            if s == "ask_name":
                shown.add("ask_name")
            if s == "name":
                shown.add("name")
            if s == "origin":
                shown.add("origin")
            if s == "estoy":
                shown.add("estoy")
            if s == "greet":
                shown.add("greet")
            if s == "gusta":
                shown.add("gusta")

    def not_asked(*keys: str) -> bool:
        return not any(k in asked for k in keys)

    def not_shown(*keys: str) -> bool:
        return not any(k in shown for k in keys)

    # --- Open ---
    # Suggest hola image; teach_assets.decide_teach_image may still reject later.
    if is_open or (blank and not learner):
        return _gated(PlanCard(
            phase="diagnostic",
            move="model_try",
            models=["¡Hola!", "Estoy bien — ¿y tú?"],
            try_prompt="Open a real Spanish greeting and ask how they are.",
            english_frame="",
            targets=PlanTargets(
                form_id="present_estar_person",
                can_do="IP-04",
                concepts=["hola", "estoy_bien"],
            ),
            image_concept="hola",  # suggestion: wave binds meaning on first open
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=8,
            reason="comm_open",
            sheet_update_hints=["observe_greeting", "observe_estoy"],
        ))

    # --- They complained about a loop ---
    if "loop_complaint" in sig:
        return _gated(_free_chat_card(
            scaffold,
            reason="loop_recovery",
            try_prompt="Apologize briefly and ask something NEW (food, coffee, boat, music).",
            can_do=nb.get("can_do") or "IP-06",
            avoid_keys=["ask_how", "ask_name"],
        ))

    # --- Form error ---
    if hit_ids:
        pid = hit_ids[0]
        cat = ERROR_PATTERN_CATALOG.get(pid) or {}
        snippet = hits[0][1] if hits else ""
        good = _good_models_for_pattern(pid, cat)
        return _gated(PlanCard(
            phase="teach_form",
            move="recast_retry",
            models=good,
            try_prompt=(
                f"Recast their error naturally, model correct form, "
                f"then ask a real question that uses: {good[0]}"
            ),
            recast_of=snippet or pid,
            targets=PlanTargets(
                form_id=cat.get("form_id"),
                error_pattern=pid,
                can_do=(cat.get("can_dos") or [None])[0],
                concepts=_concepts_for_pattern(pid),
            ),
            scaffold=scaffold,
            allow_new_topic=False,
            max_sentences=7,
            reason=f"error_hit:{pid}",
            sheet_update_hints=[f"error:{pid}"],
        ))

    # --- Next probe by priority, skipping already shown/asked ---
    # 1) If they asked our name → answer + new topic
    if "ask_name" in sig or (shown & {"ask_name"} and not_asked("ask_gusta", "ask_origin")):
        if not_shown("gusta") and not_asked("ask_gusta"):
            return _gated(PlanCard(
                phase="chat_stretch",
                move="model_try",
                models=["Me llamo Sofía.", "Me gusta el café."],
                try_prompt="Answer their name question in Spanish, then ask what they like (café, música…).",
                english_frame="",
                targets=PlanTargets(can_do="IP-06", concepts=["me_gusta"]),
                scaffold=scaffold,
                allow_new_topic=True,
                max_sentences=8,
                reason="reply_name_then_gusta",
                sheet_update_hints=["observe_gusta"],
            ))

    # 2) Name given → origin or preference (not re-ask name)
    if shown & {"name"} and not_shown("origin") and not_asked("ask_origin"):
        return _gated(PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["¡Mucho gusto!", "Yo soy de Colombia.", "¿De dónde eres?"],
            try_prompt="React to their name warmly in Spanish; ask where they're from.",
            english_frame="",
            targets=PlanTargets(
                can_do="IP-07",
                form_id="present_ser",
                concepts=["soy_de"],
            ),
            image_concept="soy_de",  # map/place association when first introducing origin
            scaffold=scaffold,
            allow_new_topic=True,
            max_sentences=8,
            reason="name_to_origin",
            sheet_update_hints=["observe_origin"],
        ))

    # 3) Origin given → free preference / life chat (café image only if decision allows)
    if shown & {"origin"} and not_asked("ask_gusta"):
        return _gated(PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["¡Qué interesante!", "A mí me gusta el café.", "¿Qué te gusta?"],
            try_prompt="React to where they're from; ask about likes (food, coffee, music, boat).",
            english_frame="",
            targets=PlanTargets(can_do="IP-06", concepts=["me_gusta", "cafe"]),
            image_concept="cafe",  # suggestion; decision may skip if rate-limited / already shown
            scaffold=scaffold,
            allow_new_topic=True,
            max_sentences=8,
            reason="origin_to_gusta",
            sheet_update_hints=["observe_gusta"],
        ))

    # 4) Greet+estoy or multi_skill without name yet
    if (
        (shown & {"estoy"} or shown & {"multi_skill"} or ("greet" in sig and "estoy" in sig))
        and not_shown("name")
        and not_asked("ask_name")
    ):
        return _gated(PlanCard(
            phase="chat_stretch",
            move="associate",
            models=["Me llamo Sofía.", "¿Y tú?"],
            try_prompt="Continue the chat; naturally ask their name in Spanish.",
            english_frame="",
            targets=PlanTargets(can_do="IP-03", concepts=["me_llamo"]),
            image_concept="me_llamo",  # first name form — associate gesture
            scaffold=scaffold,
            allow_new_topic=True,
            max_sentences=8,
            reason="chat_ask_name",
            sheet_update_hints=["observe_name"],
        ))

    # 5) Only greet, no estoy yet — social chat; image optional via decision
    if shown & {"greet"} and not_shown("estoy") and not_asked("ask_how"):
        return _gated(PlanCard(
            phase="diagnostic",
            move="model_try",
            models=["Yo estoy bien.", "¿Y tú?"],
            try_prompt="Greet back; ask how they are in natural Spanish.",
            english_frame="",
            targets=PlanTargets(
                form_id="present_estar_person",
                can_do="IP-04",
                concepts=["estoy_bien"],
            ),
            image_concept="estoy_bien",
            scaffold=scaffold,
            allow_new_topic=True,
            max_sentences=7,
            reason="chat_ask_how",
            sheet_update_hints=["observe_estoy"],
        ))

    # 6) English only / stuck — visual helps when English frame is the scaffold
    if "english_only" in sig:
        return _gated(PlanCard(
            phase="diagnostic",
            move="english_frame",
            models=["¡Hola!", "Estoy bien."],
            try_prompt="Offer a friendly Spanish line they can copy or answer; keep it a chat.",
            english_frame="English is ok — here's an easy Spanish bit to try.",
            targets=PlanTargets(can_do="IP-01", concepts=["hola"]),
            image_concept="hola",
            scaffold="en_rescue",
            allow_new_topic=True,
            max_sentences=7,
            reason="english_lifeline",
            sheet_update_hints=["observe_greeting"],
        ))

    # 7) Hot error form focus (if not looping social probes)
    if active and not_asked("ask_gusta"):  # prefer chat over endless error drill
        top = active[0]
        # Only force form focus if count is high
        if int(top.get("count") or 0) >= 2:
            pid = top["id"]
            cat = ERROR_PATTERN_CATALOG.get(pid) or {}
            good = _good_models_for_pattern(pid, cat)
            return _gated(PlanCard(
                phase="teach_form",
                move="model_try",
                models=good,
                try_prompt=f"Weave correct {pid} into a real question; don't only lecture.",
                targets=PlanTargets(
                    form_id=top.get("form_id") or cat.get("form_id"),
                    error_pattern=pid,
                    can_do=(cat.get("can_dos") or [nb.get("can_do")])[0],
                    concepts=_concepts_for_pattern(pid),
                ),
                scaffold=scaffold,
                allow_new_topic=True,
                max_sentences=7,
                reason=f"active_error:{pid}",
                sheet_update_hints=[f"weave:{pid}"],
            ))

    # 8) Default free chat toward weakest can-do
    can_do = nb.get("can_do") or "IP-06"
    # Avoid probes already done
    if can_do == "IP-03" and (shown & {"name"} or asked & {"ask_name"}):
        can_do = "IP-06"
    if can_do == "IP-04" and (shown & {"estoy"} or asked & {"ask_how"}):
        can_do = "IP-07" if not_shown("origin") else "IP-06"
    return _gated(_free_chat_card(scaffold, can_do=can_do, reason=f"free_chat:{can_do}"))


def _free_chat_card(
    scaffold: str,
    *,
    can_do: str = "IP-06",
    reason: str = "free_chat",
    try_prompt: str = "",
    avoid_keys: list[str] | None = None,
) -> PlanCard:
    intents = {
        "IP-01": "Keep a light greeting going; ask something personal and simple in Spanish.",
        "IP-03": "Names in conversation if not already known; otherwise move on.",
        "IP-04": "Wellbeing chat only if not already answered; else new topic.",
        "IP-06": "Talk about likes: coffee, food, music, boat life.",
        "IP-07": "Where from / where now / simple life facts.",
        "IP-08": "Mini role: café or market — stay playful.",
    }
    return PlanCard(
        phase="chat_stretch",
        move="model_try",
        models=[],  # executor invents natural Spanish
        try_prompt=try_prompt or intents.get(can_do, "Continue a real Spanish conversation; one new question."),
        english_frame="",
        targets=PlanTargets(can_do=can_do, concepts=[]),
        scaffold=scaffold,
        allow_new_topic=True,
        max_sentences=10,
        reason=reason,
        sheet_update_hints=[f"can_do:{can_do}"],
    )


def _gated(card: PlanCard) -> PlanCard:
    # Free chat may have empty models — gate must allow
    if not card.models and card.move in ("model_try", "associate", "english_frame"):
        # Provide soft seeds so gate passes; executor may ignore
        card.models = ["(natural Spanish)"]
    g = gate_plan_card(card)
    if g.ok and g.card:
        # Strip placeholder if we used it
        if g.card.models == ["(natural Spanish)"]:
            g.card.models = []
        return g.card
    if not card.models:
        card.models = ["¡Claro!", "¿Y tú?"]
        g2 = gate_plan_card(card)
        if g2.ok and g2.card:
            return g2.card
    return fallback_diagnostic_card()


def _good_models_for_pattern(pid: str, cat: dict) -> list[str]:
    if pid == "estar_yo_estoy_vs_esta":
        # Keep models on the form — avoid dragging in unrelated nouns
        return ["Estoy bien.", "Estoy bien hoy."]
    if pid == "me_llamo_es":
        return ["Me llamo…"]
    if pid == "tengo_not_tango":
        return ["Tengo…"]
    if pid == "soy_de_origin":
        return ["Soy de…"]
    if pid == "ser_estar_confuse":
        return ["Estoy bien.", "Soy de…"]
    return ["Estoy bien."]

def _concepts_for_pattern(pid: str) -> list[str]:
    # Prefer image-worthy ids only when a picture actually helps the form.
    # Abstract person-agreement (estoy) is *not* image-forced on recast.
    return {
        "estar_yo_estoy_vs_esta": [],  # form fix in speech, not a picture
        "me_llamo_es": ["me_llamo"],
        "tengo_not_tango": [],
        "soy_de_origin": ["soy_de"],
        "ser_estar_confuse": [],
    }.get(pid, [])
