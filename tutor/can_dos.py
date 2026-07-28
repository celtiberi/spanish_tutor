"""ACTFL-oriented Novice can-dos for Spanish (product slice).

Source of truth for statements: docs/spanish-can-dos-novice.md
This module is the machine-readable index used by the character sheet.
"""

from __future__ import annotations

# Interpersonal + light interpretive/presentational for live chat.
CAN_DOS: dict[str, dict] = {
    "IP-01": {
        "mode": "interpersonal",
        "band": "NL-NM",
        "statement": "I can greet a peer and respond to a simple greeting.",
        "priority": "high",
        "form_hooks": ["present_estar_person"],
        "coverage_topics": ["greetings_time_of_day"],
        "activity": "natural_open_chat",
    },
    "IP-02": {
        "mode": "interpersonal",
        "band": "NM",
        "statement": "I can greet and ask how someone is in a formal situation.",
        "priority": "medium",
        "form_hooks": ["register_tu_usted"],
        "coverage_topics": ["register_tu_usted", "greetings_time_of_day"],
        "activity": "brief_formal_exchange_in_role",
    },
    "IP-03": {
        "mode": "interpersonal",
        "band": "NL-NM",
        "statement": "I can say my name and ask another person's name.",
        "priority": "high",
        "form_hooks": [],
        "coverage_topics": ["introduce_self"],
        "activity": "introduce_in_conversation",
    },
    "IP-04": {
        "mode": "interpersonal",
        "band": "NL-NM",
        "statement": "I can say how I am and ask how you are with practiced phrases.",
        "priority": "high",
        "form_hooks": ["present_estar_person"],
        "coverage_topics": ["estar_basic"],
        "activity": "small_talk_wellbeing",
    },
    "IP-05": {
        "mode": "interpersonal",
        "band": "NL",
        "statement": "I can end a short exchange politely.",
        "priority": "medium",
        "form_hooks": [],
        "coverage_topics": ["leave_taking"],
        "activity": "close_exchange_naturally",
    },
    "IP-06": {
        "mode": "interpersonal",
        "band": "NM",
        "statement": "I can express simple preferences on familiar topics.",
        "priority": "medium",
        "form_hooks": ["present_regular_ar_er_ir"],
        "coverage_topics": ["food", "preferences"],
        "activity": "share_preferences",
    },
    "IP-07": {
        "mode": "interpersonal",
        "band": "NM",
        "statement": "I can ask and answer simple personal questions.",
        "priority": "medium",
        "form_hooks": ["present_ser", "tener_age_possession"],
        "coverage_topics": ["ser_basic", "family"],
        "activity": "personal_qa_chat",
    },
    "IP-08": {
        "mode": "interpersonal",
        "band": "NM",
        "statement": "I can complete a short social/transactional role task (4–8 turns).",
        "priority": "medium",
        "form_hooks": ["register_tu_usted"],
        "coverage_topics": ["roleplay_tasks"],
        "activity": "mini_roleplay_task",
    },
    "IT-01": {
        "mode": "interpretive",
        "band": "NL-NM",
        "statement": "I can get the gist of a short familiar-topic dialogue.",
        "priority": "high",
        "form_hooks": [],
        "coverage_topics": ["greetings_time_of_day"],
        "activity": "input_plus_meaning_check",
    },
    "IT-02": {
        "mode": "interpretive",
        "band": "NL",
        "statement": "I can recognize high-frequency words and phrases in context.",
        "priority": "low",
        "form_hooks": [],
        "coverage_topics": [],
        "activity": "notice_words_in_input",
    },
    "PR-01": {
        "mode": "presentational",
        "band": "NL-NM",
        "statement": "I can produce a few practiced sentences about myself.",
        "priority": "low",
        "form_hooks": ["present_ser"],
        "coverage_topics": ["introduce_self", "ser_basic"],
        "activity": "short_self_info",
    },
}

# Supporting forms (not can-dos) — focus-on-form only inside communication.
FORM_INVENTORY: dict[str, dict] = {
    "present_estar_person": {
        "supports": ["IP-04"],
        "priority": "high",
        "error_example": "esta bien for 'I am fine'",
    },
    "register_tu_usted": {
        "supports": ["IP-02", "IP-08"],
        "priority": "medium",
        "error_example": "tú forms with a boss/stranger in formal role",
    },
    "present_ser": {
        "supports": ["IP-07", "PR-01"],
        "priority": "medium",
        "error_example": "wrong copula for identity",
    },
    "gender_articles": {
        "supports": ["IP-01"],
        "priority": "low",
        "error_example": "buenos tardes",
    },
    "present_regular_ar_er_ir": {
        "supports": ["IP-06", "IP-07", "IP-08"],
        "priority": "medium",
        "error_example": "wrong person ending",
    },
    "numbers_0_20": {
        "supports": ["IP-07"],
        "priority": "low",
        "error_example": "",
    },
    "tener_age_possession": {
        "supports": ["IP-07"],
        "priority": "medium",
        "error_example": "age with ser",
    },
}

# Legacy skill keys → can-do ids (migrate old sheets / patterns)
LEGACY_SKILL_TO_CANDO = {
    "greet_informal": "IP-01",
    "greet_formal": "IP-02",
    "introduce_self": "IP-03",
    "small_talk_how_are_you": "IP-04",
    "take_leave": "IP-05",
    "simple_preferences": "IP-06",
    "ask_name": "IP-03",
    "can_follow_short_dialogue": "IT-01",
}

# Human activity labels for next_best.stretch (CLT/TBLT shaped)
STRETCH_ACTIVITIES = {
    "open_chat_and_notice": {
        "can_do": None,
        "activity": "open_chat_notice_abilities",
        "description": "Easy conversation; notice what they can already do (CLT).",
    },
    "IP-01": {
        "activity": "natural_open_chat",
        "description": "Greet and respond in real talk — not a greeting quiz.",
    },
    "IP-02": {
        "activity": "brief_formal_exchange_in_role",
        "description": "One natural formal exchange in a role, then move on.",
    },
    "IP-03": {
        "activity": "introduce_in_conversation",
        "description": "Names in the same conversation (Me llamo / ¿Cómo te llamas?).",
    },
    "IP-04": {
        "activity": "small_talk_wellbeing",
        "description": "How are you exchange with recast if needed.",
    },
    "IP-05": {
        "activity": "close_exchange_naturally",
        "description": "Practice leave-taking as the chat winds down.",
    },
    "IP-06": {
        "activity": "share_preferences",
        "description": "Talk likes/preferences on familiar topics.",
    },
    "IP-07": {
        "activity": "personal_qa_chat",
        "description": "Simple personal Q&A (where from, etc.) in scope.",
    },
    "IP-08": {
        "activity": "mini_roleplay_task",
        "description": "Short role task (meet, exchange, leave) — TBLT.",
    },
    "IT-01": {
        "activity": "input_plus_meaning_check",
        "description": "Short dialogue + one meaning question (CI).",
    },
    "change_activity": {
        "can_do": "IP-08",
        "activity": "change_activity_roleplay_or_new_topic",
        "description": "Learner bored — new task or domain, not more of the same.",
    },
}


def default_can_do_entry(can_do_id: str) -> dict:
    meta = CAN_DOS[can_do_id]
    return {
        "status": "unknown",
        "confidence": 0.0,
        "mode": meta["mode"],
        "band": meta["band"],
        "statement": meta["statement"],
        "priority": meta["priority"],
        "evidence": [],
    }


def default_form_entry(form_id: str) -> dict:
    meta = FORM_INVENTORY[form_id]
    return {
        "status": "unknown",
        "confidence": 0.0,
        "priority": meta["priority"],
        "supports": list(meta["supports"]),
        "evidence": [],
    }


def default_skills_block() -> dict:
    return {cid: default_can_do_entry(cid) for cid in CAN_DOS}


def default_grammar_block() -> dict:
    return {fid: default_form_entry(fid) for fid in FORM_INVENTORY}


# Teaching-facing morphology for the web focus rail (not full grammar units).
MORPHOLOGY_BY_FORM: dict[str, dict] = {
    "present_estar_person": {
        "label": "estar — person (states / location)",
        "lemma": "estar",
        "pos": "verb",
        "paradigm": [
            {"form": "estoy", "person": "yo", "gloss": "I am"},
            {"form": "estás", "person": "tú", "gloss": "you are"},
            {"form": "está", "person": "usted/él/ella", "gloss": "you(formal)/he/she is"},
            {"form": "estamos", "person": "nosotros", "gloss": "we are"},
        ],
        "note": "Feelings & place. Not identity (use ser).",
        "watch": "estoy ≠ esta / está",
    },
    "present_ser": {
        "label": "ser — identity / origin",
        "lemma": "ser",
        "pos": "verb",
        "paradigm": [
            {"form": "soy", "person": "yo", "gloss": "I am"},
            {"form": "eres", "person": "tú", "gloss": "you are"},
            {"form": "es", "person": "usted/él/ella", "gloss": "you(formal)/he/she is"},
            {"form": "somos", "person": "nosotros", "gloss": "we are"},
        ],
        "note": "Who/what you are; origin with de.",
        "watch": "Soy de… (not soy Estados Unidos)",
    },
    "register_tu_usted": {
        "label": "tú vs usted",
        "lemma": "address",
        "pos": "register",
        "paradigm": [
            {"form": "¿Cómo estás?", "person": "tú", "gloss": "How are you? (informal)"},
            {"form": "¿Cómo está usted?", "person": "usted", "gloss": "How are you? (formal)"},
            {"form": "¿Cómo te llamas?", "person": "tú", "gloss": "What's your name?"},
            {"form": "¿Cómo se llama?", "person": "usted", "gloss": "What's your name? (formal)"},
        ],
        "note": "Match form to the person (dockmaster, stranger → usted).",
        "watch": "Don't mix tú endings with usted",
    },
    "present_regular_ar_er_ir": {
        "label": "present regular endings (taste)",
        "lemma": "—ar / —er / —ir",
        "pos": "verb",
        "paradigm": [
            {"form": "prefiero", "person": "yo", "gloss": "I prefer (preferir)"},
            {"form": "me gusta", "person": "—", "gloss": "I like (sg thing)"},
            {"form": "me gustan", "person": "—", "gloss": "I like (pl things)"},
            {"form": "tiene", "person": "usted/él", "gloss": "you/he has (tener)"},
        ],
        "note": "Person endings carry meaning; gustar agrees with the thing liked.",
        "watch": "me gusta el café / me gustan los tacos",
    },
    "tener_age_possession": {
        "label": "tener — have / age",
        "lemma": "tener",
        "pos": "verb",
        "paradigm": [
            {"form": "tengo", "person": "yo", "gloss": "I have"},
            {"form": "tienes", "person": "tú", "gloss": "you have"},
            {"form": "tiene", "person": "usted/él", "gloss": "you/he has"},
            {"form": "tenemos", "person": "nosotros", "gloss": "we have"},
        ],
        "note": "Possession, age (tengo X años), time expressions.",
        "watch": "tengo not tango; age with tener not ser",
    },
    "gender_articles": {
        "label": "gender + articles (light)",
        "lemma": "el / la",
        "pos": "article",
        "paradigm": [
            {"form": "el café", "person": "m", "gloss": "the coffee"},
            {"form": "la pizza", "person": "f", "gloss": "the pizza"},
            {"form": "los tacos", "person": "m pl", "gloss": "the tacos"},
            {"form": "rica / rico", "person": "adj", "gloss": "agrees with noun"},
        ],
        "note": "Adjective often matches the noun (la pizza es rica).",
        "watch": "la pizza es rica (not rico)",
    },
    "numbers_0_20": {
        "label": "numbers 0–20",
        "lemma": "números",
        "pos": "numeral",
        "paradigm": [
            {"form": "uno / una", "person": "1", "gloss": "one"},
            {"form": "dos, tres", "person": "2–3", "gloss": "two, three"},
            {"form": "cinco, diez", "person": "5–10", "gloss": "five, ten"},
            {"form": "quince, veinte", "person": "15–20", "gloss": "fifteen, twenty"},
        ],
        "note": "Useful for days, prices, age, counts.",
        "watch": "",
    },
}

# Phrase chunks by can-do (when forms alone aren't enough)
MORPHOLOGY_BY_CANDO: dict[str, dict] = {
    "IP-01": {
        "label": "Greeting chunks",
        "lemma": "saludos",
        "pos": "phrase",
        "paradigm": [
            {"form": "Hola", "person": "—", "gloss": "Hi"},
            {"form": "Buenos días", "person": "—", "gloss": "Good morning"},
            {"form": "Buenas tardes", "person": "—", "gloss": "Good afternoon"},
            {"form": "Mucho gusto", "person": "—", "gloss": "Nice to meet you"},
        ],
        "note": "Social glue — use and move on once easy.",
        "watch": "",
    },
    "IP-03": {
        "label": "Name exchange",
        "lemma": "llamarse",
        "pos": "verb phrase",
        "paradigm": [
            {"form": "Me llamo…", "person": "yo", "gloss": "My name is…"},
            {"form": "Soy…", "person": "yo", "gloss": "I am… (name)"},
            {"form": "¿Cómo te llamas?", "person": "tú", "gloss": "What's your name?"},
            {"form": "¿Cómo se llama?", "person": "usted", "gloss": "What's your name? (formal)"},
        ],
        "note": "Me llamo X — no *me llamo es*.",
        "watch": "me llamo ≠ me llama es",
    },
    "IP-05": {
        "label": "Leave-taking",
        "lemma": "despedidas",
        "pos": "phrase",
        "paradigm": [
            {"form": "Adiós", "person": "—", "gloss": "Goodbye"},
            {"form": "Hasta luego", "person": "—", "gloss": "See you later"},
            {"form": "Hasta mañana", "person": "—", "gloss": "See you tomorrow"},
            {"form": "Muchas gracias", "person": "—", "gloss": "Thank you very much"},
        ],
        "note": "Close the exchange politely.",
        "watch": "",
    },
    "IP-06": {
        "label": "Preferences (gustar / preferir)",
        "lemma": "gustar / preferir",
        "pos": "verb",
        "paradigm": [
            {"form": "Me gusta…", "person": "—", "gloss": "I like… (one thing)"},
            {"form": "Me gustan…", "person": "—", "gloss": "I like… (several)"},
            {"form": "No me gusta…", "person": "—", "gloss": "I don't like…"},
            {"form": "Prefiero…", "person": "yo", "gloss": "I prefer…"},
        ],
        "note": "Gustar agrees with what is liked, not the person.",
        "watch": "me gusta el té / me gustan ambos",
    },
}


def morphology_blocks_for_can_do(can_do_id: str | None) -> list[dict]:
    """Morphology cards to show for the current stretch can-do."""
    blocks: list[dict] = []
    seen: set[str] = set()
    if can_do_id and can_do_id in MORPHOLOGY_BY_CANDO:
        b = dict(MORPHOLOGY_BY_CANDO[can_do_id])
        b["id"] = f"cando:{can_do_id}"
        blocks.append(b)
        seen.add(b["id"])
    if can_do_id and can_do_id in CAN_DOS:
        for fid in CAN_DOS[can_do_id].get("form_hooks") or []:
            if fid in MORPHOLOGY_BY_FORM:
                bid = f"form:{fid}"
                if bid not in seen:
                    b = dict(MORPHOLOGY_BY_FORM[fid])
                    b["id"] = bid
                    b["form_id"] = fid
                    blocks.append(b)
                    seen.add(bid)
    # Always offer at least a light default if empty
    if not blocks and "IP-01" in MORPHOLOGY_BY_CANDO:
        b = dict(MORPHOLOGY_BY_CANDO["IP-01"])
        b["id"] = "cando:IP-01"
        blocks.append(b)
    return blocks


_MODE_TITLES = {
    "placement": "Placement — feel out level",
    "conversation": "Conversation",
    "cf_recast": "Recast — short fix, keep chat",
    "form_focus": "Form focus (hard break)",
    "association": "Association — form ↔ meaning",
    "comprehension_check": "Comprehension check",
    "comprehension_repair": "Comprehension repair — same idea",
    "transfer": "Transfer — same form, new context",
}


def _live_focus_from_mode(mode_decision: dict | None) -> dict:
    """What the tutor is actually doing *this turn* (mode runtime)."""
    md = mode_decision if isinstance(mode_decision, dict) else {}
    mode = (md.get("mode") or "").strip() or "conversation"
    targets = md.get("targets") if isinstance(md.get("targets"), dict) else {}
    reason = (md.get("reason") or "").strip()
    instructions = (md.get("instructions") or "").strip()
    title = _MODE_TITLES.get(mode, mode.replace("_", " ").title())

    # Sharpen title from targets
    if mode == "association":
        concept = targets.get("concept") or targets.get("form") or md.get("image_concept")
        if concept:
            title = f"Associate · {targets.get('form') or concept}"
    elif mode in ("form_focus", "cf_recast"):
        pid = targets.get("error_pattern") or targets.get("form_id") or targets.get("label")
        if pid:
            title = f"{'Form focus' if mode == 'form_focus' else 'Recast'} · {pid}"
    elif mode == "transfer":
        fid = targets.get("form_id") or targets.get("error_pattern")
        title = f"Transfer · {fid}" if fid else title
    elif mode == "comprehension_repair":
        title = "Repair — re-ask same question"

    # One-line "do" for the rail (not the full mode essay)
    do = reason.replace("_", " ") if reason else mode
    if mode == "transfer":
        do = "Same form in a new micro-context"
    elif mode == "conversation" and "known_open" in reason:
        do = "Open from sheet — advance, don't re-probe"
    elif mode == "association":
        do = f"Bind meaning with image · {targets.get('form') or targets.get('concept') or 'concept'}"
    elif mode == "cf_recast":
        do = "Short recast + continue chat"
    elif mode == "form_focus":
        do = "Contrast wrong→right; produce once; exit to transfer"
    elif mode == "comprehension_repair":
        do = "Explain + simpler model; same try (no new topic)"

    why = instructions
    if len(why) > 280:
        why = why[:277] + "…"

    return {
        "mode": mode,
        "mode_reason": reason,
        "title": title,
        "activity": do,
        "why": why or reason or "—",
        "hard_break": bool(md.get("hard_break")),
        "targets": targets,
        "image_concept": md.get("image_concept"),
    }


def morphology_blocks_for_form(form_id: str | None) -> list[dict]:
    """Morphology cards for a grammar form id (e.g. present_estar_person)."""
    if not form_id or form_id not in MORPHOLOGY_BY_FORM:
        return []
    b = dict(MORPHOLOGY_BY_FORM[form_id])
    b["id"] = f"form:{form_id}"
    b["form_id"] = form_id
    return [b]


def build_focus_panel(
    sheet: dict,
    mode_decision: dict | None = None,
) -> dict:
    """Right-rail: **this-turn mode** (primary) + sheet arc (secondary).

    After the mode runtime, the tutor does *not* follow next_best as a script.
    Showing only sheet next_best (e.g. IP-03 names while chatting boat/estoy)
    is misleading — so the pill/title are live mode; sheet stretch is secondary.
    """
    nb = sheet.get("next_best") or {}
    can_do = nb.get("can_do")
    skill = (sheet.get("skills") or {}).get(can_do) or {} if can_do else {}
    meta = CAN_DOS.get(can_do) or {}
    rec = sheet.get("receptive") or {}
    aff = sheet.get("affect") or {}
    live = _live_focus_from_mode(mode_decision)

    from .character_sheet import active_error_patterns

    active_errs = active_error_patterns(sheet)
    err_summary = None
    if active_errs:
        top = active_errs[0]
        err_summary = {
            "id": top["id"],
            "count": top["count"],
            "label": top["label"],
            "teach_hint": top.get("teach_hint"),
            "examples": top.get("last_examples") or [],
        }

    # Morphology: form in play this turn / on sheet — not a stale can-do paradigm
    targets = live.get("targets") or {}
    form_id = targets.get("form_id") or nb.get("form_focus")
    if form_id and form_id not in MORPHOLOGY_BY_FORM:
        # error_pattern ids are not form inventory keys
        form_id = nb.get("form_focus")
    morph = morphology_blocks_for_form(
        form_id if form_id in MORPHOLOGY_BY_FORM else None
    )
    if not morph and nb.get("form_focus") in MORPHOLOGY_BY_FORM:
        morph = morphology_blocks_for_form(nb.get("form_focus"))
    if not morph:
        morph = morphology_blocks_for_can_do(can_do if isinstance(can_do, str) else None)

    # Turn-engaged form wins (incident 2026-07-28: card never updated on
    # dice / "I am making" meta questions). turn_morph stashes the block on
    # the live mode-decision dict; it dies with the next turn's decision.
    turn_block = None
    if isinstance(mode_decision, dict):
        tm = mode_decision.get("_turn_morph")
        if isinstance(tm, dict) and tm.get("paradigm"):
            turn_block = dict(tm)
    if turn_block:
        rest = [
            b for b in morph
            if b.get("id") != turn_block.get("id")
            and (
                not turn_block.get("form_id")
                or b.get("form_id") != turn_block.get("form_id")
            )
        ]
        morph = [turn_block] + rest[:1]

    grammar = sheet.get("grammar") or {}
    for block in morph:
        fid = block.get("form_id")
        if fid and fid in grammar:
            g = grammar[fid]
            block["learner"] = {
                "status": g.get("status"),
                "confidence": g.get("confidence"),
            }

    lex_items = []
    for lemma, meta_l in list((sheet.get("lexicon") or {}).items())[:12]:
        if not isinstance(meta_l, dict):
            continue
        if float(meta_l.get("confidence") or 0) >= 0.1 or meta_l.get("status") not in (
            None, "unknown",
        ):
            lex_items.append({
                "form": lemma.replace("_", " "),
                "status": meta_l.get("status"),
                "confidence": meta_l.get("confidence"),
            })

    # Sheet arc (background) — may disagree with this turn; show separately
    sheet_statement = (
        nb.get("statement")
        or skill.get("statement")
        or meta.get("statement")
        or ""
    )
    primary_is_form = bool(nb.get("form_focus") or nb.get("error_pattern") or err_summary)

    return {
        "focus": {
            # Live (mode runtime) — what the tutor is doing now
            "live": bool(mode_decision),
            "mode": live.get("mode"),
            "mode_reason": live.get("mode_reason"),
            "hard_break": live.get("hard_break"),
            "title": live.get("title") or "Conversation",
            "activity": live.get("activity") or "chat",
            "why": live.get("why") or "—",
            "image_concept": live.get("image_concept"),
            # Sheet stretch (secondary)
            "can_do": can_do,
            "sheet_title": sheet_statement,
            "sheet_activity": nb.get("activity") or nb.get("stretch"),
            "sheet_reason": nb.get("reason"),
            "primary_is_form": primary_is_form,
            "avoid": nb.get("avoid"),
            "reason": live.get("why") or nb.get("reason"),
            "method": nb.get("method") or "CLT/TBLT + CI + focus_on_form",
            "skill_status": skill.get("status") or "unknown",
            "skill_confidence": skill.get("confidence") or 0.0,
            "scaffold": bool(rec.get("needs_english_scaffold", True)),
            "energy": aff.get("energy"),
            # Personal-data capture disabled 2026-07-28: the UI never gets a name.
            "learner_name": None,
            "band": meta.get("band") or skill.get("band"),
            "error_pattern": nb.get("error_pattern") or (
                err_summary["id"] if err_summary else None
            ),
            "form_focus": nb.get("form_focus"),
            "error_focus": err_summary,
        },
        "morphology": morph,
        "lexicon_focus": lex_items[:8],
        "error_patterns_active": active_errs,
    }


def migrate_skills(skills: dict) -> dict:
    """Map legacy skill keys into can-do ids; keep unknown keys lightly."""
    out = default_skills_block()
    if not skills:
        return out
    for k, v in skills.items():
        if not isinstance(v, dict):
            continue
        cid = LEGACY_SKILL_TO_CANDO.get(k, k if k in CAN_DOS else None)
        if not cid:
            continue
        prev = out.get(cid) or default_can_do_entry(cid)
        # keep higher confidence / richer evidence
        conf = max(float(prev.get("confidence") or 0), float(v.get("confidence") or 0))
        merged = {**prev, **{kk: vv for kk, vv in v.items() if kk != "confidence"}}
        merged["confidence"] = conf
        if v.get("status") in ("unknown", "emerging", "fragile", "known", "blocked"):
            # prefer more advanced status if conf high
            if conf >= float(prev.get("confidence") or 0):
                merged["status"] = v.get("status") or prev.get("status")
        # restore can-do metadata
        meta = CAN_DOS[cid]
        merged["mode"] = meta["mode"]
        merged["band"] = meta["band"]
        merged["statement"] = meta["statement"]
        merged["priority"] = meta.get("priority", prev.get("priority"))
        out[cid] = merged
    return out
