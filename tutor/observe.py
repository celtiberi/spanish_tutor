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
) -> dict[str, Any]:
    """Bundle hard observations for the AI tutor context."""
    text = "" if is_open else (learner or "")
    sig = probe_signals(text)
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
        "active_errors": [
            {"id": e.get("id"), "count": e.get("count"), "form_id": e.get("form_id")}
            for e in active[:5]
            if isinstance(e, dict)
        ],
        "next_best": {
            "can_do": nb.get("can_do"),
            "statement": nb.get("statement"),
            "activity": nb.get("activity"),
            "avoid": nb.get("avoid"),
            "form_focus": nb.get("form_focus"),
        },
        "blank_sheet": is_blank_learner(sheet),
    }
