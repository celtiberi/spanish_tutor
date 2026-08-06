"""Offline Spanish verification data — the auditor's reference shelf.

USER 2026-08-05 ("what spanish offline resources could we be using"):
the model teaches; code audits — and an auditor needs ground truth.
Two sources, both fully offline:

- wordfreq (pip): Zipf frequency for is-this-real-Spanish. Calibrated
  2026-08-05: real A1 vocabulary scores >=3.1 (senderismo 3.11, lápiz
  3.82, bien 6.11); garble scores <=2.7 (bein 2.68, grasias 2.30).
  Threshold 3.0. Names are NOT separable by frequency (sam 4.11 beats
  lápiz) — the name leak stays a grading-layer issue.
- Jehle verb DB (domain/spanish_a1/conjugations.json, 637 verbs,
  CC BY-NC-SA, Fred Jehle): full A1-relevant paradigms for
  is-this-a-form-of-that-verb.
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import config

# Frozen 2026-08-05 (pre-grading round, Grok amendment: ONE number
# everywhere): real A1 vocabulary >= 3.11 (senderismo — closest margin),
# garble <= 2.68. Do not tune without a new review round.
GARBLE_ZIPF = 3.1


@lru_cache(maxsize=1)
def _db() -> dict:
    p = config.REPO_ROOT / "domain" / "spanish_a1" / "conjugations.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("verbs") or {}
    except (OSError, ValueError):
        return {}


@lru_cache(maxsize=1)
def _form_index() -> dict[str, str]:
    """conjugated form -> lemma (first wins on the rare collision)."""
    idx: dict[str, str] = {}
    for lemma, forms in _db().items():
        for f in forms:
            idx.setdefault(f, lemma)
    return idx


def _strip_accents(s: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


@lru_cache(maxsize=1)
def _accentless_multi_index() -> dict[str, list[tuple[str, str]]]:
    """accent-stripped surface -> ALL (lemma, canonical_form) parses.
    'fui' -> [(ir,'fui'),(ser,'fui')]; 'esta' -> [(estar,'está')].
    Multi-parse listing is REQUIRED by the pre-grading review (never
    collapse an ambiguous surface to one reading)."""
    idx: dict[str, list[tuple[str, str]]] = {}
    for lemma, forms in _db().items():
        for f in forms:
            key = _strip_accents(f)
            pair = (lemma, f)
            bucket = idx.setdefault(key, [])
            if pair not in bucket:
                bucket.append(pair)
    return idx


def parses_of_surface(word: str) -> list[tuple[str, str]]:
    """All (lemma, canonical_form) readings of a surface token,
    accent-lenient. Empty list = not a known conjugated form."""
    w = _strip_accents(str(word or "").strip().lower())
    return list(_accentless_multi_index().get(w) or [])


def forms_of(lemma: str) -> list[str]:
    return _db().get(str(lemma or "").strip().lower()) or []


def lemma_of_form(form: str) -> str | None:
    return _form_index().get(str(form or "").strip().lower())


def is_real_spanish(word: str) -> bool:
    """Frequency-backed reality check for a single word. Multi-word
    phrases and empty strings return True (not this check's job)."""
    w = str(word or "").strip().lower()
    if not w or " " in w:
        return True
    if w in _form_index() or w in _db():
        return True  # any conjugation-table hit is real by construction
    try:
        from wordfreq import zipf_frequency
    except ImportError:
        return True  # dependency missing: audit degrades open, visibly
    return zipf_frequency(w, "es") >= GARBLE_ZIPF


@lru_cache(maxsize=1)
def _paradigms() -> dict:
    p = config.REPO_ROOT / "domain" / "spanish_a1" / "conjugations.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"paradigms": d.get("paradigms") or {},
                "english": d.get("english") or {}}
    except (OSError, ValueError):
        return {"paradigms": {}, "english": {}}


# English person-conjugation is rule-based with a handful of irregulars —
# deterministic beats a model pass (P2 round, 2026-08-06).
_EN_IRREGULAR = {"be": {"1": "am", "3": "is", "p": "are"},
                 "have": {"3": "has"}, "go": {"3": "goes"},
                 "do": {"3": "does"}}


def _en_third(base: str) -> str:
    irr = _EN_IRREGULAR.get(base)
    if irr and "3" in irr:
        return irr["3"]
    if base.endswith(("s", "sh", "ch", "x", "z", "o")):
        return base + "es"
    if base.endswith("y") and len(base) > 1 and base[-2] not in "aeiou":
        return base[:-1] + "ies"
    return base + "s"


def render_paradigm(lemma: str, highlight: str = "") -> dict | None:
    """Ground-truth present-indicative card rows for a verb, with derived
    English glosses. None when the lemma is not covered (caller falls
    back to model-authored rows — the C3a coverage gate)."""
    lem = str(lemma or "").strip().lower()
    data = _paradigms()
    para = data["paradigms"].get(lem)
    if not para:
        return None
    base = (data["english"].get(lem) or "").removeprefix("to ").strip()
    irr = _EN_IRREGULAR.get(base, {})
    gloss = {
        "yo": f"I {irr.get('1', base)}",
        "tú": f"you {irr.get('p', base)}" if base == "be" else f"you {base}",
        "usted/él/ella": f"you (formal) / he / she {_en_third(base)}",
        "nosotros": f"we {irr.get('p', base)}" if base == "be" else f"we {base}",
        "ustedes/ellos": f"they {irr.get('p', base)}" if base == "be" else f"they {base}",
    } if base else {}
    hl = _strip_accents(str(highlight or "").strip().lower())
    rows = []
    for person, form in para.items():
        rows.append({
            "form": form,
            "person": person,
            "gloss": gloss.get(person, ""),
            "highlight": bool(hl) and _strip_accents(form.lower()) == hl,
        })
    return {
        "label": f"{lem} — {data['english'].get(lem, '')}".rstrip(" —"),
        "paradigm": rows,
        "note": "",
        "live": True,
        "source": "code",
    }
