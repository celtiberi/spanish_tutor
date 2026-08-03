"""Pack association-table loader (r7 S4 subsystem).

Purpose: deterministic anchor lookups for the introduce router — cognate
anchors, false-friend traps, imageable flags, curated keyword mnemonics,
and themes. Rule references (docs/pedagogy-research-r7-association-intro.md
section 5):

- R-A cognate anchor: ``anchor_for`` prefers a true cognate, but never for a
  listed false friend — a trap cannot be an anchor. The loader hard-fails any
  table entry that sets both ``cognate_en`` and ``false_friend``.
- R-E keyword fallback: a pack-curated ``keyword_en`` is the next anchor
  choice; the model does not improvise keyword mnemonics.
- R-F cluster ban keys on theme: ``same_theme`` / ``entries_for_theme`` feed
  the near-synonym/antonym interference ban (introduce one, park the other).

Code-owned: the model never edits this table. Stdlib only.
"""

from __future__ import annotations

import json
from pathlib import Path

TABLE_FILENAME = "association_table.json"

# ---------------------------------------------------------------------------
# Structural exemption sets (canonical home since Phase 5 batch 2 — they
# describe TABLE data, so they live with the table; output_gate re-exports
# its historical names).  Grammar infrastructure: pronouns, question words,
# copulas, counting sequences and `hay` are paradigms, not lexical topics or
# introductions — the gate's first-exposure scan skips them (Round-2 AMEND
# 3B) and the topic-concept palette excludes them (CHAR-BUG-007 fix).
# ---------------------------------------------------------------------------
STRUCTURAL_THEMES = frozenset({
    "pronouns", "question_words", "copulas", "function", "numbers",
})
STRUCTURAL_KEYS = frozenset({
    # surface forms of exempt paradigms not themed as structural
    "soy", "eres", "es", "somos", "sois", "son",
    "estoy", "estás", "está", "estamos", "estáis", "están",
})

# Conversational-formula themes: greetings, courtesy and social moves are
# things you SAY, not things you talk ABOUT — they must never bind as a
# topic CONCEPT ("location:y tu" incident, gate retune 2026-08-03: the
# palette tail matched «y tú» as the concept of a location try).  The gate's
# first-exposure scan deliberately does NOT use this set (social phrases are
# still lexical introductions there — Grok guardrail on the farewell block).
SOCIAL_FORMULA_THEMES = frozenset({
    "greetings", "how_are_you", "farewells", "introductions", "courtesy",
})

_REQUIRED_FIELDS = ("gloss_en", "theme", "imageable")
_NULLABLE_STR_FIELDS = ("cognate_en", "false_friend", "keyword_en")
_ALLOWED_FIELDS = frozenset(_REQUIRED_FIELDS) | frozenset(_NULLABLE_STR_FIELDS) | {
    "in_pack"
}
MAX_GLOSS_WORDS = 6


def load_association_table(pack_dir: Path | str) -> dict[str, dict]:
    """Load and validate ``<pack_dir>/association_table.json``.

    Raises ValueError listing ALL offending keys (not just the first) when
    any entry violates the schema:
    - ``gloss_en``: str, <= 6 words
    - ``theme``: non-empty str
    - ``imageable``: bool
    - ``cognate_en`` / ``false_friend`` / ``keyword_en``: str or null
    - an entry may not set BOTH ``cognate_en`` and ``false_friend``
      (a trap cannot be an anchor — R-A guard)
    """
    path = Path(pack_dir) / TABLE_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"No {TABLE_FILENAME} in {pack_dir}")
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{TABLE_FILENAME}: top level must be an object")

    problems: list[str] = []
    for key, entry in raw.items():
        if not isinstance(key, str) or not key.strip():
            problems.append(f"{key!r}: key must be a non-empty string")
            continue
        if not isinstance(entry, dict):
            problems.append(f"{key}: entry must be an object")
            continue
        gloss = entry.get("gloss_en")
        if not isinstance(gloss, str) or not gloss.strip():
            problems.append(f"{key}: gloss_en must be a non-empty string")
        elif len(gloss.split()) > MAX_GLOSS_WORDS:
            problems.append(
                f"{key}: gloss_en over {MAX_GLOSS_WORDS} words ({gloss!r})"
            )
        theme = entry.get("theme")
        if not isinstance(theme, str) or not theme.strip():
            problems.append(f"{key}: theme must be a non-empty string")
        if not isinstance(entry.get("imageable"), bool):
            problems.append(f"{key}: imageable must be a bool")
        for field in _NULLABLE_STR_FIELDS:
            value = entry.get(field)
            if value is not None and not isinstance(value, str):
                problems.append(f"{key}: {field} must be a string or null")
        if entry.get("cognate_en") and entry.get("false_friend"):
            problems.append(
                f"{key}: has BOTH cognate_en and false_friend "
                "(a trap cannot be an anchor)"
            )
        unknown = set(entry) - _ALLOWED_FIELDS
        if unknown:
            problems.append(f"{key}: unknown fields {sorted(unknown)}")
    if problems:
        raise ValueError(
            f"{TABLE_FILENAME} schema errors ({len(problems)}):\n"
            + "\n".join(f"- {p}" for p in problems)
        )
    return raw


def anchor_for(table: dict[str, dict], key: str) -> dict:
    """Best deterministic anchor for ``key``.

    Preference order: cognate (R-A; skipped for false friends) -> curated
    keyword (R-E) -> plain gloss. Always includes ``gloss_en``; includes
    ``false_friend`` note when the entry is a listed trap so the router can
    surface the warning instead of an anchor.
    """
    entry = table[key]
    false_friend = entry.get("false_friend")
    anchor: dict = {"gloss_en": entry["gloss_en"]}
    if false_friend:
        anchor["false_friend"] = false_friend
    if entry.get("cognate_en") and not false_friend:
        anchor["type"] = "cognate"
        anchor["cognate_en"] = entry["cognate_en"]
    elif entry.get("keyword_en"):
        anchor["type"] = "keyword"
        anchor["keyword_en"] = entry["keyword_en"]
    else:
        anchor["type"] = "gloss"
    return anchor


def is_false_friend(table: dict[str, dict], key: str) -> bool:
    """True when ``key`` is a listed false-friend trap (unknown keys: False)."""
    return bool(table.get(key, {}).get("false_friend"))


def same_theme(table: dict[str, dict], a: str, b: str) -> bool:
    """True when both keys exist and share a theme (R-F cluster-ban probe)."""
    ea, eb = table.get(a), table.get(b)
    if ea is None or eb is None:
        return False
    return ea["theme"] == eb["theme"]


def entries_for_theme(table: dict[str, dict], theme: str) -> list[str]:
    """All keys in ``theme``, in table order (R-F cluster-ban candidates)."""
    return [k for k, v in table.items() if v["theme"] == theme]


# ---------------------------------------------------------------------------
# Phase 5 batch 2 (inventory flip, docs/reviews-architecture-refactor.md):
# the four legacy concept lists (session_memory.TOPIC_CONCEPT_NOUNS /
# SPANISH_CONCEPT_PAIRS, modes.NOUN_TEXT_PAIRS / NEW_CONCRETE_NOUNS,
# observe's topic_vocab regex) derive from THIS table — one inventory, no
# parallel frozen lists.  The default-pack table is loaded once per process
# through the validating loader; a broken/missing default pack raises LOUDLY
# at first use instead of silently emptying routing lists (the loader's
# validation is the contract — do not bypass it with a lax re-parse).
# ---------------------------------------------------------------------------

_default_table_cache: dict[str, dict] | None = None


def cached_default_table() -> dict[str, dict]:
    """Validated association table for ``config.DEFAULT_PACK_DIR``, loaded
    once per process (module-level cache; cheap for the derived-list
    builders).  Sessions with a CUSTOM pack dir still load their own table
    (``ConversationalSession.association_table``); this cache backs only the
    module-level derived constants, exactly like the hardcoded lists it
    replaced."""
    global _default_table_cache
    if _default_table_cache is None:
        from .config import DEFAULT_PACK_DIR

        _default_table_cache = load_association_table(DEFAULT_PACK_DIR)
    return _default_table_cache


def content_topic_keys(table: dict[str, dict] | None) -> list[str]:
    """Table keys that can honestly be a TOPIC concept, in table order.

    Excludes STRUCTURAL_THEMES / STRUCTURAL_KEYS — grammar infrastructure
    (pronouns, question words, copulas, numbers, `hay`) is never a topic of
    conversation (CHAR-BUG-007: «¿Dónde estás tú?» must register the bare
    ``location`` frame, not ``location:tu``) — and SOCIAL_FORMULA_THEMES:
    conversational formulas («y tú», «mucho gusto») are moves, not topics
    (gate retune 2026-08-03, the ``location:y tu`` derivation bug).  No
    in_pack filter: off-pack keys stay valid for OBSERVATION (asked-topics,
    probe-loop dedupe) even though they are introduce-ineligible (batch-1
    record)."""
    out: list[str] = []
    for key, entry in (table or {}).items():
        if not isinstance(entry, dict):
            continue
        theme = str(entry.get("theme") or "")
        if theme in STRUCTURAL_THEMES or theme in SOCIAL_FORMULA_THEMES:
            continue
        if key in STRUCTURAL_KEYS:
            continue
        out.append(key)
    return out
