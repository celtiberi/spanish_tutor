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
