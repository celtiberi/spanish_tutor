"""tutor/textnorm.py — the ONE home for Spanish text normalization.

Phase 2 of the adjudicated architecture refactor
(docs/reviews-architecture-refactor.md §6 duplication inventory): the
boundary-regex family (×3), the Spanish letter class (×5) and the accent
folds (×4 surviving telemetry's deletion) all live here now, stdlib only.

Two hard laws:

1. **The fold policies are THREE (plus one) NAMED POLICIES, never one
   merged function** (Grok Phase 2 amendment). Their semantics differ
   DELIBERATELY: `fold_lexical` keeps ñ and spaces (topic-registry keys),
   `fold_asset_key` folds ñ and underscores spaces (image cache keys),
   `fold_id` underscores spaces AND hyphens (error-pattern ids). A naive
   merge silently changes image cache keys and topic keys. If you need a
   new folding behavior, add a NEW named policy — do not "generalize" one
   of these.

2. **The boundary matchers are TWO NAMED VARIANTS, not one** — see the
   `word_present` vs `phrase_match`/`phrase_present` divergence notes
   below (characterized 2026-07-28; CHAR_BUG candidates in the Phase 2
   runbook entry). Each caller keeps ITS historical semantics; unifying
   them is a bugfix PR with pin updates, not a refactor.

Contract test: tests/test_textnorm_contract.py (differential corpus run
against the pre-migration implementations; byte-identical outputs pinned).
"""

from __future__ import annotations

import re
import unicodedata


# The one Spanish letter class (body of a regex character class): lowercase
# ASCII range + accented vowels + ü + ñ. Used for word boundaries
# ("letter-adjacent = same word") and token scans. Callers lowercase their
# text before matching — this class is deliberately lowercase-only.
# Replaces: observe._ES_LETTERS, task_runtime._ES_LETTERS,
# output_gate._ES_BOUND, turn_morph._ES, tutor_response._CONCEPT_TOKEN's
# inline class.
SPANISH_LETTERS = "a-záéíóúüñ"


# ---------------------------------------------------------------------------
# Boundary matcher family
# ---------------------------------------------------------------------------

def word_present(needle: str, text: str) -> bool:
    """Spanish word-boundary containment, plural-tolerant (observe.py's
    historical semantics, verbatim).

    Raw substring checks put a SUN image on «Hola Marisol» ('sol' inside
    the name) and on «yo solo…». A needle only matches as a whole word (or
    its simple plural): sol≠Marisol/solo, but gato→gatos still hits.
    No accent folding — «cafe» never matches «café».

    Users: observe (re-export façade), conv_session, introduce_router,
    modes, session_memory.topic_key_for_try, teach_assets.concept_in_text.

    DIVERGENCES from phrase_match/phrase_present (kept deliberately,
    characterized 2026-07-28 — see the Phase 2 runbook entry before
    "fixing" either):
    - The needle is escaped WHOLE: a multiword needle matches only with
      exactly its own literal whitespace («cómo estás» misses
      «cómo  estás» / a newline between the words), while the phrase
      family joins words with \\s+.
    - An empty or unmatchable-whitespace needle degenerates to a bare
      boundary pattern that CAN match (word_present("", "hola !") is
      True); the phrase family returns falsy for empty needles.
    """
    return bool(re.search(
        rf"(?<![{SPANISH_LETTERS}]){re.escape((needle or '').lower())}"
        rf"(?:e?s)?(?![{SPANISH_LETTERS}])",
        (text or "").lower(),
    ))


def phrase_body(needle: str) -> str:
    """Escaped regex body for a (possibly multiword) needle: lowercased,
    split on any whitespace, words re-joined with \\s+. Empty string for
    an empty/whitespace-only needle.

    Exposed so output_gate.gloss_after_key can compose its key+gloss
    regex from the same body the matchers use (one definition, no drift).
    """
    words = [re.escape(w) for w in (needle or "").lower().split()]
    return r"\s+".join(words)


def phrase_match(needle: str, text: str) -> "re.Match[str] | None":
    """Boundary-safe first match of a word or multiword phrase; the Match
    object (output_gate._key_match's historical semantics, verbatim —
    callers use .start()/.end() for overlap filtering).

    Same discipline as word_present — whole-word containment with simple
    plural tolerance on the final word, Spanish-aware letter boundaries,
    no accent folding — but whitespace in the needle is normalized and
    matched as \\s+ (see word_present's divergence notes). Returns None
    for an empty needle.

    Users: output_gate (unscaffolded-new-item scan, anchor_in_reply).
    """
    body = phrase_body(needle)
    if not body:
        return None
    return re.search(
        rf"(?<![{SPANISH_LETTERS}]){body}(?:e?s)?(?![{SPANISH_LETTERS}])",
        (text or "").lower(),
    )


def phrase_present(needle: str, text: str) -> bool:
    """Word/phrase-boundary containment as bool (task_runtime's historical
    phrase_present semantics: single words behave exactly like
    word_present on a stripped single word; multiword phrases match each
    word at the same boundaries joined by \\s+, plural tolerance on the
    final word — «leche» never matches inside «lechero», «cómo estás»
    matches inside «Hola, ¿cómo estás hoy?»).

    Equivalent to bool(phrase_match(...)) — pinned by the contract test.

    Users: task_runtime (re-export façade; evidence-list slot filling).
    """
    return phrase_match(needle, text) is not None


# ---------------------------------------------------------------------------
# Accent-fold policies — named, deliberately incompatible. Do not merge.
# ---------------------------------------------------------------------------

def fold_lexical(text: str) -> str:
    """Lexical-comparison fold (session_memory._deaccent's historical
    semantics, verbatim): lowercase; fold the SIX accented vowels
    á é í ó ú ü → a e i o u u; KEEP ñ (año ≠ ano is a real distinction);
    keep spaces and punctuation untouched.

    Users: session_memory (asked-topic registry keys — compose_topic_key /
    topic_key_for_try) and output_gate's probe-loop due-exemption, which
    must compare due-item keys through the SAME transform the registry
    used (this replaces output_gate's private import of
    session_memory._deaccent).
    """
    out = (text or "").lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
                 ("ü", "u")):
        out = out.replace(a, b)
    return out


def fold_asset_key(concept: str | None) -> str:
    """Image-asset cache-key fold (teach_assets._norm_key's historical
    semantics, verbatim): strip + lowercase; fold FIVE accented vowels
    á é í ó ú (NOT ü — «pingüino» keeps its ü) and ñ → n; spaces →
    underscores; drop … and .; strip a leading el_/la_ article prefix
    (el_ checked first, so el_la_casa → casa).

    Users: teach_assets ONLY (concept lexicon lookups, alias resolution,
    on-disk image cache keys, warm-index keys). Changing this policy
    ORPHANS every existing cached image — it is pinned byte-exact.
    """
    if not concept:
        return ""
    s = str(concept).strip().lower()
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    s = s.replace(" ", "_").replace("…", "").replace(".", "")
    if s.startswith("el_"):
        s = s[3:]
    if s.startswith("la_"):
        s = s[3:]
    return s


def fold_id(pattern_id: str) -> str:
    """Identifier fold (the folding step inside
    character_sheet.normalize_error_pattern_id, verbatim): lowercase;
    spaces AND hyphens → underscores; fold FIVE accented vowels á é í ó ú
    (NOT ü) and ñ → n. No strip, no article handling — the caller owns
    catalog/alias/fuzzy resolution around this pure fold.

    Users: character_sheet.normalize_error_pattern_id ONLY (error-pattern
    ids live in sheets on disk — changing this policy re-keys them).
    """
    key = (pattern_id or "").lower().replace(" ", "_").replace("-", "_")
    key = key.replace("á", "a").replace("é", "e").replace("í", "i")
    key = key.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return key


# Combining diacritical marks (NFD residue) OR sentence punctuation noise.
_PROSE_NOISE = re.compile(r"[\u0300-\u036f]|[¿¡\?\.!,;:\"']+")


def fold_prose(s: str) -> str:
    """Prose-scan fold (character_sheet.fold's historical semantics,
    verbatim) — the FOURTH named policy, shipped here rather than kept
    local so every fold has one home: lowercase + strip; NFD-decompose,
    then drop ALL combining marks (so ñ → n and ü → u, unlike
    fold_lexical, and ANY diacritic folds — ç → c, ô → o) and the
    sentence punctuation ¿¡?.!,;:"'; collapse whitespace runs to single
    spaces.

    Users: character_sheet ONLY (error-pattern detect/resolve regex scans
    over learner prose, affect/receptive heuristics — imported there as
    `fold`). Unique to that caller; if a second caller ever wants it,
    import THIS name rather than re-deriving.
    """
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = _PROSE_NOISE.sub("", s)
    return re.sub(r"\s+", " ", s)
