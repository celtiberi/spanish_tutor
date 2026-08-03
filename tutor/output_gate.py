"""Generate-then-verify: gate the *tutor output*, not a topic ladder.

After the model speaks, code checks for failures that prompts cannot self-guarantee:
  - no teach move (model/try/recast)
  - English wall (tutor turn mostly English when it should be Spanish-forward)
  - probe loop (re-asking something session memory already covered)
  - unscaffolded new item (r7 S3: naked first exposure / cluster dump in
    the visible teaching text) and re-gloss of already-introduced items

On failure the session may do **one** bounded re-ask with a specific fault.
See docs/reviews-claude-idea-spar.md (Claude: gate output, not decision).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .pedagogy_contract import evaluate_turn
# Phase 2 (docs/reviews-architecture-refactor.md): boundary matching + the
# lexical fold come from the shared textnorm module. fold_lexical replaces
# the old private import of session_memory._deaccent — the registry keys and
# this gate's due-exemption compare through the SAME named policy.
from .textnorm import SPANISH_LETTERS, fold_lexical, phrase_body, phrase_match

# Adjudicated turn-level wall (2026-07-26 Tier-1 #2): critical iff
# spanish_token_ratio < MIN_SPANISH_RATIO and alphabetic tokens >= MIN_ALPHA_TOKENS.
# The length floor replaces the old open-specific soft threshold: short framing
# turns never trip; long English does, even on open.
MIN_SPANISH_RATIO = 0.50
MIN_ALPHA_TOKENS = 12
# True-zero exemption (2026-07-28 zero-English incident): a COMPLIANT
# true-zero opening (one English framing line + glossed tiny Spanish)
# measures tl_ratio ≈ 0.32–0.40 and used to trip the wall, whose forced
# "Rewrite Spanish-forward" re-ask reproduced the 100%-Spanish incident.
# Placement mode and blank_zero turns (zero-register overlay riding
# conversation/repair modes, threaded from conv_session) use this floor
# instead; a genuinely all-English turn (ratio ≈ 0) still faults everywhere.
ZERO_MIN_SPANISH_RATIO = 0.25
# Short L1 sandwich in <explain>: exclude English from the ratio when explain
# has at most this many non-Spanish alphabetic tokens (A3 "≤6 words" gloss).
MAX_EXPLAIN_GLOSS_WORDS = 6

# Tokens that count as Spanish-ish (novice chat)
_ES_RE = re.compile(
    r"\b(hola|buenos|buenas|estoy|estás|estas|está|esta|somos|soy|eres|es|"
    r"llamo|llamas|llaman|gracias|adiós|adios|hasta|luego|mañana|manana|"
    r"cómo|como|dónde|donde|qué|que|quién|quien|por|favor|sí|si|no|"
    r"bien|mal|más|mas|menos|muy|también|tambien|aquí|aqui|allí|alli|"
    r"me|te|se|nos|gusto|gusta|gustan|tengo|tiene|quiero|prefiero|"
    r"café|cafe|bote|barco|música|musica|comida|río|rio|de|"
    r"perdón|perdon|claro|vale|bueno|mucho|poco|hoy|ahora|"
    r"usted|señor|senor|señora|senora|amigo|amiga)\b",
    re.I,
)
_EN_RE = re.compile(
    r"\b(the|and|you|your|are|is|am|how|what|where|when|why|this|that|"
    r"with|from|have|has|will|would|should|could|please|try|say|means|"
    r"name|hello|good|fine|well|right|already|asked|sorry|english|"
    r"spanish|tutor|practice|sentence|word|phrase)\b",
    re.I,
)

_PROBE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ask_how", re.compile(r"c[oó]mo\s+est[aá]s|how\s+are\s+you", re.I)),
    ("ask_name", re.compile(r"c[oó]mo\s+te\s+llamas|what(?:'s|\s+is)\s+your\s+name", re.I)),
    ("ask_origin", re.compile(r"de\s+d[oó]nde\s+eres|where\s+(?:are\s+you|you\s+from)", re.I)),
    ("ask_gusta", re.compile(r"qu[eé]\s+te\s+gusta|do\s+you\s+like", re.I)),
]


@dataclass
class OutputGateResult:
    ok: bool
    faults: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    spanish_ratio: float | None = None
    repair_instruction: str = ""
    # Round-2 AMEND 1c: keys that would have faulted but were saved solely by
    # an in-reply scaffold, mapped to the scaffold kind ("gloss" | "anchor").
    # The session writes their durable first_seen bit post-turn.
    scaffold_saved: dict[str, str] = field(default_factory=dict)
    # Round-2 storm soften: bare keys degraded to soft gate:unscaffolded_flood.
    flood_keys: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "faults": list(self.faults),
            "notes": list(self.notes),
            "spanish_ratio": self.spanish_ratio,
            "repair_instruction": self.repair_instruction,
            "scaffold_saved": dict(self.scaffold_saved),
            "flood_keys": list(self.flood_keys),
        }


@dataclass
class GateContext:
    """E3 (Phase 4 batch 3, docs/reviews-architecture-refactor.md): the
    gate's full input surface as ONE typed object — what the historical
    18-argument ``check_output_gate`` signature encoded (2 positionals +
    16 keyword-only).  ``check_output_gate(ctx)`` is the new surface; the
    legacy kwarg call remains as a thin shim that builds this context, so
    the existing gate tests keep their call shape.  Field semantics are
    exactly the old parameters':

    - ``parts``/``visible``/``raw``: the parsed tutor reply under test
      (per-ATTEMPT fields — the repair loop re-checks a rewritten reply
      via ``dataclasses.replace`` on the same turn-constant base).
    - ``require_recast``/``truncated``: per-attempt check switches.
    - everything else is turn-constant session/turn state (sheet, table,
      memory registries, mode, learner text, blank-zero register).
    """

    # -- per-attempt: the reply under test -----------------------------------
    parts: dict | None = None
    visible: str = ""
    raw: str | None = None
    require_recast: bool = False
    truncated: bool = False
    # -- turn-constant context ----------------------------------------------
    is_open: bool = False
    already_asked: set[str] | list[str] | None = None
    already_shown: set[str] | list[str] | None = None
    mode: str | None = None
    image_present: bool = False
    association_table: dict | None = None
    sheet: dict | None = None
    introduce_key: str | None = None
    retrieval_failed_keys: Any = None
    learner_text: str = ""
    blank_zero: bool = False
    asked_topics: Any = None
    topic_nouns: Any = None


_ALPHA_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")


def _strip_md_noise(text: str) -> str:
    return re.sub(r"[*_`#]+", " ", text or "")


def alphabetic_tokens(text: str) -> list[str]:
    """Learner-facing alphabetic tokens (Spanish-aware letters)."""
    return _ALPHA_TOKEN_RE.findall(text or "")


def alphabetic_token_count(text: str) -> int:
    return len(alphabetic_tokens(text))


def spanish_token_ratio(text: str) -> float:
    """Fraction of (es+en) closed-lexicon hits that look Spanish.

    Always returns a float in [0, 1]. With no lexicon hits, returns 1.0 (no
    evidence of an English wall). Pure: no I/O, no mutation. Note this is the
    gate-lexicon ratio, not a true token-level TL% (tokenizer upgrade tracked).
    """
    t = _strip_md_noise(text)
    es = len(_ES_RE.findall(t))
    en = len(_EN_RE.findall(t))
    if es + en == 0:
        return 1.0
    return es / (es + en)


def tutor_spanish_ratio(text: str) -> float | None:
    """Legacy helper: same ratio, but None if fewer than 3 lexicon hits."""
    t = _strip_md_noise(text)
    es = len(_ES_RE.findall(t))
    en = len(_EN_RE.findall(t))
    if es + en < 3:
        return None
    return es / (es + en)


def explain_gloss_word_count(explain: str) -> int:
    """Non-Spanish alphabetic tokens in explain (short L1 gloss budget)."""
    return sum(
        1 for tok in alphabetic_tokens(explain) if not _ES_RE.search(tok)
    )


def _strip_en_lexicon(text: str) -> str:
    """Remove closed-list English hits so they do not affect the ratio."""
    return _EN_RE.sub(" ", text or "")


def learner_facing_blob(parts: dict | None, visible: str) -> str:
    """Learner-facing text the wall measures (same composition as before)."""
    parts = parts or {}
    blob = " ".join(
        str(parts.get(k) or "")
        for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
    )
    if not blob.strip():
        blob = visible or ""
    return blob


def ratio_blob_with_sandwich_exempt(parts: dict | None, visible: str) -> str:
    """Learner-facing text for the ratio; short <explain> L1 gloss stripped."""
    parts = parts or {}
    explain = str(parts.get("explain") or "")
    exempt = (
        bool(explain.strip())
        and explain_gloss_word_count(explain) <= MAX_EXPLAIN_GLOSS_WORDS
    )
    chunks: list[str] = []
    for k in ("acknowledge", "recast", "explain", "model", "try", "continue"):
        piece = str(parts.get(k) or "")
        if k == "explain" and exempt:
            piece = _strip_en_lexicon(piece)
        chunks.append(piece)
    blob = " ".join(chunks)
    if not blob.strip():
        blob = visible or ""
    return blob


def detect_tutor_probe_keys(text: str) -> set[str]:
    """Which social probes the tutor turn is asking."""
    low = text or ""
    found: set[str] = set()
    for key, pat in _PROBE_PATTERNS:
        if pat.search(low):
            found.add(key)
    return found


# Model pasting character-sheet / tool state into the chat (root fault, not UX polish).
# Prefer high-precision markers so normal Spanish/English teach talk never trips this.
_SHEET_LEAK_MARKERS = (
    "active_error_focus",
    "resolved_streak",
    "solid_uses",
    "error_patterns",
    "update_character_sheet",
    "present_estar_person",
)
_SHEET_LEAK_RES = (
    re.compile(r'"confidence"\s*:'),
    re.compile(r'"grammar"\s*:\s*\{'),
    re.compile(r'"skills"\s*:\s*\{'),
    re.compile(r"```\s*json\b", re.I),
)


# --- Phase 4 enforcement (r7 S3, docs/pedagogy-research-r7-association-intro.md §7)
# gate:unscaffolded_new_item (CRITICAL): the model presented an association-
# table key anywhere in the VISIBLE teaching text (all composed parts —
# acknowledge/recast/explain/model/try/continue; widened 2026-07-28 after
# blind-grade defect #2: bare «Mucho gusto» rode the acknowledge part past a
# model/try-only scan) that the ledger + sheet say the learner has NEVER
# seen (not introduced, no lexicon evidence), that is not this turn's
# IntroducePlan key, and that carries no in-reply scaffold (no "(≤6-word
# gloss)" parenthetical right after it, no cognate/keyword anchor text from
# its table entry). Cluster veto (r7 R-F as CODE, not advice): more than one
# unintroduced same-theme key in one reply faults the extras even when
# glossed — one new item per turn; the IntroducePlan key holds its slot.
# gate:regloss (SOFT): an already-introduced key re-glossed with a fresh
# "(english)" parenthetical without a retrieval failure this turn (r7 E2:
# retrieval re-encounters ride WITHOUT re-gloss unless they fail).
#
# gate:unscaffolded_flood (SOFT — Round-2 storm soften, docs/
# reviews-pedagogy-engine-build.md Adjudication Round 2 §2): when >= 3
# DISTINCT bare unscaffolded keys fire on one turn (formulaic-opener
# signature, e.g. hola/cómo estás/bien on a blank sheet), the critical fault
# degrades to this soft note carrying the key list — logged, no forced
# rewrite. Same-theme cluster extras are EXCEPT-ed: they stay CRITICAL
# gate:unscaffolded_new_item at ANY count (the dual-farewell case fires at
# 2 glossed farewells and is untouched). <= 2 bare keys stay CRITICAL.
#
# Pragmatics (never trip): keys already introduced; keys with a durable
# `first_seen` bit (Round-2 AMEND 1c: the tutor already presented them WITH
# an in-reply scaffold — later bare reuse is re-encounter, not naked first
# exposure); keys with ANY sheet lexicon evidence (confidence > 0 — the
# learner has produced/seen them; this subsumes the high-confidence skip);
# keys in the learner's OWN current utterance; entries marked in_pack: false;
# structural paradigm/sequence themes (pronouns, question words, copulas,
# numbers, `hay`) — grammar infrastructure, not lexical introductions; the
# r7 cluster ban targets near-synonym/antonym interference, which paradigms
# and counting sequences are not — plus STRUCTURAL_KEYS, surface forms of
# exempt paradigms the table themes elsewhere (`soy` sits under
# `introductions`; ser/estar conjugations are copula paradigm, Round-2
# AMEND 3 option B). Greetings/how_are_you/farewells themes are NOT
# structural (Grok guardrail — that would gut the dual-farewell block).
# Placement mode is exempt: the blank-sheet feel-out precedes the introduce
# protocol (blank_open_placement freezes the phase clock and the router
# never plans on placement). Without an association table AND a sheet the
# check is disabled entirely.
# Canonical home moved to tutor/association_table.py (Phase 5 batch 2 —
# the sets describe table data; session_memory's topic palette shares them).
# Historical names re-exported here; the semantics are unchanged.
from .association_table import (  # noqa: E402  (re-export façade)
    STRUCTURAL_KEYS,
    STRUCTURAL_THEMES,
)
MAX_NEW_ITEM_GLOSS_WORDS = 6
# >= this many DISTINCT bare unscaffolded keys on one turn → soft flood.
FLOOD_MIN_DISTINCT = 3

def gloss_after_key(key: str, text: str) -> bool:
    """True when the key is immediately followed by a short "(gloss)".

    Markdown emphasis and light punctuation between key and parenthetical are
    tolerated; the parenthetical must respect the ≤6-word micro-gloss law.
    Shared scaffold-evidence detector: used by the unscaffolded-new-item scan
    below AND by conv_session.mark_introduced_if_visible (introduce-move
    evidence, 2026-07-28 false-planted incident) — one definition, no drift."""
    body = phrase_body(key)
    if not body:
        return False
    m = re.search(
        rf"(?<![{SPANISH_LETTERS}]){body}(?:e?s)?[\*_`]*[\s:,–—-]*\(([^)]{{1,80}})\)",
        (text or "").lower(),
    )
    if not m:
        return False
    return len(_ALPHA_TOKEN_RE.findall(m.group(1))) <= MAX_NEW_ITEM_GLOSS_WORDS


def anchor_in_reply(entry: dict, text: str, key: str) -> bool:
    """Cognate/keyword anchor present on the same LINE as ``key``.

    Shared scaffold-evidence detector (same sharing law as gloss_after_key):
    `entry` needs only `cognate_en` / `keyword_en` fields — callers may pass a
    real association-table entry or a plan-payload shim.

    ``key`` is REQUIRED — presence-anywhere is never scaffold evidence
    (2026-07-29 floating-anchor incident; countersign REJECTED the keyless
    fallback: zero remaining callers, and the keyless path IS the founding
    bug). The association forms between anchor and form on one line of
    learner-facing text, or not at all (§2.2 attachment clause / P2).
    """
    from .textnorm import phrase_present

    if not (key or "").strip():
        return False
    for field_name in ("cognate_en", "keyword_en"):
        raw = entry.get(field_name)
        if not raw:
            continue
        head = str(raw).split("(")[0].strip().strip(" .,'\"").lower()
        if not head:
            continue
        for line in (text or "").splitlines():
            if phrase_match(head, line) and phrase_present(key, line):
                return True
    return False


def scan_unscaffolded_new_items(
    parts: dict | None,
    visible: str,
    *,
    table: dict | None,
    sheet: dict | None,
    introduce_key: str | None = None,
    retrieval_failed_keys=None,
    learner_text: str = "",
) -> tuple[list[str], list[str], list[str], dict[str, str]]:
    """(bare_keys, cluster_extra_keys, reglossed_keys, scaffold_saved).

    bare_keys: unintroduced keys presented with NO in-reply scaffold (flood-
    eligible — the caller applies the >=3 soften). cluster_extra_keys: keys
    that carried a scaffold but faulted anyway as same-theme cluster extras
    (r7 R-F as code — ALWAYS critical, any count). scaffold_saved maps keys
    that WOULD have faulted but were saved solely by an in-reply scaffold to
    the scaffold kind ("gloss" | "anchor") — the session writes their durable
    first_seen bit post-turn (Round-2 AMEND 1c).

    Detection scans ALL visible teaching text — the composed learner-facing
    reply (acknowledge/recast/explain/model/try/continue; full visible reply
    when unstructured). Incident 2026-07-28 (blind-grade defect #2): bare
    «¡Mucho gusto, Patrick!» rode the <acknowledge> part while the scan
    looked only at model/try — new items reach the learner from EVERY part.
    Scaffold signals (gloss/anchor) may likewise live anywhere in the
    learner-facing text; the formulaic-storm vector stays covered by the
    >=3-distinct-bare flood soften. Keys present in the learner's OWN
    current utterance are evidence of exposure (the sheet observer only
    records them after the gate runs) and never fault. Pure; see the module
    notes above for the law.
    """
    if not table or not isinstance(sheet, dict):
        return [], [], [], {}
    from .retrieval_scheduler import has_first_seen, is_introduced

    parts = parts or {}
    teach_blob = learner_facing_blob(parts, visible)
    full_blob = teach_blob
    failed = set(retrieval_failed_keys or [])

    hits: list[tuple[int, int, str]] = []
    reglossed: list[str] = []
    for key, entry in table.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("in_pack") is False:
            continue
        if str(entry.get("theme") or "") in STRUCTURAL_THEMES:
            continue
        if key in STRUCTURAL_KEYS:
            # Surface form of an exempt paradigm themed elsewhere (AMEND 3B).
            continue
        if is_introduced(sheet, key, "lexicon"):
            if key not in failed and gloss_after_key(key, full_blob):
                reglossed.append(key)
            continue
        if has_first_seen(sheet, key, "lexicon"):
            # Already presented once WITH scaffold (AMEND 1c): re-encounter,
            # not naked first exposure — bare reuse rides free.
            continue
        lex = (sheet.get("lexicon") or {}).get(key)
        conf = 0.0
        if isinstance(lex, dict):
            try:
                conf = float(lex.get("confidence") or 0.0)
            except (TypeError, ValueError):
                conf = 0.0
        if conf > 0.0:
            # Sheet evidence = the learner has met this key; not "never seen".
            continue
        if learner_text and phrase_match(key, learner_text) is not None:
            # The learner just used it themselves (observer lags the gate).
            continue
        m = phrase_match(key, teach_blob)
        if m is not None:
            hits.append((m.start(), m.end(), key))

    # Overlap filter: «muy bien» must not also count «bien»; the plural-
    # tolerant matcher makes «cómo está» cover «cómo estás» — keep only the
    # longest key over any covered span.
    kept: list[tuple[int, str]] = []
    for s, e, key in hits:
        covered = False
        for s2, e2, key2 in hits:
            if key2 == key:
                continue
            if s2 <= s and e2 >= e and (
                (e2 - s2) > (e - s)
                or ((e2 - s2) == (e - s) and len(key2) > len(key))
            ):
                covered = True
                break
        if not covered:
            kept.append((s, key))
    kept.sort()
    ordered = [k for _, k in kept]

    bare: list[str] = []
    scaffold_saved: dict[str, str] = {}
    for key in ordered:
        entry = table.get(key) or {}
        # Audit (a4) 2026-07-28: the planned introduce_key is checked AFTER
        # the scaffold detectors, not skipped entirely. A planned intro whose
        # scaffold TYPE lapsed (R-A cognate planned, gloss delivered) still
        # exposed the learner to a scaffolded key — record scaffold_saved so
        # the first_seen ledger sees it (no bare fault either way; the
        # introduce path owns the lapse). Skipping the key outright left
        # BOTH ledgers blind → guaranteed critical thrash on next bare use
        # (Grok's encantado proof).
        if gloss_after_key(key, full_blob):
            scaffold_saved[key] = "gloss"
            continue
        if anchor_in_reply(entry, full_blob, key=key):
            scaffold_saved[key] = "anchor"
            continue
        if key == introduce_key:
            continue  # planned key bare: introduce path owns fault/lapse
        bare.append(key)
    # Cluster veto: >1 unintroduced same-theme key in one reply → the extras
    # fault even when glossed (one new item per turn). Bare same-theme keys
    # are already in `bare` (flood-eligible); the veto's distinctive output
    # is the GLOSSED extras, which stay critical at any count.
    by_theme: dict[str, list[str]] = {}
    for key in ordered:
        theme = str((table.get(key) or {}).get("theme") or "")
        by_theme.setdefault(theme, []).append(key)
    cluster_extras: list[str] = []
    for keys in by_theme.values():
        if len(keys) < 2:
            continue
        keep_key = introduce_key if introduce_key in keys else keys[0]
        for key in keys:
            if key != keep_key and key not in bare and key not in cluster_extras:
                cluster_extras.append(key)
    # A glossed key that faulted as a cluster extra was NOT saved.
    for key in cluster_extras:
        scaffold_saved.pop(key, None)
    return bare, cluster_extras, reglossed, scaffold_saved


def detect_sheet_leak(text: str) -> list[str]:
    """Return which sheet/tool dump markers appear in model output (empty = clean)."""
    t = text or ""
    if not t.strip():
        return []
    low = t.lower()
    hits = [m for m in _SHEET_LEAK_MARKERS if m in low]
    for rx in _SHEET_LEAK_RES:
        if rx.search(t):
            hits.append(rx.pattern)
    # De-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def check_output_gate(
    parts: dict | GateContext | None,
    visible: str = "",
    *,
    is_open: bool = False,
    already_asked: set[str] | list[str] | None = None,
    already_shown: set[str] | list[str] | None = None,
    mode: str | None = None,
    image_present: bool = False,
    require_recast: bool = False,
    raw: str | None = None,
    truncated: bool = False,
    association_table: dict | None = None,
    sheet: dict | None = None,
    introduce_key: str | None = None,
    retrieval_failed_keys=None,
    learner_text: str = "",
    blank_zero: bool = False,
    asked_topics=None,
    topic_nouns=None,
) -> OutputGateResult:
    """Hard checks on the composed tutor turn (+ optional per-mode contracts).

    E3 surface (Phase 4 batch 3): pass a single ``GateContext`` as the
    first argument — ``check_output_gate(ctx)``.  The legacy 18-argument
    kwarg signature remains as a thin shim that builds the context; both
    paths funnel into the same implementation, so shim == context by
    construction.

    association_table + sheet (+ this turn's IntroducePlan key and any
    retrieval-failure keys) enable the Phase 4 r7 S3 checks; without both the
    unscaffolded/regloss checks are disabled (e.g. table failed to load).
    blank_zero (threaded from conv_session): the true-zero register overlay
    is active — the english_wall floor drops to ZERO_MIN_SPANISH_RATIO.
    asked_topics + topic_nouns: the session's semantic asked-topic registry
    (SessionMemory) — a composed try whose semantic key was already asked
    faults gate:probe_loop even off the 4 social fast-path regexes.
    """
    if isinstance(parts, GateContext):
        return _check_output_gate(parts)
    return _check_output_gate(GateContext(
        parts=parts,
        visible=visible,
        is_open=is_open,
        already_asked=already_asked,
        already_shown=already_shown,
        mode=mode,
        image_present=image_present,
        require_recast=require_recast,
        raw=raw,
        truncated=truncated,
        association_table=association_table,
        sheet=sheet,
        introduce_key=introduce_key,
        retrieval_failed_keys=retrieval_failed_keys,
        learner_text=learner_text,
        blank_zero=blank_zero,
        asked_topics=asked_topics,
        topic_nouns=topic_nouns,
    ))


def _check_output_gate(gctx: GateContext) -> OutputGateResult:
    """The gate implementation — all inputs ride the GateContext."""
    visible = gctx.visible
    is_open = gctx.is_open
    already_asked = gctx.already_asked
    already_shown = gctx.already_shown
    mode = gctx.mode
    image_present = gctx.image_present
    require_recast = gctx.require_recast
    raw = gctx.raw
    truncated = gctx.truncated
    association_table = gctx.association_table
    sheet = gctx.sheet
    introduce_key = gctx.introduce_key
    retrieval_failed_keys = gctx.retrieval_failed_keys
    learner_text = gctx.learner_text
    blank_zero = gctx.blank_zero
    asked_topics = gctx.asked_topics
    topic_nouns = gctx.topic_nouns

    parts = gctx.parts or {}
    asked = set(already_asked or [])
    shown = set(already_shown or [])
    faults: list[str] = []
    notes: list[str] = []
    mode_l = (mode or "").strip().lower()

    # Reply hit the token cap → shipped text ends mid-sentence. Always critical.
    if truncated:
        faults.append("gate:truncated")
        notes.append("gate:truncated stop_reason=max_tokens")

    # Sheet/tool dump in raw model text = model failure (not silent scrub)
    leak_blob = "\n".join(
        [
            raw or "",
            visible or "",
            *(str(parts.get(k) or "") for k in (
                "acknowledge", "recast", "explain", "model", "try", "continue",
            )),
        ]
    )
    leak_hits = detect_sheet_leak(leak_blob)
    if leak_hits:
        faults.append("gate:sheet_leak")
        notes.append("gate:sheet_leak " + ",".join(leak_hits[:8]))

    ped = evaluate_turn(
        parts,
        is_open=is_open or mode_l == "placement",
        structured=bool(parts.get("structured")),
        visible=visible,
    )
    for v in ped.violations:
        faults.append(v)
    notes.extend(ped.notes)

    # Form error this turn → must expose a short recast (not only soft rewrite in ack)
    if require_recast or mode_l in ("cf_recast", "form_focus"):
        has_recast = bool((parts.get("recast") or "").strip())
        if not has_recast:
            faults.append("gate:missing_recast")
            notes.append("gate:missing_recast")

    # Per-mode contracts (teaching system v2)
    if mode_l == "association" and not image_present:
        # Soft: prefer image; do not hard-fail if cache miss (warm later)
        notes.append("mode:association_no_image_cache")
    if mode_l == "form_focus":
        has_contrast = bool(
            (parts.get("explain") or "").strip()
            or (parts.get("recast") or "").strip()
            or (parts.get("model") or "").strip()
        )
        if not has_contrast:
            faults.append("gate:form_focus_needs_model")
            notes.append("gate:form_focus_needs_model")
    if mode_l == "comprehension_check":
        try_t = (parts.get("try") or parts.get("continue") or "").lower()
        if not any(x in try_t for x in ("?", "¿", " o ", "sí", "si", "no")):
            faults.append("gate:comprehension_needs_check")
            notes.append("gate:comprehension_needs_check")

    # English wall on learner-facing text (model+try+ack+recast+explain).
    # Spec 2026-07-26: critical iff ratio < 0.50 AND >= 12 alphabetic tokens;
    # short L1 sandwich in <explain> excluded from the ratio (<= 6 non-ES words).
    full_blob = learner_facing_blob(parts, visible)
    ratio = spanish_token_ratio(ratio_blob_with_sandwich_exempt(parts, visible))
    n_alpha = alphabetic_token_count(full_blob)
    notes.append(f"tl_ratio={ratio:.2f}")
    # True-zero exemption (2026-07-28 incident): placement opens and
    # blank_zero overlay turns REQUIRE English orientation — the wall floor
    # drops to 0.25 there so a compliant glossed opening passes while a
    # genuinely all-English turn (ratio ≈ 0) still faults in every mode.
    min_ratio = (
        ZERO_MIN_SPANISH_RATIO
        if (mode_l == "placement" or blank_zero)
        else MIN_SPANISH_RATIO
    )
    if n_alpha >= MIN_ALPHA_TOKENS and ratio < min_ratio:
        faults.append("gate:english_wall")
        notes.append(f"gate:english_wall ratio={ratio:.2f}<{min_ratio}")

    # Phase 4 enforcement (r7 S3): naked first exposures + cluster veto +
    # re-gloss. Placement (blank feel-out) precedes the introduce protocol.
    # Round-2 storm soften: >= FLOOD_MIN_DISTINCT bare keys degrade to SOFT
    # gate:unscaffolded_flood; same-theme cluster extras stay CRITICAL at
    # any count (dual-farewell block untouched).
    unscaffolded: list[str] = []
    flood_keys: list[str] = []
    reglossed: list[str] = []
    scaffold_saved: dict[str, str] = {}
    if association_table and isinstance(sheet, dict) and mode_l != "placement":
        bare, cluster_extras, reglossed, scaffold_saved = (
            scan_unscaffolded_new_items(
                parts,
                visible,
                table=association_table,
                sheet=sheet,
                introduce_key=introduce_key,
                retrieval_failed_keys=retrieval_failed_keys,
                learner_text=learner_text,
            )
        )
        if len(bare) >= FLOOD_MIN_DISTINCT:
            flood_keys = list(bare)
        else:
            unscaffolded = list(bare)
        unscaffolded += [k for k in cluster_extras if k not in unscaffolded]
        if unscaffolded:
            faults.append("gate:unscaffolded_new_item")
            notes.append(
                "gate:unscaffolded_new_item " + ",".join(unscaffolded[:8])
            )
        if flood_keys:
            faults.append("gate:unscaffolded_flood")
            notes.append(
                "gate:unscaffolded_flood " + ",".join(flood_keys[:8])
            )
        if reglossed:
            faults.append("gate:regloss")
            notes.append("gate:regloss " + ",".join(reglossed[:8]))

    # Loop: tutor re-asks a probe we already asked OR they already answered
    probe_blob = " ".join(
        str(parts.get(k) or "") for k in ("try", "continue", "model", "acknowledge")
    )
    probes = detect_tutor_probe_keys(probe_blob)
    loop_hits: list[str] = []
    for p in probes:
        if p in asked:
            loop_hits.append(p)
        # They already showed the skill this session
        skill_map = {
            "ask_how": "estoy",
            "ask_name": "name",
            "ask_origin": "origin",
            "ask_gusta": "gusta",
        }
        sk = skill_map.get(p)
        if sk and sk in shown:
            loop_hits.append(f"{p}/shown:{sk}")
    # Registry check (2026-07-28 repetition forensics): the composed try's
    # semantic key — same extractor that writes SessionMemory.asked_topics —
    # already asked this session ⇒ probe loop on ANY topic, not only the 4
    # social fast-path regexes (turn-4/5 city-size re-ask escaped them).
    if asked_topics:
        from .session_memory import compose_topic_key, topic_key_for_try

        try_txt = str(parts.get("try") or parts.get("continue") or "")
        frame, concept = topic_key_for_try(try_txt, nouns=topic_nouns)
        topic_key = compose_topic_key(frame, concept)
        if topic_key and topic_key in set(asked_topics):
            # Audit (a2) 2026-07-28 — retrieval > anti-repeat: a currently-
            # due concept may be re-elicited even if this frame+concept was
            # asked earlier this session (P3 spacing is law; do_not_re_ask
            # is a courtesy). Ledger keys keep their accents («café»); the
            # extractor deaccents its concept — compare through the same
            # textnorm.fold_lexical transform (exact key match otherwise).
            concept_due = False
            if concept and isinstance(sheet, dict):
                from .retrieval_scheduler import due_items

                due_keys = {
                    fold_lexical(d.key) for d in due_items(sheet, max_due=50)
                }
                concept_due = concept in due_keys
            if concept_due:
                notes.append(f"probe_loop_due_exempt:{topic_key}")
            else:
                loop_hits.append(f"topic:{topic_key}")
    if loop_hits:
        faults.append("gate:probe_loop")
        notes.append("gate:probe_loop " + ",".join(sorted(set(loop_hits))))

    ok = not faults
    # Diagnostic only — auto-rewrite path DELETED 2026-08-01 (never hide failures).
    diagnosis = (
        f"GATE FAIL (visible, not rewritten): {', '.join(faults)}"
        if faults else ""
    )

    return OutputGateResult(
        ok=ok,
        faults=faults,
        notes=notes,
        spanish_ratio=ratio,
        repair_instruction=diagnosis,
        scaffold_saved=scaffold_saved,
        flood_keys=flood_keys,
    )
