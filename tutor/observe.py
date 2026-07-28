"""Light code observations — hints for the AI tutor, not a lesson script.

probe_signals / error hits feed session memory and the model as *facts*.
They must not become a fixed Hola→Estoy→Me llamo ladder.
"""

from __future__ import annotations

import re
from typing import Any

from .character_sheet import (
    ERROR_PATTERN_CATALOG,
    active_error_patterns,
    detect_error_pattern_hits,
)
from .pedagogy_contract import is_blank_learner


_QUOTED_SPANS = (
    re.compile(r"«[^»]{1,120}»"),
    re.compile(r"[“”][^“”]{1,120}[“”]"),
    re.compile(r'"[^"]{1,120}"'),
    re.compile(r"'[^']{4,120}'"),
)


_ES_LETTERS = "a-záéíóúüñ"


def word_present(needle: str, text: str) -> bool:
    """Spanish word-boundary containment, plural-tolerant.

    Raw substring checks put a SUN image on «Hola Marisol» ('sol' inside the
    name) and on «yo solo…». A needle only matches as a whole word (or its
    simple plural): sol≠Marisol/solo, but gato→gatos still hits.
    """
    return bool(re.search(
        rf"(?<![{_ES_LETTERS}]){re.escape((needle or '').lower())}(?:e?s)?(?![{_ES_LETTERS}])",
        (text or "").lower(),
    ))


def strip_quoted(text: str) -> str:
    """Drop quoted spans — learners echo tutor Spanish to ask about it, which
    must not count as their own production."""
    t = text or ""
    for rx in _QUOTED_SPANS:
        t = rx.sub(" ", t)
    return t


# §2.1a self-flagged form — SURFACE-form spotting only (legit per §4.2: did
# the learner literally mark a token as uncertain). Two cheap shapes:
#   1) gloss-guess: their own token immediately followed by a short
#      parenthetical guess, e.g. «uvia (rain)», «Afruera (outside?)»
#      (incident session 20260728-103617, turns 6/9);
#   2) a quoted SINGLE Spanish-ish token («uvia», "uvia", 'uvia') — multiword
#      quotes are usually tutor-Spanish echoes and stay with the meta guards.
# MEANING classification (content_offer vs answer) stays with the shadow LLM
# classifier — regex never routes it (§4.2, §2.1a architecture clause).
_ES_TOKEN = rf"[A-Za-zÁÉÍÓÚÜÑ{_ES_LETTERS}]+"
_SELF_FLAG_GLOSS_RE = re.compile(
    rf"\b({_ES_TOKEN})\s*\(\s*[A-Za-z][A-Za-z' ]{{0,30}}\??\s*\)",
)
_SELF_FLAG_QUOTED_RES = (
    re.compile(rf"«\s*({_ES_TOKEN})\s*»"),
    re.compile(rf'"\s*({_ES_TOKEN})\s*"'),
    re.compile(rf"'\s*({_ES_TOKEN})\s*'"),
)


def detect_self_flagged_token(text: str) -> str | None:
    """First token the learner marked as uncertain, or None.

    Pure surface detection for the §2.1a instruction path — the caller
    (conv_session.self_flag_uptake_block) owns guard-turn exclusion and the
    content-uptake budget. Plain Spanish production never matches.
    """
    t = text or ""
    if not t.strip():
        return None
    m = _SELF_FLAG_GLOSS_RE.search(t)
    if m:
        return m.group(1).lower()
    for rx in _SELF_FLAG_QUOTED_RES:
        m = rx.search(t)
        if m:
            return m.group(1).lower()
    return None


def probe_signals(learner: str) -> set[str]:
    """What the *current utterance* already shows (placement evidence)."""
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
    if re.search(r"\b(caf[eé]|bote|barco|r[ií]o|comida|m[uú]sica|calor|fr[ií]o)\b", low):
        s.add("topic_vocab")
    # Broader Spanish surface markers (include imperfect learner forms)
    es_hits = len(re.findall(
        r"\b(hola|estoy|est[aá]s|est[aá]|llamo|llamas|gracias|gusta|gustan|"
        r"soy|eres|tengo|tiene|bien|mal|sí|si|no|buenos|buenas|adi[oó]s|"
        r"dónde|donde|c[oó]mo|como|hace|calor|fr[ií]o|hoy|muy|poco|"
        r"en|mi|tu|el|la|los|las|un|una|de|del|con|y|pero|también|"
        r"tambien|r[ií]o|bote|caf[eé]|m[uú]sica|comida)\b",
        low,
    ))
    # Real English function words — not "any Latin token" (that false-flagged Spanish)
    en_func = len(re.findall(
        r"\b(the|and|you|your|are|is|was|were|have|has|had|will|would|should|"
        r"could|this|that|with|from|what|where|when|why|how|should|right|"
        r"said|have|don't|does|did|can|can't|not|just|really|because|"
        r"think|know|want|need|please|thanks|hello|today|weather)\b",
        low,
    ))
    # Pure English meta questions about Spanish still count as English frame
    if en_func >= 2 and es_hits == 0:
        s.add("english_only")
    elif en_func >= 3 and es_hits <= 1:
        s.add("english_only")
    if es_hits >= 2 or (es_hits >= 1 and len(low.split()) <= 8):
        s.add("spanish_ok")
    if len(s & {"greet", "estoy", "name", "ask_name", "gusta", "origin"}) >= 2:
        s.add("multi_skill")
    if re.search(r"\balready\s+asked\b|\bya\s+(me\s+)?pregunt", low):
        s.add("loop_complaint")
    # Learner asks for a word/phrase (vocab help) — NOT non-comprehension of
    # our last Spanish. Missing this signal caused an ignored "I always forget
    # how to say searching" (session 20260727-231954; Grok round-1 F).
    if re.search(
        r"\bhow\s+do\s+i\s+say\b|"
        r"\bhow\s+do\s+you\s+say\b|"
        r"\bhow\s+to\s+say\b|"
        r"\bwhat'?s\s+the\s+word\s+for\b|"
        r"\bwhat\s+is\s+the\s+word\s+for\b|"
        r"\bi\s+always\s+forget\s+how\s+to\s+say\b|"
        r"\bi\s+forget\s+how\s+to\s+say\b|"
        r"\bi\s+always\s+forget\s+how\s+to\b|"
        r"\bhow\s+do\s+you\s+write\b|"
        r"\bc[oó]mo\s+se\s+dice\b|"
        r"\bc[oó]mo\s+digo\b|"
        r"\bhelp\s+me\s+say\b",
        low,
    ):
        s.add("help_request")
    # Learner steering the lesson: new topic / activity request or topic fatigue.
    # English is HOW a novice makes this request — it must not read as
    # "didn't understand the Spanish" (session 20260726-155600 turn 3).
    if re.search(
        r"\bcan\s+we\s+(talk|do|try|practice|switch|work|learn)\b|"
        r"\blet'?s\s+(talk|do|try|practice|switch)\b|"
        r"\bsomething\s+(new|different|else)\b|"
        r"\b(new|different|another|other)\s+topic\b|"
        r"\bchange\s+(the\s+|of\s+)?(topic|subject)\b|"
        r"\byou\s+always\s+(talk|ask|say)\b|"
        r"\bsame\s+(topic|thing|stuff|questions?)\b|"
        r"\balgo\s+(nuevo|diferente)\b|"
        r"\botro\s+tema\b|"
        r"\bcambiar\s+de\s+tema\b|"
        r"\bsiempre\s+(hablamos|hablando|preguntas)\b",
        low,
    ):
        s.add("topic_request")
    # Meta: asking what the tutor's Spanish means / not understanding the last turn
    if re.search(
        r"\bwhat\s+(does|do|is|are)\b|"
        r"\bwhat\s+you\s+(are\s+)?saying\b|"
        r"\bi\s+don'?t\s+know\s+what\b|"
        r"\bi\s+don'?t\s+understand\b|"
        r"\bno\s+entiendo\b|"
        r"\bwhat\s+does\s+.+mean\b|"
        r"\bmeans?\b.+\?|"
        r"\bis\s+like\b|"
        r"\bis\s+something\s+about\b|"
        r"\bi\s+think\s+this\s+is\b|"
        r"\bque\s+es\b|\bqué\s+es\b|"
        r"\bwhat\s+things\b",
        low,
    ):
        s.add("meta_comprehension")
    # Quoted tutor Spanish often means "explain this phrase"
    if re.search(r'[""«»].+[""«»]', learner or "") or re.search(r"'[^']{4,}'", learner or ""):
        if re.search(r"[áéíóúñ¿¡]|hola|como|est|rio|gust|salud|cosas", low):
            s.add("meta_comprehension")
    return s


def build_observations(
    sheet: dict,
    *,
    learner: str = "",
    is_open: bool = False,
    extra_signals: set[str] | None = None,
) -> dict[str, Any]:
    """Bundle hard observations for the AI tutor context.

    `extra_signals` come from the LLM intent classifier (routing authority);
    regex probe_signals remain for surface-form detection + fallback."""
    text = "" if is_open else (learner or "")
    sig = probe_signals(text) | set(extra_signals or [])
    hits = detect_error_pattern_hits(text) if text else []
    hit_ids = [pid for pid, _ in hits]
    active = active_error_patterns(sheet) or []
    nb = sheet.get("next_best") or {}
    return {
        "signals": sorted(sig),
        "error_hits": [
            {"id": pid, "snippet": snip, "form_id": (ERROR_PATTERN_CATALOG.get(pid) or {}).get("form_id")}
            for pid, snip in hits
        ],
        "error_hit_ids": hit_ids,
        # Full active-error list for the teacher (no top-N clip in testing)
        "active_errors": [
            {
                "id": e.get("id"),
                "count": e.get("count"),
                "form_id": e.get("form_id"),
                "label": e.get("label"),
                "teach_hint": e.get("teach_hint"),
                "resolved_streak": e.get("resolved_streak"),
                "correct_uses": e.get("correct_uses"),
                "last_examples": e.get("last_examples"),
                "last_seen": e.get("last_seen"),
            }
            for e in active
            if isinstance(e, dict)
        ],
        "next_best": dict(nb) if isinstance(nb, dict) else {},
        "blank_sheet": is_blank_learner(sheet),
    }
