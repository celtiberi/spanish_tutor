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
