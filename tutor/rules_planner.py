"""Rules-only pedagogical planner → PlanCard.

Communicative probes first (CLT). Flashcard ladders only when the learner
is stuck / English-only / zero production. Association images still attach
to new forms — but the *try* is a real conversational move when they can.
"""

from __future__ import annotations

import re
from typing import Any

from .character_sheet import (
    ERROR_PATTERN_CATALOG,
    active_error_patterns,
    detect_error_pattern_hits,
    detect_error_pattern_resolves,
)
from .pedagogy_contract import is_blank_learner
from .plan_card import (
    PlanCard,
    PlanTargets,
    fallback_diagnostic_card,
    gate_plan_card,
)


def _scaffold_for_sheet(sheet: dict) -> str:
    rec = sheet.get("receptive") or {}
    if rec.get("needs_english_scaffold", True):
        if is_blank_learner(sheet):
            return "es_forward"  # still Spanish-forward; EN only as lifeline
        return "es_forward"
    return "mostly_es"


def _skill_conf(sheet: dict, cid: str) -> float:
    sk = (sheet.get("skills") or {}).get(cid) or {}
    try:
        return float(sk.get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def probe_signals(learner: str) -> set[str]:
    """What the *current utterance* already shows (placement, not a drill queue)."""
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
    if re.search(r"\b(gracias|por\s+favor|adi[oó]s|hasta\s+luego)\b", low):
        s.add("polite")
    if re.search(r"\b(caf[eé]|bote|barco|r[ií]o|comida|m[uú]sica)\b", low):
        s.add("topic_vocab")
    # Mostly English (few Spanish content words)
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
    if len(s & {"greet", "estoy", "name", "ask_name", "gusta"}) >= 2:
        s.add("multi_skill")
    return s


def plan_turn(
    sheet: dict,
    *,
    learner: str = "",
    is_open: bool = False,
) -> PlanCard:
    """Produce a gated PlanCard for this turn."""
    learner = (learner or "").strip()
    hits = detect_error_pattern_hits(learner) if learner else []
    resolves = detect_error_pattern_resolves(learner) if learner else []
    hit_ids = [pid for pid, _ in hits]
    scaffold = _scaffold_for_sheet(sheet)
    blank = is_blank_learner(sheet)
    active = active_error_patterns(sheet)
    nb = sheet.get("next_best") or {}
    sig = probe_signals(learner)

    # --- Open: real Spanish exchange, not "say hola if you can" ---
    if is_open or (blank and not learner):
        card = PlanCard(
            phase="diagnostic",
            move="model_try",
            models=["¡Hola! Estoy bien.", "¿Cómo estás?"],
            try_prompt="¿Cómo estás?",
            english_frame=(
                "¡Hola! We'll chat in Spanish — short answers are perfect."
            ),
            targets=PlanTargets(
                form_id="present_estar_person",
                can_do="IP-04",
                concepts=["hola", "estoy_bien"],
            ),
            image_concept="hola",
            scaffold="es_forward",
            allow_new_topic=True,  # conversation, not a worksheet cell
            max_sentences=6,
            reason="comm_open_probe",
            sheet_update_hints=["observe_greeting", "observe_estoy"],
        )
        return _gated(card)

    # --- Form error: recast in conversation, then retry ---
    if hit_ids:
        pid = hit_ids[0]
        cat = ERROR_PATTERN_CATALOG.get(pid) or {}
        snippet = hits[0][1] if hits else ""
        good = _good_models_for_pattern(pid, cat)
        card = PlanCard(
            phase="teach_form",
            move="recast_retry",
            models=good,
            try_prompt=_try_for_pattern(pid, good),
            recast_of=snippet or pid,
            targets=PlanTargets(
                form_id=cat.get("form_id"),
                error_pattern=pid,
                can_do=(cat.get("can_dos") or [None])[0],
                concepts=_concepts_for_pattern(pid),
            ),
            scaffold=scaffold,
            allow_new_topic=False,
            max_sentences=5,
            reason=f"error_hit:{pid}",
            sheet_update_hints=[f"error:{pid}", "observe_retry"],
        )
        return _gated(card)

    # --- Communicative branch from what they just said ---
    if "ask_name" in sig:
        # They asked our name — answer + new real question (NOT re-drill Me llamo)
        card = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["Me llamo Sofía.", "¿Te gusta el café?"],
            try_prompt="¿Te gusta el café? — **Sí, me gusta** / **No, no me gusta**.",
            english_frame=(
                "¡Claro! *¿Cómo te llamas?* = What's your name? "
                "I'm Sofía. Now a preference:"
            ),
            targets=PlanTargets(
                can_do="IP-06",
                concepts=["me_gusta"],
            ),
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=7,
            reason="answered_ask_name_probe_gusta",
            sheet_update_hints=["observe_gusta", "can_do:IP-06"],
        )
        return _gated(card)

    if "name" in sig and "ask_name" not in sig:
        # They gave their name — react, probe origin/preference in Spanish
        name_m = re.search(
            r"me\s+llamo\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
            learner,
            re.I,
        )
        nm = name_m.group(1) if name_m else ""
        card = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=[
                f"¡Mucho gusto{', ' + nm if nm else ''}!",
                "¿De dónde eres?",
                "Yo soy de Colombia.",
            ],
            try_prompt="¿De dónde eres? — **Soy de…**",
            english_frame=(
                f"¡Mucho gusto{', ' + nm if nm else ''}! "
                "*¿De dónde eres?* = Where are you from?"
            ),
            targets=PlanTargets(
                can_do="IP-07",
                form_id="present_ser",
                concepts=["soy_de"],
            ),
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=7,
            reason="name_given_probe_origin",
            sheet_update_hints=["observe_origin", "can_do:IP-07"],
        )
        return _gated(card)

    if "multi_skill" in sig or (
        "greet" in sig and "estoy" in sig
    ):
        # Strong first production — skip flashcard ladder, probe names in chat
        card = PlanCard(
            phase="chat_stretch",
            move="associate",
            models=["Me llamo Sofía.", "¿Cómo te llamas?"],
            try_prompt="¿Cómo te llamas?",
            english_frame=(
                "¡Muy bien! You greeted me and said how you are. "
                "**Me llamo…** = My name is… / **¿Cómo te llamas?** = What's your name?"
            ),
            targets=PlanTargets(
                can_do="IP-03",
                concepts=["me_llamo"],
            ),
            image_concept="me_llamo",
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=7,
            reason="probe_name_after_greeting_estoy",
            sheet_update_hints=["observe_name", "can_do:IP-03"],
        )
        return _gated(card)

    if "greet" in sig and "estoy" not in sig:
        # Only hola — keep chatting about how they are (not a worksheet)
        card = PlanCard(
            phase="diagnostic",
            move="associate",
            models=["Estoy bien.", "¿Y tú? ¿Cómo estás?"],
            try_prompt="¿Cómo estás? — **Estoy bien** / **Estoy más o menos**.",
            english_frame=(
                "¡Hola! **¿Cómo estás?** = How are you? "
                "**Estoy bien** = I am fine."
            ),
            targets=PlanTargets(
                form_id="present_estar_person",
                can_do="IP-04",
                concepts=["estoy_bien"],
            ),
            image_concept="estoy_bien",
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=6,
            reason="probe_how_are_you",
            sheet_update_hints=["observe_estoy"],
        )
        return _gated(card)

    if "estoy" in sig and "greet" not in sig and "name" not in sig:
        card = PlanCard(
            phase="chat_stretch",
            move="associate",
            models=["Me llamo Sofía.", "¿Cómo te llamas?"],
            try_prompt="¿Cómo te llamas?",
            english_frame=(
                "¡Bien! **Me llamo…** = My name is… "
                "Picture = introducing myself."
            ),
            targets=PlanTargets(can_do="IP-03", concepts=["me_llamo"]),
            image_concept="me_llamo",
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=6,
            reason="estoy_then_name_chat",
            sheet_update_hints=["observe_name"],
        )
        return _gated(card)

    if "gusta" in sig or "topic_vocab" in sig:
        card = PlanCard(
            phase="chat_stretch",
            move="model_try",
            models=["A mí me gusta el café.", "¿Y el bote? ¿Te gusta?"],
            try_prompt="¿Qué te gusta? — **Me gusta…**",
            english_frame="Nice — keep going. **Me gusta…** = I like…",
            targets=PlanTargets(can_do="IP-06", concepts=["me_gusta"]),
            scaffold="es_forward",
            allow_new_topic=True,
            max_sentences=7,
            reason="preference_chat",
            sheet_update_hints=["observe_gusta"],
        )
        return _gated(card)

    # English-only / stuck — then we scaffold harder (still a real question)
    if "english_only" in sig or (blank and "spanish_ok" not in sig):
        card = PlanCard(
            phase="diagnostic",
            move="english_frame",
            models=["¡Hola!", "Estoy bien.", "¿Cómo estás?"],
            try_prompt="Try: **Hola** or **Estoy bien** — or answer **¿Cómo estás?**",
            english_frame=(
                "No problem — English is fine for a second. "
                "Here's a tiny Spanish chat move:"
            ),
            targets=PlanTargets(
                can_do="IP-01",
                concepts=["hola", "estoy_bien"],
            ),
            image_concept="hola",
            scaffold="en_rescue",
            allow_new_topic=True,
            max_sentences=6,
            reason="english_scaffold_probe",
            sheet_update_hints=["observe_greeting", "observe_estoy"],
        )
        return _gated(card)

    # Hot error on sheet (weaning)
    if active:
        top = active[0]
        pid = top["id"]
        cat = ERROR_PATTERN_CATALOG.get(pid) or {}
        good = _good_models_for_pattern(pid, cat)
        card = PlanCard(
            phase="teach_form",
            move="model_try",
            models=good,
            try_prompt=_try_for_pattern(pid, good),
            targets=PlanTargets(
                form_id=top.get("form_id") or cat.get("form_id"),
                error_pattern=pid,
                can_do=(cat.get("can_dos") or [nb.get("can_do")])[0],
                concepts=_concepts_for_pattern(pid),
            ),
            scaffold=scaffold,
            allow_new_topic=False,
            max_sentences=6,
            reason=f"active_error:{pid}×{top.get('count')}",
            sheet_update_hints=[f"weave:{pid}"],
        )
        return _gated(card)

    # Known learner / next_best — still model+try but conversational
    can_do = nb.get("can_do") or "IP-07"
    card = _card_for_can_do(can_do, nb, scaffold)
    return _gated(card)


def _gated(card: PlanCard) -> PlanCard:
    g = gate_plan_card(card)
    if g.ok and g.card:
        return g.card
    # Retry with allow_new_topic relaxed if that was the only issue
    if g.errors == ["diagnostic_no_new_topic"]:
        card.allow_new_topic = False
        g2 = gate_plan_card(card)
        if g2.ok and g2.card:
            return g2.card
    return fallback_diagnostic_card()


def _good_models_for_pattern(pid: str, cat: dict) -> list[str]:
    if pid == "estar_yo_estoy_vs_esta":
        return ["Estoy bien.", "Estoy en el bote.", "Yo estoy aquí."]
    if pid == "me_llamo_es":
        return ["Me llamo Alex.", "Me llamo…"]
    if pid == "tengo_not_tango":
        return ["Tengo un café.", "Tengo…"]
    if pid == "soy_de_origin":
        return ["Soy de Guatemala.", "Soy de…"]
    if pid == "ser_estar_confuse":
        return ["Estoy bien.", "Estoy nervioso/a.", "Soy estudiante."]
    return ["Estoy bien.", "Intenta otra vez."]


def _try_for_pattern(pid: str, models: list[str]) -> str:
    m0 = models[0] if models else "…"
    if pid == "estar_yo_estoy_vs_esta":
        return f"¿Y tú? Di: **{m0.replace('.', '')}**"
    return f"Your turn — **{m0.replace('.', '')}**"


def _concepts_for_pattern(pid: str) -> list[str]:
    return {
        "estar_yo_estoy_vs_esta": ["estoy", "bien"],
        "me_llamo_es": ["me_llamo"],
        "tengo_not_tango": ["tengo"],
        "soy_de_origin": ["soy_de"],
        "ser_estar_confuse": ["estar", "ser"],
    }.get(pid, [])


def _card_for_can_do(can_do: str, nb: dict, scaffold: str) -> PlanCard:
    """Map next_best can-do to a *conversational* probe, not a flashcard."""
    catalog: dict[str, tuple[list[str], str, list[str], str, str | None]] = {
        # models, try, concepts, english_frame, image
        "IP-01": (
            ["¡Hola!", "¿Qué tal?"],
            "¿Qué tal?",
            ["hola"],
            "Quick greeting chat:",
            "hola",
        ),
        "IP-03": (
            ["Me llamo Sofía.", "¿Cómo te llamas?"],
            "¿Cómo te llamas?",
            ["me_llamo"],
            "**¿Cómo te llamas?** = What's your name?",
            "me_llamo",
        ),
        "IP-04": (
            ["Estoy bien.", "¿Cómo estás hoy?"],
            "¿Cómo estás hoy?",
            ["estoy_bien"],
            "**¿Cómo estás?** = How are you?",
            "estoy_bien",
        ),
        "IP-05": (
            ["Hasta luego.", "¡Nos vemos!"],
            "Di: **Hasta luego** when you're done — or keep chatting: ¿Qué te gusta?",
            ["adios"],
            "Leave-taking if you need it — or stay:",
            None,
        ),
        "IP-06": (
            ["Me gusta el café.", "¿Te gusta la música?"],
            "¿Qué te gusta?",
            ["me_gusta"],
            "**Me gusta…** = I like…",
            None,
        ),
        "IP-07": (
            ["Estoy en Guatemala.", "¿De dónde eres?"],
            "¿De dónde eres? o ¿Dónde estás?",
            ["soy_de", "estoy_en"],
            "Personal chat: where from / where now?",
            None,
        ),
    }
    models, try_p, concepts, frame, img = catalog.get(
        can_do,
        (
            ["¿Qué te gusta?", "Me gusta…"],
            "¿Qué te gusta?",
            ["me_gusta"],
            "Let's keep chatting:",
            None,
        ),
    )
    return PlanCard(
        phase="chat_stretch",
        move="model_try",
        models=list(models),
        try_prompt=try_p,
        english_frame=frame,
        targets=PlanTargets(
            can_do=can_do,
            form_id=nb.get("form_focus"),
            error_pattern=nb.get("error_pattern"),
            concepts=list(concepts),
        ),
        image_concept=img,
        scaffold=scaffold,
        allow_new_topic=True,
        max_sentences=7,
        reason=f"next_best_chat:{can_do}",
        sheet_update_hints=[f"can_do:{can_do}"],
    )
