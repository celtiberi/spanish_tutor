"""Turn-engaged morphology for the web Morphology card.

Incident 2026-07-28: the card never updated — build_focus_panel only keyed
morphology off mode targets' form_id / next_best.form_focus, and meta
questions ("digo and dices... breakdown?", "Yo hacer (I am making?)")
produce neither, so the card pinned one static can-do block all session.

This module decides — in CODE (PEDAGOGY.md §1.1) — WHICH verb form the
learner's turn engages:
  1. an error-pattern hit whose catalog entry maps to a form inventory id;
  2. pronoun + bare infinitive ("Yo hacer…") — an attempted conjugation;
  3. a grammar/meta question naming a Spanish form (digo/dices → decir);
  4. an English how-do-I-say / "I am Xing?" aiming at an A1 verb.
No engagement → None (the card keeps its existing fallback).

The result is stashed onto the live mode-decision dict (same object the
session passes to every build_focus_panel repaint), so the block persists
for the turn and is naturally replaced with the next mode decision. The
focus-rail LLM may only fill natural example cells afterwards — it never
picks the form. Pack-aware: A1 present tense only, 4 person rows, no
untaught-tense paradigm dumps.
"""

from __future__ import annotations

import re

# Phase 2 (docs/reviews-architecture-refactor.md): the one Spanish letter
# class lives in textnorm; historical local name kept for the token scan.
from .textnorm import SPANISH_LETTERS as _ES

# A1 present-tense mini-breakdowns (4 canonical persons — never full
# six-person / multi-tense dumps; that is untaught territory at A1).
A1_VERB_MORPH: dict[str, dict] = {
    "decir": {
        "label": "decir — to say",
        "paradigm": [
            {"form": "digo", "person": "yo", "gloss": "I say"},
            {"form": "dices", "person": "tú", "gloss": "you say"},
            {"form": "dice", "person": "usted/él/ella", "gloss": "you(formal)/he/she says"},
            {"form": "decimos", "person": "nosotros", "gloss": "we say"},
        ],
        "note": "Irregular yo: digo. «¿Cómo se dice…?» = How do you say…?",
        "watch": "digo (I say) ≠ dice (he/she says)",
    },
    "hacer": {
        "label": "hacer — to do / make",
        "paradigm": [
            {"form": "hago", "person": "yo", "gloss": "I make / am making"},
            {"form": "haces", "person": "tú", "gloss": "you make"},
            {"form": "hace", "person": "usted/él/ella", "gloss": "you(formal)/he/she makes"},
            {"form": "hacemos", "person": "nosotros", "gloss": "we make"},
        ],
        "note": "Spanish present covers English “am making”: «Hago el desayuno».",
        "watch": "yo hago (not yo hacer)",
    },
    "ir": {
        "label": "ir — to go",
        "paradigm": [
            {"form": "voy", "person": "yo", "gloss": "I go / am going"},
            {"form": "vas", "person": "tú", "gloss": "you go"},
            {"form": "va", "person": "usted/él/ella", "gloss": "you(formal)/he/she goes"},
            {"form": "vamos", "person": "nosotros", "gloss": "we go"},
        ],
        "note": "«Voy a + place»: Voy al río.",
        "watch": "voy a + place (with a)",
    },
    "querer": {
        "label": "querer — to want",
        "paradigm": [
            {"form": "quiero", "person": "yo", "gloss": "I want"},
            {"form": "quieres", "person": "tú", "gloss": "you want"},
            {"form": "quiere", "person": "usted/él/ella", "gloss": "you(formal)/he/she wants"},
            {"form": "queremos", "person": "nosotros", "gloss": "we want"},
        ],
        "note": "«Quiero café» / «Quiero + infinitive»: Quiero comer.",
        "watch": "quiero + thing or + infinitive",
    },
    "comer": {
        "label": "comer — to eat",
        "paradigm": [
            {"form": "como", "person": "yo", "gloss": "I eat / am eating"},
            {"form": "comes", "person": "tú", "gloss": "you eat"},
            {"form": "come", "person": "usted/él/ella", "gloss": "you(formal)/he/she eats"},
            {"form": "comemos", "person": "nosotros", "gloss": "we eat"},
        ],
        "note": "Regular -er endings: -o, -es, -e, -emos.",
        "watch": "",
    },
    "beber": {
        "label": "beber — to drink",
        "paradigm": [
            {"form": "bebo", "person": "yo", "gloss": "I drink"},
            {"form": "bebes", "person": "tú", "gloss": "you drink"},
            {"form": "bebe", "person": "usted/él/ella", "gloss": "you(formal)/he/she drinks"},
            {"form": "bebemos", "person": "nosotros", "gloss": "we drink"},
        ],
        "note": "Regular -er endings: -o, -es, -e, -emos.",
        "watch": "",
    },
    "hablar": {
        "label": "hablar — to speak",
        "paradigm": [
            {"form": "hablo", "person": "yo", "gloss": "I speak"},
            {"form": "hablas", "person": "tú", "gloss": "you speak"},
            {"form": "habla", "person": "usted/él/ella", "gloss": "you(formal)/he/she speaks"},
            {"form": "hablamos", "person": "nosotros", "gloss": "we speak"},
        ],
        "note": "Regular -ar endings: -o, -as, -a, -amos.",
        "watch": "",
    },
    "vivir": {
        "label": "vivir — to live",
        "paradigm": [
            {"form": "vivo", "person": "yo", "gloss": "I live"},
            {"form": "vives", "person": "tú", "gloss": "you live"},
            {"form": "vive", "person": "usted/él/ella", "gloss": "you(formal)/he/she lives"},
            {"form": "vivimos", "person": "nosotros", "gloss": "we live"},
        ],
        "note": "«Vivo en + place»: Vivo en un barco.",
        "watch": "",
    },
}

# estar / ser / tener already have richer pack blocks in can_dos — reuse them
# (keeps learner grammar-status stamping, which keys on form_id).
LEMMA_TO_FORM_ID: dict[str, str] = {
    "estar": "present_estar_person",
    "ser": "present_ser",
    "tener": "tener_age_possession",
}

# Trigger tokens → (lemma, person-of-that-row or None). Ambiguous tokens that
# collide with English or Spanish function words (es, como, come, comes, esta,
# van…) are deliberately absent: better to miss than to flash a wrong card.
_TOKEN_INDEX: dict[str, tuple[str, str | None]] = {
    "decir": ("decir", None), "digo": ("decir", "yo"), "dices": ("decir", "tú"),
    "dice": ("decir", "usted/él/ella"), "decimos": ("decir", "nosotros"),
    "hacer": ("hacer", None), "hago": ("hacer", "yo"), "haces": ("hacer", "tú"),
    "hace": ("hacer", "usted/él/ella"), "hacemos": ("hacer", "nosotros"),
    "ir": ("ir", None), "voy": ("ir", "yo"), "vas": ("ir", "tú"),
    "va": ("ir", "usted/él/ella"), "vamos": ("ir", "nosotros"),
    "querer": ("querer", None), "quiero": ("querer", "yo"),
    "quieres": ("querer", "tú"), "quiere": ("querer", "usted/él/ella"),
    "queremos": ("querer", "nosotros"),
    "comer": ("comer", None), "comemos": ("comer", "nosotros"),
    "beber": ("beber", None), "bebo": ("beber", "yo"), "bebes": ("beber", "tú"),
    "bebe": ("beber", "usted/él/ella"), "bebemos": ("beber", "nosotros"),
    "hablar": ("hablar", None), "hablo": ("hablar", "yo"),
    "hablas": ("hablar", "tú"), "habla": ("hablar", "usted/él/ella"),
    "hablamos": ("hablar", "nosotros"),
    "vivir": ("vivir", None), "vivo": ("vivir", "yo"), "vives": ("vivir", "tú"),
    "vive": ("vivir", "usted/él/ella"), "vivimos": ("vivir", "nosotros"),
    "estar": ("estar", None), "estoy": ("estar", "yo"),
    "estás": ("estar", "tú"), "está": ("estar", "usted/él/ella"),
    "estamos": ("estar", "nosotros"),
    "ser": ("ser", None), "soy": ("ser", "yo"), "eres": ("ser", "tú"),
    "somos": ("ser", "nosotros"),
    "tener": ("tener", None), "tengo": ("tener", "yo"),
    "tienes": ("tener", "tú"), "tiene": ("tener", "usted/él/ella"),
    "tenemos": ("tener", "nosotros"),
}

# English target words → lemma (how-do-I-say / "I am Xing?" path only —
# never scanned over the whole turn, so frame words like "say" in
# "how do I say…" cannot self-trigger decir).
_EN_TO_LEMMA: dict[str, str] = {
    "say": "decir", "saying": "decir", "says": "decir", "tell": "decir",
    "make": "hacer", "making": "hacer", "makes": "hacer",
    "doing": "hacer", "cook": "hacer", "cooking": "hacer",
    "go": "ir", "going": "ir", "goes": "ir",
    "eat": "comer", "eating": "comer",
    "drink": "beber", "drinking": "beber",
    "speak": "hablar", "speaking": "hablar",
    "talk": "hablar", "talking": "hablar",
    "live": "vivir", "living": "vivir",
    "want": "querer", "wanting": "querer",
    "have": "tener", "having": "tener",
}

# Grammar/meta engagement markers — the learner is asking ABOUT language.
_META_MARKERS = re.compile(
    r"\bwhat\s+does\b|\bmean(?:s|ing)?\b|\bbreak\s?downs?\b|\bexplain\b|"
    r"\bdifference\b|\bhow\s+(?:do|to|would|should)\b|\bwhen\s+do\b|"
    r"\buse\s+(?:it|them|this|that)\b|\bconjugat\w*\b|"
    r"\bwhat(?:'s|\s+is|\s+are)\b|\bword\s+for\b|"
    r"\bc[oó]mo\s+se\s+dice\b|\bc[oó]mo\s+digo\b|\bhelp\b",
    re.I,
)

# How-say frames (stripped before Spanish token scan so «cómo se dice X»
# never reads its own "dice"/"digo" as the asked-about form).
_HOWSAY_FRAME = re.compile(
    r"\bhow\s+(?:do\s+(?:i|you)|to|would\s+i)\s+say\b|"
    r"\bc[oó]mo\s+se\s+dice\b|\bc[oó]mo\s+digo\b",
    re.I,
)

# Pronoun + bare infinitive: an attempted-but-unconjugated form (Yo hacer…).
_PRON_INF = re.compile(
    r"\b(yo|t[uú]|[eé]l|ella|usted|nosotros)\s+"
    r"(decir|hacer|ir|querer|comer|beber|hablar|vivir|estar|ser|tener)\b",
    re.I,
)

_PRON_TO_PERSON = {
    "yo": "yo", "tu": "tú", "tú": "tú",
    "el": "usted/él/ella", "él": "usted/él/ella",
    "ella": "usted/él/ella", "usted": "usted/él/ella",
    "nosotros": "nosotros",
}

_GERUND_SELF = re.compile(r"\bi\s+am\s+([a-z]+ing)\b", re.I)


def _block_for_lemma(lemma: str) -> dict | None:
    """Card block (same shape the client already renders) for a lemma."""
    fid = LEMMA_TO_FORM_ID.get(lemma)
    if fid:
        from .can_dos import MORPHOLOGY_BY_FORM

        if fid not in MORPHOLOGY_BY_FORM:
            return None
        b = dict(MORPHOLOGY_BY_FORM[fid])
        b["paradigm"] = [dict(r) for r in (b.get("paradigm") or [])]
        b["id"] = f"turn:{lemma}"
        b["form_id"] = fid
        b["lemma"] = b.get("lemma") or lemma
        return b
    src = A1_VERB_MORPH.get(lemma)
    if not src:
        return None
    b = dict(src)
    b["paradigm"] = [dict(r) for r in (b.get("paradigm") or [])]
    b["id"] = f"turn:{lemma}"
    b["lemma"] = lemma
    b["pos"] = "verb"
    return b


def _highlight(block: dict, persons: set[str]) -> None:
    for row in block.get("paradigm") or []:
        if row.get("person") in persons:
            row["highlight"] = True


def _add_watch(block: dict, text: str) -> None:
    t = (text or "").strip()
    if not t:
        return
    prev = (block.get("watch") or "").strip()
    block["watch"] = (f"{t} · {prev}" if prev else t)[:200]


def detect_turn_morph(learner: str) -> dict | None:
    """Which verb form does THIS learner turn engage? None = no engagement.

    Code-owned (no LLM). Priority: produced error > attempted conjugation >
    Spanish form named in a meta question > English how-say target.
    """
    text = learner or ""
    if not text.strip():
        return None
    low = text.lower()

    from .observe import strip_quoted

    own = strip_quoted(text)

    # 1) Error-pattern hit on their own production → that pattern's form.
    from .character_sheet import ERROR_PATTERN_CATALOG, detect_error_pattern_hits

    for pid, example in detect_error_pattern_hits(own):
        cat = ERROR_PATTERN_CATALOG.get(pid) or {}
        fid = cat.get("form_id")
        if not fid:
            continue
        lemma = next(
            (lem for lem, f in LEMMA_TO_FORM_ID.items() if f == fid), None
        )
        block = _block_for_lemma(lemma) if lemma else None
        if block is None:
            from .can_dos import MORPHOLOGY_BY_FORM

            if fid not in MORPHOLOGY_BY_FORM:
                continue
            block = dict(MORPHOLOGY_BY_FORM[fid])
            block["paradigm"] = [dict(r) for r in (block.get("paradigm") or [])]
            block["id"] = f"turn:{fid}"
            block["form_id"] = fid
        block["engaged_by"] = "error_pattern"
        block["learner_attempt"] = str(example or "")[:80]
        if example:
            _add_watch(block, f"you said: {example}")
        _highlight(block, {"yo"})
        return block

    # 2) Pronoun + infinitive (Yo hacer…) — show the conjugated target row.
    m = _PRON_INF.search(own)
    if m:
        pron_raw, lemma = m.group(1).lower(), m.group(2).lower()
        block = _block_for_lemma(lemma)
        if block:
            person = _PRON_TO_PERSON.get(pron_raw, "yo")
            target = next(
                (r.get("form") for r in block.get("paradigm") or []
                 if r.get("person") == person),
                None,
            )
            block["engaged_by"] = "form_error"
            block["learner_attempt"] = f"{m.group(1)} {m.group(2)}"[:80]
            if target:
                _add_watch(
                    block, f"«{m.group(1)} {m.group(2)}» → «{m.group(1)} {target}»"
                )
            _highlight(block, {person})
            return block

    # 3) Spanish form named in a grammar/meta question (digo and dices…?).
    if _META_MARKERS.search(low):
        scan = _HOWSAY_FRAME.sub(" ", low)
        hits: list[tuple[str, str | None]] = []
        for token in re.findall(rf"[{_ES}]+", scan):
            if token in _TOKEN_INDEX:
                hits.append(_TOKEN_INDEX[token])
        if hits:
            lemma = hits[0][0]
            block = _block_for_lemma(lemma)
            if block:
                persons = {p for lem, p in hits if lem == lemma and p}
                block["engaged_by"] = "meta_question"
                _highlight(block, persons or {"yo"})
                return block

    # 4) English how-say / "I am Xing?" → the aimed-at A1 verb.
    tail = None
    fm = _HOWSAY_FRAME.search(low)
    if fm:
        tail = low[fm.end():]
    gm = _GERUND_SELF.search(low)
    words: list[str] = []
    if tail:
        words.extend(re.findall(r"[a-z]+", tail))
    if gm and ("?" in text or fm):
        words.insert(0, gm.group(1))
    for w in words:
        lemma = _EN_TO_LEMMA.get(w)
        if not lemma:
            continue
        block = _block_for_lemma(lemma)
        if block:
            block["engaged_by"] = "translation_request"
            _highlight(block, {"yo"})
            if gm:
                block["learner_attempt"] = gm.group(0)[:80]
            return block

    return None


# stash_turn_morph / stash_intro_morph DELETED (§1.1b settlement round,
# 2026-07-29): the shared-dict _turn_morph stash was the accretion pattern
# in miniature (two writers, precedence rules on a mutable bag). The card
# view is now derived once per turn by exchange_render.card_engagement
# (which calls the pure detectors below) and frozen into TurnRender at
# stage_settle_chrome.


def detect_intro_morph(keys: list[str]) -> dict | None:
    """Which tutor-introduced key engages a verb-form card? None = none.

    Review 2026-07-29 (docs/reviews-morph-card-introductions.md): when the
    TUTOR introduces a structural item (estar via recast+model), chat
    explain is capped at 1–3 lines and this card was the designed home for
    paradigm depth — but every detect path above only reads the LEARNER's
    turn, so introductions never reached it. Keys come from the turn's
    INTRODUCED / FIRST_SEEN events (pipeline knowledge — no reply re-scan);
    tokens go through the same ambiguity-safe _TOKEN_INDEX (better to miss
    than flash a wrong card).
    """
    for raw in keys:
        text = (raw or "").lower().replace("_", " ")
        if not text.strip():
            continue
        lemma: str | None = None
        persons: set[str] = set()
        for token in re.findall(rf"[{_ES}]+", text):
            hit = _TOKEN_INDEX.get(token)
            if hit is None:
                continue
            if lemma is None:
                lemma = hit[0]
            if hit[0] == lemma and hit[1]:
                persons.add(hit[1])
        if lemma is None:
            continue
        block = _block_for_lemma(lemma)
        if block is None:
            continue
        block["engaged_by"] = "introduction"
        if text != lemma:
            _add_watch(block, f"new this turn: {text}")
        _highlight(block, persons or {"yo"})
        return block
    return None


def lemma_engaged_by_text(text: str, key: str) -> bool:
    """Did ``text`` realize ``key`` — verbatim OR via a conjugated surface
    form of its verb lemma? («¿Cómo estás?» realizes the due key «estar».)

    Encounter-variety round (Grok constraint, 2026-07-29): a bare
    word_present(lemma) check would systematically miss conjugated elicits
    and silently under-count frames_seen. Uses the same ambiguity-safe
    _TOKEN_INDEX as the card triggers — better to miss than to over-credit.
    """
    from .textnorm import phrase_present

    if phrase_present(key, text):
        return True
    k = (key or "").lower().strip()
    if not k:
        return False
    for token in re.findall(rf"[{_ES}]+", (text or "").lower()):
        hit = _TOKEN_INDEX.get(token)
        if hit is not None and hit[0] == k:
            return True
    return False


