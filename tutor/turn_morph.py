"""Morphology card + frames bookkeeping.

The card is MODEL-AUTHORED (USER 2026-08-03: "this could be something
that changes or gets updated along with the response like grading" — the
code-detection era card sat static and guessed). The teacher emits a
<morph> block alongside its reply when a form table helps THIS turn —
introducing a structure, correcting a conjugation, answering "how does
this verb work". extract_morph() harvests it (never learner-visible in
chat); the rail renders it; the model chooses the rows and may highlight
one with a leading *.

    <morph title="trabajar — to work" note="With yo: trabajo — no -s.">
    trabajo | yo | I work
    *trabajas | tú | you work
    </morph>

lemma_engaged_by_text stays: it is the frames_seen ledger's conjugated-
surface matcher (encounter-variety round, 2026-07-29) — bookkeeping,
not display.
"""

from __future__ import annotations

import datetime as _dt
import re

# Phase 2 (docs/reviews-architecture-refactor.md): the one Spanish letter
# class lives in textnorm; historical local name kept for the token scan.
from .textnorm import SPANISH_LETTERS as _ES

_MORPH_RE = re.compile(r"<morph\b([^>]*)>(.*?)</morph>", re.S | re.I)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def extract_morph(raw: str) -> tuple[dict | None, str]:
    """(card | None, cleaned_raw).

    Harvests the model's <morph> block from its raw reply and strips it
    so table text never leaks into the chat. Tolerant: attribute order
    free; rows are "form | person | gloss" lines (missing cells fine);
    a leading * on the form highlights that row. Malformed/empty block →
    no card, tag still stripped (never learner-visible).
    """
    text = raw or ""
    m = _MORPH_RE.search(text)
    if not m:
        return None, text
    attrs = dict(_ATTR_RE.findall(m.group(1) or ""))
    rows: list[dict] = []
    for line in (m.group(2) or "").splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        form = cells[0]
        highlight = form.startswith("*")
        if highlight:
            form = form.lstrip("*").strip()
        if not form:
            continue
        rows.append({
            "form": form,
            "person": cells[1] if len(cells) > 1 else "",
            "gloss": cells[2] if len(cells) > 2 else "",
            "highlight": highlight,
        })
    cleaned = _MORPH_RE.sub(" ", text).strip()
    if not rows:
        return None, cleaned
    card = {
        "label": attrs.get("title") or rows[0]["form"],
        "paradigm": rows,
        "note": attrs.get("note") or "",
        "live": True,
        "source": "model",
        "ts": _dt.datetime.now().isoformat(timespec="seconds"),
    }
    return card, cleaned


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
