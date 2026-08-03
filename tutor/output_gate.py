"""Output gate — PLUMBING ONLY (S11, USER-ruled 2026-08-03).

The gate audits the *tutor output* for failures only code can judge:

  - gate:truncated  — the provider cut the reply (stop_reason=max_tokens);
    shipped text ends mid-sentence.
  - gate:sheet_leak — internal character-sheet / tool JSON leaked into
    learner-visible text.

That is the whole fault vocabulary.  Every teaching-opinion check the gate
used to run — cluster veto, probe loop, english wall, the pedagogy-contract
shape faults, unscaffolded/regloss advisories — was DELETED from the runtime
(S11, docs/reviews-full-code-audit-20260803.md; §4.6: git is the archive)
and lives ONLY as eval test cases over AI-student transcripts
(evals/student_checks.py).  The teaching rules themselves are unchanged in
PEDAGOGY §2 — the model still receives them; evals judge whether pedagogy +
prompts are working.

What survives BESIDE the two faults is bookkeeping, not judgment:

  - the first-exposure scan (``scan_first_exposures``) still produces the
    ``scaffold_saved`` exposure map — every not-yet-introduced
    association-table key the tutor visibly used this turn, mapped to its
    scaffold-evidence kind ("gloss" | "anchor" | "image" | "bare").  The
    session writes durable first_seen bits post-turn
    (turn_pipeline.stage_first_seen).  Exposure only, never ability, never
    a fault.
  - ``gloss_after_key`` / ``anchor_in_reply`` — the shared scaffold-evidence
    detectors (also used by conv_session.introduce_scaffold_evidence; one
    definition, no drift).

Faults ship raw + visible (no-hide, 2026-08-01): the gate never rewrites,
strips, or blanks a reply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Phase 2 (docs/reviews-architecture-refactor.md): boundary matching + the
# lexical fold come from the shared textnorm module.
from .textnorm import SPANISH_LETTERS, phrase_body, phrase_match


@dataclass
class OutputGateResult:
    ok: bool
    faults: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    repair_instruction: str = ""
    # Exposure-ledger map (bookkeeping — survives S11): not-yet-introduced
    # keys visibly presented this turn, mapped to the evidence kind —
    # "gloss" | "anchor" | "image" (scaffolded) or "bare" (naked use).
    # The session writes their durable first_seen bit post-turn
    # (stage_first_seen).  Exposure only — never ability evidence.
    scaffold_saved: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "faults": list(self.faults),
            "notes": list(self.notes),
            "repair_instruction": self.repair_instruction,
            "scaffold_saved": dict(self.scaffold_saved),
        }


@dataclass
class GateContext:
    """E3 (Phase 4 batch 3, docs/reviews-architecture-refactor.md): the
    gate's full input surface as ONE typed object.  ``check_output_gate
    (ctx)`` is the surface; the legacy kwarg call remains as a thin shim
    that builds this context, so gate tests keep their call shape.

    S11 (2026-08-03): the fields only teaching checks read died with those
    checks — is_open / already_asked / introduce_key /
    retrieval_failed_keys / blank_zero / asked_topics / topic_nouns are
    GONE.  What remains feeds the two plumbing checks and the exposure
    scan:

    - ``parts``/``visible``/``raw``: the parsed tutor reply under test.
    - ``truncated``: per-attempt truncation flag (stop_reason=max_tokens).
    - ``association_table``/``sheet``: exposure-scan inputs.
    - ``learner_text``: keys in the learner's OWN current utterance are
      their exposure, not the tutor's (the observer lags the gate).
    - ``image_concepts``: teach-image concepts attached this turn (a
      same-turn image for a key counts as its scaffold kind).
    """

    # -- per-attempt: the reply under test -----------------------------------
    parts: dict | None = None
    visible: str = ""
    raw: str | None = None
    truncated: bool = False
    # -- turn-constant context ----------------------------------------------
    image_concepts: Any = None
    association_table: dict | None = None
    sheet: dict | None = None
    learner_text: str = ""


_ALPHA_TOKEN_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+")


def learner_facing_blob(parts: dict | None, visible: str) -> str:
    """The composed learner-facing text (all visible teaching parts)."""
    parts = parts or {}
    blob = " ".join(
        str(parts.get(k) or "")
        for k in ("acknowledge", "recast", "explain", "model", "try", "continue")
    )
    if not blob.strip():
        blob = visible or ""
    return blob


# Model pasting character-sheet / tool state into the chat (root fault, not UX polish).
# Prefer high-precision markers so normal Spanish/English teach talk never trips this.
_SHEET_LEAK_MARKERS = (
    "active_error_focus",
    "resolved_streak",
    "solid_uses",
    "error_patterns",
    "present_estar_person",
)
_SHEET_LEAK_RES = (
    re.compile(r'"confidence"\s*:'),
    re.compile(r'"grammar"\s*:\s*\{'),
    re.compile(r'"skills"\s*:\s*\{'),
    re.compile(r"```\s*json\b", re.I),
    # The tool name counts ONLY in a JSON-/call-ish context (gate retune
    # 2026-08-03): the system prompt itself teaches the model the term
    # `update_character_sheet`, so a prose mention is not a sheet dump —
    # quoted/braced or followed by call/JSON punctuation is.
    re.compile(
        r"[\"'{\[]\s*update_character_sheet"
        r"|update_character_sheet\s*[\"':,({]"
    ),
)


# --- First-exposure scan (bookkeeping; the fault half died with S11) --------
#
# Exposure ledger (gate retune 2026-08-03, Grok AMEND 2a — the surviving
# half): EVERY not-yet-introduced association-table key the tutor visibly
# used this turn lands in scaffold_saved with its evidence kind; the session
# writes durable first_seen bits post-turn, so a bare-but-used key is never
# forgotten (the «bien» fired-5× pathology).  Exposure only, never ability.
#
# Pragmatics (never recorded): keys already introduced; keys with a durable
# `first_seen` bit; keys with ANY sheet lexicon evidence (confidence > 0);
# keys in the learner's OWN current utterance; entries marked
# in_pack: false; structural paradigm/sequence themes (pronouns, question
# words, copulas, numbers, `hay`) plus STRUCTURAL_KEYS surface forms
# (Round-2 AMEND 3B).  Without an association table AND a sheet the scan is
# disabled entirely.  Canonical home of the structural sets is
# tutor/association_table.py (Phase 5 batch 2).
from .association_table import (  # noqa: E402  (re-export façade)
    STRUCTURAL_KEYS,
    STRUCTURAL_THEMES,
)
MAX_NEW_ITEM_GLOSS_WORDS = 6

def gloss_after_key(key: str, text: str) -> bool:
    """True when the key is immediately followed by a short "(gloss)".

    Markdown emphasis and light punctuation between key and parenthetical are
    tolerated; the parenthetical must respect the ≤6-word micro-gloss law.
    Shared scaffold-evidence detector: used by the first-exposure scan
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


def scan_first_exposures(
    parts: dict | None,
    visible: str,
    *,
    table: dict | None,
    sheet: dict | None,
    learner_text: str = "",
    image_concepts=None,
) -> dict[str, str]:
    """The exposure map: not-yet-introduced keys visibly used this turn →
    evidence kind ("gloss" | "anchor" | "image" | "bare").

    Bookkeeping only (S11): no faults are derived here — the session writes
    durable first_seen bits post-turn so exposure is never forgotten.

    Detection scans ALL visible teaching text — the composed learner-facing
    reply (acknowledge/recast/explain/model/try/continue; full visible reply
    when unstructured). Incident 2026-07-28 (blind-grade defect #2): bare
    «¡Mucho gusto, Patrick!» rode the <acknowledge> part while the scan
    looked only at model/try — new items reach the learner from EVERY part.
    Keys present in the learner's OWN current utterance are evidence of
    exposure (the sheet observer only records them after the gate runs) and
    are not recorded as tutor exposure. Pure; see the module notes above.
    """
    if not table or not isinstance(sheet, dict):
        return {}
    from .retrieval_scheduler import has_first_seen, is_introduced
    from .textnorm import fold_asset_key

    parts = parts or {}
    teach_blob = learner_facing_blob(parts, visible)
    full_blob = teach_blob
    img_concepts = {str(c) for c in (image_concepts or []) if c}

    hits: list[tuple[int, int, str]] = []
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
            continue
        if has_first_seen(sheet, key, "lexicon"):
            # Already presented once (AMEND 1c): re-encounter, not a first
            # exposure — nothing to record.
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

    scaffold_saved: dict[str, str] = {}
    for _pos, key in kept:
        entry = table.get(key) or {}
        if gloss_after_key(key, full_blob):
            scaffold_saved[key] = "gloss"
            continue
        if anchor_in_reply(entry, full_blob, key=key):
            scaffold_saved[key] = "anchor"
            continue
        if fold_asset_key(key) in img_concepts or key in img_concepts:
            # AMEND 2b: a same-turn attached teach image for the key IS a
            # scaffold (dual-coding delivered).
            scaffold_saved[key] = "image"
            continue
        # AMEND 2a: bare use is STILL exposure — the ledger records it so
        # the key is never treated as unseen again.
        scaffold_saved[key] = "bare"
    return scaffold_saved


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
    raw: str | None = None,
    truncated: bool = False,
    association_table: dict | None = None,
    sheet: dict | None = None,
    learner_text: str = "",
    image_concepts=None,
) -> OutputGateResult:
    """Plumbing checks on the composed tutor turn (S11: truncated +
    sheet_leak only) plus the first-exposure scan.

    E3 surface (Phase 4 batch 3): pass a single ``GateContext`` as the
    first argument — ``check_output_gate(ctx)``.  The legacy kwarg
    signature remains as a thin shim that builds the context; both paths
    funnel into the same implementation.

    association_table + sheet enable the exposure scan; without both the
    scan is disabled (e.g. table failed to load) and scaffold_saved is
    empty.
    """
    if isinstance(parts, GateContext):
        return _check_output_gate(parts)
    return _check_output_gate(GateContext(
        parts=parts,
        visible=visible,
        raw=raw,
        truncated=truncated,
        association_table=association_table,
        sheet=sheet,
        learner_text=learner_text,
        image_concepts=image_concepts,
    ))


def _check_output_gate(gctx: GateContext) -> OutputGateResult:
    """The gate implementation — all inputs ride the GateContext."""
    visible = gctx.visible
    raw = gctx.raw
    parts = gctx.parts or {}
    faults: list[str] = []
    notes: list[str] = []

    # Reply hit the token cap → shipped text ends mid-sentence. Always critical.
    if gctx.truncated:
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

    # First-exposure bookkeeping (never a fault — S11).
    scaffold_saved: dict[str, str] = {}
    if gctx.association_table and isinstance(gctx.sheet, dict):
        scaffold_saved = scan_first_exposures(
            parts,
            visible,
            table=gctx.association_table,
            sheet=gctx.sheet,
            learner_text=gctx.learner_text,
            image_concepts=gctx.image_concepts,
        )

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
        repair_instruction=diagnosis,
        scaffold_saved=scaffold_saved,
    )
