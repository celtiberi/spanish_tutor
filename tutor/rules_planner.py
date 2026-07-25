"""Rules-only pedagogical planner → PlanCard.

No LLM. Sheet + learner utterance + error hits → closed decision.
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
            return "en_rescue"
        return "es_forward"
    return "mostly_es"


def _skill_conf(sheet: dict, cid: str) -> float:
    sk = (sheet.get("skills") or {}).get(cid) or {}
    try:
        return float(sk.get("confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


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

    # --- Open / blank diagnostic ---
    if is_open or (blank and not learner):
        card = PlanCard(
            phase="diagnostic",
            move="english_frame",
            models=["Hola.", "Estoy bien."],
            try_prompt=(
                "Say **Hola** — or try **Estoy bien** (I am fine) if you can."
            ),
            english_frame=(
                "Hi — I'm your Spanish tutor. We'll start tiny so I can see "
                "what you already know."
            ),
            targets=PlanTargets(
                form_id="present_estar_person",
                can_do="IP-01",
                concepts=["hola", "estoy_bien"],
            ),
            # Primary visual: wave hello → associates Hola without English dump
            image_concept="hola",
            scaffold="en_rescue" if blank else scaffold,
            allow_new_topic=False,
            max_sentences=5,
            reason="diagnostic_open" if is_open else "blank_learner",
            sheet_update_hints=["observe_greeting", "observe_estoy"],
        )
        g = gate_plan_card(card)
        return g.card if g.ok and g.card else fallback_diagnostic_card()

    # --- Same-turn form error → recast + retry ---
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
            english_frame=(
                ""
                if scaffold == "mostly_es"
                else ""
            ),
        )
        g = gate_plan_card(card)
        if g.ok and g.card:
            return g.card

    # --- Still diagnostic if blank but they spoke (English or minimal) ---
    if blank:
        card = _diagnostic_followup(sheet, learner, scaffold, resolves)
        g = gate_plan_card(card)
        return g.card if g.ok and g.card else fallback_diagnostic_card()

    # --- Hot error on sheet (weaning / focus) ---
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
        g = gate_plan_card(card)
        if g.ok and g.card:
            return g.card

    # --- Transfer if form getting usable ---
    form_focus = nb.get("form_focus") or nb.get("error_pattern")
    if form_focus and _form_transfer_ready(sheet, form_focus):
        card = PlanCard(
            phase="transfer",
            move="transfer_try",
            models=_transfer_models(form_focus),
            try_prompt=_transfer_try(form_focus),
            targets=PlanTargets(
                form_id=form_focus if form_focus.startswith("present_") else None,
                error_pattern=nb.get("error_pattern"),
                can_do=nb.get("can_do"),
                concepts=["estoy"] if "estar" in str(form_focus) else [],
            ),
            scaffold=scaffold,
            allow_new_topic=False,
            max_sentences=6,
            reason="transfer_form",
            sheet_update_hints=["observe_transfer"],
        )
        g = gate_plan_card(card)
        if g.ok and g.card:
            return g.card

    # --- next_best stretch with model+try ---
    can_do = nb.get("can_do") or "IP-04"
    card = _card_for_can_do(can_do, nb, scaffold, resolves)
    g = gate_plan_card(card)
    if g.ok and g.card:
        return g.card
    return fallback_diagnostic_card()


def _diagnostic_followup(
    sheet: dict, learner: str, scaffold: str, resolves: list[str],
) -> PlanCard:
    """After first reply on blank sheet: stay tiny, build evidence."""
    low = learner.lower()
    if re.search(r"\bhola\b", low) and not re.search(r"\bestoy\b", low):
        return PlanCard(
            phase="diagnostic",
            move="associate",
            models=["Estoy bien.", "Estoy más o menos."],
            try_prompt="Your turn: **Estoy bien**.",
            english_frame=(
                "¡Muy bien! — *hola* is a greeting (hello). "
                "Next: **Estoy bien** means “I am fine.” "
                "Picture = feeling OK. Then say *Estoy bien*."
            ),
            targets=PlanTargets(
                form_id="present_estar_person",
                can_do="IP-04",
                concepts=["estoy_bien"],
            ),
            image_concept="estoy_bien",
            scaffold="en_rescue",
            allow_new_topic=False,
            max_sentences=6,
            reason="diagnostic_after_hola",
            sheet_update_hints=["observe_estoy"],
        )
    if "estoy" in resolves or re.search(r"\bestoy\b", low):
        return PlanCard(
            phase="diagnostic",
            move="associate",
            # One new form only — association, not a double question dump
            models=["Me llamo Alex.", "Me llamo…"],
            try_prompt="Your turn: **Me llamo** + your name.",
            english_frame=(
                "¡Muy bien! — you used *estoy*. "
                "Next phrase: **Me llamo…** means “My name is…”. "
                "Picture: pointing to myself. Then you say *Me llamo* + your name."
            ),
            targets=PlanTargets(
                can_do="IP-03",
                concepts=["me_llamo"],
            ),
            image_concept="me_llamo",
            scaffold="en_rescue",
            allow_new_topic=False,
            max_sentences=6,
            reason="diagnostic_after_estoy",
            sheet_update_hints=["observe_name"],
        )
    # English or freeze
    return PlanCard(
        phase="diagnostic",
        move="english_frame",
        models=["Hola.", "Estoy bien."],
        try_prompt="Just try one: **Hola** or **Estoy bien**.",
        english_frame=(
            "No problem — Spanish takes time. Copy one short line:"
        ),
        targets=PlanTargets(
            form_id="present_estar_person",
            can_do="IP-01",
            concepts=["hola", "estoy_bien"],
        ),
        scaffold="en_rescue",
        reason="diagnostic_english_or_stuck",
        sheet_update_hints=["observe_greeting", "observe_estoy"],
    )


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
        return f"Di una: **{m0.replace('.', '')}**"
    return f"Your turn — say: **{m0.replace('.', '')}**"


def _concepts_for_pattern(pid: str) -> list[str]:
    return {
        "estar_yo_estoy_vs_esta": ["estoy", "bien"],
        "me_llamo_es": ["me_llamo"],
        "tengo_not_tango": ["tengo"],
        "soy_de_origin": ["soy_de"],
        "ser_estar_confuse": ["estar", "ser"],
    }.get(pid, [])


def _form_transfer_ready(sheet: dict, form_focus: str) -> bool:
    g = (sheet.get("grammar") or {}).get(form_focus) or {}
    try:
        conf = float(g.get("confidence") or 0)
    except (TypeError, ValueError):
        conf = 0.0
    status = (g.get("status") or "").lower()
    return conf >= 0.45 or status in ("emerging", "known", "usable")


def _transfer_models(form_focus: str) -> list[str]:
    if "estar" in str(form_focus):
        return ["Estoy relajado/a.", "Estoy trabajando."]
    return ["Otra frase con la misma forma."]


def _transfer_try(form_focus: str) -> str:
    if "estar" in str(form_focus):
        return "¿Y tú? **Estoy** relajado/a o **estoy** trabajando?"
    return "Try the same form in a new short sentence."


def _card_for_can_do(
    can_do: str, nb: dict, scaffold: str, resolves: list[str],
) -> PlanCard:
    """Map next_best can-do to models + try."""
    catalog = {
        "IP-01": (
            ["Hola.", "Buenos días."],
            "Di: **Hola**.",
            ["hola"],
        ),
        "IP-03": (
            ["Me llamo…", "¿Cómo te llamas?"],
            "Di: **Me llamo** + your name.",
            ["me_llamo"],
        ),
        "IP-04": (
            ["Estoy bien.", "Estoy más o menos."],
            "Di: **Estoy bien**.",
            ["estoy_bien"],
        ),
        "IP-05": (
            ["Adiós.", "Hasta luego."],
            "Di: **Hasta luego**.",
            ["adios"],
        ),
        "IP-06": (
            ["Me gusta el café.", "Me gusta…"],
            "Di: **Me gusta** + something you like.",
            ["me_gusta"],
        ),
        "IP-07": (
            ["Estoy en…", "Soy de…"],
            "Di where you are: **Estoy en**…",
            ["estoy_en", "soy_de"],
        ),
    }
    models, try_p, concepts = catalog.get(
        can_do,
        (
            ["Estoy bien.", "Hola."],
            "Di una frase corta en español.",
            ["hola"],
        ),
    )
    phase = "chat_stretch"
    if can_do in ("IP-01", "IP-04") and _skill_conf_from_nb(nb) < 0.4:
        phase = "teach_form"
    return PlanCard(
        phase=phase,
        move="model_try",
        models=list(models),
        try_prompt=try_p,
        targets=PlanTargets(
            can_do=can_do,
            form_id=nb.get("form_focus"),
            error_pattern=nb.get("error_pattern"),
            concepts=list(concepts),
        ),
        scaffold=scaffold,
        allow_new_topic=False,
        max_sentences=6,
        reason=f"next_best:{can_do}",
        sheet_update_hints=[f"can_do:{can_do}"],
    )


def _skill_conf_from_nb(nb: dict) -> float:
    # Placeholder — planner uses sheet skills in callers when needed
    return 0.3
