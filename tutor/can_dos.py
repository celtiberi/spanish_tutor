"""Can-do / form mechanics over the domain-model DATA.

S10 (full-code-audit 2026-08-03): the content that used to live here as
Python literals — the can-do inventory, theme routing, grammar-form
inventory, paradigms, phrase chunks, stretch-activity labels — is DATA in
``domain/spanish_a1/`` (``can_dos.json`` + ``grammar_forms.json``), loaded
and validated by ``tutor/domain_data.py`` at import.  Editing those files
changes what the teacher teaches and grades; this module keeps only
mechanics (default entries, migration, focus-panel projection).

The public names below are bound from the loader so consumers don't churn;
the JSON is the source of truth.
"""

from __future__ import annotations

from .domain_data import cached_default_domain

_DOMAIN = cached_default_domain()

# Interpersonal + light interpretive/presentational for live chat.
CAN_DOS: dict[str, dict] = _DOMAIN.can_dos

# Journey routing: association-table THEMES whose items visibly support a
# can-do (r8 progress round, docs/pedagogy-research-r8-progress-measurement
# .md, Grok Q3 ruling: themes are content domains, NOT functions — they may
# route supporting items UNDER a can-do, never stand in for one). Unmapped
# themes stay ordinary theme groups on the rail. A theme may serve at most
# ONE can-do (validated at load + in tests).
CAN_DO_THEMES: dict[str, tuple[str, ...]] = _DOMAIN.can_do_themes

THEME_TO_CAN_DO: dict[str, str] = {
    theme: cid for cid, themes in CAN_DO_THEMES.items() for theme in themes
}


# Supporting forms (not can-dos) — focus-on-form only inside communication.
FORM_INVENTORY: dict[str, dict] = _DOMAIN.form_inventory

# Teaching-facing morphology for the web focus rail (not full grammar units).
MORPHOLOGY_BY_FORM: dict[str, dict] = _DOMAIN.morphology_by_form

# Phrase chunks by can-do (when forms alone aren't enough)
MORPHOLOGY_BY_CANDO: dict[str, dict] = _DOMAIN.morphology_by_cando

# Human activity labels for next_best.stretch (CLT/TBLT shaped)
STRETCH_ACTIVITIES: dict[str, dict] = _DOMAIN.stretch_activities

# Legacy skill keys → can-do ids (migrate old sheets / patterns).  Stays in
# CODE: it maps this codebase's own pre-can-do key names, i.e. migration
# machinery, not domain content (S10 call, recorded in the audit stamp).
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


def build_focus_panel(sheet: dict) -> dict:
    """Right-rail: sheet arc + morphology/lexicon projection.

    The live this-turn-mode overlay DELETED 2026-08-03 with the mode
    router (full-code-audit S4): the rail is a projection of the SHEET —
    what the model actually teaches each turn is its own decision and is
    visible in the transcript, not paraphrased by code.
    """
    nb = sheet.get("next_best") or {}
    can_do = nb.get("can_do")
    skill = (sheet.get("skills") or {}).get(can_do) or {} if can_do else {}
    meta = CAN_DOS.get(can_do) or {}
    rec = sheet.get("receptive") or {}
    aff = sheet.get("affect") or {}

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

    # The LIVE morphology card is MODEL-AUTHORED (2026-08-03; merged by
    # conv_session.sheet_public from session.last_morph). The panel adds
    # REFERENCE paradigms projected from the LEARNER RECORD (USER
    # 2026-08-04: "its not giving the morphology of words") — forms the
    # sheet shows in progress (evidence-based state, never next_best /
    # agenda), weakest first, capped at 3.
    grammar_state = sheet.get("grammar") or {}
    working = []
    for fid, g in grammar_state.items():
        if not isinstance(g, dict):
            continue
        # In-progress forms first; KNOWN forms are the fallback tier so the
        # panel never goes blank the moment the learner succeeds (USER
        # 2026-08-04: "its blank only showing lexicon" — both live entries
        # had graduated to known and vanished).
        status = g.get("status")
        if status in ("emerging", "fragile") and fid in MORPHOLOGY_BY_FORM:
            working.append((0, float(g.get("confidence") or 0.0), fid, g))
        elif status == "known" and fid in MORPHOLOGY_BY_FORM:
            working.append((1, -float(g.get("confidence") or 0.0), fid, g))
    working.sort(key=lambda x: (x[0], x[1]))
    morph: list = []
    for _tier, _key, fid, g in working[:3]:
        b = dict(MORPHOLOGY_BY_FORM[fid])
        b["paradigm"] = [dict(r) for r in (b.get("paradigm") or [])]
        b["id"] = fid
        b["form_id"] = fid
        b["live"] = False
        b["kind"] = "from_sheet"
        b["learner"] = {
            "status": g.get("status"),
            "confidence": g.get("confidence"),
        }
        morph.append(b)

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
            # Sheet projection only (mode-runtime "live" keys DELETED
            # 2026-08-03 with the router — full-code-audit S4).
            "title": sheet_statement or "Conversation",
            "activity": nb.get("activity") or nb.get("stretch") or "chat",
            "why": nb.get("reason") or "—",
            "can_do": can_do,
            "sheet_title": sheet_statement,
            "sheet_activity": nb.get("activity") or nb.get("stretch"),
            "sheet_reason": nb.get("reason"),
            "primary_is_form": primary_is_form,
            "avoid": nb.get("avoid"),
            "reason": nb.get("reason"),
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
